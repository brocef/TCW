"""Filesystem implementation of the storage-neutral project registry."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import yaml

from tcw.findings import Finding
from tcw.store.base import (
    ConnectedProject, Project, ProjectOverride, ProjectRegistry,
    RepositoryDeclaration, StoreDeclarationError, UnreachableProject,
    parse_connected_entry, retired_key_problem,
)
from tcw.errors import ProjectGraphError, Unreachable, UnknownProject
from tcw.project_files import (LEGACY_PROJECT, LEGACY_SENTINEL, LOCAL_MANIFEST,
                               LOCAL_MANIFEST_NAME, MANIFEST, PROJECT_ID_PATTERN,
                               RESERVED_PROJECT_IDS, SENTINEL, TCW_FOLDER,
                               legacy_message, personal_files_skipped, root_of,
                               validate_project_id, version_problem)
from tcw.store.manifest import ManifestEntry, parse_manifest
from tcw.store.checkouts import normalized_url, provisioned_root
from tcw.store.yaml_source import UniqueKeyLoader as _UniqueKeyLoader, load as _load_named_yaml

def override_variable(project_id: str) -> str:
    """The environment variable that says where `project_id` lives on this machine.

    The id, uppercased, with `-` as `_`: `app-repo` →
    `TCW_PROJECT_APP_REPO`. **Project ids, not repository names** — the two are
    routinely different, and a workspace where they are crossed is what this
    mapping is most often got wrong against.

    Injective, and only because `PROJECT_ID_PATTERN` admits neither an
    underscore nor an uppercase letter: with either allowed, `a_b` or `A-b` would
    claim the same variable as `a-b`. `test_invalid_or_reserved_project_ids`
    holds that guarantee, so this function may not be given a laxer id.

    The variable supplies a fact about this machine that no shared
    configuration can carry, and is read as one step of an ordered fallback.
    """
    return "TCW_PROJECT_" + project_id.upper().replace("-", "_")


# The cache lives as long as the process: one command for the CLI, but a whole
# server run under `tcw serve`. A graph walk re-probes the same handful of
# directories, so an unbounded module-level dict is the right cache here —
# don't "fix" it into an LRU. The price is that a directory added or removed as
# a linked worktree while a server runs is seen only after a restart.
_ANCHOR_CACHE: dict[Path, tuple[Path, Path] | None] = {}


#: The registry opened for each project root while a command runs; None
#: outside a command, so a library caller and a test always read afresh.
_OPEN: "dict[Path, FsProjectRegistry] | None" = None


def begin_command() -> None:
    global _OPEN
    _OPEN = {}


def end_command() -> None:
    global _OPEN
    _OPEN = None


def forget_registries() -> None:
    """Drop the registries this command has opened, after it wrote a
    `tcw-config.yaml` or a manifest, so the next `open` reads the files as
    they are now. It cannot refresh a registry a caller already holds in a
    variable: such a caller opens the registry again after writing."""
    if _OPEN is not None:
        _OPEN.clear()


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


def personal_file(root: Path, name: str,
                  anchors: "tuple[Path, Path] | None | bool" = True) -> Path:
    """Where to read the personal file `name` (`tcw-config.local.yaml` or
    `tcw-manifest.local.yaml`) of the project at `root` (TCW-107 Design 4.2):
    its own `.tcw/<name>` when that is a file; otherwise, when `root` lies
    inside a linked git worktree, the same file below the main checkout when
    that one is a file; otherwise its own. A file is personal by its name: git
    is asked only where the worktree is, never whether the file is tracked.

    `anchors` is the worktree's `(top, main)` when the caller already holds
    them (None for none), or True to probe `root`."""
    own = Path(root) / TCW_FOLDER / name
    if own.is_file():
        return own
    if anchors is True:
        anchors = worktree_anchors(Path(root))
    if not anchors:
        return own
    top, main = anchors
    inside = _below(Path(root).resolve(), top)
    if inside is None:
        return own
    borrowed = main / inside / TCW_FOLDER / name
    return borrowed if borrowed.is_file() else own


def _below(path: Path, root: Path) -> Path | None:
    """The part of `path` below `root` when `path` is `root` or inside it, else
    None — deciding "inside" by folder identity, not by text.

    `Path.resolve()` keeps the spelling it was given, so on a disk that ignores
    letter case `.../APP/pkg` and git's `.../app/pkg` are one folder that text
    comparison calls two. The text answer is tried first; failing it, each of
    `path` and its parents is compared with `root` by device and inode, as
    `_canonical` compares the graph's keys. A folder that cannot be read is
    skipped, and a filesystem reporting no inode numbers keeps the text answer.
    """
    if path.is_relative_to(root):
        return path.relative_to(root)
    try:
        found = root.stat()
    except OSError:
        return None
    if not found.st_ino:
        return None
    for ancestor in (path, *path.parents):
        try:
            here = ancestor.stat()
        except OSError:
            continue
        if (here.st_dev, here.st_ino) == (found.st_dev, found.st_ino):
            return path.relative_to(ancestor)
    return None


def _config_file(path: Path) -> Path:
    """A `.tcw/tcw-config.yaml` path with its project root resolved and the file
    itself not followed. A symlinked config belongs to the project it sits in:
    that folder is the project, and its relative locators are read from there —
    resolving the file took them from wherever the link pointed."""
    return root_of(path).resolve() / SENTINEL


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


# ---------------------------------------------------------------------------
# Finding a project's folder from its ID (TCW-107 Design 2)


def _read_text(path: Path) -> str:
    """A file's text. Every file the registry reads is read here, so a test
    can count the reads (TCW-107 AC 24, AC 27)."""
    return Path(path).read_text(encoding="utf-8")


def _list_folder(path: Path) -> list[tuple[str, bool]]:
    """Each entry in a folder, by name, and whether it is a folder. Every
    folder the registry lists is listed here, for the same reason. Raises the
    `OSError` listing it raised."""
    result = []
    with os.scandir(path) as entries:
        for entry in entries:
            try:
                is_dir = entry.is_dir()
            except OSError:
                is_dir = False
            result.append((entry.name, is_dir))
    return sorted(result)


#: The folders macOS asks a person's permission to read, directly in the home
#: folder. The search never tests one next to a project (see `_protected`).
_PROTECTED_NAMES = ("Desktop", "Documents", "Downloads")
_ON_MACOS = sys.platform == "darwin"


def _holds_only_git(path: str) -> str:
    """The words for an entry folder holding nothing but `.git`: what a
    clone or a submodule update leaves when it stopped before checking out a
    file. The fetching command refuses such a folder (TCW-115), so the person
    is told to deal with it first."""
    return f"{path} holds only .git; finish or remove it with git"


@dataclass(frozen=True)
class _Probe:
    """What a folder's two files say (Design 2.6): `none` (neither file),
    `project` (a 4.0 project declaring `id`), `version` (a 4.0 file whose
    version this TCW cannot read; `id` when it declares one), `legacy` (a 3.x
    root file; `id` when it declares one) or `unreadable`."""

    kind: str
    id: str | None = None
    detail: str = ""


@dataclass(frozen=True)
class _Answer:
    """One answer to "where is `X`, asked by `P`" (Design 2.11 b).

    `folder` is the project's root when found, and `by` the rule that found
    it: `manifest` (with the deciding `entry`), `variable` or `search`.
    Otherwise `problem` is the graph problem, rendered as recorded, or the
    project is not here: `named` says whether anything the walk consulted
    names the ID, and `message` is Design 6.2's text."""

    folder: Path | None = None
    by: str | None = None
    entry: ManifestEntry | None = None
    entry_folder: Path | None = None
    problem: str | None = None
    named: bool = False
    message: str = ""


