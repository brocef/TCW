"""Filesystem implementation of the storage-neutral project registry."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import yaml

from tcw.store.base import (
    ConnectedProject, Project, ProjectOverride, ProjectRegistry,
    RepositoryDeclaration, StoreDeclarationError, UnreachableProject,
    WORK_STATUSES, parse_connected_entry,
)
from tcw.store.checkouts import normalized_url, provisioned_root

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


def override_variable(project_id: str) -> str:
    """The environment variable that says where `project_id` lives on this machine.

    The id, uppercased, with `-` as `_`: `proposit-core` →
    `TCW_PROJECT_PROPOSIT_CORE`. **Node ids, not repository names** — the two are
    routinely different, and a workspace where they are crossed is what this
    mapping is most often got wrong against.

    Injective, and only because `PROJECT_ID_PATTERN` admits neither an
    underscore nor an uppercase letter: with either allowed, `a_b` or `A-b` would
    claim the same variable as `a-b`. `test_invalid_or_reserved_project_ids`
    holds that guarantee, so this function may not be given a laxer id.

    `TCW_PROJECT_` cannot collide with `TCW_WORK_OWNER`, the existing precedent
    for this shape — an environment supplying a machine fact no shared config
    can carry, read as one rung of an ordered fallback.
    """
    return "TCW_PROJECT_" + project_id.upper().replace("-", "_")


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


def _config_file(path: Path) -> Path:
    """A `tcw-config.yaml` path with its folder resolved and the file itself not
    followed. A symlinked config belongs to the folder it sits in: that folder
    is the node, and its relative locators are read from there — resolving the
    file took them from wherever the link pointed."""
    return path.parent.resolve() / path.name


def _git_lines(directory: Path, *args: str) -> list[str] | None:
    """`git -C directory <args>`'s output lines, or None on any failure."""
    try:
        return subprocess.run(
            ["git", "-C", str(directory), *args],
            capture_output=True, text=True, check=True,
            stdin=subprocess.DEVNULL,      # reads no input; see tcw/store/fs.py::_git
            # splitlines(), NOT split(): git emits one path per line, and a repo
            # path containing a space (`~/My Drive`, `~/Google Drive`) would split
            # into more than two tokens and silently disable worktree resolution.
        ).stdout.splitlines()
    except (subprocess.CalledProcessError, OSError):   # OSError covers git absent
        return None


def _probe_worktree(directory: Path) -> tuple[Path, Path] | None:
    out = _git_lines(directory, "rev-parse", "--path-format=absolute",
                     "--show-toplevel", "--git-common-dir")
    if not out or len(out) != 2:
        return None
    top, common = Path(out[0]).resolve(), Path(out[1]).resolve()
    if common.name == ".git":
        main = common.parent
    else:
        # A repository that is itself a submodule keeps its git dir at
        # `<outer>/.git/modules/<name>`, and records its checkout as
        # `core.worktree`, relative to that dir. A *bare* repo records none and
        # is not a worktree at all, so it gives no anchors.
        worktree = _git_lines(common, "--git-dir", str(common), "config", "--get",
                              "core.worktree")
        if not worktree:
            return None
        main = (common / worktree[0]).resolve()
    if main != top:
        return top, main
    # Not a linked worktree of its own repository. A submodule checked out in a
    # superproject's linked worktree is its own repository, checked out right
    # there; the worktree that matters is the superproject's.
    outer = _git_lines(directory, "rev-parse", "--show-superproject-working-tree")
    return worktree_anchors(Path(outer[0])) if outer else None


@dataclass(frozen=True)
class _Config:
    project: Project
    path: Path
    parent: dict[str, ConnectedProject]
    children: dict[str, ConnectedProject]
    upstream: dict[str, ConnectedProject]
    raw: dict[str, Any]


def _same_repository(marker: Path, main: Path) -> bool:
    """Whether a directory holding `marker` (its `.git`) is still the repository
    whose main worktree is `main`: no marker, or a submodule of it — a `.git`
    file whose `gitdir:` lies inside `main/.git`, which is the commit this
    branch pins. A `.git` directory, or a file pointing anywhere else, is a
    separate repository nested here."""
    if not marker.exists():
        return True
    if not marker.is_file():
        return False
    try:
        first = marker.read_text(encoding="utf-8").splitlines()[0]
    except (OSError, UnicodeDecodeError, IndexError):
        return False
    if not first.startswith("gitdir:"):
        return False
    gitdir = (marker.parent / first[len("gitdir:"):].strip()).resolve()
    return gitdir.is_relative_to((main / ".git").resolve())


