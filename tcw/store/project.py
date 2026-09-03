"""Filesystem implementation of the storage-neutral project registry."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from tcw.store.base import (
    Project, ProjectRegistry, UnreachableProject, WORK_STATUSES,
)

SENTINEL = "tcw-config.yaml"
PROJECT_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RESERVED_PROJECT_IDS = {"t", "c", "w", "local", *WORK_STATUSES}


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _unique_mapping(loader: yaml.SafeLoader, node: yaml.MappingNode) -> dict:
    mapping: dict = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if key in mapping:
            raise yaml.YAMLError(f"duplicate key: {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=True)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping
)


def validate_project_id(project_id: str) -> str:
    value = (project_id or "").strip()
    if not PROJECT_ID_PATTERN.fullmatch(value):
        raise ValueError(
            "project ID must match ^[a-z0-9]+(?:-[a-z0-9]+)*$"
        )
    if value in RESERVED_PROJECT_IDS:
        raise ValueError(f"project ID is reserved: {value}")
    return value


# A CLI invocation never outlives the process, and a graph walk re-probes the
# same handful of directories, so an unbounded module-level dict is the right
# cache here — don't "fix" it into an LRU.
_ANCHOR_CACHE: dict[Path, tuple[Path, Path] | None] = {}


def worktree_anchors(directory: Path) -> tuple[Path, Path] | None:
    """`(current worktree top, main worktree root)` when `directory` sits inside a
    *linked* git worktree, else None — None for git absent, not a repository, the
    primary checkout, a bare main repo, or any git failure. Never raises.

    Lives here rather than beside `git_root` in `fs.py`: `fs.py` imports this
    module, so the reverse import would be circular. It is a filesystem-adapter
    private detail — `ProjectRegistry` exposes no path-resolution operation.
    """
    key = directory.resolve()
    if key not in _ANCHOR_CACHE:
        _ANCHOR_CACHE[key] = _probe_worktree(key)
    return _ANCHOR_CACHE[key]


def _probe_worktree(directory: Path) -> tuple[Path, Path] | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(directory), "rev-parse", "--path-format=absolute",
             "--show-toplevel", "--git-common-dir"],
            capture_output=True, text=True, check=True,
            stdin=subprocess.DEVNULL,      # reads no input; see tcw/store/fs.py::_git
            # splitlines(), NOT split(): git emits one path per line, and a repo
            # path containing a space (`~/My Drive`, `~/Google Drive`) would split
            # into more than two tokens, trip the guard below, and silently
            # disable worktree resolution for that user.
        ).stdout.splitlines()
    except (subprocess.CalledProcessError, OSError):   # OSError covers git absent
        return None
    if len(out) != 2:
        return None
    top, common = Path(out[0]).resolve(), Path(out[1]).resolve()
    # A normal repo's common dir is `<main>/.git`; a *bare* main repo's is the
    # bare directory itself, whose parent is not a worktree at all. Re-anchoring
    # against that parent would be nonsense, so treat bare as "no anchors".
    if common.name != ".git":
        return None
    main = common.parent
    return None if main == top else (top, main)


@dataclass(frozen=True)
class _Config:
    project: Project
    path: Path
    parent: dict[str, str]
    children: dict[str, str]
    raw: dict[str, Any]


class FsProjectRegistry(ProjectRegistry):
    """A project graph loaded solely by following declared config locators."""

    def __init__(self, node_root: Path):
        self.node_root = node_root.resolve()
        self._cache: dict[Path, _Config] = {}
        self._by_id: dict[str, _Config] = {}
        self._problems: list[str] = []
        self._unreachable: list[UnreachableProject] = []
        self._visiting: set[Path] = set()
        self._loaded = False
        self._current_path = self.node_root / SENTINEL
        # Probed once per registry, not once per locator (~8 ms a call).
        self._anchors = worktree_anchors(self.node_root)
        # The current node's config as the *main* worktree spells it — the one
        # path Rule 2 aliases onto the worktree copy. None outside a worktree.
        self._counterpart_path = (
            None if self._anchors is None
            else (self._anchors[1] / self.node_root.relative_to(self._anchors[0])
                  / SENTINEL).resolve()
        )

    @classmethod
    def open(cls, node_root: Path) -> "FsProjectRegistry":
        registry = cls(node_root)
        registry._load_graph()
        return registry

    @property
    def current(self) -> Project:
        cfg = self._cache.get(self._current_path.resolve())
        if cfg is None:
            raise ValueError(self._problems[0] if self._problems else "invalid project registry")
        return cfg.project

    def get(self, project_id: str) -> Project | None:
        cfg = self._by_id.get(project_id)
        return cfg.project if cfg else None

    def parent(self, project_id: str | None = None) -> Project | None:
        cfg = self._config_for(project_id)
        if not cfg or not cfg.parent:
            return None
        parent_id = next(iter(cfg.parent))
        return self.get(parent_id)

    def children(self, project_id: str | None = None) -> list[Project]:
        cfg = self._config_for(project_id)
        if not cfg:
            return []
        return [
            self._by_id[child_id].project
            for child_id in cfg.children
            if child_id in self._by_id
        ]

    def ancestors(self, project_id: str | None = None) -> list[Project]:
        result: list[Project] = []
        seen: set[str] = set()
        current = self.parent(project_id)
        while current and current.id not in seen:
            result.append(current)
            seen.add(current.id)
            current = self.parent(current.id)
        return result

    def descendants(self, project_id: str | None = None) -> list[Project]:
        result: list[Project] = []

        def visit(parent_id: str) -> None:
            for child in self.children(parent_id):
                result.append(child)
                visit(child.id)

        cfg = self._config_for(project_id)
        if cfg:
            visit(cfg.project.id)
        return result

    def check(self) -> list[str]:
        return list(self._problems)

    def unreachable(self) -> list[UnreachableProject]:
        return list(self._unreachable)

    def require_valid(self) -> "FsProjectRegistry":
        if self._problems:
            raise ValueError("; ".join(self._problems))
        return self

    def config(self, project_id: str | None = None) -> dict[str, Any]:
        cfg = self._config_for(project_id)
        return dict(cfg.raw) if cfg else {}

    def _config_for(self, project_id: str | None) -> _Config | None:
        if project_id is None:
            return self._cache.get(self._current_path.resolve())
        return self._by_id.get(project_id)

    def _load_graph(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        self._visit(self._current_path.resolve(), declared_id=None)
        self._validate_reciprocity()
        self._validate_cycles()

    def _visit(self, config_path: Path, declared_id: str | None,
               declared_in: Path | None = None) -> _Config | None:
        config_path = config_path.resolve()
        if config_path in self._cache:
            cfg = self._cache[config_path]
            if declared_id and cfg.project.id != declared_id:
                self._problem(
                    config_path,
                    f"registered key '{declared_id}' does not match target id '{cfg.project.id}'",
                )
            return cfg
        if config_path in self._visiting:
            self._problem(config_path, "cycle in connected-projects")
            return None
        self._visiting.add(config_path)
        try:
            cfg = self._read_config(config_path, declared_id, declared_in)
            if cfg is None:
                return None
            self._cache[config_path] = cfg
            previous = self._by_id.get(cfg.project.id)
            if previous and previous.path != config_path:
                self._problem(
                    config_path,
                    f"duplicate project id '{cfg.project.id}' also used by {previous.path}",
                )
            else:
                self._by_id[cfg.project.id] = cfg
            for child_id, locator in cfg.children.items():
                self._visit(self._target_path(config_path, locator), child_id,
                            config_path)
            for parent_id, locator in cfg.parent.items():
                self._visit(self._target_path(config_path, locator), parent_id,
                            config_path)
            return cfg
        finally:
            self._visiting.discard(config_path)

    def _read_config(self, path: Path, declared_id: str | None,
                     declared_in: Path | None = None) -> _Config | None:
        if not path.is_file():
            # Not a defect. A locator is a fact about one machine — the same
            # thing `work.path` is — so a target that is not here means this
            # checkout does not have that project, not that the declaration
            # is wrong. Failing closed here refused every command in exactly
            # the checkouts that have only some of a graph's repositories.
            # Everything else below stays an error: those targets are present
            # and wrong, which is what fail-closed was written for.
            self._unreachable_edge(declared_in or path, declared_id, path.parent)
            return None
        try:
            raw = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader) or {}
        except (OSError, yaml.YAMLError) as error:
            self._problem(path, f"invalid YAML: {error}")
            return None
        if not isinstance(raw, dict):
            self._problem(path, "config must be a mapping")
            return None
        project_id = raw.get("id")
        if not isinstance(project_id, str) or not project_id.strip():
            self._problem(
                path,
                "missing project id; migrate with `tcw init --id <project-id>`",
            )
            return None
        try:
            project_id = validate_project_id(project_id)
        except ValueError as error:
            self._problem(path, str(error))
            return None
        if declared_id and declared_id != project_id:
            self._problem(
                path,
                f"registered key '{declared_id}' does not match target id '{project_id}'",
            )
        connected = raw.get("connected-projects")
        if connected is None:
            connected = {}
        if not isinstance(connected, dict):
            self._problem(path, "connected-projects must be a mapping")
            connected = {}
        unknown = set(connected) - {"parent", "children"}
        if unknown:
            self._problem(path, f"unknown connected-projects keys: {', '.join(sorted(unknown))}")
        children = self._relation(path, connected.get("children"), "children")
        parent = self._relation(path, connected.get("parent"), "parent")
        if len(parent) > 1:
            self._problem(path, "connected-projects.parent must contain at most one entry")
        return _Config(
            project=Project(project_id, path.parent),
            path=path,
            parent=parent,
            children=children,
            raw=raw,
        )

    def _relation(self, path: Path, value: Any, label: str) -> dict[str, str]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            self._problem(path, f"connected-projects.{label} must be a mapping")
            return {}
        result: dict[str, str] = {}
        for project_id, locator in value.items():
            try:
                valid_id = validate_project_id(project_id if isinstance(project_id, str) else "")
            except ValueError as error:
                self._problem(path, f"{label} key: {error}")
                continue
            if not isinstance(locator, str) or not locator.strip():
                self._problem(path, f"locator for '{valid_id}' must be a nonempty string")
                continue
            result[valid_id] = locator
        return result

    def _target_path(self, source_config: Path, locator: str) -> Path:
        target = Path(locator)
        source_dir = source_config.parent.resolve()
        resolved = (
            (target if target.is_absolute() else source_dir / target) / SENTINEL
        ).resolve()
        if self._anchors is None:
            return resolved
        top, main = self._anchors
        # Rule 1 — re-anchor only on escape, and only a *relative* locator: an
        # absolute one names a place, not an offset from the config. A target
        # that stays inside the worktree is a sibling node on the same branch and
        # belongs to the worktree (this is what keeps multi-project-in-one-repo
        # working). Only a target that leaves the checkout was authored against
        # the primary checkout's position on disk, so resolve it against the
        # source directory's counterpart under the main worktree root instead.
        if (
            not target.is_absolute()
            and source_dir.is_relative_to(top)
            and not resolved.parent.is_relative_to(top)
        ):
            counterpart = main / source_dir.relative_to(top)
            resolved = (counterpart / target / SENTINEL).resolve()
        # Rule 2 — collapse the worktree's own identity. Once the parent is
        # reachable it points back at the current node as the *main* worktree
        # spells it, so the graph would hold two configs under one ID and fail
        # reciprocity. Alias that one path onto the worktree copy, so the graph
        # holds exactly one node for the current project — the checked-out one.
        # Exactly one pair, only under a linked worktree: a wider alias would
        # mask genuine duplicate-ID errors, which is a real validation here.
        # Applies to absolute locators too — the parent may name the current node
        # by absolute path, and that path is the counterpart just the same.
        if resolved == self._counterpart_path:
            return self._current_path.resolve()
        return resolved

    def _validate_reciprocity(self) -> None:
        for cfg in self._cache.values():
            for child_id, locator in cfg.children.items():
                child_path = self._target_path(cfg.path, locator)
                child = self._cache.get(child_path)
                if child is None:
                    continue
                reciprocal = child.parent.get(cfg.project.id)
                if reciprocal is None:
                    self._problem(
                        child.path,
                        f"nonreciprocal connection: parent '{cfg.project.id}' is not declared",
                    )
                elif self._points_elsewhere(child.path, reciprocal, cfg.path):
                    self._problem(
                        child.path,
                        f"parent locator for '{cfg.project.id}' does not point back to {cfg.path.parent}",
                    )
                if child.project.id != child_id:
                    self._problem(
                        child.path,
                        f"registered key '{child_id}' does not match target id '{child.project.id}'",
                    )
            for parent_id, locator in cfg.parent.items():
                parent_path = self._target_path(cfg.path, locator)
                parent = self._cache.get(parent_path)
                if parent is None:
                    continue
                reciprocal = parent.children.get(cfg.project.id)
                if reciprocal is None:
                    self._problem(
                        parent.path,
                        f"nonreciprocal connection: child '{cfg.project.id}' is not declared",
                    )
                elif self._points_elsewhere(parent.path, reciprocal, cfg.path):
                    self._problem(
                        parent.path,
                        f"child locator for '{cfg.project.id}' does not point back to {cfg.path.parent}",
                    )
                if parent.project.id != parent_id:
                    self._problem(
                        parent.path,
                        f"registered key '{parent_id}' does not match target id '{parent.project.id}'",
                    )

    def _points_elsewhere(self, source_config: Path, locator: str,
                          expected: Path) -> bool:
        """Whether `locator`, read from `source_config`, names a node other than
        `expected` — as far as this machine can tell.

        An **absent** target cannot answer the question and must not be read as
        "no". Two nodes routinely name each other at paths that exist only on the
        machine whose author wrote them: a monorepo nested inside an orchestrator
        on one disk and cloned beside it on another. Comparing a path that is
        here against a path that is not decides nothing, and deciding it against
        the declaration made every such pair non-reciprocal — the failure that
        made a provisioned parent unusable.

        Where both are present the comparison is real and the check is unchanged;
        the ids already agreed, or the caller would not have got this far.
        """
        target = self._target_path(source_config, locator)
        if not target.is_file():
            return False
        return target != expected

    def _validate_cycles(self) -> None:
        visited: set[str] = set()
        active: set[str] = set()

        def visit(project_id: str) -> None:
            if project_id in active:
                cfg = self._by_id.get(project_id)
                self._problem(
                    cfg.path if cfg else self._current_path,
                    f"cycle in connected-projects involving '{project_id}'",
                )
                return
            if project_id in visited:
                return
            visited.add(project_id)
            active.add(project_id)
            cfg = self._by_id.get(project_id)
            if cfg:
                for child_id in cfg.children:
                    visit(child_id)
            active.remove(project_id)

        for project_id in list(self._by_id):
            visit(project_id)

    def _problem(self, path: Path, message: str) -> None:
        rendered = f"{path}: {message}"
        if rendered not in self._problems:
            self._problems.append(rendered)

    def _unreachable_edge(self, config_path: Path, project_id: str | None,
                          locator: Path) -> None:
        """Record a declared project that is not here, rather than a problem.

        `project_id` is the key the declaring config used. It can be None only
        for the current node's own config, which is never an edge — the guard is
        here so a future caller cannot record a nameless entry that no message
        could ever render.
        """
        if not project_id:
            return
        entry = UnreachableProject(id=project_id, locator=locator,
                                   declared_in=config_path)
        if entry not in self._unreachable:
            self._unreachable.append(entry)

    def unreachable_project(self, project_id: str) -> UnreachableProject | None:
        """The recorded entry for `project_id`, or None.

        The lookup every "declared but not here" message needs: a caller holding
        an id that `get()` answered None for asks this before deciding which
        message to print.
        """
        self._load_graph()
        return next((u for u in self._unreachable if u.id == project_id), None)