def _holds_only_id(entry: ConnectedProject) -> bool:
    """A `projects:` entry naming its project by ID alone, which the lookup
    resolves (TCW-107 Design 3.1); one with a 3.x location is still resolved
    by `_target_path` until those are refused."""
    return entry.locator is None and entry.repository is None


def _search(registry: "FsProjectRegistry", project_id: str,
            named_by: Path) -> tuple[list[Path], list[tuple[Path, str]]]:
    """Design 2.4-2.8: the folders next to `named_by` and enclosing it that
    declare `project_id`, and the problems of candidates that are
    `project_id` but cannot be read as 4.0. Every match is collected; the
    registry decides. Never reads below a folder it tests (Design 2.6).

    A module-level function, so a test run can replace it with one that finds
    nothing, and so show that each test's projects are placed by its
    manifests rather than found by accident."""
    matches: list[Path] = []
    problems: list[tuple[Path, str]] = []
    for folder in registry._search_candidates(named_by):
        probe = registry._probe(folder)
        if probe.id != project_id:
            continue
        if probe.kind == "project":
            matches.append(folder)
        elif probe.kind == "version":
            problems.append((folder / SENTINEL, probe.detail))
        elif probe.kind == "legacy":
            problems.append((folder, f"is {LEGACY_PROJECT}"))
    return matches, problems


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

    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()
        self._cache: dict[Path, _Config] = {}
        self._by_id: dict[str, _Config] = {}
        # The same problems twice, in step: rendered for the refusals that
        # raise them, and as findings for `check()` (TCW-73 Design 6.3).
        self._problems: list[str] = []
        self._findings: list[Finding] = []
        self._unreachable: list[UnreachableProject] = []
        # Configs reached only across an `upstream` edge. Loaded as far as their
        # own file and no further: their connections are not the reader's to
        # load, check or write, so nothing beyond an upstream enters this graph.
        self._upstream_only: set[Path] = set()
        # Who declared each config as an upstream, by the config's path: named
        # when two declarers disagree about where one project lives.
        self._upstream_declarers: dict[Path, list[str]] = {}
        self._warnings: list[str] = []
        self._warning_findings: list[Finding] = []
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
        # The first spelling met of each project folder, by the folder's identity: on
        # a case-insensitive disk `Root` and `ROOT` are one folder, and keying the
        # graph by path text loaded it twice.
        self._spellings: dict[tuple[int, int], Path] = {}
        self._current_path = self.project_root / SENTINEL
        # Probed once per registry, not once per locator (~8 ms a call).
        self._anchors = worktree_anchors(self.project_root)
        # The lookup's reads, each made at most once (TCW-107 Design 2.13): a
        # file's text or the error reading it, a folder's listing or the error
        # listing it, what a folder's two files say, and each project root's
        # manifests (None when one has a problem, which makes it unusable).
        self._texts: dict[Path, str | Exception] = {}
        self._listings: dict[Path, list[tuple[str, bool]] | OSError] = {}
        self._probes: dict[Path, _Probe] = {}
        self._manifests: dict[Path, list[tuple[Any, Path, dict]] | None] = {}
        self._manifest_problem: dict[Path, str] = {}
        # One answer per question, "where is `X`, asked by `P`", keyed by the
        # ID and `P`'s root (Design 2.11 b), and the answer that placed each
        # configuration in the graph, for `found`.
        self._answers: dict[tuple[str, Path], _Answer] = {}
        self._placed: dict[Path, _Answer] = {}
        # Configurations read only to learn a project's family, outside the
        # walk, and the folders `project_folder` returned, by ID.
        self._peeked: dict[Path, _Config | None] = {}
        self._found: dict[str, Path] = {}

    @classmethod
    def open(cls, project_root: Path) -> "FsProjectRegistry":
        """The registry of the project at `project_root`, its graph loaded.
        While a command runs, the same registry for the same root, so the
        graph, every lookup's answer and every folder the search reads are
        read once (TCW-107 Design 2.13); outside a command, a new one."""
        if _OPEN is None:
            registry = cls(project_root)
            registry._load_graph()
            return registry
        key = Path(project_root).resolve()
        if key not in _OPEN:
            registry = cls(project_root)
            registry._load_graph()
            # Kept only once the load has finished, so a load that raised is
            # never handed out half-built.
            _OPEN[key] = registry
        return _OPEN[key]

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

        A project's repository is written in the manifest entries that place
        it (TCW-107 Design 6.4), read in a fixed order so the answer does not
        depend on which lookups the command made first: `_manifest_order`'s.
        For the first entry whose repository is `url` and whose project this
        command has found, the repository's folder is the found folder with the
        entry's `subfolder` removed. An entry whose project is not found, or
        whose found folder does not end with its `subfolder`, gives no answer:
        it names a repository but no location here, and sending the store
        ladder to a path that is not there is worse than sending it nowhere.
        """
        self._load_graph()
        wanted = normalized_url(url)
        if not wanted:
            return None
        for root in self._manifest_order():
            for _file, _base, entries in self._manifests_of(root) or []:
                for entry in entries.values():
                    if entry.url is None or normalized_url(entry.url) != wanted:
                        continue
                    folder = self._known_folder(entry.id)
                    if folder is None:
                        continue
                    folder = Path(folder).resolve()
                    if entry.subfolder is None:
                        return folder
                    tail = Path(entry.subfolder).parts
                    if folder.parts[-len(tail):] == tail:
                        return folder.parents[len(tail) - 1]
        return None

    def _manifest_order(self) -> list[Path]:
        """The roots whose manifests `checkout_of` reads, in Design 2.2's order
        from the active project: its own, its ancestors' nearest first, its
        descendants' breadth first. Then every other project the graph follows
        the connections of (a sibling, say), in the order the walk met them;
        an upstream-only project's manifests are not read (Design 2.10)."""
        order, _ = self._family(self.project_root, "")
        seen = {self._identity(root) for root in order}
        for path, cfg in list(self._cache.items()):
            if cfg is None or path in self._upstream_only:
                continue
            root = root_of(path)
            if self._identity(root) not in seen:
                seen.add(self._identity(root))
                order.append(root)
        return order

    def check(self) -> list[Finding]:
        return list(self._findings)

    def warnings(self) -> list[str]:
        return list(self._warnings)

    def warning_findings(self) -> list[Finding]:
        """The same warnings as findings, the file each concerns as `where`."""
        return list(self._warning_findings)

    def read_only_reason(self, project_id: str,
                         from_id: str | None = None) -> str | None:
        self._load_graph()
        if project_id not in self._by_id:
            # Not on this machine: still answerable from the declarations, so
            # an absent upstream project is refused as upstream rather than
            # treated as any other missing project.
            reader = self._upstream_reader(project_id)
            if reader is None:
                return None
            return (f"'{project_id}' is a read-only upstream project here "
                    f"(reached through '{reader}')")
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

    def entry(self, project_id: str) -> ConnectedProject | None:
        """The first `projects` entry in this graph naming
        `project_id`, whether or not that project is on this machine."""
        self._load_graph()
        for cfg in self._cache.values():
            for entries in (cfg.parent, cfg.children, cfg.upstream):
                if project_id in entries:
                    return entries[project_id]
        return None

    def overrides(self) -> list[ProjectOverride]:
        """The `TCW_PROJECT_*` locators that took effect in this graph.

        Discovered by walking, so the graph is loaded first: an override is in
        force only where some config actually declares that project, and one
        naming a project nothing connects to is never consulted. Listing it
        would claim the graph depends on something it does not.

        Includes an override that resolved to the *wrong* project. The id mismatch
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
        # An edge naming its project by ID alone wrote no locator to report.
        return [entry for entry in self._unreachable
                if entry.id in self._by_id and not entry.message]

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
        if self._canonical(self._current_path) in self._cache:
            # Read whether or not anything is looked up, so their problems are
            # reported (Design 1.8); a missing file costs one failed read.
            self._manifests_of(self.project_root)
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
        """The parent first, then the children in the order the configuration
        lists them, then the upstreams (TCW-107 Design 2.11 a), so a project's
        parent chain has been found by the time its children are looked up."""
        for relation in (cfg.parent, cfg.children, cfg.upstream):
            via_upstream = relation is cfg.upstream
            for target_id, entry in relation.items():
                if _holds_only_id(entry):
                    self._follow_id(config_path, target_id, via_upstream)
                else:
                    self._visit(self._target_path(config_path, entry), target_id,
                                config_path, entry.repository,
                                via_upstream=via_upstream)

    def _follow_id(self, config_path: Path, target_id: str,
                   via_upstream: bool) -> None:
        """One edge naming its project by ID alone, resolved by the lookup.
        A problem is already recorded, and the edge is not followed."""
        answer = self._locate(target_id, root_of(config_path))
        if answer.problem is not None:
            return
        if answer.folder is None:
            self._unreachable_edge(
                config_path, target_id, answer.entry_folder, message=answer.message,
                decided_by=answer.entry.file if answer.entry else None,
                repository=answer.entry.repository if answer.entry else None)
            return
        target = self._canonical(answer.folder / SENTINEL)
        self._placed.setdefault(target, answer)
        self._visit(target, target_id, config_path, via_upstream=via_upstream)

    def _read_config(self, path: Path, declared_id: str | None,
                     declared_in: Path | None = None,
                     declaration: RepositoryDeclaration | None = None,
                     quiet_connections: bool = False,
                     ) -> _Config | None:
        if not path.is_file() and (root_of(path) / LEGACY_SENTINEL).is_file():
            # A 3.x project: present, and in a format this TCW does not read
            # (TCW-106 Design 4.2). Not "this machine does not have it". A
            # TCW_PROJECT_<ID> that named it has already said so, naming itself.
            if not any(o.locator == root_of(path) and o.problem
                       for o in self._overrides):
                self._problem(root_of(path), f"is {LEGACY_PROJECT}")
            return None
        if not path.is_file():
            # Not a defect. A locator is a fact about one machine — the same
            # thing `work.path` is — so a target that is not here means this
            # checkout does not have that project, not that the declaration
            # is wrong. Failing closed here refused every command in exactly
            # the checkouts that have only some of a graph's repositories.
            # Everything else below stays an error: those targets are present
            # and wrong, which is what fail-closed was written for.
            if declared_id is None and declared_in is None:
                # The project the command was run in, not a target it declared.
                # The fail-open below is argued for *targets* — "this checkout
                # does not have that project" — and says nothing about a
                # directory that is not a project at all. Recording nothing for it
                # made `require_valid()` accept any directory on the disk, and
                # every helper built on it answer "no parent, no children,
                # valid".
                self._problem(path, f"no {SENTINEL} here")
                return None
            self._unreachable_edge(declared_in or path, declared_id, root_of(path),
                                   declaration)
            return None
        text = self._text(path)
        if isinstance(text, UnicodeDecodeError):
            self._problem(path, _not_utf8(text))
            return None
        try:
            if isinstance(text, Exception):
                raise text
            raw = _load_named_yaml(text, path, _UniqueKeyLoader) or {}
        except (OSError, yaml.YAMLError) as error:
            self._problem(path, f"invalid YAML: {error}")
            return None
        if not isinstance(raw, dict):
            self._problem(path, "config must be a mapping")
            return None
        version = version_problem(raw)
        if version:
            # Read by every reader of a `tcw-*.yaml` file (TCW-106 Design 3.4a).
            self._problem(path, version)
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
        retired = retired_key_problem(raw)
        if retired:
            self._problem(path, retired)
        connected = raw.get("projects")
        if connected is None:
            connected = {}
        if not isinstance(connected, dict):
            self._problem(path, "projects must be a mapping")
            connected = {}
        unknown = set(connected) - {"parent", "children", "upstream"}
        if unknown:
            self._problem(path, f"unknown projects keys: {', '.join(sorted(map(str, unknown)))}")
        children = self._relation(path, connected.get("children"), "children")
        parent = self._relation(path, connected.get("parent"), "parent")
        upstream = self._relation(path, connected.get("upstream"), "upstream")
        if len(parent) > 1:
            self._problem(path, "projects.parent must contain at most one entry")
        if quiet_connections:
            del self._problems[before_connections:]
            del self._findings[before_connections:]
        return _Config(
            project=Project(project_id, root_of(path)),
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
            self._problem(path, f"projects.{label} must be a mapping")
            return {}
        result: dict[str, ConnectedProject] = {}
        for project_id, raw in value.items():
            try:
                valid_id = validate_project_id(project_id if isinstance(project_id, str) else "")
            except ValueError as error:
                self._problem(path, f"{label} key: {error}")
                continue
            entry, problems = parse_connected_entry(
                valid_id, raw, f"projects.{label}.{valid_id}")
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
        existing project, which no rung below rule 1 can reach. It is also the
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
                    provisioned_root(root_of(source_config), entry.repository)
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
        return candidates[0] if candidates else (root_of(source_config) / SENTINEL)

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
        project is a mistake with no benign reading, and it is refused rather than
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
            problem = (f"{name} names {LEGACY_PROJECT}"
                       if (root / LEGACY_SENTINEL).is_file()
                       else f"{name} names a directory with no {SENTINEL}")
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
        # on the wrong project still explains a path the reader will otherwise find
        # in no config, and `_read_config` reports the mismatch itself, naming
        # both ids — parsing the config here to say it again would print two
        # messages for one cause.
        self._overrides.append(ProjectOverride(id=project_id, source=name,
                                               locator=root))
        return config_path

    def _locator_path(self, source_config: Path, locator: str) -> Path:
        target = Path(locator)
        source_dir = root_of(source_config).resolve()
        resolved = _config_file(
            (target if target.is_absolute() else source_dir / target) / SENTINEL)
        if self._anchors is None:
            return resolved
        top, main = self._anchors
        # Rule 1 — re-anchor only on escape, and only a *relative* locator: an
        # absolute one names a place, not an offset from the config. A target
        # that stays inside the worktree is a sibling project on the same branch and
        # belongs to the worktree (this is what keeps multi-project-in-one-repo
        # working). Only a target that leaves the checkout was authored against
        # the primary checkout's position on disk, so resolve it against the
        # source directory's counterpart under the main worktree root instead.
        inside = _below(source_dir, top)
        if (
            not target.is_absolute()
            and inside is not None
            and _below(root_of(resolved), top) is None
        ):
            counterpart = main / inside
            resolved = _config_file(counterpart / target / SENTINEL)
        return self._worktree_copy(resolved)

    def _worktree_copy(self, resolved: Path) -> Path:
        """Rule 2 — a config path under the main worktree, as this worktree's copy.

        Projects outside this worktree point back into its repository as the *main*
        worktree spells it — the current project, and every sibling in the same
        repository — so the graph would load each twice under one ID and fail
        reciprocity. A path under the main worktree whose counterpart under this
        worktree holds a config, in this same repository, is the same project on the
        checked-out branch, so it resolves there (GitHub #39). Anything else keeps
        its path, so an ID repeated across *different* repositories is still a
        duplicate — including a repository nested inside this one, which the
        branch does not hold even when a copy sits at the same place. A path
        already inside this worktree is left alone: TCW's own worktrees live under
        the primary checkout (`.worktrees/<slug>`), where every worktree path is
        also "under main". Applied to every way a project is declared — a locator,
        absolute or relative, and a `repository:` checkout."""
        if self._anchors is None:
            return resolved
        top, main = self._anchors
        under_main = _below(resolved, main)
        if under_main is None or _below(resolved, top) is not None:
            return resolved
        copy = top / under_main
        if not copy.is_file():
            return resolved
        between = root_of(copy)
        while between != top and between.is_relative_to(top):
            if not _same_repository(between / ".git", main):
                return resolved                  # another repository's project
            between = between.parent
        return _config_file(copy)

    def _canonical(self, config_path: Path) -> Path:
        """`config_path` (see `_config_file`) under the first spelling seen of its
        folder; as given when the folder cannot be read."""
        config_path = _config_file(config_path)
        root = root_of(config_path)
        try:
            found = root.stat()
        except OSError:
            return config_path
        if not found.st_ino:
            return config_path    # a filesystem with no inode numbers: text only
        folder = self._spellings.setdefault((found.st_dev, found.st_ino), root)
        return folder / SENTINEL

    def _upstream_reader(self, project_id: str) -> str | None:
        """A project in this graph declaring `project_id` as its upstream."""
        return next((cfg.project.id for cfg in self._cache.values()
                     if project_id in cfg.upstream), None)

    def _read_as_upstream(self, cfg: _Config, parent_id: str, reader: str) -> None:
        message = (f"'{cfg.project.id}' names '{parent_id}' as its parent, but is "
                   f"read as an upstream project by '{reader}'; remove the parent "
                   f"entry from '{cfg.project.id}' — an upstream need not name its "
                   f"readers")
        warning = f"{cfg.path}: {message}"
        if warning not in self._warnings:
            self._warnings.append(warning)
            self._warning_findings.append(Finding("warning", str(cfg.path), message))

    def _validate_reciprocity(self) -> None:
        for cfg in self._cache.values():
            if cfg.path in self._upstream_only:
                # Its connections are not ours to check. The one thing worth
                # saying is the migration's leftover: a parent claim its parent
                # now answers by reading it as an upstream.
                for parent_id, entry in cfg.parent.items():
                    target = self._edge_target(cfg.path, parent_id, entry)
                    if target is None and _holds_only_id(entry):
                        # Its edges were not followed, so nothing looked its
                        # parent up; by ID, as reciprocity is (Design 3.2).
                        found = self._by_id.get(parent_id)
                        target = found.path if found is not None else None
                    parent = self._cache.get(target)
                    if (parent is not None and cfg.project.id not in parent.children
                            and (reader := self._upstream_reader(cfg.project.id))):
                        self._read_as_upstream(cfg, parent_id, reader)
                continue
            for child_id, entry in cfg.children.items():
                child = self._cache.get(self._edge_target(cfg.path, child_id, entry))
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
                        f"parent locator for '{cfg.project.id}' does not point back to {root_of(cfg.path)}",
                    )
                if child.project.id != child_id:
                    self._problem(
                        child.path,
                        f"registered key '{child_id}' does not match target id '{child.project.id}'",
                    )
            for parent_id, entry in cfg.parent.items():
                parent = self._cache.get(self._edge_target(cfg.path, parent_id, entry))
                if parent is None:
                    continue
                reciprocal = parent.children.get(cfg.project.id)
                if reciprocal is None:
                    # The migration's middle state: the parent moved this project
                    # from `children` to `upstream`, and this project has not yet
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
                        f"child locator for '{cfg.project.id}' does not point back to {root_of(cfg.path)}",
                    )
                if parent.project.id != parent_id:
                    self._problem(
                        parent.path,
                        f"registered key '{parent_id}' does not match target id '{parent.project.id}'",
                    )

    def _validate_upstreams(self) -> None:
        """An upstream is read-only, so it cannot also be something its declarer
        writes to — its own child or parent, or any project it reaches through
        them. Checked from the declarer, not from the current project: the conflict
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
        """Whether `locator`, read from `source_config`, names a project other than
        `expected` — as far as this machine can tell.

        An **absent** target cannot answer the question and must not be read as
        "no". Two projects routinely name each other at paths that exist only on the
        machine whose author wrote them: a monorepo nested inside an orchestrator
        on one disk and cloned beside it on another. Comparing a path that is
        here against a path that is not decides nothing, and deciding it against
        the declaration made every such pair non-reciprocal — the failure that
        made a provisioned parent unusable.

        Where both are present the comparison is real and the check is unchanged;
        the ids already agreed, or the caller would not have got this far.

        An entry holding only its ID has no locator to compare; two projects
        finding one ID at two folders is the duplicate ID instead (TCW-107
        Design 2.9, 3.2).
        """
        if _holds_only_id(locator):
            return False
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
                    f"cycle in projects involving '{project_id}'",
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
        override resolves; a directory holding the *wrong* project is known only
        once that project's config has been read, by the same mismatch check that
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
            # necessarily what the override pointed at. Name the project actually
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
                f"{root_of(copy)}; '{override.id}' is read from another branch "
                f"than the rest of the graph")

    def _problem(self, path: Path, message: str) -> None:
        rendered = f"{path}: {message}"
        if rendered not in self._problems:
            self._problems.append(rendered)
            self._findings.append(Finding("error", str(path), message))

    def _unreachable_edge(self, config_path: Path, project_id: str | None,
                          locator: Path | None,
                          declaration: RepositoryDeclaration | None = None, *,
                          message: str = "", decided_by: Any = None,
                          repository: str | None = None) -> None:
        """Record a declared project that is not here, rather than a problem.

        `project_id` is the key the declaring config used. It can be None only
        for the current project's own config, which is never an edge — the guard is
        here so a future caller cannot record a nameless entry that no message
        could ever render.
        """
        if not project_id:
            return
        if project_id in self._override_refused:
            # Told where it is, and it is not a project. That is a refusal, not a
            # thing to obtain, and `run tcw provision` would contradict it.
            return
        entry = UnreachableProject(id=project_id, locator=locator,
                                   declared_in=config_path,
                                   declaration=declaration, message=message,
                                   decided_by=decided_by, repository=repository)
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

    # -----------------------------------------------------------------------
    # Finding a project's folder from its ID (TCW-107 Design 2)

    def project_folder(self, project_id: str, named_by: Path) -> Path:
        """The root folder of project `project_id`, asked by the project at
        `named_by`, the one whose configuration, manifest or record names the
        ID (Design 2.12). Any valid ID: it need not appear under `projects:`.

        `named_by` must be a folder this registry has found: the active
        project's root, a project in its graph, or a folder an earlier call
        returned; anything else is a `ValueError`. Raises `Unreachable` for a
        project something names that is not on this machine, `UnknownProject`
        for an ID nothing names or holds, and `ProjectGraphError` for a graph
        problem, which is also added to `check()`.

        A method, because its answer depends on the active project's worktree
        and on what this command has already found (Design 2.9, 2.11 b)."""
        self._load_graph()
        root = self._root_key(named_by)
        if root not in self._found_roots():
            raise ValueError(f"{named_by} is not a project this registry has found")
        cfg = self._config_at(root)
        if cfg is not None and cfg.project.id == project_id:
            return root
        if cfg is not None and self._canonical(root / SENTINEL) not in self._cache:
            # Not in the graph: its family is located from it, so the walk of
            # Design 2.2 can read their manifests.
            for family_id in (*cfg.parent, *cfg.children):
                if family_id != project_id and self._known_folder(family_id) is None:
                    answer = self._locate(family_id, root)
                    if answer.folder is not None and self._checked(
                            family_id, answer) is None:
                        self._found.setdefault(family_id, answer.folder)
        answer = self._locate(project_id, root)
        if answer.problem is not None:
            raise ProjectGraphError(answer.problem)
        if answer.folder is None:
            if not answer.named:
                raise UnknownProject(f"no project with ID '{project_id}' is known or "
                                     f"found near this one; check the spelling")
            raise Unreachable(answer.message, project=project_id,
                              repository=answer.entry.repository if answer.entry
                              else None)
        problem = self._checked(project_id, answer)
        if problem is not None:
            raise ProjectGraphError(problem)
        self._found.setdefault(project_id, answer.folder)
        return answer.folder

    def found(self, project_id: str) -> dict | None:
        """How the lookup placed a project in the graph (Design 6.1): by a
        manifest, naming its file; by `TCW_PROJECT_<ID>`, naming it; or by the
        search. None for the current project and for one not here."""
        self._load_graph()
        cfg = self._by_id.get(project_id)
        if cfg is None or cfg.path == self._canonical(self._current_path):
            return None
        answer = self._placed.get(cfg.path)
        if answer is None:
            return None
        if answer.by == "manifest":
            return {"by": "manifest", "file": str(answer.entry.file)}
        if answer.by == "variable":
            return {"by": "variable", "name": override_variable(project_id)}
        return {"by": "search"}

    def _found_roots(self) -> set[Path]:
        return {self.project_root, *(root_of(path) for path in self._cache),
                *self._found.values()}

    def _checked(self, project_id: str, answer: _Answer) -> str | None:
        """The problem, recorded, with a found folder: one that does not hold
        `project_id` (only a variable can place one there), or another folder
        than the one this command already holds for the ID (Design 2.9)."""
        probe = self._probe(answer.folder)
        if probe.kind != "project" or probe.id != project_id:
            return self._recorded(
                answer.folder / SENTINEL,
                f"{override_variable(project_id)} names {answer.folder}, which does "
                f"not declare '{project_id}'")
        known = self._known_folder(project_id)
        if known is not None and self._identity(known) != self._identity(answer.folder):
            return self._recorded(
                answer.folder / SENTINEL,
                f"duplicate project id '{project_id}' also used by {known / SENTINEL}")
        return None

    def _recorded(self, path: Path, message: str) -> str:
        self._problem(path, message)
        return f"{path}: {message}"

    def _edge_target(self, source_config: Path, target_id: str,
                     entry: ConnectedProject) -> Path | None:
        """Where an edge's configuration is: for an entry holding only its ID,
        the answer the walk got (never looked up again, Design 2.11 b)."""
        if not _holds_only_id(entry):
            return self._target_path(source_config, entry)
        answer = self._answers.get((target_id, self._root_key(root_of(source_config))))
        if answer is None or answer.folder is None:
            return None
        return self._canonical(answer.folder / SENTINEL)

    def _root_key(self, root: Path) -> Path:
        """A project root under the first spelling met of its folder."""
        return root_of(self._canonical(Path(root) / SENTINEL))

    def _identity(self, root: Path) -> Any:
        try:
            found = root.stat()
        except OSError:
            return root
        return (found.st_dev, found.st_ino) if found.st_ino else root

    def _known_folder(self, project_id: str) -> Path | None:
        """The folder this command has found for `project_id`, if any."""
        cfg = self._by_id.get(project_id)
        if cfg is not None:
            return root_of(cfg.path)
        return self._found.get(project_id)

    def _config_at(self, root: Path) -> _Config | None:
        """The configuration of the project at `root`: the walk's, or read
        quietly to learn the project's family, its problems left to the walk
        or to `tcw validate` in that project."""
        path = self._canonical(root / SENTINEL)
        if path in self._cache:
            return self._cache[path]
        if path not in self._peeked:
            marks = (len(self._problems), len(self._findings), len(self._unreachable))
            cfg = self._read_config(path, None, root, quiet_connections=True)
            del self._problems[marks[0]:]
            del self._findings[marks[1]:]
            del self._unreachable[marks[2]:]
            self._peeked[path] = cfg
        return self._peeked[path]

    def _text(self, path: Path) -> str | Exception:
        """A file's text, or the error reading it, read at most once."""
        path = Path(path)
        if path not in self._texts:
            try:
                self._texts[path] = _read_text(path)
            except (OSError, UnicodeDecodeError) as error:
                self._texts[path] = error
        return self._texts[path]

    def _listing(self, folder: Path) -> list[tuple[str, bool]] | OSError:
        if folder not in self._listings:
            try:
                self._listings[folder] = _list_folder(folder)
            except OSError as error:
                self._listings[folder] = error
        return self._listings[folder]

    def _probe(self, folder: Path) -> _Probe:
        """What `folder`'s `.tcw/tcw-config.yaml` and root `tcw-config.yaml`
        say, the only two files the search reads in a folder (Design 2.6)."""
        if folder in self._probes:
            return self._probes[folder]
        text = self._text(folder / SENTINEL)
        if isinstance(text, str):
            probe = self._probe_text(text, folder / SENTINEL, legacy=False)
        elif isinstance(text, (FileNotFoundError, NotADirectoryError)):
            legacy = self._text(folder / LEGACY_SENTINEL)
            if isinstance(legacy, str):
                probe = self._probe_text(legacy, folder / LEGACY_SENTINEL, legacy=True)
            elif isinstance(legacy, (FileNotFoundError, NotADirectoryError)):
                probe = _Probe("none")
            else:
                probe = _Probe("unreadable", detail=str(legacy))
        else:
            probe = _Probe("unreadable", detail=str(text))
        self._probes[folder] = probe
        return probe

    @staticmethod
    def _probe_text(text: str, path: Path, *, legacy: bool) -> _Probe:
        try:
            raw = _load_named_yaml(text, path, _UniqueKeyLoader)
        except yaml.YAMLError as error:
            return _Probe("unreadable", detail=f"invalid YAML: {error}")
        if not isinstance(raw, dict):
            return _Probe("unreadable", detail="config must be a mapping")
        try:
            project_id = validate_project_id(str(raw.get("id") or ""))
        except ValueError:
            project_id = None
        if legacy:
            return _Probe("legacy", project_id)
        version = version_problem(raw)
        if version is not None:
            return _Probe("version", project_id, version)
        if project_id is None:
            return _Probe("unreadable", detail="missing or invalid project id")
        return _Probe("project", project_id)

    def _manifests_of(self, root: Path) -> list[tuple[Any, Path, dict]] | None:
        """`root`'s manifests, each as `(file as TCW names it, the root its
        paths are read from, entries)`, the personal one first, unless
        personal files are skipped (Design 1.10). None when one has a problem:
        it is recorded against its file, and a lookup that would consult it
        fails (Design 1.8)."""
        root = self._root_key(root)
        if root in self._manifests:
            return self._manifests[root]
        files = [] if personal_files_skipped() else [
            (personal_file(root, LOCAL_MANIFEST_NAME, self._anchors), True)]
        files.append((root / MANIFEST, False))
        result: list[tuple[Any, Path, dict]] | None = []
        for path, personal in files:
            text = self._text(path)
            if isinstance(text, (FileNotFoundError, NotADirectoryError)):
                continue
            problems: list[str] = []
            if isinstance(text, UnicodeDecodeError):
                problems.append(_not_utf8(text))
            elif isinstance(text, Exception):
                problems.append(f"cannot be read: {text}")
            else:
                try:
                    mapping = _load_named_yaml(text, path, _UniqueKeyLoader)
                except yaml.YAMLError as error:
                    problems.append(f"invalid YAML: {error}")
                else:
                    entries, problems = parse_manifest(mapping, path, personal=personal)
                    if not problems and result is not None:
                        result.append((path, root, entries))
            for problem in problems:
                self._problem(path, problem)
            if problems:
                self._manifest_problem.setdefault(root, f"{path}: {problems[0]}")
                result = None
        self._manifests[root] = result
        return result

    def _family(self, named_by: Path, project_id: str) -> tuple[list[Path], set[str]]:
        """The roots whose manifests the lookup of `project_id` from
        `named_by` consults, in Design 2.2's order, and every ID their
        `projects:` entries name.

        `named_by`, then each ancestor nearest first, then each descendant
        breadth first, children in the order the configuration lists them. A
        project is consulted only once this command has found its folder. One
        whose folder is the one being looked up is skipped; when its folder is
        known the walk carries on through its configuration, and otherwise it
        stops there. A record of the folders visited ends a cycle."""
        cfg = self._config_at(named_by)
        order = [named_by]
        named = _named_ids(cfg)
        seen = {self._identity(named_by)}

        def member(member_id: str) -> tuple[Path | None, _Config | None]:
            folder = self._known_folder(member_id)
            if folder is None or self._identity(folder) in seen:
                return None, None
            seen.add(self._identity(folder))
            here = self._config_at(folder)
            if member_id != project_id:
                order.append(folder)
                named.update(_named_ids(here))
            return folder, here

        current = cfg
        while current is not None and current.parent:
            _, current = member(next(iter(current.parent)))
        queue = [cfg] if cfg is not None else []
        while queue:
            for child_id in queue.pop(0).children:
                folder, child = member(child_id)
                if child is not None:
                    queue.append(child)
        return order, named

    def _locate(self, project_id: str, named_by: Path) -> _Answer:
        """Design 2.1-2.8, answered once per question for the whole command."""
        key = (project_id, self._root_key(named_by))
        if key not in self._answers:
            self._answers[key] = self._answer(project_id, key[1])
        return self._answers[key]

    def _answer(self, project_id: str, named_by: Path) -> _Answer:
        override = self._override_path(project_id)
        if override is not None:
            if project_id in self._override_refused:
                return _Answer(problem=next(o.problem for o in self._overrides
                                            if o.id == project_id and o.problem))
            return _Answer(folder=root_of(override), by="variable")
        roots, named = self._family(named_by, project_id)
        for root in roots:
            manifests = self._manifests_of(root)
            if manifests is None:
                return _Answer(problem=self._manifest_problem[self._root_key(root)])
            for _, base, entries in manifests:
                if project_id in entries:
                    return self._entry_answer(entries[project_id], base)
        matches, problems = _search(self, project_id, named_by)
        if problems:
            rendered = [self._recorded(path, message) for path, message in problems]
            return _Answer(problem=rendered[0], named=True)
        distinct: dict[Any, Path] = {}
        for match in matches:
            folder = root_of(self._worktree_copy(_config_file(match / SENTINEL)))
            distinct.setdefault(self._identity(folder), folder)
        if len(distinct) > 1:
            folders = " and ".join(str(f) for f in distinct.values())
            return _Answer(problem=self._recorded(
                named_by / SENTINEL,
                f"project '{project_id}' is declared by more than one folder near "
                f"this one: {folders}; add an entry for '{project_id}' to "
                f"{LOCAL_MANIFEST} (this machine) or {MANIFEST} (everyone)"))
        if distinct:
            return _Answer(folder=next(iter(distinct.values())), by="search")
        return _Answer(named=project_id in named, message=(
            f"project '{project_id}' is not on this machine: no manifest lists it, "
            f"and no folder next to {named_by} or enclosing it declares it; add it "
            f"to {MANIFEST} or {LOCAL_MANIFEST}"))

    def _entry_answer(self, entry: ManifestEntry, base: Path, *,
                      record: bool = True) -> _Answer:
        """Design 2.3: the deciding entry decides, whatever is on disk. A
        problem is recorded unless `record` is false, when it is only
        returned, unrendered (for `manifest_findings`)."""
        named = f"entry for '{entry.id}' in {entry.file}"
        try:
            written = str(Path(entry.path).expanduser())
        except RuntimeError as error:       # `~name` naming no user
            return _Answer(entry=entry, problem=self._recorded(entry.file, f"{named}: {error}")
                           if record else f"{named}: {error}")
        folder = root_of(self._locator_path(base / SENTINEL, written))
        probe = self._probe(folder)
        if probe.kind == "project" and probe.id == entry.id:
            return _Answer(folder=folder, by="manifest", entry=entry)
        if probe.kind == "project":
            wrong = f"places it at {folder}, which declares '{probe.id}', not '{entry.id}'"
        elif probe.kind == "version":
            wrong = f"places it at {folder}, whose {SENTINEL} {probe.detail}"
        elif probe.kind == "legacy":
            wrong = f"places it at {legacy_message(folder)}"
        elif probe.kind == "unreadable":
            wrong = f"places it at {folder}, whose {SENTINEL} cannot be read: {probe.detail}"
        else:
            listing = self._listing(folder)
            if isinstance(listing, FileNotFoundError) or (
                    isinstance(listing, list) and [n for n, _ in listing] in ([], [".git"])):
                only_git = isinstance(listing, list) and bool(listing)
                return _Answer(entry=entry, entry_folder=folder, named=True,
                               message=self._not_here(entry, only_git))
            if isinstance(listing, OSError):
                wrong = (f"places it at {folder}, which cannot be listed, so whether "
                         f"it is empty is not known: {listing.strerror or listing}")
            else:
                wrong = (f"places it at {folder}, which is not a TCW project: it "
                         f"holds files and no {SENTINEL}")
        return _Answer(entry=entry, problem=self._recorded(entry.file, f"{named} {wrong}")
                       if record else f"{named} {wrong}")

    def manifest_files(self) -> set:
        """The active project's two manifests, as TCW names them."""
        root = self._root_key(self.project_root)
        return {root / LOCAL_MANIFEST, root / MANIFEST}

    def manifest_findings(self) -> list[Finding]:
        """`tcw validate`'s check of every entry in the active project's two
        manifests, whether or not `projects:` names the ID (Design 5.1): an
        entry whose folder is not here, or empty, is `unresolved`; one whose
        folder is wrong is an `error`, or a `warning` when the shared entry
        does not decide on this machine because the personal manifest or
        `TCW_PROJECT_<ID>` places the project. A manifest with a format
        problem is already a graph problem, and gives nothing here."""
        self._load_graph()
        manifests = self._manifests_of(self.project_root) or []
        personal = {entry_id: file for file, _, entries in manifests
                    if file.name == LOCAL_MANIFEST_NAME for entry_id in entries}
        findings: list[Finding] = []
        for file, base, entries in manifests:
            for entry in entries.values():
                answer = self._entry_answer(entry, base, record=False)
                if answer.folder is not None:
                    continue
                if answer.problem is None:
                    findings.append(Finding("unresolved", str(file), answer.message))
                    continue
                by = None
                if file.name != LOCAL_MANIFEST_NAME:
                    by = (str(personal[entry.id]) if entry.id in personal
                          else self._variable_places(entry.id))
                if by is None:
                    findings.append(Finding("error", str(file), answer.problem))
                else:
                    findings.append(Finding(
                        "warning", str(file),
                        f"{answer.problem} (overridden on this machine by {by})"))
        return findings

    @staticmethod
    def _variable_places(project_id: str) -> str | None:
        """`TCW_PROJECT_<ID>`'s name when it names a folder on this machine,
        read without recording it as an override in force."""
        name = override_variable(project_id)
        value = (os.environ.get(name) or "").strip()
        if not value:
            return None
        try:
            return name if Path(value).expanduser().is_dir() else None
        except (RuntimeError, OSError):
            return None

    @staticmethod
    def _not_here(entry: ManifestEntry, only_git: bool) -> str:
        """Design 6.2's message for a project its deciding entry places in a
        folder that is not here, or empty."""
        message = (f"project '{entry.id}' is not on this machine: {entry.file} places "
                   f"it at {entry.path}")
        if entry.repository is None:
            return message + (f"; {_holds_only_git(entry.path)}" if only_git else "")
        fetch = f"fetch it with 'tcw project provision {entry.id}'"
        if only_git:
            fetch = f"{_holds_only_git(entry.path)}, then {fetch}"
        return f"{message}, from {entry.repository}; {fetch}"

    def _search_candidates(self, named_by: Path):
        """The folders the search tests, in order: each folder next to
        `named_by` (Design 2.4), then each folder enclosing it (2.5).

        Inside the active project's linked worktree (Design 4.3), what lies
        outside the repository is read from the main checkout: when `named_by`
        is the worktree's top folder, the folders next to it are those next to
        the main checkout; the enclosing folders are the worktree's own up to
        its top, then those enclosing the main checkout, whose own root is not
        tested again."""
        holder, own, enclosing = named_by.parent, named_by, list(named_by.parents)
        if self._anchors is not None and _below(named_by, self._anchors[0]) is not None:
            top, main = self._anchors
            if named_by == top:
                holder, own = main.parent, main
            enclosing = [p for p in named_by.parents if _below(p, top) is not None]
            enclosing += list(main.parents)
        listing = self._listing(holder)
        if isinstance(listing, list):
            for name, is_dir in listing:
                folder = holder / name
                if (is_dir and name != TCW_FOLDER and folder != own
                        and not self._protected(folder)):
                    yield folder
        yield from enclosing

    @staticmethod
    def _protected(folder: Path) -> bool:
        """Whether `folder` is one macOS asks a person's permission to read:
        Desktop, Documents or Downloads, directly in the home folder. Never
        tested as a folder next to a project, so a project kept directly in
        the home folder does not make the search read inside one the person
        never passed through. The search still tests such a folder as one
        enclosing a project, which the person is already working inside."""
        if not _ON_MACOS or folder.name not in _PROTECTED_NAMES:
            return False
        try:
            home = Path.home().resolve()
        except (RuntimeError, KeyError, OSError):
            return False
        return folder.parent == home


def _named_ids(cfg: _Config | None) -> set[str]:
    if cfg is None:
        return set()
    return {*cfg.parent, *cfg.children, *cfg.upstream}


def _not_utf8(error: UnicodeDecodeError) -> str:
    return (f"is not valid UTF-8 text (byte "
            f"0x{error.object[error.start:error.start + 1].hex()} "
            f"at position {error.start})")