class FsProjectRegistry(ProjectRegistry):
    """A project graph loaded solely by following declared config locators."""

    def __init__(self, node_root: Path):
        self.node_root = node_root.resolve()
        self._cache: dict[Path, _Config] = {}
        self._by_id: dict[str, _Config] = {}
        self._problems: list[str] = []
        self._unreachable: list[UnreachableProject] = []
        # Configs reached only across an `upstream` edge. Loaded as far as their
        # own file and no further: their connections are not the reader's to
        # load, check or write, so nothing beyond an upstream enters this graph.
        self._upstream_only: set[Path] = set()
        # Who declared each config as an upstream, by the config's path: named
        # when two declarers disagree about where one project lives.
        self._upstream_declarers: dict[Path, list[str]] = {}
        self._warnings: list[str] = []
        # Rule 0's answer per project id, memoised. `_target_path` runs again for
        # every edge during the reciprocity walk, so without this the disk is
        # re-probed and `_overrides` grows with the graph's edge count.
        self._override_cache: dict[str, Path | None] = {}
        self._overrides: list[ProjectOverride] = []
        # Ids whose override was present and wrong. They are not "not obtained
        # yet", so they must not also be reported as unreachable — that would
        # answer a refusal with `run tcw provision`, which is advice that
        # contradicts it.
        self._override_refused: set[str] = set()
        self._loaded = False
        # The first spelling met of each node folder, by the folder's identity: on
        # a case-insensitive disk `Root` and `ROOT` are one folder, and keying the
        # graph by path text loaded it twice.
        self._spellings: dict[tuple[int, int], Path] = {}
        self._current_path = self.node_root / SENTINEL
        # Probed once per registry, not once per locator (~8 ms a call).
        self._anchors = worktree_anchors(self.node_root)

    @classmethod
    def open(cls, node_root: Path) -> "FsProjectRegistry":
        registry = cls(node_root)
        registry._load_graph()
        return registry

    @property
    def current(self) -> Project:
        cfg = self._cache.get(self._canonical(self._current_path))
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

    def declared_parent_id(self, project_id: str | None = None) -> str | None:
        cfg = self._config_for(project_id)
        if not cfg or not cfg.parent:
            return None
        return next(iter(cfg.parent))

    def declared_child_ids(self, project_id: str | None = None) -> list[str]:
        cfg = self._config_for(project_id)
        return list(cfg.children) if cfg else []

    def declared_upstream_ids(self, project_id: str | None = None) -> list[str]:
        cfg = self._config_for(project_id)
        return list(cfg.upstream) if cfg else []

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

    def projects(self) -> list[Project]:
        self._load_graph()
        return [cfg.project for cfg in self._by_id.values()]

    def checkout_of(self, url: str) -> Path | None:
        """Where a project this graph holds is a checkout of `url`, or None.

        **Filesystem-adapter private, deliberately not on `ProjectRegistry`.**
        The question itself is storage-neutral — a tracker-backed registry could
        answer "which of your projects comes from this source" perfectly well —
        but answering it here means comparing `RepositoryDeclaration.url` and
        returning a `Project.locator`, and both are documented as things nothing
        above the adapter may read. The one caller is `resolve_store` in
        `fs.py`, which is the same adapter reading its own values.

        Asks the *resolved* project rather than the declaration that named it.
        That is the entire point: a declaration says where a project comes from,
        and only the graph knows where it landed here, `TCW_PROJECT_<ID>`
        included. A lookup that returned the declared locator would answer with
        the path the config wrote, which on a machine needing this is exactly
        the path that does not exist.

        A project is reached through the edges pointing at it, since a node's
        own repository is declared by whoever knows about that edge rather than
        by the node itself. A declared project the graph does not hold answers
        None: it names a repository but no location here, and sending the store
        ladder to a path that is not there is worse than sending it nowhere.
        """
        self._load_graph()
        wanted = normalized_url(url)
        if not wanted:
            return None
        for cfg in list(self._cache.values()):
            for entry in (*cfg.parent.values(), *cfg.children.values(),
                          *cfg.upstream.values()):
                if entry.repository is None:
                    continue
                if normalized_url(entry.repository.url) != wanted:
                    continue
                target = self._by_id.get(entry.id)
                if target is not None:
                    return Path(target.project.locator).resolve()
        return None

    def check(self) -> list[str]:
        return list(self._problems)

    def warnings(self) -> list[str]:
        return list(self._warnings)

    def read_only_reason(self, project_id: str,
                         from_id: str | None = None) -> str | None:
        self._load_graph()
        if project_id not in self._by_id:
            return None
        start = self._config_for(from_id)
        if start is None:
            return None
        seen = {start.project.id}
        frontier = [start]
        while frontier:
            cfg = frontier.pop()
            if cfg.project.id == project_id:
                return None
            for neighbor_id in (*cfg.children, *cfg.parent):
                neighbor = self._by_id.get(neighbor_id)
                if neighbor is None or neighbor_id in seen:
                    continue
                seen.add(neighbor_id)
                frontier.append(neighbor)
        declarer = next((cfg.project.id for cfg in self._cache.values()
                         if project_id in cfg.upstream), None)
        if declarer is None:
            return (f"'{project_id}' is not connected to '{start.project.id}' as a "
                    f"parent or child")
        return (f"'{project_id}' is a read-only upstream project here (reached "
                f"through '{declarer}')")

    def overrides(self) -> list[ProjectOverride]:
        """The `TCW_PROJECT_*` locators that took effect in this graph.

        Discovered by walking, so the graph is loaded first: an override is in
        force only where some config actually declares that project, and one
        naming a project nothing connects to is never consulted. Listing it
        would claim the graph depends on something it does not.

        Includes an override that resolved to the *wrong* node. The id mismatch
        is reported separately, and a reader who sees only that message is
        looking at a path written in no config they can find.
        """
        self._load_graph()
        return list(self._overrides)

    def unreachable(self) -> list[UnreachableProject]:
        """Declared projects this checkout does not have.

        Filtered by what the graph ended up holding, not by what each locator
        did. Every connection is declared twice — once by each side — and in a
        multi-repository workspace the two sides are written against different
        machines, so a locator failing to resolve is routine and says nothing on
        its own. Only the project being absent from the graph does.

        Filtered here rather than at the point of record so the walk order cannot
        matter: an edge may be recorded before the route that resolves the same
        project is followed.
        """
        return [entry for entry in self._unreachable if entry.id not in self._by_id]

    def misdirected(self) -> list[UnreachableProject]:
        """Declared locators that do not resolve here, for projects that do.

        The other half of `unreachable()`, and the reason it cannot be one list.
        `unreachable()` means "obtain this"; these entries name a project the
        checkout already has, so that message would be wrong. What is left is
        still worth saying: the locator written here does not point at it.

        Two readings, and nothing on disk distinguishes them. It may be a typo —
        which nothing reported at all, because reciprocity abstains on an absent
        target and this project is filtered out of `unreachable()`. Or it may be
        a locator that is simply right for another machine, which is routine in a
        workspace whose repositories sit differently on different disks, and is
        exactly why this is *not* a problem. So the wording states both facts and
        draws no conclusion: declared there, found here.
        """
        # No comparison of the two paths: an entry reaches `_unreachable` only
        # from the branch that could not read a config file, and `cfg.path` is by
        # construction a file that was read, so they can never be equal. A guard
        # that cannot fire tells the next reader a state exists when it does not.
        return [entry for entry in self._unreachable if entry.id in self._by_id]

    def require_valid(self) -> "FsProjectRegistry":
        if self._problems:
            raise ValueError("; ".join(self._problems))
        return self

    def config(self, project_id: str | None = None) -> dict[str, Any]:
        cfg = self._config_for(project_id)
        return dict(cfg.raw) if cfg else {}

    def _config_for(self, project_id: str | None) -> _Config | None:
        if project_id is None:
            return self._cache.get(self._canonical(self._current_path))
        return self._by_id.get(project_id)

    def _load_graph(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        self._visit(self._current_path, declared_id=None)
        self._validate_reciprocity()
        self._validate_upstreams()
        self._validate_cycles()
        self._reconcile_overrides()

    def _visit(self, config_path: Path, declared_id: str | None,
               declared_in: Path | None = None,
               declaration: RepositoryDeclaration | None = None,
               via_upstream: bool = False) -> _Config | None:
        """Load one config and, unless it was reached across an `upstream` edge,
        every config its connections name.

        A config reached across an upstream edge is loaded as far as its own
        file: its id, so `get` finds it for `extends` and references, and
        nothing it connects to. If the same folder is later reached through a
        `parent` or `children` edge, it is one project reached both ways, and it
        is loaded in full then."""
        config_path = self._canonical(config_path)
        if config_path in self._cache:
            cfg = self._cache[config_path]
            if declared_id and cfg.project.id != declared_id:
                self._problem(
                    config_path,
                    f"registered key '{declared_id}' does not match target id '{cfg.project.id}'",
                )
            if config_path in self._upstream_only and not via_upstream:
                self._upstream_only.discard(config_path)
                # Read again with its connection problems recorded this time:
                # they were not the reader's to check, and now they are.
                cfg = self._read_config(config_path, declared_id, declared_in,
                                        declaration) or cfg
                self._cache[config_path] = cfg
                if self._by_id.get(cfg.project.id, cfg).path == config_path:
                    self._by_id[cfg.project.id] = cfg
                self._follow_edges(config_path, cfg)
            return cfg
        # No re-entry guard, and none is needed. The config is cached *before*
        # its own edges are walked, so a cycle comes back to a cached config and
        # the walk terminates on the cache hit above. The guard that used to sit
        # here could therefore never fire, and the comments around it were the
        # only thing making it look as though something caught a cycle at load
        # time. `_validate_cycles` is what reports one.
        cfg = self._read_config(config_path, declared_id, declared_in,
                                declaration, quiet_connections=via_upstream)
        if cfg is None:
            return None
        self._cache[config_path] = cfg
        if via_upstream and declared_in is not None:
            declarer = self._cache.get(self._canonical(declared_in))
            if declarer is not None:
                self._upstream_declarers.setdefault(config_path, []).append(
                    declarer.project.id)
        previous = self._by_id.get(cfg.project.id)
        if previous and previous.path != config_path:
            declarers = [*self._upstream_declarers.get(previous.path, []),
                         *self._upstream_declarers.get(config_path, [])]
            named = (f"; declared upstream by {', '.join(repr(d) for d in declarers)}"
                     if declarers else "")
            self._problem(
                config_path,
                f"duplicate project id '{cfg.project.id}' also used by {previous.path}"
                f"{named}",
            )
        else:
            self._by_id[cfg.project.id] = cfg
        if via_upstream:
            self._upstream_only.add(config_path)
            return cfg
        self._follow_edges(config_path, cfg)
        return cfg

    def _follow_edges(self, config_path: Path, cfg: _Config) -> None:
        for child_id, entry in cfg.children.items():
            self._visit(self._target_path(config_path, entry), child_id,
                        config_path, entry.repository)
        for parent_id, entry in cfg.parent.items():
            self._visit(self._target_path(config_path, entry), parent_id,
                        config_path, entry.repository)
        for upstream_id, entry in cfg.upstream.items():
            self._visit(self._target_path(config_path, entry), upstream_id,
                        config_path, entry.repository, via_upstream=True)

    def _read_config(self, path: Path, declared_id: str | None,
                     declared_in: Path | None = None,
                     declaration: RepositoryDeclaration | None = None,
                     quiet_connections: bool = False,
                     ) -> _Config | None:
        if not path.is_file():
            # Not a defect. A locator is a fact about one machine — the same
            # thing `work.path` is — so a target that is not here means this
            # checkout does not have that project, not that the declaration
            # is wrong. Failing closed here refused every command in exactly
            # the checkouts that have only some of a graph's repositories.
            # Everything else below stays an error: those targets are present
            # and wrong, which is what fail-closed was written for.
            if declared_id is None and declared_in is None:
                # The node the command was run in, not a target it declared.
                # The fail-open below is argued for *targets* — "this checkout
                # does not have that project" — and says nothing about a
                # directory that is not a node at all. Recording nothing for it
                # made `require_valid()` accept any directory on the disk, and
                # every helper built on it answer "no parent, no children,
                # valid".
                self._problem(path, "no tcw-config.yaml here")
                return None
            self._unreachable_edge(declared_in or path, declared_id, path.parent,
                                   declaration)
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
        # An upstream's connections are its own business, not its readers': a
        # problem in them must not refuse a command in a project that only reads
        # it. Everything above — the file, its id — is still checked.
        before_connections = len(self._problems)
        connected = raw.get("connected-projects")
        if connected is None:
            connected = {}
        if not isinstance(connected, dict):
            self._problem(path, "connected-projects must be a mapping")
            connected = {}
        unknown = set(connected) - {"parent", "children", "upstream"}
        if unknown:
            self._problem(path, f"unknown connected-projects keys: {', '.join(sorted(map(str, unknown)))}")
        children = self._relation(path, connected.get("children"), "children")
        parent = self._relation(path, connected.get("parent"), "parent")
        upstream = self._relation(path, connected.get("upstream"), "upstream")
        if len(parent) > 1:
            self._problem(path, "connected-projects.parent must contain at most one entry")
        if quiet_connections:
            del self._problems[before_connections:]
        return _Config(
            project=Project(project_id, path.parent),
            path=path,
            parent=parent,
            children=children,
            upstream=upstream,
            raw=raw,
        )

    def _relation(self, path: Path, value: Any,
                  label: str) -> dict[str, ConnectedProject]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            self._problem(path, f"connected-projects.{label} must be a mapping")
            return {}
        result: dict[str, ConnectedProject] = {}
        for project_id, raw in value.items():
            try:
                valid_id = validate_project_id(project_id if isinstance(project_id, str) else "")
            except ValueError as error:
                self._problem(path, f"{label} key: {error}")
                continue
            entry, problems = parse_connected_entry(
                valid_id, raw, f"connected-projects.{label}.{valid_id}")
            if entry is None:
                # A declaration that is present and wrong is an error, never an
                # unreachable edge: the difference is whether we were told
                # something incorrect or told nothing this machine can act on.
                for problem in problems or [f"locator for '{valid_id}' must be a "
                                            f"nonempty string"]:
                    self._problem(path, problem)
                continue
            result[valid_id] = entry
        return result

    def _target_path(self, source_config: Path,
                     entry: ConnectedProject) -> Path:
        """Where `entry`'s `tcw-config.yaml` is, on this machine.

        The same ladder a component store resolves through, for the same reason:
        **a locator that is here always wins, and a declaration answers only when
        it cannot.** One configuration then serves the machine that has the
        project nested beside its siblings and the machine that cloned one
        repository, without either being told about the other.

        Above both sits rule 0, the environment's own statement — see
        `_override_path`. It is first, not last, and that is load-bearing: the
        case it exists for is a declared locator that resolves to the *wrong*
        existing node, which no rung below rule 1 can reach. It is also the
        honest ordering, since the ladder's standing rule is that the more
        specific answer wins, and *I am telling you where this is on this
        machine* is as specific as an answer gets.

        Falls back to the locator when neither rung answers, so the unreachable
        record names the place the user actually wrote — the declaration is what
        `tcw provision` acts on, not what the reader should be sent to check.
        """
        override = self._override_path(entry.id)
        if override is not None:
            return self._canonical(override)
        candidates: list[Path] = []
        if entry.locator is not None:
            candidates.append(self._locator_path(source_config, entry.locator))
        if entry.repository is not None:
            try:
                candidates.append(self._worktree_copy(_config_file(
                    provisioned_root(source_config.parent, entry.repository)
                    / SENTINEL)))
            except StoreDeclarationError as error:
                # A declaration this machine cannot turn into a path — a `~name`
                # naming no user. Recorded against the config that carried it,
                # because this runs during the graph load on every command, and
                # letting it propagate put a raw traceback out of `tcw validate`
                # and `tcw work list` from a value the parser accepted.
                self._problem(source_config, str(error))
        for candidate in candidates:
            if candidate.is_file():
                return self._canonical(candidate)
        return candidates[0] if candidates else (source_config.parent / SENTINEL)

    def _override_path(self, project_id: str) -> Path | None:
        """Rule 0: where `TCW_PROJECT_<ID>` says this project is, or None.

        None means the ladder carries on — either no variable, or one naming a
        path this machine does not have. A `Path` means it answered, and the
        caller must not consult a lower rung.

        **Absent is not wrong.** A variable pointing at a directory that is not
        here means this machine does not have that project, which is the same
        thing an unresolvable locator means, and `_read_config` has drawn that
        distinction for every locator since fail-closed refused every checkout
        holding part of a graph. It is what lets one set of variables be
        configured once for an environment — a cloud session's base directory,
        say — and used by sessions that attach different subsets of the
        repositories, with neither needing to know which case it is in.

        **Present and wrong is wrong.** A directory that is here and is not a
        node is a mistake with no benign reading, and it is refused rather than
        skipped. Skipping it is the fail-open shape that produces "my override
        does nothing" with nothing at all to read.

        A relative value resolves against the *process's working directory*, not
        the declaring config — the one path in this module that does. A locator
        is written in a file, so it means "relative to that file"; a variable is
        written in a shell, so it means what the shell means.
        """
        if project_id not in self._override_cache:
            self._override_cache[project_id] = self._resolve_override(project_id)
        return self._override_cache[project_id]

    def _resolve_override(self, project_id: str) -> Path | None:
        name = override_variable(project_id)
        value = (os.environ.get(name) or "").strip()
        if not value:
            # An exported-but-empty variable names no path. Reading it as one
            # yields the working directory, which nobody means by `FOO=`.
            return None
        root = Path(value).expanduser()
        if not root.is_absolute():
            root = Path.cwd() / root
        root = root.resolve()
        if not root.is_dir():
            return None
        config_path = root / SENTINEL
        if not config_path.is_file():
            problem = f"{name} names a directory with no {SENTINEL}"
            self._problem(root, problem)
            self._override_refused.add(project_id)
            # Recorded as an override too, not only as a problem. It stopped the
            # ladder, so it is in force; a caller asking "which overrides are
            # acting on this graph" must not be told none.
            self._overrides.append(ProjectOverride(id=project_id, source=name,
                                                   locator=root,
                                                   problem=f"{root}: {problem}"))
            return config_path
        # Recorded before the id is known to be right. An override that landed
        # on the wrong node still explains a path the reader will otherwise find
        # in no config, and `_read_config` reports the mismatch itself, naming
        # both ids — parsing the config here to say it again would print two
        # messages for one cause.
        self._overrides.append(ProjectOverride(id=project_id, source=name,
                                               locator=root))
        return config_path

    def _locator_path(self, source_config: Path, locator: str) -> Path:
        target = Path(locator)
        source_dir = source_config.parent.resolve()
        resolved = _config_file(
            (target if target.is_absolute() else source_dir / target) / SENTINEL)
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
            resolved = _config_file(counterpart / target / SENTINEL)
        return self._worktree_copy(resolved)

    def _worktree_copy(self, resolved: Path) -> Path:
        """Rule 2 — a config path under the main worktree, as this worktree's copy.

        Nodes outside this worktree point back into its repository as the *main*
        worktree spells it — the current node, and every sibling in the same
        repository — so the graph would load each twice under one ID and fail
        reciprocity. A path under the main worktree whose counterpart under this
        worktree holds a config, in this same repository, is the same node on the
        checked-out branch, so it resolves there (GitHub #39). Anything else keeps
        its path, so an ID repeated across *different* repositories is still a
        duplicate — including a repository nested inside this one, which the
        branch does not hold even when a copy sits at the same place. A path
        already inside this worktree is left alone: TCW's own worktrees live under
        the primary checkout (`.worktrees/<slug>`), where every worktree path is
        also "under main". Applied to every way a node is declared — a locator,
        absolute or relative, and a `repository:` checkout."""
        if self._anchors is None:
            return resolved
        top, main = self._anchors
        if not resolved.is_relative_to(main) or resolved.is_relative_to(top):
            return resolved
        copy = top / resolved.relative_to(main)
        if not copy.is_file():
            return resolved
        between = copy.parent
        while between != top and between.is_relative_to(top):
            if not _same_repository(between / ".git", main):
                return resolved                  # another repository's node
            between = between.parent
        return _config_file(copy)

    def _canonical(self, config_path: Path) -> Path:
        """`config_path` (see `_config_file`) under the first spelling seen of its
        folder; as given when the folder cannot be read."""
        config_path = _config_file(config_path)
        try:
            found = config_path.parent.stat()
        except OSError:
            return config_path
        if not found.st_ino:
            return config_path    # a filesystem with no inode numbers: text only
        folder = self._spellings.setdefault((found.st_dev, found.st_ino), config_path.parent)
        return folder / config_path.name

    def _upstream_reader(self, project_id: str) -> str | None:
        """A project in this graph declaring `project_id` as its upstream."""
        return next((cfg.project.id for cfg in self._cache.values()
                     if project_id in cfg.upstream), None)

    def _read_as_upstream(self, cfg: _Config, parent_id: str, reader: str) -> None:
        warning = (f"{cfg.path}: '{cfg.project.id}' names '{parent_id}' as its parent, "
                   f"but is read as an upstream project by '{reader}'; remove the "
                   f"parent entry from '{cfg.project.id}' — an upstream need not "
                   f"name its readers")
        if warning not in self._warnings:
            self._warnings.append(warning)

    def _validate_reciprocity(self) -> None:
        for cfg in self._cache.values():
            if cfg.path in self._upstream_only:
                # Its connections are not ours to check. The one thing worth
                # saying is the migration's leftover: a parent claim its parent
                # now answers by reading it as an upstream.
                for parent_id, entry in cfg.parent.items():
                    parent = self._cache.get(self._target_path(cfg.path, entry))
                    if (parent is not None and cfg.project.id not in parent.children
                            and (reader := self._upstream_reader(cfg.project.id))):
                        self._read_as_upstream(cfg, parent_id, reader)
                continue
            for child_id, entry in cfg.children.items():
                child_path = self._target_path(cfg.path, entry)
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
            for parent_id, entry in cfg.parent.items():
                parent_path = self._target_path(cfg.path, entry)
                parent = self._cache.get(parent_path)
                if parent is None:
                    continue
                reciprocal = parent.children.get(cfg.project.id)
                if reciprocal is None:
                    # The migration's middle state: the parent moved this node
                    # from `children` to `upstream`, and this node has not yet
                    # dropped its parent entry. A warning, so neither side is
                    # blocked while the two repositories catch up.
                    if (reader := self._upstream_reader(cfg.project.id)) is not None:
                        self._read_as_upstream(cfg, parent_id, reader)
                        continue
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

    def _validate_upstreams(self) -> None:
        """An upstream is read-only, so it cannot also be something its declarer
        writes to — its own child or parent, or any project it reaches through
        them. Checked from the declarer, not from the current node: the conflict
        is in the declarer's connections, wherever the command was run."""
        for cfg in list(self._cache.values()):
            if cfg.path in self._upstream_only:
                continue
            for upstream_id in cfg.upstream:
                if upstream_id == cfg.project.id:
                    self._problem(cfg.path, f"'{upstream_id}' is declared as its own "
                                            f"upstream")
                elif (upstream_id in self._by_id and self.read_only_reason(
                        upstream_id, from_id=cfg.project.id) is None):
                    self._problem(
                        cfg.path,
                        f"'{upstream_id}' is declared upstream (read-only) by "
                        f"'{cfg.project.id}', but '{cfg.project.id}' is also "
                        f"connected to it as a parent or child; declare one or the "
                        f"other")

    def _points_elsewhere(self, source_config: Path, locator: ConnectedProject,
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
        """Report a cycle among the loaded projects. The only thing that does.

        `children` edges only, and deliberately: every connection is declared
        from both sides, so walking `parent` as well would make each legitimate
        reciprocal pair a two-cycle. Reciprocity is what guarantees a `parent`
        edge has a `children` counterpart here to be walked — so a cycle
        expressed *purely* through `parent` edges is reported by
        `_validate_reciprocity` as a missing counterpart rather than by this, and
        that is the honest description of the coverage rather than a claim that
        one check sees everything.

        Nothing catches a cycle during the load itself. `_visit` caches a config
        before walking its edges, so a cycle terminates on the cache hit; the
        re-entry guard that used to sit there could never fire.
        """
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

    def _reconcile_overrides(self) -> None:
        """Fill in `problem` for every override that did not deliver its project.

        Run after the walk because one of the two failures cannot be seen before
        it. A directory holding no `tcw-config.yaml` is known the moment the
        override resolves; a directory holding the *wrong* node is known only
        once that node's config has been read, by the same mismatch check that
        catches a wrong declared locator.

        The test is deliberately the outcome rather than a list of failure
        modes: an override is satisfied when the graph ended up holding its
        project, under its id, at the place it pointed. Anything else failed,
        including a mode nobody has thought of yet.
        """
        for index, override in enumerate(self._overrides):
            if override.problem is not None:
                continue
            # Through `_canonical`, as the walk read it: the variable may spell
            # the folder in other letter case than the walk met it first.
            where = self._canonical(Path(override.locator) / SENTINEL)
            cfg = self._by_id.get(override.id)
            if cfg is not None and cfg.path == where:
                if (warning := self._other_branch_warning(override, where)):
                    self._overrides[index] = replace(override, warning=warning)
                continue
            # Not `cfg`: that is whatever answered for this id, which is not
            # necessarily what the override pointed at. Name the node actually
            # sitting at the overridden location, read from the walk's cache.
            at_location = self._cache.get(where)
            found = (f"which is '{at_location.project.id}', not '{override.id}'"
                     if at_location is not None
                     else f"which did not yield '{override.id}'")
            self._overrides[index] = replace(
                override,
                problem=f"{override.source} names {override.locator}, {found}",
            )

    def _other_branch_warning(self, override: ProjectOverride,
                              where: Path) -> str | None:
        """Why `override`, run from a linked worktree, reads its project from
        another branch: it names the primary checkout's copy while this
        worktree holds the same project. Kept as stated — it says exactly where
        the project is — but a variable set once for a machine lands here
        whenever a worktree is used, and the graph then mixes two branches."""
        copy = self._worktree_copy(where)
        if copy == where:
            return None
        try:
            held = yaml.safe_load(copy.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError):
            return None
        try:                                   # read as `_read_config` reads it
            held_id = validate_project_id(str(held.get("id") or "")) \
                if isinstance(held, dict) else None
        except ValueError:
            return None
        if held_id != override.id:
            return None
        return (f"{override.source} names {override.locator}, the primary "
                f"checkout's copy, while this worktree has its own at "
                f"{copy.parent}; '{override.id}' is read from another branch "
                f"than the rest of the graph")

    def _problem(self, path: Path, message: str) -> None:
        rendered = f"{path}: {message}"
        if rendered not in self._problems:
            self._problems.append(rendered)

    def _unreachable_edge(self, config_path: Path, project_id: str | None,
                          locator: Path,
                          declaration: RepositoryDeclaration | None = None) -> None:
        """Record a declared project that is not here, rather than a problem.

        `project_id` is the key the declaring config used. It can be None only
        for the current node's own config, which is never an edge — the guard is
        here so a future caller cannot record a nameless entry that no message
        could ever render.
        """
        if not project_id:
            return
        if project_id in self._override_refused:
            # Told where it is, and it is not a node. That is a refusal, not a
            # thing to obtain, and `run tcw provision` would contradict it.
            return
        entry = UnreachableProject(id=project_id, locator=locator,
                                   declared_in=config_path,
                                   declaration=declaration)
        if entry not in self._unreachable:
            self._unreachable.append(entry)

    def unreachable_project(self, project_id: str) -> UnreachableProject | None:
        """The recorded entry for `project_id`, or None.

        The lookup every "declared but not here" message needs: a caller holding
        an id that `get()` answered None for asks this before deciding which
        message to print.
        """
        self._load_graph()
        # Through `unreachable()`, not the raw list: a project another route
        # resolved is not missing, and a message telling the user to obtain a
        # repository they already have is worse than no message.
        return next((u for u in self.unreachable() if u.id == project_id), None)
