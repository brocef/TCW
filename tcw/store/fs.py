"""Filesystem store adapters + the FS-local helpers they share.

`git_root`/`init` (Phase 1) scaffold; `FsTaxonomyStore` (Phase 2) realizes the
`TaxonomyStore` interface over `docs/taxonomy/`. The capabilities and work
adapters land here in their phases; the genuinely-shared primitives get factored
into a tree-store core in Phase 4 (don't pre-abstract —
`docs/lifecycle/implementation.md`).
"""

# Defer annotation evaluation (PEP 563) so forward refs like `"TermDetail" | None`
# don't raise at class-definition time on Python 3.11–3.13. See tcw/store/base.py.
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from contextlib import suppress
from functools import cached_property
from pathlib import Path

import yaml

from tcw.store.yaml_source import load as _load_named_yaml
from tcw.store.base import (
    CAP_FIELDS, CAP_LIFECYCLES, CAP_PRIORITIES, CAP_STATUSES,
    TAXONOMY_EDITABLE_FIELDS, _UNSET, AmbiguousRef, Capability, CapabilitiesStore,
    CapabilityDetail, RefError, slugify, StaleRevision, parse_connected_entry,
    parse_repository_declaration, ProvisionResult, RepositoryDeclaration,
    StoreDeclarationError, StoreLocationUnusable, StoreNotProvisioned,
    StoreProvisioner, UnreachableProject, TaxonomyStore, Term, TermDetail,
)
from tcw.store import config_edit
from tcw.store.checkouts import (
    checkout_root, provisioned_root as provisioned_store_root,
)
from tcw.store.project import (FsProjectRegistry, _below, validate_project_id,
                               worktree_anchors)

# Component trees `tcw init` scaffolds. `work` gets a status-folder skeleton;
# `taxonomy` and `capabilities` are flat trees that fill in per their phases.
COMPONENTS = ("taxonomy", "capabilities", "work")


def _store_classes() -> dict:
    """Component → filesystem store class. A function, and consulted through the
    `STORE_CLASSES` mapping below, because the classes are defined further down
    this module than the helpers that need them."""
    return {"taxonomy": FsTaxonomyStore,
            "capabilities": FsCapabilitiesStore,
            "work": WorkLocation}


class WorkLocation:
    """The work store as the location ladder sees it (TCW-70 Design 3.4-3.5).

    The work path is found as every store's location is (`work.path`, else
    `docs/work`, re-anchored in a linked worktree, else a declared repository's
    provisioned checkout). It is usable when the directory is there: an empty
    store is a real state, and nothing inside it is required.
    """

    COMPONENT = "work"

    def __init__(self, root: Path):
        self.root = root

    @classmethod
    def open(cls, node_root: Path) -> "WorkLocation":
        return resolve_store(cls, Path(node_root))

    @classmethod
    def _local_root(cls, node_root: Path, configured: str | None) -> Path:
        if configured is None:
            return node_root / "docs" / cls.COMPONENT
        value = Path(configured).expanduser()
        if value.is_absolute():
            return value
        return anchor_configured_path(node_root, value) / value

    @classmethod
    def _open_at(cls, raw_root: Path, node_root: Path, config_path: Path, *,
                 external: bool, must_exist: bool = True, declaration=None,
                 _walk=None) -> "WorkLocation":
        if not raw_root.is_dir():
            raise StoreLocationUnusable(
                f"{config_path}: work.path is not a directory: {raw_root}")
        return cls(raw_root.resolve())


class _StoreClasses:
    """Lazy view over `_store_classes()`, so `find_node` and `run_provision` name
    one mapping instead of each growing its own `if component ==` ladder — the
    shape that once left `run_provision` opening the work store for every
    component it looped over."""

    def __getitem__(self, component: str):
        try:
            return _store_classes()[component]
        except KeyError:
            raise ValueError(
                f"unknown component '{component}'; "
                f"choose from: {', '.join(COMPONENTS)}") from None

    def __contains__(self, component: str) -> bool:
        return component in _store_classes()


STORE_CLASSES = _StoreClasses()


def _modified_timestamp(resources: list[Path]) -> str:
    existing = [path for path in resources if path.is_file()]
    if not existing:
        return ""
    modified = max(path.stat().st_mtime for path in existing)
    return datetime.fromtimestamp(modified, timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )


def _capability_resources(folder: Path, meta: dict) -> list[Path]:
    names = [
        "meta.yaml",
        "description.md",
        *_as_list(meta.get("prependedDocs")),
        *_as_list(meta.get("appendedDocs")),
    ]
    return [folder / name for name in names]


# ── git + node helpers (FS-adapter local details, not store-interface ops) ──

#: How to read git's `-z` path output. `-z` prints a path's raw bytes, and one
#: that is not UTF-8 must not crash the decode; `surrogateescape` round-trips it
#: back to the same bytes when it becomes a `Path` again.
_GIT_PATHS = {"encoding": "utf-8", "errors": "surrogateescape"}


def _git(*args, **kwargs):
    """Run a `git` command with stdin closed.

    None of these calls take input on stdin and none contact a remote, so this
    closes no *known* hang — git redirects its own hooks' stdin, which was the
    failure this was first written for and which turned out not to exist.

    It stands as an invariant instead: a child process that reads no stdin does
    not get the parent's. Every `subprocess` call in this module is a git call,
    so this is the single place that has to hold it, and
    `tests/test_subprocess_stdin.py` enforces the same rule package-wide — which
    is what caught the three `serve` spawns that do matter.
    """
    stdin = kwargs.pop("stdin", subprocess.DEVNULL)
    return subprocess.run(*args, stdin=stdin, **kwargs)


INDEX_LOCK_RETRY = 2.0


def _git_index(args: list, check: bool = False, **kwargs) -> "subprocess.CompletedProcess":
    """Run a git command that takes the index (`add`, `mv`, `rm`, `commit`),
    retrying briefly while another git process holds `index.lock`.

    Another session's commit, an editor's git integration, or a `git status`
    can hold the index for a moment. This store's own writers are kept apart
    by `_store_lock`; nothing can keep them apart from git run by something
    else, so a failure is retried for up to `INDEX_LOCK_RETRY` seconds while
    the lock file exists. The test is the file, never git's message, which is
    translated and changes between versions. A lock that outlives the wait —
    often one a crashed git left behind — is named in the error.

    Always captures output, so a retried failure does not print once per try.
    `check=True` raises `CalledProcessError` carrying git's own stderr."""
    kwargs.setdefault("capture_output", True)
    kwargs.setdefault("text", True)
    root = args[args.index("-C") + 1] if "-C" in args else "."
    deadline = time.monotonic() + INDEX_LOCK_RETRY
    lock = None
    while True:
        r = _git(args, **kwargs)
        if r.returncode == 0:
            return r
        if lock is None:
            where = _git(["git", "-C", str(root), "rev-parse", "--git-path", "index.lock"],
                         capture_output=True, text=True)
            lock = (Path(root) / where.stdout.strip()) if where.returncode == 0 else Path()
        # Retried while the lock file is there, or on git's exit 128 — what a
        # lock it could not create exits with — since the other process may
        # have finished between the failure and this check. A refusing
        # `pre-commit` hook exits 1 and is never run twice.
        held = bool(lock.name) and lock.exists()
        if not (held or r.returncode == 128) or time.monotonic() >= deadline:
            break
        time.sleep(0.1)
    if lock is not None and lock.name and lock.exists():
        note = (f"\n{lock} is still there after {INDEX_LOCK_RETRY:g}s. If no other git "
                f"process is running, a crashed one left it behind: delete it by hand "
                f"and retry.")
        if isinstance(r.stderr, str):
            r = subprocess.CompletedProcess(r.args, r.returncode, r.stdout,
                                            r.stderr.rstrip("\n") + note)
    if check:
        raise subprocess.CalledProcessError(r.returncode, args, r.stdout, r.stderr)
    return r


def _literal(path: "str | Path") -> str:
    """`path` as a git pathspec that means only itself.

    Git reads every path argument as a pattern, even after `--`, so a store
    folder named `a*` would also match `abc`. Per path rather than
    `--literal-pathspecs`: that flag works by exporting `GIT_LITERAL_PATHSPECS`,
    which the hooks `git commit` runs would inherit, and a user's hook filtering
    on `'*.py'` would then silently match nothing. Not for `git mv`, which takes
    plain paths and rejects the prefix.

    Plain when `GIT_LITERAL_PATHSPECS` is already on — git exports it to hooks
    and aliases run under `git --literal-pathspecs` — because git then reads the
    prefix as part of a file name, and every path is literal anyway."""
    setting = os.environ.get("GIT_LITERAL_PATHSPECS", "").strip().lower()
    if setting in ("true", "yes", "on") or (setting.isdecimal() and int(setting)):
        return str(path)
    return f":(literal){path}"


def git_root(start: Path | None = None) -> Path | None:
    """Top of the git work-tree containing `start` (cwd by default), or None.

    Shells out to git so worktrees/submodules resolve correctly — more correct
    on edge cases than walking up looking for a literal `.git` dir.
    """
    start = (start or Path.cwd()).resolve()
    try:
        out = _git(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return Path(out)


SENTINEL = "tcw-config.yaml"
def write_sentinel(root: Path, project_id: str | None = None) -> bool:
    """Create or backfill the node sentinel without discarding configuration.

    Backfilling adds one `id:` line and touches nothing else in the file. `True`
    only when it wrote.
    """
    p = root / SENTINEL
    existing = load_config(p) if p.exists() else {}
    text = config_edit.edit_text(p, config_edit.read_text(p),
                                 _sentinel_edits(p, existing, project_id))
    if text is None:
        return False
    _atomic_write_all([(p, text)])
    return True


def _sentinel_edits(p: Path, existing: dict, project_id: str | None) -> list:
    """The edit that gives the sentinel its `id`, or none when it has one.

    `id: null` counts as none. It used to be read that way and then written
    back unchanged — `{"id": new, **existing}` let the old `None` win — while
    reporting a successful backfill.
    """
    configured = existing.get("id")
    if configured is not None:
        if not isinstance(configured, str):
            raise ValueError(f"{p}: project ID must be a string")
        configured = validate_project_id(configured)
        if project_id is not None and validate_project_id(project_id) != configured:
            raise ValueError(
                f"project already has id '{configured}'; refusing conflicting id '{project_id}'"
            )
        return []
    # Direct adapter callers (principally isolated store tests) receive a stable
    # fixture identity. The public CLI enforces explicit --id before calling us.
    return [config_edit.SetId(validate_project_id(project_id or "test-project"))]


def find_node_root(start: Path | None = None) -> Path | None:
    """The nearest ancestor of `start` (cwd by default) holding a `tcw-config.yaml`
    *file* — the node root, or None. FS-adapter-local: realizes 'locate the node'.
    Resolves `start` (like `git_root`) so a symlinked cwd chains identically."""
    d = (start or Path.cwd()).resolve()
    while True:
        if (d / SENTINEL).is_file():
            return d
        if d == d.parent:                  # filesystem-root fixpoint
            return None
        d = d.parent


# Files an operating system writes into any folder a file browser opens. Named
# exactly, never by pattern: removing a term deletes these if nothing else is
# left, and a pattern would reach files a person made.
OS_METADATA_FILES = frozenset({".DS_Store", "Thumbs.db", "desktop.ini"})


def _untracked_under(folder: Path, tracked: set[Path]) -> list[Path]:
    """Files (and symlinks) under `folder` that are not in `tracked`, skipping
    operating-system metadata files. Symlinks are listed, never followed, and
    compared as themselves: `tracked` holds paths with their folders resolved
    and their last component as git lists it."""
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(folder, followlinks=False):
        base = Path(dirpath)
        links = [n for n in dirnames if (base / n).is_symlink()]
        for name in [*filenames, *links]:
            path = base / name              # `base` is under the resolved folder
            if name not in OS_METADATA_FILES and path not in tracked:
                found.append(path)
    return sorted(found)


def find_node(component: str, start: Path | None = None) -> Path | None:
    """The node owning `component`'s store, or None. A node is the nearest
    ancestor marked by a `tcw-config.yaml` sentinel (FS-adapter-local). Returns
    the node iff it has that component, preserving the prior contract.

    "Has that component" is asked of the *resolved* store, never of a literal
    `docs/<component>` folder. The two answers differ in exactly the case this
    feature exists for: a checkout that cloned only the code repository has no
    `docs/taxonomy/`, because the taxonomy is in the other repository — so
    looking for the folder answered None before the resolution ladder could read
    the declaration, and the node's own config went unread.
    """
    nr = find_node_root(start)
    if nr is None:
        return None
    FsProjectRegistry.open(nr).require_valid()
    try:
        store = STORE_CLASSES[component].open(nr)
    except (StoreNotProvisioned, StoreDeclarationError):
        # Not "no node here" — the node is right in front of us and says where
        # its store comes from. Flattening this to None is what made `tcw work
        # list` answer a declared-but-absent store with "run `tcw init`", which
        # would scaffold a second, empty store beside the real one.
        #
        # A *malformed* declaration is the same node with the same hazard, only
        # the actionable message is "fix this line" rather than "run this
        # command", so it travels the same way.
        raise
    except StoreLocationUnusable:
        # The one failure that means "there is no store at this location" — the
        # ladder's own definition (see `resolve_store`). Anything else, a broken
        # `extends` or a malformed `<component>.path`, is a node that is here and
        # wrong, and "run `tcw init`" is the wrong advice for it.
        return None
    # A work store that opened is a work store; a tree store's `open` validates
    # nothing when nothing is configured (rule 4), so the "is this component
    # here at all?" question is still this function's to ask. Asked of the
    # resolved root rather than the default one, which is the whole point.
    return nr if component == "work" or store.root.is_dir() else None


def tree_store_present(node_root: Path, component: str) -> bool:
    """Whether this node has a `component` tree store to check: its default
    folder is there, or its config says where the store is (`<c>.path` or
    `<c>.repository`, any value but null — a malformed one is present and must
    be reported, not skipped). FS-adapter-local, like `find_node`.

    Asked by `FsCapabilitiesStore._taxonomy` instead of
    `(node_root / "docs" / component).is_dir()`, which is true of neither a moved
    store nor one kept in another repository — so capabilities never checked
    Subject or Feature against a moved taxonomy. Deliberately not "open it and
    see", which `tcw validate` uses: `extends` alone is not a location, and a
    node that only inherits a taxonomy should not have its capability checks
    fail on that inheritance.
    """
    if (node_root / "docs" / component).is_dir():
        return True
    try:
        config = load_config(node_root / SENTINEL)
    except ValueError:
        return False            # a broken config is reported where it is read
    section = config.get(component) if isinstance(config, dict) else None
    return isinstance(section, dict) and (
        section.get("path") is not None or section.get("repository") is not None)


# The three helpers below enumerate the graph, and a graph may now be partial —
# a connected project whose repository is not in this checkout is absent from it
# rather than fatal to it. Each therefore answers for what is here, deliberately:
# a topology is the set of nodes this machine can actually open, and a caller
# that needs the graph complete says so in its own message. What none of them
# may do is imply the absent node was never declared.
def child_nodes(root: Path) -> list[Path]:
    """Direct registered children that contain a work store."""
    registry = FsProjectRegistry.open(root).require_valid()
    return [
        Path(project.locator)
        for project in registry.children()
        if _has_work_store(Path(project.locator))
    ]


def _routed(root: Path) -> "tuple[list[Path], list[UnreachableProject]]":
    """One walk down `root`'s own registry: the nearest node with a work store on
    each branch, and every declared child found absent on the way.

    **One registry, opened at `root`.** Opening another at each routing node
    looks equivalent and is not: worktree aliasing depends on where a registry
    was opened, so from a linked worktree a routing node's own registry can see
    the primary checkout's copy of `root` and refuse a graph `root`'s registry
    accepts — which broke `delegate` even to a direct child."""
    registry = FsProjectRegistry.open(root).require_valid()
    found: list[Path] = []
    absent: list = []

    def walk(project_id: str | None) -> None:
        for child_id in registry.declared_child_ids(project_id):
            project = registry.get(child_id)
            if project is None:
                if (entry := registry.unreachable_project(child_id)) is not None:
                    absent.append(entry)
                continue
            child = Path(project.locator)
            if _has_work_store(child):
                found.append(child)
            else:
                walk(child_id)      # a routing node; `require_valid` ruled out cycles
    walk(None)
    return found, absent


def routed_children(root: Path) -> list[Path]:
    """The nearest node with a work store on each branch below `root`: a
    registered child that keeps a board, or — for one that does not, a routing
    node — its own routed children. The downward mirror of
    `nearest_work_ancestor`, for `delegate`: coordination passes through a node
    that only groups others, and stops at the first one that keeps a board.
    A declared but unprovisioned store counts as none, as it does going up."""
    return _routed(root)[0]


def routed_unreachable_children(root: Path) -> "list[UnreachableProject]":
    """`unreachable_children` of `root` and of every routing node on the way
    down, so a target declared behind one is reported as absent, not unknown."""
    return _routed(root)[1]


def parent_node(root: Path) -> Path | None:
    """Direct registered parent that contains a work store.

    The *direct* question, for callers that mean it — `tcw work nodes` prints
    this node's parent, not the nearest one that happens to keep a board. A walk
    up the graph wants `nearest_work_ancestor` instead.
    """
    registry = FsProjectRegistry.open(root).require_valid()
    parent = registry.parent()
    if parent is None:
        return None
    path = Path(parent.locator)
    return path if _has_work_store(path) else None


def registered_parent(root: Path) -> Path | None:
    """Direct registered parent, board or no board.

    What `parent_node` answers before the store filter. `tcw work nodes` needs
    both to tell "no parent registered" apart from "the registered parent keeps
    no board", which used to print identically.
    """
    parent = FsProjectRegistry.open(root).require_valid().parent()
    return None if parent is None else Path(parent.locator)


def registered_children(root: Path) -> list[Path]:
    """Direct registered children, board or no board.

    What `child_nodes` answers before the store filter. `tcw work nodes` needs
    the unfiltered list: a routing node that keeps no board is still a child, and
    omitting it made a node with one read as a leaf.
    """
    registry = FsProjectRegistry.open(root).require_valid()
    return [Path(project.locator) for project in registry.children()]


def unreachable_parent(root: Path) -> "UnreachableProject | None":
    """The declared parent this checkout does not have, or None.

    What `registered_parent` cannot answer: it returns a path, and a project
    that is not here has none. Without this, `tcw work nodes` printed
    `(none — root)` for a node whose config plainly names a parent — the exact confusion the comment above
    `child_nodes` forbids, and which `docs/guide/multi-repo.md` promises does
    not happen.
    """
    registry = FsProjectRegistry.open(root).require_valid()
    parent_id = registry.declared_parent_id()
    if parent_id is None or registry.get(parent_id) is not None:
        return None
    return registry.unreachable_project(parent_id)


def unreachable_children(root: Path) -> "list[UnreachableProject]":
    """The declared children this checkout does not have. See
    `unreachable_parent`."""
    registry = FsProjectRegistry.open(root).require_valid()
    absent = []
    for child_id in registry.declared_child_ids():
        if registry.get(child_id) is not None:
            continue
        entry = registry.unreachable_project(child_id)
        if entry is not None:
            absent.append(entry)
    return absent


def descendant_nodes(root: Path) -> list[Path]:
    """All registered descendants that contain a work store."""
    registry = FsProjectRegistry.open(root).require_valid()
    return [
        Path(project.locator)
        for project in registry.descendants()
        if _has_work_store(Path(project.locator))
    ]


def _has_work_store(node_root: Path) -> bool:
    """Whether `node_root` has a usable work store. The *configured* store is the
    only authority: a literal `docs/work` folder must not vouch for a node whose
    `work.path` points somewhere else (or somewhere broken).

    A declared-but-unprovisioned store answers `False` here rather than raising,
    unlike `find_node`. The difference is whose store is being asked about: this
    one is asked about *other* nodes while listing a topology, and one
    unprovisioned child must not turn a parent's listing into a hard failure.
    "No usable store here" is true of such a node, and it is the answer every
    caller of this function actually wants.
    """
    try:
        WorkLocation.open(node_root)
        return True
    except ValueError:                     # StoreNotProvisioned included, by design
        return False


def unreachable_project_note(registry, project_id: str) -> str | None:
    """"Declared but not reachable here" for `project_id`, or None.

    One renderer for every site that resolves a project id and got None back.
    Without it each message says the project was never registered, which sends
    the reader to their config to add a declaration that is already there.
    """
    absent = registry.unreachable_project(project_id)
    if absent is None:
        return None
    if absent.declaration is not None:
        # A declared project has a remedy, so the message names it rather than
        # only the symptom — the same shape `StoreNotProvisioned` uses.
        return (f"project '{project_id}' is declared in {absent.declaration.url} "
                f"but has not been provisioned here; run `tcw provision` to "
                f"obtain it")
    return (f"project '{project_id}' is declared in {absent.declared_in} but is "
            f"not reachable in this checkout ({absent.locator})")


def registered_project_id(anchor: Path, target: Path) -> str:
    """Return the canonical ID for a project reachable from ``anchor``."""
    target = target.resolve()
    registry = FsProjectRegistry.open(anchor).require_valid()
    projects = [registry.current, *registry.ancestors(), *registry.descendants()]
    for project in projects:
        if Path(project.locator).resolve() == target:
            return project.id
    raise ValueError(f"{target} is not registered from project '{registry.current.id}'")


def _warn_hidden(node_root: Path, *paths: Path) -> None:
    """Say on stderr that an ignore rule is hiding a write we just made.

    A rule can be written at any time, so this is checked at write time:
    the file is still written, and the user is just told git has no record.

    Advisory, on stderr, warn-and-proceed.

    # ponytail: no de-duplication — a command staging two hidden paths in two
    # calls prints two lines. Only happens in an already-broken setup, and a
    # cache is state this function does not otherwise carry.
    """
    hidden = list(paths)
    shown = []
    for p in hidden:
        try:
            shown.append(str(p.relative_to(node_root)))
        except ValueError:
            shown.append(str(p))
    print(f"tcw: a .gitignore rule hides {', '.join(shown)}; it is on disk but "
          f"git will not record it. Remove the rule, or run `git add -f` on it.",
          file=sys.stderr)


def git_stage(node_root: Path, *paths: Path) -> None:
    """Stage paths, dropping any git ignores: `git add` on an ignored path
    fails outright rather than no-opping. A dropped path is reported — see
    `_warn_hidden`."""
    ignored = [p for p in paths if git_ignored(node_root, p)]
    # Only paths that are actually there: `start` stages the *vacated* source
    # folder as a deletion, and warning about one that no longer exists would
    # be false. Sound as well as convenient — plain `check-ignore` reports a
    # tracked path as not ignored, so a dropped path is always untracked.
    live = [str(p) for p in paths if p not in ignored]
    if live:
        _git_index(["git", "-C", str(node_root), "add", "--", *map(_literal, live)],
                   check=True)
    # After the `git add`, not before: if staging the live paths is refused the
    # caller rolls the whole write back, and a warning already on stderr saying
    # the dropped path "is on disk" would be false by the time it is read.
    _warn_hidden(node_root, *(p for p in ignored if p.exists() or p.is_symlink()))


def _same_folder(a: Path, b: Path) -> bool:
    """Whether `a` and `b` are one folder. One gone since it was listed or
    resolved is not a match; any other error leaves the question open, so it
    propagates and the caller's delete stops."""
    try:
        return a.samefile(b)
    except FileNotFoundError:
        return False


def git_rm(node_root: Path, path: Path) -> None:
    # -f so a term staged-but-not-yet-committed (just `add`ed) can still be removed.
    # Literal: `--` ends options but a path is still a glob to git, so removing
    # a folder named `a*` would also delete `abc`.
    _git_index(["git", "-C", str(node_root), "rm", "-rfq", "--", _literal(path)],
               check=True)


NOT_A_REPOSITORY = "not inside a git repository. Run `git init` first."


def require_repository(root: Path) -> None:
    """Refuse a filesystem-store write outside git.

    A filesystem-adapter precondition, not a model concept — a remote store has
    no repository to require, so nothing about this belongs in the abstract
    interface. `ValueError` because that is already how the store interface says
    "this write is refused", which means every existing CLI and HTTP handler
    reports it without new plumbing.
    """
    if git_root(root) is None:
        raise ValueError(NOT_A_REPOSITORY)


def git_ignored(node_root: Path, path: Path, *, no_index: bool = False) -> bool:
    """Whether `.gitignore` excludes `path`. False outside a repository.

    `no_index=True` asks the ignore *rules* instead. Plain `check-ignore` reports
    a tracked path as not ignored however the rules read, which is what the
    staging callers want — it mirrors what `git add` is about to do — and the
    wrong question for anyone asking whether files written there later will be
    recorded at all.
    """
    return _git(
        ["git", "-C", str(node_root), "check-ignore", "-q",
         *(["--no-index"] if no_index else []), "--", str(path)],
        capture_output=True).returncode == 0


def init(components: list[str], root: Path, project_id: str | None = None,
         work_path: Path | None = None,
         paths: dict[str, Path] | None = None) -> list[Path]:
    """Scaffold `docs/<component>/` skeletons under `root` and mark it a node.
    Returns the dirs made. A `.gitkeep` lands in each so the empty skeleton
    survives a commit (git doesn't track empty directories).

    The work component is one directory and its `.gitkeep`, nothing else: no
    status folders and no ignore rules (TCW-70 Design 11). Unstaged, like
    everything else init writes.
    """
    # Read ahead of `write_sentinel`, so its own mapping check no longer runs
    # first — a malformed config used to come back from it as a `ValueError` and
    # would otherwise surface here as an `AttributeError` from `.get`.
    existing_config = load_config(root / SENTINEL)
    # `work_path` kept as its own parameter rather than folded into `paths`:
    # it is the fourth positional argument every existing caller passes, and
    # this component's location has a name in the CLI (`--work-path`,
    # `tcw init work --work-path`) that predates the mapping.
    paths = dict(paths or {})
    if work_path is not None:
        paths["work"] = work_path
    work_path = paths.get("work")
    # A location read back from the file is used, never written: writing it
    # would replace what the user typed (`./store`, `~/store`) with its
    # normalized, home-expanded form.
    read_from_config: set[str] = set()
    # Every component, not only `work`: `tcw taxonomy init` used to scaffold
    # `docs/taxonomy` under a configured `taxonomy.path`, so the "run `tcw
    # init`" advice for a configured-but-absent store never came true.
    configured_text: dict[str, str] = {}
    for c in components:
        if c in paths:
            continue
        section = existing_config.get(c) or {}
        # `in`, not truthiness: `work.path: []` and `work.path: false` used to
        # fall through to the default store without a word, so a configuration
        # mistake read as a deliberate choice.
        if isinstance(section, dict) and "path" in section:
            configured_path = section["path"]
            if (not isinstance(configured_path, str)
                    or not configured_path.strip()):
                raise ValueError(f"{root / SENTINEL}: {c}.path must be a string")
            paths[c] = Path(configured_path).expanduser()
            configured_text[c] = configured_path
            read_from_config.add(c)
    work_path = paths.get("work")
    # Everything `init` can refuse over, decided before it writes anything at
    # all — the sentinel included. It writes two locations, and each of these
    # checks used to sit next to the write it protects rather than ahead of all
    # of them, so a refusal left `tcw-config.yaml` rewritten with the bad path,
    # or a new sentinel in a project that had none, or the whole status tree.
    default_root = root / "docs" / "work"
    replacing_default_store = False
    if work_path is not None and "work" in components:
        target = work_path if work_path.is_absolute() else root / work_path
        # Probed at the nearest *existing* ancestor, not at the target:
        # `git_root` shells out to `git -C <path>`, which fails on a path that
        # does not exist — and the target usually does not, since this call is
        # what creates it. Probing the target directly would refuse a good
        # `--work-path <repo>/new/nested/dir`. `is_symlink()` alongside
        # `exists()` because the latter follows the link: a dangling symlink
        # reads as absent, and skipping past it accepted a target that `mkdir`
        # then died on.
        probe = next((c for c in (target, *target.parents)
                      if c.exists() or c.is_symlink()), root)
        target_git = git_root(probe)
        if target_git is None:
            raise ValueError(f"work.path target is not inside a Git repository: {target}")
        if default_root.exists() and default_root.resolve() != target.resolve():
            # `is_symlink` first: replacing a default store means deleting it,
            # and a symlink is someone else's directory. Anything in it but
            # `.gitkeep`, Finder's `.DS_Store` or an empty hidden file may be
            # someone's work — an item, a 2.x status folder, a note — and work
            # is moved by a person, never deleted by init.
            def disposable(entry: Path) -> bool:
                return (entry.name.startswith(".") and entry.is_file()
                        and not entry.is_symlink()
                        and (entry.name in (".gitkeep", ".DS_Store")
                             or entry.stat().st_size == 0))
            held = [] if default_root.is_symlink() else sorted(
                entry.name for entry in default_root.iterdir()
                if not disposable(entry))
            if default_root.is_symlink() or held:
                shown = ", ".join(held[:5]) + (f" and {len(held) - 5} more"
                                               if len(held) > 5 else "")
                raise ValueError(
                    f"refusing to replace non-pristine {default_root}"
                    + (f" (it holds {shown})" if held else "")
                    + "; move existing work manually, update work.path, then "
                    "re-run init"
                )
            replacing_default_store = True
    # The exact directories this call will create, worked out before it creates
    # any of them — the pre-flight below needs the list, and so does the loop
    # that makes them, so there is only one of it.
    plan: list[tuple[str, Path, list[Path]]] = []
    for c in components:
        configured = paths.get(c)
        if c != "work" and c in configured_text:
            # Where the readers will look for it (`resolve_store`), not merely
            # `root / path`: a relative path leaving a linked worktree re-anchors
            # there, and a store built anywhere else is one nobody finds.
            base = STORE_CLASSES[c]._local_root(root, configured_text[c])
        else:
            base = ((configured if configured.is_absolute() else root / configured)
                    if configured is not None else root / "docs" / c)
        section = existing_config.get(c)
        if (c != "work" and isinstance(section, dict)
                and section.get("repository") is not None and not base.exists()):
            # A local tree always wins over a declared home (`resolve_store`
            # rule 1), so an empty one scaffolded here would hide the real store
            # from then on. Whether the home is already provisioned decides the
            # advice: "run `tcw provision`" after it succeeded sends the user in
            # a circle.
            others = [o for o in components if o != c]
            rest = (f" To scaffold the rest, name them: `tcw init {' '.join(others)}`."
                    if others else "")
            try:
                resolve_store(STORE_CLASSES[c], root)
            except ValueError:
                raise ValueError(
                    f"{root / SENTINEL}: {c} declares a repository; run `tcw provision` "
                    f"to fetch it rather than scaffolding an empty local store.{rest}"
                ) from None
            raise ValueError(
                f"{root / SENTINEL}: {c} is already provided by its declared "
                f"repository; there is nothing to scaffold.{rest}")
        plan.append((c, base, [base]))
    for component, _, leaves in plan:
        for leaf in leaves:
            # `mkdir(parents=True, exist_ok=True)` raises on a leaf that exists as
            # a file and on a parent that does — and it raised after the sentinel
            # and the earlier leaves had landed. The nearest path that exists
            # decides: if it is a directory, everything below it is still to be
            # created. `is_symlink` again, because a dangling one is not a
            # directory to `mkdir` either.
            occupied = next((c for c in (leaf, *leaf.parents)
                             if c.exists() or c.is_symlink()), None)
            if occupied is not None and not occupied.is_dir():
                raise ValueError(f"cannot scaffold {leaf}: {occupied} is not a directory")
    # The config's whole change — `id` and every `<component>.path` — decided
    # and verified as one edit before anything is written. It used to be two
    # writes with the default store's deletion between them, so a refusal at
    # the second would have left `id` written and the store already gone.
    config_path = root / SENTINEL
    configured = {c: p for c, p in paths.items() if c in components}
    for component in configured:
        section = existing_config.get(component)
        if section is not None and not isinstance(section, dict):
            # Used to be replaced by `{path: …}`, discarding what was typed.
            raise ValueError(f"{config_path}: {component} must be a mapping, "
                             f"found {type(section).__name__}")
    config_text = config_edit.edit_text(
        config_path, config_edit.read_text(config_path),
        _sentinel_edits(config_path, existing_config, project_id)
        + [config_edit.SetScalar(c, "path", str(location))
           for c, location in configured.items() if c not in read_from_config])
    if config_text is not None:
        _atomic_write_all([(config_path, config_text)])
    if replacing_default_store:
        shutil.rmtree(default_root)
    created: list[Path] = []
    for c, base, leaves in plan:
        for leaf in leaves:
            leaf.mkdir(parents=True, exist_ok=True)
            (leaf / ".gitkeep").touch()
            created.append(leaf)
    return created


# ── YAML helpers ────────────────────────────────────────────────────────────

class _UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader that errors on duplicate mapping keys (PyYAML silently keeps
    the last) — so `check` can flag a duplicate `extends` alias."""


def _no_dup_keys(loader: yaml.SafeLoader, node: yaml.MappingNode) -> dict:
    mapping: dict = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if key in mapping:
            raise yaml.YAMLError(f"duplicate key: {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=True)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dup_keys)


#: The YAML filenames TCW writes as records, held to `load_yaml`'s mapping
#: contract by `tcw validate`. Named rather than inferred and kept in one place,
#: because naming what TCW owns is narrower than exempting what it does not.
#:
#: `item.yaml` is a work item's record (TCW-70 Design 3.2). The node sentinel
#: `tcw-config.yaml` sits outside the scanned trees and is refused by
#: `load_config` the moment anything reads it. A work item's `capabilities.yaml`
#: is checked by the work checks in `tcw validate`, not by this list. A leftover
#: per-store `config.yaml` is not a record of ours: `check()` names any copy at a
#: store root as no longer read (`FsTreeStore._legacy_config_problems`).
OWNED_YAML_NAMES = frozenset({"meta.yaml", "item.yaml"})


class NotAMapping(yaml.YAMLError):
    """A YAML document that parsed perfectly well and is not a mapping.

    A **subclass** of `yaml.YAMLError` on purpose. The eleven sites that already
    catch one keep catching this without being touched, which is what makes a
    corrupt record degrade to empty instead of crashing the board. The subclass
    exists only so a caller that can say something better — `load_config` — can
    tell "your file is not a mapping" apart from "your file is not YAML".
    """


def load_yaml(path: Path, unique: bool = False) -> dict:
    """Load a YAML **mapping**. `{}` when the file is absent or has no content;
    `yaml.YAMLError` when it holds anything that is not a mapping.

    This used to end in ``return data or {}``, which kept neither half of that
    promise. A falsy document — ``[]``, ``false``, ``0`` — became a mapping, so a
    malformed ``tcw-config.yaml`` read as "no configuration" and `init`
    overwrote it, while the same file holding ``- a`` was refused and left alone.
    A truthy non-mapping came back unchanged and reached ``.get``, so one corrupt
    record crashed `tcw work list` and took the whole board down.

    **The raised type is `yaml.YAMLError` deliberately, not `ValueError`.** Ten
    sites already catch it around a load — `_safe_yaml` above all, whose whole
    job is that "a malformed state file degrades to empty rather than crashing
    the board". A well-formed non-mapping never raised one, so that promise had
    never applied to this case; raising the type they already expect keeps it at
    every one of them without touching any.

    Degrading is not reporting. `tcw validate` is what names a TCW-owned file
    that is not a mapping — see `tcw/validate.py`.
    """
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    data = _load_named_yaml(text, path,
                            _UniqueKeyLoader if unique else yaml.SafeLoader)
    if data is None:                       # absent content: empty file, or `null`
        return {}
    if not isinstance(data, dict):
        raise NotAMapping(
            f"{path}: expected a mapping, found {type(data).__name__}")
    return data


def load_config(path: Path) -> dict:
    """The node sentinel, read as a mapping, refusing as a `ValueError`.

    A config the user has broken is their mistake, not a failure of the YAML
    layer, and `ValueError` is the channel `tcw`'s top level already renders as
    a plain message. Every reader of the sentinel that must refuse goes through
    here, so `init`, a store resolving and the tag registry all say one thing
    about one file.

    The two readers that must *not* refuse — `declared_repository` and
    `declared_connected_projects`, which exist to answer for a graph that cannot
    be fully loaded — deliberately do not use this.
    """
    try:
        return load_yaml(path, unique=True)
    except NotAMapping as error:
        raise ValueError(f"malformed {path}: config must be a mapping") from error
    except yaml.YAMLError as error:
        raise ValueError(f"malformed {path}: {error}") from error


def _extends_ids(config: dict, label: str) -> list[str]:
    """The declared `extends` list, or a `ValueError` naming what is wrong.

    `label` is how a refusal addresses the declaration. It is the key path —
    `<path>/tcw-config.yaml: taxonomy.extends` — not just the file, because one
    node config can hold both `taxonomy.extends` and `capabilities.extends` and
    naming only the file leaves the reader to guess which one is meant.

    All four refusals carry it, including the project-id one: `validate_project_id`
    raises a perfectly good message about the id and knows nothing about where
    the id was read from, which sent people hunting for a key nothing named.
    """
    value = config.get("extends") or []
    if isinstance(value, dict):
        raise ValueError(
            f"{label}: legacy extends map is unsupported; replace it with "
            "a list of registered project IDs"
        )
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        raise ValueError(f"{label}: extends must be a list of project IDs")
    ids = []
    for v in value:
        try:
            ids.append(validate_project_id(v))
        except ValueError as error:
            raise ValueError(f"{label}: {error}") from None
    if len(ids) != len(set(ids)):
        raise ValueError(f"{label}: extends contains duplicate project IDs")
    return ids


class _FederationWalk:
    """State threaded down an `extends` walk.

    Two things with different lifetimes, which is why they cannot be one set.
    `seen` is the projects on *this* path, copied at every descent, and is what
    detects a cycle: a project is a back edge only relative to the route that
    reached it. `built` is shared by the whole walk and is what stops a diamond
    from rebuilding the same subtree once per route — `seen` alone terminated a
    cycle and memoised nothing, so a graph where two extended projects reach a
    common ancestor cost 2^depth store constructions.

    **Only a subtree that truncated nothing is cached.** A store built with a
    cycle truncated in it is correct for the path that built it and wrong for any
    other, since a back edge is a property of the route. A cycle-free subtree is
    path-independent, so it can be reused anywhere — and that is the common case,
    which is the one the cost was in.
    """

    __slots__ = ("seen", "built")

    def __init__(self, seen: "frozenset[Path]" = frozenset(),
                 built: "dict | None" = None):
        self.seen = seen
        self.built = {} if built is None else built

    def descend(self, node_root: Path) -> "_FederationWalk":
        """The walk as seen one project further down. Shares `built`."""
        return _FederationWalk(self.seen | {node_root}, self.built)


class _FederationCycles:
    """Mixin for the two tree stores: the cycles anywhere below this one.

    A cycle is recorded by the store that closes it — the deepest one built —
    so a caller checking the store at the top of the chain finds nothing on
    itself. Gathering the whole tree is what makes `check()` report a cycle
    from wherever it is run.
    """

    def _federation_cycles(self) -> list[str]:
        cached = getattr(self, "_cycles_cache", None)
        if cached is not None:
            return cached
        found: list[str] = list(getattr(self, "extends_cycles", []))
        for store in getattr(self, "extends", {}).values():
            for project_id in store._federation_cycles():
                if project_id not in found:
                    found.append(project_id)
        # Memoised because the `extends` tree is fixed once construction
        # returns, and because the walk asks this of every store it builds to
        # decide whether the subtree may be cached — recomputing it there would
        # trade one quadratic for another.
        self._cycles_cache = found
        return found


def _extended_component_stores(
    node_root: Path, config: dict, label: str, component: str,
    walk: "_FederationWalk | None" = None,
) -> "tuple[dict[str, object], list[str]]":
    """Each extended project's component store, by project id, and the ids whose
    edge closed a cycle.

    `walk` carries the state of the whole `extends` walk — see
    `_FederationWalk`. Its `seen` half is the *projects* already on this path,
    and it is checked before the store is opened, which it has to be: resolving a
    sibling's store now opens it, and opening a tree store resolves its own
    `extends`, so a cycle would recur infinitely instead of being reported.
    Project identity is known before any store is touched, which is what makes
    the guard possible at all — and a cycle in `extends` is a cycle among
    projects, so this is also the
    honest place to detect one.
    """
    registry = FsProjectRegistry.open(node_root).require_valid()
    walk = (walk or _FederationWalk()).descend(node_root.resolve())
    stores: dict[str, object] = {}
    cyclic: list[str] = []
    for project_id in _extends_ids(config, label):
        project = registry.get(project_id)
        if project is None:
            note = unreachable_project_note(registry, project_id)
            # `label` already ends in `<component>.extends`, so the word is not
            # repeated here the way it was when this took a bare file path.
            raise ValueError(
                f"{label}: {note}" if note else
                f"{label}: project '{project_id}' is not reachable "
                "through connected-projects"
            )
        # Identity first: extending yourself is wrong whatever the store does,
        # and asking the store about it would make a config error depend on
        # whether a tree happens to be provisioned.
        if Path(project.locator).resolve() == node_root.resolve():
            raise ValueError(f"a {component} store cannot extend itself")
        if Path(project.locator).resolve() in walk.seen:
            # The back edge of a federation cycle. Truncated here so the walk
            # terminates, and *named*, because a truncated tree cannot show a
            # cycle to anyone looking at it afterwards — which is why `check()`
            # used to report nothing at all.
            cyclic.append(project_id)
            continue
        # The extended project's *configured* store, not `docs/<component>` under
        # its root. Composing that path skipped the whole resolution ladder, so a
        # sibling that had moved its tree with `<component>.path` could not be
        # extended from, and one whose tree was declared but unprovisioned read
        # as having no tree at all — the confusion the ladder exists to end.
        # Failures are re-worded for a reader standing in a *different* node than
        # the one that failed.
        cache_key = (component, Path(project.locator).resolve())
        if (cached := walk.built.get(cache_key)) is not None:
            # Built already, somewhere else on this walk, with nothing truncated
            # in it — see `_FederationWalk`. This is what makes a diamond cost
            # one construction of the shared subtree instead of one per route.
            stores[project_id] = cached
            continue
        try:
            # The store itself, not its root. Rebuilding it from the root is
            # what broke the hop past a moved tree — `FsTreeStore` falls back to
            # `root.parent.parent` for `node_root`, correct only for the
            # `docs/<component>` shape this resolution exists to stop assuming.
            store = STORE_CLASSES[component].open(
                Path(project.locator), _walk=walk)
        except StoreNotProvisioned as error:
            raise ValueError(f"project '{project_id}': {error}") from None
        except StoreDeclarationError as error:
            raise ValueError(f"project '{project_id}': {error}") from None
        except ValueError as error:
            # The sibling's own error, quoted. Rewriting every `ValueError` as
            # "has no <component> component" sent readers to create a store that
            # already existed — a legacy `extends` map, a failed `require_valid`
            # and a self-extend all arrived here wearing that message.
            raise ValueError(f"project '{project_id}': {error}") from None
        # Rule 4 of the ladder validates nothing for a bare default, so a project
        # with no tree at all resolves to a path that is simply not there. That
        # is the honest answer for the project's *own* store and the wrong one to
        # federate from.
        if not store.root.is_dir():
            raise ValueError(f"project '{project_id}' has no {component} component")
        if not store._federation_cycles():
            walk.built[cache_key] = store
        stores[project_id] = store
    return stores, cyclic


# ── Revision tokens & atomic writes (FS-adapter private details) ─────────────

def _revision(content: str) -> str:
    """Cheap content-hash revision token (16 hex chars of SHA-256).

    `surrogateescape` so a file read by `_read_revision_text` hashes back to its
    own bytes: identical to a strict encode for any valid UTF-8 text, and a
    stable token, distinct per byte sequence, for a file that is not."""
    return hashlib.sha256(content.encode("utf-8", "surrogateescape")).hexdigest()[:16]


def _read_revision_text(path: Path) -> str:
    """A file's text for computing its revision — never for display or parsing.

    Lossless: bytes that are not UTF-8 survive as escapes, so a damaged file
    still has a revision, and the snapshot that hands one out and the guard that
    checks it agree. A guarded save can therefore replace a damaged file, which
    is how an editor repairs it. `read_text` keeps its newline handling, so no
    valid file's token changes."""
    return path.read_text(encoding="utf-8", errors="surrogateescape")


def _require_detail(detail, kind: str, ref: str):
    """The detail a composite operation promised to return, or a handled error.

    `get_detail` and its siblings are `-> … | None` because a concurrent move or
    delete can outlast their retries. `create_work` / `update_work` /
    `update_term` / `update_capability` are not: they declare a value. Handing
    `None` through anyway relocates the failure to whichever caller dereferences
    it first — a 500 out of `serve`, an `AttributeError` out of the CLI.

    The message does not claim the write landed, because at one of the five call
    sites (`update_work`'s no-change early return) nothing was written. It always
    names the ref: after a failed `tcw work new` that is the only place the user
    learns the slug of the item that now exists.
    """
    if detail is None:
        raise ValueError(f"{kind} '{ref}' could not be read back: another process "
                         f"moved or removed it. Re-read it.")
    return detail


def _revision_multi(*contents: str) -> str:
    """Revision for multiple resources concatenated (core = fields + body)."""
    return _revision("\x00".join(contents))


def _safe_store_id(value: str, label: str) -> str:
    """Validate a caller-supplied identifier that will be joined into a store
    path. Nested ids ('web/editing') are allowed; traversal is not — reject
    absolute paths, '..'/'.'/empty segments, backslashes, and NUL bytes. Returns
    the trimmed id. (Web writes reach these with arbitrary input; the bounded-
    input rule in the spec forbids escaping the store root.)"""
    v = (value or "").strip()
    if not v:
        raise ValueError(f"{label} is required")
    if v.startswith(("/", "\\")) or "\\" in v or "\x00" in v:
        raise ValueError(f"invalid {label}: {value!r}")
    for seg in v.split("/"):
        if seg in ("", ".", "..") or seg != seg.strip():
            raise ValueError(f"invalid {label}: {value!r}")
    return v


def _umask() -> int:
    """The process umask, read without leaving it changed."""
    current = os.umask(0)
    os.umask(current)
    return current


def _atomic_write_all(pairs: list[tuple[Path, str]]) -> None:
    """Write several files as one unit: stage every temp, then promote each.

    `pairs` is `(target path, content)` in promote order. The failure class this
    closes is content production — ENOSPC, EACCES, a serialization error — which
    can only happen in the staging phase, before anything is promoted, so the
    targets are left untouched. One handler spans both phases and unlinks every
    temp, so no temp file is left beside a real file in the user's git tree.
    Temps are `mkstemp`-unique rather than `<target>.tmp`, so an existing file
    or symlink at a predictable name is never truncated, promoted, or deleted.
    `BaseException` on purpose: a `KeyboardInterrupt` mid-batch still cleans up.

    # ponytail: the promote loop is not atomic across files — a process death
    # between two replace() calls still leaves a partial update. Upgrade path is
    # a journal or a whole-directory swap (the `accept_inbox` shape, fs.py:2246);
    # neither is worth its cost for the failure class actually reachable here.
    """
    staged = []
    try:
        for path, content in pairs:
            # A unique temp beside the target, not `<target>.tmp`: the
            # deterministic name is a real path a user (or a symlink) can
            # already occupy, and this would truncate it, promote it over the
            # target, and delete it on failure. `mkstemp` refuses to reuse an
            # existing name and never follows a symlink.
            fd, tmp_name = tempfile.mkstemp(dir=path.parent,
                                            prefix=path.name + ".", suffix=".tmp")
            os.close(fd)                     # mkstemp is for the *name*
            tmp = Path(tmp_name)
            staged.append((tmp, path, content))
            tmp.write_text(content, encoding="utf-8", newline="")
            # `mkstemp` is 0600 by design. Carry the target's mode when it has
            # one, so promoting does not silently re-permission a file someone
            # chmod'ed; otherwise fall back to what an ordinary write would give.
            try:
                os.chmod(tmp, path.stat().st_mode)
            except OSError:
                os.chmod(tmp, 0o666 & ~_umask())
        for tmp, path, _ in staged:
            tmp.replace(path)
    except BaseException:
        for tmp, _, _ in staged:
            tmp.unlink(missing_ok=True)
        raise


# ── Shared tree-store core (Phase 4) ─────────────────────────────────────────

def _mkdir_owned(d: Path) -> bool:
    """Create `d`, returning whether *this call* made it.

    `exist_ok=False` is the ownership proof: exactly one process's `mkdir`
    succeeds, so there is no check-then-act window. That is what lets a failed
    write remove the folder outright — knowing it removes nothing it did not
    create — where an `existed = d.exists()` probe beforehand could not.
    """
    try:
        d.mkdir(parents=True)
        return True
    except FileExistsError:
        return False


def anchor_configured_path(node_root: Path, value: Path) -> Path:
    """The directory a relative `<component>.path` is resolved against.

    Inside a *linked worktree* this follows the same rule
    `FsProjectRegistry._target_path` applies to `connected-projects` locators
    (`tcw/store/project.py:322-334`), and for the same reasons:

    - **Re-anchor only on escape.** A relative path that stays inside the
      worktree is this node's store on this branch and belongs to the worktree,
      exactly as the default `docs/<component>` does. Only a path that leaves
      the checkout was authored against the primary checkout's position on disk.
      Re-anchoring an inside-staying path used to send a worktree user to the
      primary checkout's store while the *identical* default did not.
    - **Anchor at this node's counterpart, not at the main worktree root.**
      `worktree_anchors` returns `(current top, main root)`; using the second
      alone drops the sub-path of a node nested inside the repository, so
      `apps/server`'s relative path got applied from the repository root and the
      store could not be found at all (GitHub #26).

    One function, not one per store class: both `_local_root` hooks had their
    own copy of this and only the work store's was ever fixed, which is the
    drift `resolve_store` exists to prevent. Getting it wrong silently swaps a
    worktree user's real store for a cache clone.

    Returns `node_root` unchanged outside a worktree, for a node that is not in
    a git repository, and for a path that stays inside the checkout.
    """
    anchors = worktree_anchors(node_root)
    if anchors is None:
        return node_root
    top, main = anchors
    resolved = (node_root / value).resolve()
    inside = _below(node_root, top)
    if inside is not None and _below(resolved, top) is None:
        return main / inside
    return node_root


class FsTreeStore:
    """Common FS-adapter base for the three bounded-tree stores.

    Captures the boilerplate every component shares — the store root, the
    enclosing node (repo) root, config loading, the `open(node_root)` entry
    point, and the git-plumbing methods that *effect* transitions. Component
    specifics (node = dir vs file, identifier resolution, the status state
    machine) stay in the subclasses (phase-4-shared-core: don't over-pull).

    Subclasses set `COMPONENT` (the `docs/<COMPONENT>/` dir) and optionally
    `LEGACY_CONFIG_NAME` (the per-store config file this component used to
    write, retained so it stays out of the attachment surface and so `check`
    can report a leftover copy).
    """
    COMPONENT: str
    #: The filename this component once kept its own `extends` in, before it
    #: moved to the node's `tcw-config.yaml`. Nothing reads or writes the file
    #: any more. The name survives on the class for two reasons: `_node_reserved`
    #: keeps it out of a folder's attachments (see the comment there), and
    #: `_legacy_config_problems` reports a copy left at the store root.
    LEGACY_CONFIG_NAME: str | None = None

    def __init__(self, root: Path, *, node_root: Path | None = None,
                 store_git_root: Path | None = None):
        self.root = root                       # docs/<component>/, or wherever configured
        # Two roots, because they answer different questions and diverge the
        # moment a store leaves its node's repository — the same split the
        # work store has carried since `work.path` existed.
        #
        # `node_root` is the *node*: whose config this is, and what federation
        # resolves `extends` against. `store_git_root` is the repository a write
        # here has to land in. They are the same directory for a store sitting
        # in its own node, and are not for a configured or provisioned one.
        self.node_root = node_root or root.parent.parent
        self.store_git_root = store_git_root or git_root(root) or self.node_root
        # This component's section of the *node's* config, not a file inside the
        # store. Re-read here rather than threaded down from `resolve_store`,
        # because `tcw/validate.py` builds a store by calling `_open_at`
        # directly: a threaded section would arrive empty there and that store
        # would silently resolve no inheritance at all.
        self.config = self._component_config()

    @classmethod
    def open(cls, node_root: Path, _walk: "_FederationWalk | None" = None):
        """Resolve this node's store for this component. The ladder is
        `resolve_store`, shared with the work store.

        `_walk` is private and carries the federation walk's state: the projects
        already on this path, so `extends` can resolve a sibling's store without
        a cycle becoming infinite recursion, and the stores already built
        anywhere on the walk, so a shared subtree is built once. Callers outside
        federation never pass it.
        """
        return resolve_store(cls, node_root, _walk=_walk)

    @classmethod
    def _local_root(cls, node_root: Path, configured: str | None) -> Path:
        """Where this component's tree sits on this machine, per
        `<component>.path`, or the default `docs/<component>`. A relative path
        re-anchors per `anchor_configured_path`."""
        if configured is None:
            return node_root / "docs" / cls.COMPONENT
        value = Path(configured).expanduser()
        if value.is_absolute():            # names a place, not an offset
            return value
        return anchor_configured_path(node_root, value) / value

    @classmethod
    def _open_at(cls, raw_root: Path, node_root: Path, config_path: Path, *,
                 external: bool, must_exist: bool = True,
                 declaration: "RepositoryDeclaration | None" = None,
                 _walk: "_FederationWalk | None" = None):
        """Build the store at a candidate root, validating it only when
        something points at it.

        `declaration` is accepted and deliberately ignored: a tree store never
        publishes. A taxonomy term or a capability status is a claim *about the
        code*, realized when the code implementing it merges, so the edit belongs
        to that change and lands with it. Publishing one on its own would
        announce a capability to everyone reading the ledger while the code
        making it true is still unmerged. Work is different — an item's state is
        the record of a session and changes independently of any code.

        A tree store has no layout to check — see `_is_store_layout` — so
        "usable" is "the directory is there", and that is the strongest honest
        answer rather than a shortcut. When `must_exist` is false this validates
        nothing at all, which is the pre-ladder behaviour for a component's bare
        default and the contract every existing project relies on.
        """
        if must_exist:
            # `StoreLocationUnusable`, not a bare `ValueError`: the ladder falls
            # through on "there is no store here" and must *not* fall through on
            # anything the store itself reports while opening.
            if raw_root.is_symlink() and not raw_root.exists():
                raise StoreLocationUnusable(
                    f"{config_path}: {cls.COMPONENT}.path is a broken symlink: {raw_root}")
            if not raw_root.is_dir():
                raise StoreLocationUnusable(
                    f"{config_path}: {cls.COMPONENT}.path is not a directory: {raw_root}")
        root = raw_root.resolve() if raw_root.exists() else raw_root
        owner = (git_root(root) if external else node_root) or node_root
        # The node stays the node — federation resolves `extends` against it —
        # while writes follow the store into whatever repository holds it.
        return cls(root, _walk=_walk, node_root=node_root,
                   store_git_root=owner)

    # -- containment: a store id never names a file outside its own store --
    #
    # `_safe_store_id` closes every *syntactic* escape and never touches the
    # filesystem, so a symlink planted inside a store is lexically clean and the
    # join lands wherever it points. These two restore the bound. Not race-safe
    # and not claiming to be: nothing binds the later open()/mkdir to the object
    # resolved here, so an attacker who can swap a directory for a symlink mid
    # command defeats it — and one with write access to the store has cheaper
    # attacks. What this restores is the stated property, against a symlink that
    # is already on disk when the command runs.

    @cached_property
    def _resolved_root(self) -> Path:
        """The store root with symlinks resolved.

        A `cached_property` rather than an `__init__` assignment, so a subclass
        whose `__init__` does not chain to this one still has it. Cached for the life of
        the instance — one CLI command, one HTTP request.
        """
        return self.root.resolve()

    def _node_readable(self, d: Path) -> bool:
        """Whether `d` is a node this store may read — folder *and* own meta.

        Two questions, because they fail apart: the folder can be reached
        through a symlink out of the store, or the folder can be ordinary while
        its `meta.yaml` is the symlink. Guarding only the folder leaves the
        second open, and an escaped meta reads as `{}`, which `_term` would turn
        into a *phantom* term named after its own slug rather than a miss.
        """
        return self._within_store(d) and self._within_store(d / "meta.yaml")

    def _within_store(self, path: Path) -> bool:
        """True iff `path` stays inside the store root once symlinks resolve.

        Both sides are resolved: taxonomy and capabilities roots keep whatever
        lexical spelling they were opened with, so comparing a resolved path to
        an unresolved root would reject a checkout reached through a symlinked
        ancestor.

        `RuntimeError` as well as `OSError`: a symlink loop raises `RuntimeError`
        on Python < 3.13 — not an `OSError` — and since 3.13 raises nothing,
        returning the path unresolved. The floor is 3.11, so both eras are live.
        A loop answering True is harmless and deliberately not pinned: every read
        through one fails with ELOOP, and every caller stats before it reads.
        """
        try:
            return path.resolve().is_relative_to(self._resolved_root)
        except (OSError, RuntimeError):       # broken symlink; loop on < 3.13
            return False

    def _write_git_root(self) -> Path:
        """The repository a write here has to land in — the store's own, which is
        the node's only while the store sits inside it."""
        return self.store_git_root

    def _require_repository(self) -> None:
        """Deliberately stateless — see `test_non_git_writes.py`'s no-state pin."""
        require_repository(self._write_git_root())

    # -- the node's own `tcw-config.yaml` --
    #
    # On `FsTreeStore` rather than on one component, because all three now write
    # it: `work.tags`, `taxonomy.extends` and `capabilities.extends`. It is the
    # node's file, not any store's, and the two roots vary independently.

    def _config_path(self) -> Path:
        """The node sentinel's path. Not resolved — `FsTreeStore` keeps
        `node_root` as it was handed over, and a plain join is correct either
        way."""
        return self.node_root / SENTINEL

    def _config(self) -> dict:
        """Read the node sentinel config, tolerant of absence/emptiness. A
        malformed file raises a clear error naming the path rather than a raw
        YAML traceback. Plain board listing never calls this, so a broken config
        only fails operations that actually need it."""
        return load_config(self._config_path())

    def _component_config(self) -> dict:
        """This component's section of the node config, as a mapping.

        Mirrors `resolve_store` exactly, and has to: a section that is present
        but not a mapping normalizes to `{}` there (see the `isinstance` guard
        beside `<component>.path`), so doing anything else here would turn
        `taxonomy: docs/tax` into an `AttributeError` on a path `resolve_store`
        answers calmly.
        """
        section = self._config().get(self.COMPONENT)
        return section if isinstance(section, dict) else {}

    def _persist_extends(self, extends: list[str]) -> None:
        """Write this component's `extends` to the node config, and keep the
        in-memory copy in step.

        The in-memory update is why this is not just `_write_node_config`: a
        second add/rm in the same process reads `self.config`, and term
        *resolution* (`self.extends`) stays load-time only — reopen to use it.
        An empty list removes the key rather than writing `extends: []`, which
        is what the per-store file did.

        The in-memory copy changes only once the write has succeeded, so a
        refused write leaves this store agreeing with the file.
        """
        config = self._config()
        section = config.get(self.COMPONENT)
        if section is not None and not isinstance(section, dict):
            # Reading normalizes this to "no configuration" (`_component_config`,
            # matching `resolve_store`), and writing could do the same — but
            # reading discards nothing, while writing would replace whatever the
            # user typed with a mapping of our own. `taxonomy: docs/taxonomy` is
            # someone reaching for `taxonomy: {path: docs/taxonomy}`, and telling
            # them so costs less than silently deleting it.
            raise ValueError(
                f"{self._config_path()}: {self.COMPONENT} must be a mapping, "
                f"found {type(section).__name__}")
        # `Remove` drops a section that is left holding nothing, so removing the
        # last `extends` from a node that configured nothing else leaves the
        # config as it was rather than growing an empty `taxonomy: {}`.
        self._write_node_config([
            config_edit.SetList(self.COMPONENT, "extends", tuple(extends)) if extends
            else config_edit.Remove(self.COMPONENT, "extends")])
        if extends:
            self.config["extends"] = extends
        else:
            self.config.pop("extends", None)

    def _extends_label(self) -> str:
        """What a refusal about `extends` calls the thing it is refusing.

        The key path, not just the file: one `tcw-config.yaml` can hold both
        `taxonomy.extends` and `capabilities.extends`, and a message naming only
        the file leaves the reader to guess which one is wrong.
        """
        return f"{self._config_path()}: {self.COMPONENT}.extends"

    def _write_node_config(self, edits: list) -> None:
        """Apply `edits` to the node sentinel and stage it in the **node's**
        repository.

        The store root and the node root are different repositories in the
        orchestrator layout, and `git add` refuses a path outside the repository
        it is run in — staging this against the store's repository is what made
        `tcw work tags add` fail with *is outside repository at …*, so the whole
        verb was unusable there.

        The `None` branch is narrower than it looks: callers run
        `_require_repository` first, which refuses a non-git node whose store is
        its own default folder. What reaches it is the node that is not a
        repository while its *store* is — an external `<component>.path`
        pointing into one — where writing the file is the whole of what can be
        done.

        Only the lines of the keys being changed are touched — comments and
        formatting everywhere else survive — and a file that cannot be edited
        that way is refused, not rewritten (`config_edit`). Edits that change
        nothing write and stage nothing.
        """
        config_path = self._config_path()
        self._config()                           # a malformed file refuses as before
        text = config_edit.edit_text(config_path, config_edit.read_text(config_path), edits)
        if text is None:
            return
        node_repository = git_root(config_path.parent)
        payload = [(config_path, text)]
        if node_repository is None:
            _atomic_write_all(payload)
        else:
            self._write_staged(payload, stage_root=node_repository)

    def _stage(self, *paths: Path) -> None:
        self._require_repository()
        git_stage(self.store_git_root, *paths)

    def _write_staged(self, pairs: list[tuple[Path, str]], *,
                      owned_dir: Path | None = None,
                      also_stage: tuple[Path, ...] = (),
                      stage_root: Path | None = None) -> None:
        """Write every `(path, content)` and stage the lot, undoing what *this
        call* created if either half fails, then re-raising.

        A repository that exists and *refuses* — a held `index.lock`, a rejecting
        hook, a permissions error — is only discovered when staging fails, which
        is after the content is on disk. A precondition cannot help: it cannot
        predict a lock acquired a millisecond later. So this rolls back instead.

        **Never removes a path that was already there.** An update whose staging
        is refused keeps what it just wrote, because deleting it would turn a
        recoverable failure into real data loss. `owned_dir` is a directory the
        caller proved it created (`_mkdir_owned`) and is removed whole;
        everything else is per file, and only files absent when this call began.

        `also_stage` are paths to stage alongside the written ones but not to
        write — a deletion this call made, which git records by staging the path
        it used to occupy. They ride inside the same `try` on purpose: staging
        them afterwards would put a second `git add` outside the rollback, and a
        refusal there would leave the write standing.

        Best-effort and silent: the undo must not mask the original error, and
        must not add a second line to a refusal whose one-line shape is pinned.

        `stage_root` names the repository to stage in, for the one write that is
        not a store file: the node's own `tcw-config.yaml`. The store root and
        the node root vary independently — in the orchestrator layout they are
        different repositories — and `git add` refuses a path outside the
        repository it is given. Everything else defaults to the store's.
        """
        # `exists() or is_symlink()`: `exists()` follows the link, so a
        # pre-existing *dangling* symlink read as absent, was replaced by a real
        # file, and was then unlinked here — destroying a path this call did not
        # create. Same idiom `init`'s ancestor walk uses for the same reason.
        new = [p for p, _ in pairs if not (p.exists() or p.is_symlink())]
        try:
            _atomic_write_all(pairs)
            paths = (*(p for p, _ in pairs), *also_stage)
            if stage_root is None:
                self._stage(*paths)
            else:
                self._require_repository()
                git_stage(stage_root, *paths)
        except BaseException:
            if owned_dir is not None:
                shutil.rmtree(owned_dir, ignore_errors=True)
            else:
                for p in new:
                    with suppress(OSError):
                        p.unlink()
            raise

    def _rm(self, path: Path) -> None:
        self._require_repository()
        git_rm(self.store_git_root, path)


    # -- shared folder-node anatomy (meta.yaml + description.md + attachments) --
    #
    # A "node" is a folder holding a `meta.yaml` (named fields), a
    # `description.md` (the body), and zero or more named attachment files. Both
    # the taxonomy and capabilities adapters realize their items this way; the
    # read/write mechanics live here so they are defined once. (Abstract spine:
    # body + named fields + named attachments — bounded, never globbed open.)

    def _node_texts(self, d: Path) -> list[str]:
        """A folder node's [meta, description] texts; empty strings when absent."""
        return [f.read_text(encoding="utf-8")
                if f.is_file() and self._within_store(f) else ""
                for f in (d / "meta.yaml", d / "description.md")]

    def _node_reserved(self) -> set[str]:
        """Filenames in a node folder that are not attachments.

        **Kept per-store after `extends` moved to the node config.** Each store
        still reserves the file it used to write — taxonomy `config.yaml`,
        capabilities `.config.yaml` — so a folder holding a leftover copy lists
        the same attachments it listed before.

        Only taxonomy can actually observe this: `_term` carries the list onto
        `Term.attachments`, while `_capability` discards it and composes bodies
        from `prependedDocs`/`appendedDocs` read by name out of `meta.yaml`. So
        the capabilities half is inert, and is kept anyway — the two stores
        reading alike costs one string and removes the question. See
        `test_the_capabilities_store_has_no_attachment_surface_to_regress`,
        which fails if `Capability` ever grows an attachments field and makes
        this reasoning stale.
        """
        names = {"meta.yaml", "description.md"}
        if self.LEGACY_CONFIG_NAME:
            names.add(self.LEGACY_CONFIG_NAME)
        return names

    def _legacy_config_problems(self) -> list[str]:
        """The pre-2.5.0 config file at this store's root, reported, or `[]`.

        An upgraded project that never moved its `extends` out of this file
        silently lost every inherited entry, and nothing said why. So a copy at
        the store root is a problem whatever it holds — even one that only
        repeats `<component>.extends` misleads the next reader into thinking it
        is read. Existence only: the file is never opened, so a corrupt copy
        cannot make `check` raise, and it is never rewritten or deleted.

        Only the root: a file of the same name inside a folder node is an
        ordinary file of that node.
        """
        if not self.LEGACY_CONFIG_NAME:
            return []
        path = self.root / self.LEGACY_CONFIG_NAME
        if not path.is_file():
            return []
        try:
            shown = str(path.relative_to(self.node_root))
        except ValueError:
            shown = str(path)
        return [f"{shown}: no longer read since TCW 2.5.0 — move any needed "
                f"extends into {self._extends_label()}, then delete the file; "
                f"if already migrated, just delete it"]

    def _load_node(self, d: Path) -> tuple[dict, str, list[str]]:
        """Read a folder node → (meta mapping, description text, attachment names).

        Attachments are the folder's non-reserved, non-dot files (bounded set).
        """
        # Containment per resource, not just per folder. A folder can be
        # legitimately inside the store while a file in it is a symlink pointing
        # out, and the folder guards upstream cannot see that. A resource that
        # escapes reads as *absent* — the same fail-closed shape `get_local`
        # already uses for the folder. An empty meta is what makes the node stop
        # resolving: `_is_capability` and the `overrides` test both read falsey,
        # and a taxonomy node with no kind is not a term.
        meta_path = d / "meta.yaml"
        meta = load_yaml(meta_path) if self._within_store(meta_path) else {}
        desc = d / "description.md"
        description = (desc.read_text(encoding="utf-8")
                       if desc.exists() and self._within_store(desc) else "")
        reserved = self._node_reserved()
        attachments = sorted(
            f.name for f in d.iterdir()
            if f.is_file() and f.name not in reserved and not f.name.startswith(".")
            and self._within_store(f))
        return meta, description, attachments

    def _write_node(self, d: Path, meta: dict, description: str) -> None:
        """Create/overwrite a folder node's meta + description, atomically, staged.

        Rollback is `_write_staged`'s, and it spans the staging phase too: a git
        refusal after both files landed undoes this call's work rather than
        leaving an untracked node behind. What it removes depends on who made
        the directory — the whole folder when this call did, only the files it
        created when the node already existed. Same applies to `_write_meta`.
        """
        self._require_repository()          # ahead of the mkdir, not the stage
        # `_mkdir_owned` rather than `exist_ok=True` + a prior `d.exists()`:
        # exactly one process's `mkdir` succeeds, so this is an ownership proof
        # with no check-then-act window — retiring the TOCTOU the old `existed`
        # probe carried, where a second writer creating the node between our
        # check and our failure would have had its directory removed.
        owned = _mkdir_owned(d)
        self._write_staged(
            [(d / "meta.yaml",
              yaml.safe_dump(meta, sort_keys=False, allow_unicode=True)),
             (d / "description.md", description)],
            owned_dir=d if owned else None)


# ── FsTaxonomyStore ─────────────────────────────────────────────────────────

TAXONOMY_KINDS = {"Vocabulary", "Feature"}


def _normalize_taxonomy_kind(kind: str | None) -> str:
    if not kind:
        return "Vocabulary"
    by_lower = {k.lower(): k for k in TAXONOMY_KINDS}
    return by_lower.get(str(kind).lower(), str(kind))


def _wrong_kind_ref(ref: str, kind: str) -> str:
    """The one wording for "this vocabulary ref points at the wrong kind"."""
    return f"vocabulary ref '{ref}' points to {kind}, expected Vocabulary"


class FsTaxonomyStore(FsTreeStore, _FederationCycles, TaxonomyStore):
    """`TaxonomyStore` over nested dirs under `docs/taxonomy/` (Phase 2 B.3).

    A term's slug is its directory path under the taxonomy root. `extends`
    aliases (local-path repo roots) are realized as nested stores.
    """
    COMPONENT = "taxonomy"
    LEGACY_CONFIG_NAME = "config.yaml"

    def __init__(self, root: Path, *,
                 _walk: "_FederationWalk | None" = None,
                 node_root: Path | None = None, store_git_root: Path | None = None):
        super().__init__(root, node_root=node_root, store_git_root=store_git_root)
        self.extends: dict[str, "FsTaxonomyStore"] = {}
        # Reused, never rebuilt: the resolution below already constructed each
        # store with the right node root and the right walk state. There is no
        # second filter on the results — the `_seen` set that used to be one was
        # dead once recursion moved into `_extended_component_stores`, since the
        # only case it could refuse is a self-extend the identity check there
        # already refuses by project id.
        self.extends, self.extends_cycles = _extended_component_stores(
            self.node_root, self.config, self._extends_label(), "taxonomy",
            walk=_walk,
        )

    # -- reads --

    def _term(self, slug: str, origin: str = "local") -> Term:
        d = self.root / slug
        meta, description, attachments = self._load_node(d)
        return Term(
            slug=slug,
            name=meta.get("name") or slug.rsplit("/", 1)[-1].replace("-", " ").title(),
            description=description,
            kind=_normalize_taxonomy_kind(meta.get("kind")),
            relates_to=list(meta.get("relatesTo") or []),
            vocabulary=list(meta.get("vocabulary") or []),
            attachments=attachments,
            origin=origin,
            modified=_modified_timestamp(
                [d / "meta.yaml", d / "description.md"]
            ),
        )

    def get_local(self, slug: str) -> Term | None:
        # A ref is joined onto the store root, so it is bounded input like any
        # other store id: one that escapes (`../capabilities/thing`) resolves to
        # nothing rather than raising — `get()` is documented to return None for
        # a ref that resolves to nothing, and `check()` catches only AmbiguousRef,
        # so a raise here would crash `check` on a taxonomy that already holds one.
        try:
            slug = _safe_store_id(slug, "term ref")
        except ValueError:
            return None
        d = self.root / slug
        # Order matters: the cheap stat first, so a miss pays no `resolve()`;
        # containment second; the read (`_term`) only after both.
        return self._term(slug) if d.is_dir() and self._node_readable(d) else None

    def _local_slugs(self) -> list[str]:
        # `list` must not advertise what `show`/`rm` refuse. Note `rglob` does
        # not descend into a symlinked directory, so only the final component
        # can be one — but that is the case this filter is for.
        return sorted(
            str(p.relative_to(self.root)) for p in self.root.rglob("*")
            if p.is_dir() and self._node_readable(p))

    def _inherited_stores(self) -> dict[str, "FsTaxonomyStore"]:
        """Every inherited taxonomy keyed by its owning project ID.

        ``self.extends`` remains the direct declarations used by writes and cycle
        checks.  Reads flatten their nested stores so a source keeps the same
        canonical namespace regardless of the route that reaches it.
        """
        stores: dict[str, FsTaxonomyStore] = {}
        for project_id, store in self.extends.items():
            stores.setdefault(project_id, store)
            for inherited_id, inherited_store in store._inherited_stores().items():
                stores.setdefault(inherited_id, inherited_store)
        return stores

    def list_all(self, local_only: bool = False) -> list[Term]:
        terms = [self._term(s) for s in self._local_slugs()]
        if not local_only:
            for project_id, store in self._inherited_stores().items():
                terms += [
                    self._term_via(store, slug, project_id)
                    for slug in store._local_slugs()
                ]
        return terms

    @staticmethod
    def _term_via(store: "FsTaxonomyStore", slug: str, alias: str) -> Term:
        return store._term(slug, origin=alias)

    def get(self, ref: str) -> Term | None:
        inherited_stores = self._inherited_stores()
        head, _, rest = ref.partition("/")
        if head in inherited_stores:                   # prefixed (B.6.1)
            return self.get_inherited(head, rest)
        local = self.get_local(ref)                    # bare-wins-local (B.6.2)
        if local is not None:
            return local
        matches = [
            (project_id, term)
            for project_id, store in inherited_stores.items()
            if (term := store.get_local(ref)) is not None
        ]
        if len(matches) == 1:
            project_id = matches[0][0]
            return self._term_via(inherited_stores[project_id], ref, project_id)
        if len(matches) > 1:
            raise AmbiguousRef(ref)
        return None

    def get_inherited(self, alias: str, slug: str) -> Term | None:
        st = self._inherited_stores().get(alias)
        return self._term_via(st, slug, alias) if st and st.get_local(slug) else None

    def search(self, query: str) -> list[Term]:
        q = query.lower()
        return [t for t in self.list_all()
                if q in t.name.lower() or q in t.description.lower()]

    # -- writes --

    def add(self, name: str, slug: str | None = None, parent: str | None = None,
            description: str = "", kind: str = "Vocabulary",
            vocabulary: list[str] | None = None) -> Term:
        leaf = _safe_store_id(slug or slugify(name), "slug")
        if parent:
            parent = _safe_store_id(parent, "parent")
        full = f"{parent.strip('/')}/{leaf}" if parent else leaf
        if parent and not (self.root / parent).is_dir():
            raise ValueError(f"parent term does not exist: {parent}")
        kind = _normalize_taxonomy_kind(kind)
        if kind not in TAXONOMY_KINDS:
            raise ValueError(f"invalid taxonomy kind '{kind}' "
                             f"(choose: {', '.join(sorted(TAXONOMY_KINDS))})")
        d = self.root / full
        # Before `d.exists()` and before the first mkdir: one guard covers a
        # symlinked `--parent` and a symlinked leaf alike, and it keeps the
        # fail-closed contract below (a rejected write leaves no partial folder).
        if not self._within_store(d):
            raise ValueError(f"parent term does not exist: {parent or full}")
        if d.exists() or d.is_symlink():   # a dangling/looping link reads absent
            raise ValueError(f"term already exists: {full}")
        # Fail closed on refs *before* the first mkdir: a rejected write must
        # leave no partial folder behind. The same rules `check` applies, so a
        # term that `add` accepted never fails the very next `check`.
        if kind == "Feature" and not vocabulary:
            raise ValueError("Feature requires at least one vocabulary ref")
        meta = {"name": name, "kind": kind, "relatesTo": []}
        if vocabulary:
            meta["vocabulary"] = [self._resolve_vocab_ref(r) for r in vocabulary]
        self._write_node(d, meta, description)
        return self._term(full)

    def remove(self, ref: str) -> None:
        term = self.get(ref)
        # The exact listed spelling only, as `FsCapabilitiesStore.remove`: on a
        # case-insensitive disk `ADMIN` resolves to the `admin` folder but echoes
        # the spelling back as the slug, and git would not find that path.
        if term is not None and term.origin == "local" and term.slug not in self._local_slugs():
            term = None
        if term is None:
            raise ValueError(f"no such term: {ref}")
        if term.origin != "local":
            raise ValueError(f"cannot remove inherited term '{term.qualified}' "
                             f"(edit it at its source)")
        d = self.root / term.slug
        # Refused, never cascaded: `_rm` is a `git rm -rf` of the whole folder.
        # Asked of git rather than the disk, because git's answer is what gets
        # deleted: a folder holding only untracked files (a `.DS_Store` left in a
        # removed child's folder) is deleted by nothing, and refusing over it
        # would name a "term" no `rm` can reach.
        self._require_repository()
        listed = _git(["git", "-C", str(self.store_git_root),
                       "ls-files", "-z", "--", _literal(d)],
                      capture_output=True, check=True, **_GIT_PATHS).stdout
        here, top = d.resolve(), self.root.resolve()
        # The folder resolved, the name kept: resolving the last component would
        # let a symlink stand in for its target, or the target for the link.
        tracked = [(self.store_git_root / f).parent.resolve() / Path(f).name
                   for f in listed.split("\0") if f]
        if not any(f.parent == here for f in tracked):
            # `git rm` would fail with git's own words; say it in ours.
            raise ValueError(f"cannot remove '{term.slug}': its files are not tracked "
                             f"by git; `git add` them first, or delete the folder")
        nested = sorted({str(f.parent.relative_to(top)) for f in tracked
                         if here in f.parent.parents})
        if nested:
            raise ValueError(f"cannot remove '{term.slug}': nested under it: "
                             f"{', '.join(nested)} (remove those first)")
        # What `git rm` would leave behind: untracked files anywhere under the
        # term. The listing counts any folder as a term, so a leftover would keep
        # the term listed after "Removed". Refused here, before anything is
        # touched, except for files an operating system writes into folders on
        # its own, which are deleted with the term (below) — refusing over those
        # would make every folder a file browser has opened unremovable.
        untracked = _untracked_under(here, set(tracked))
        if untracked:
            names = ", ".join(str(p.relative_to(top)) for p in untracked)
            raise ValueError(
                f"cannot remove '{term.slug}': {names} under it is not tracked by "
                f"git; `git add` it (`git add -f` if ignored) and remove it first, "
                f"or delete it")
        referrers = self._referrers(d) + self._capability_referrers(d, term.slug)
        if referrers:
            raise ValueError(f"cannot remove '{term.slug}': still referenced by "
                             f"{', '.join(referrers)} (repoint or clear those first)")
        self._rm(d)
        if d.exists() and not _untracked_under(d.resolve(), set()):
            shutil.rmtree(d)                    # only OS metadata files are left
        if term.slug in self._local_slugs():
            # A safety net: the check above found nothing to leave, so only a
            # file written meanwhile gets here.
            raise ValueError(f"removed the tracked files of '{term.slug}', but it "
                             f"still lists: files git does not track remain in {d}")

    def _capability_referrers(self, target: Path, slug: str) -> list[str]:
        """`capability <path> (Subject|Feature)` for every local capability whose
        reference resolves to the term folder `target` — what `tcw capabilities
        check` would report dangling once it is gone.

        The node's capabilities store is found by the normal resolution. None
        here: nothing to ask. One that cannot be opened or read refuses the
        removal, because whether it names the term cannot then be known.
        """
        try:
            caps = FsCapabilitiesStore.open(self.node_root)
            if not caps.root.is_dir():
                return []
            local = caps.list_all(local_only=True)
            # An override's references become the composed capability's own, so
            # a term one names is as named as one a local capability names.
            overrides = caps._override_fields()
        except (ValueError, yaml.YAMLError) as e:
            raise ValueError(f"cannot remove '{slug}': the capabilities that might "
                             f"name it cannot be read: {e}") from None
        referrers = ([(f"capability {cap.path}", cap.fields) for cap in local]
                     + [(f"capability override {path}", fields)
                        for path, fields in overrides])
        out = []
        for label, fields in referrers:
            named = set()
            for field, ref in FsCapabilitiesStore._term_refs(fields):
                try:
                    hit = self.get(ref)
                except AmbiguousRef:
                    continue
                if (hit is not None and hit.origin == "local"
                        and _same_folder(self.root / hit.slug, target)):
                    named.add(field)
            out += [f"{label} ({field})"
                    for field in ("Subject", "Feature") if field in named]
        return out

    def _referrers(self, target: Path) -> list[str]:
        """`<term> (<field>)` for every other local term whose `relatesTo` or
        `vocabulary` resolves to the local term folder `target` — exactly the
        refs `check` would report dangling once it is gone. Compared by folder
        identity, not spelling, so `admin/permission` never matches a top-level
        `permission`."""
        out = []
        for term in self.list_all(local_only=True):
            if _same_folder(self.root / term.slug, target):
                continue
            # `vocabulary` only on a Feature, the one kind `check` reads it on.
            vocabulary = term.vocabulary if term.kind == "Feature" else []
            for field, refs in (("relatesTo", term.relates_to),
                                ("vocabulary", vocabulary)):
                for ref in refs:
                    try:
                        hit = self.get(ref)
                    except AmbiguousRef:
                        continue
                    if (hit is not None and hit.origin == "local"
                            and _same_folder(self.root / hit.slug, target)):
                        out.append(f"{term.slug} ({field})")
                        break
        return out

    def extends_add(self, project_id: str) -> None:
        self._require_repository()
        project_id = validate_project_id(project_id)
        extends = _extends_ids(self.config, self._extends_label())
        if project_id in extends:
            raise ValueError(f"extends project already exists: {project_id}")
        registry = FsProjectRegistry.open(self.node_root).require_valid()
        project = registry.get(project_id)
        if project is None:
            note = unreachable_project_note(registry, project_id)
            raise ValueError(note or f"project '{project_id}' is not registered")
        if project_id == registry.current.id:
            raise ValueError("a taxonomy cannot extend itself")
        if not (Path(project.locator) / "docs" / "taxonomy").is_dir():
            raise ValueError(f"project '{project_id}' has no docs/taxonomy/")
        extends.append(project_id)
        self._persist_extends(extends)

    def extends_remove(self, project_id: str) -> None:
        self._require_repository()
        extends = _extends_ids(self.config, self._extends_label())
        if project_id not in extends:
            raise ValueError(f"no such extends project: {project_id}")
        extends.remove(project_id)
        self._persist_extends(extends)

    # -- validation --

    def _ref_problem(self, ref: str, expect_vocabulary: bool = False
                     ) -> tuple[Term | None, str | None]:
        """Resolve one taxonomy ref: `(term, problem)`.

        `problem` is None when the ref resolves (and, with `expect_vocabulary`,
        points at a Vocabulary), else one of `"dangling"`, `"ambiguous"`,
        `"kind"`. The three callers — `check`, `update_term`, `add` — each render
        those codes in their own wording; only `_wrong_kind_ref` is shared.
        """
        try:
            term = self.get(ref)
        except AmbiguousRef:
            return None, "ambiguous"
        if term is None:
            return None, "dangling"
        if expect_vocabulary and term.kind != "Vocabulary":
            return term, "kind"
        return term, None

    def _require_ref(self, ref: str, label: str, expect_vocabulary: bool = False) -> Term:
        """`_ref_problem` in raising form — the write paths (`add`, `update_term`)."""
        term, problem = self._ref_problem(ref, expect_vocabulary)
        if problem == "dangling":
            raise ValueError(f"{label} ref '{ref}' does not resolve")
        if problem == "ambiguous":
            raise ValueError(f"{label} ref '{ref}' is ambiguous")
        if problem == "kind":
            raise ValueError(_wrong_kind_ref(ref, term.kind))
        return term

    def _resolve_vocab_ref(self, ref: str) -> str:
        """A `--vocab` ref as it will be stored — or `ValueError`.

        A ref that already resolves is stored verbatim (nothing is qualified).
        One that does not is retried as a *leaf slug* against the local tree,
        and the full path it matched is what gets stored. The asymmetry is
        deliberate: a leaf slug is an input convenience at the write boundary,
        not a stored identity, so no read path widens (`get()` is unchanged and
        `tcw taxonomy show zeta` still fails) while a stored ref always
        resolves for `check`. Local terms only — an inherited tree stays
        addressable as `alias/path`, like `get_inherited`.
        """
        if self._ref_problem(ref, expect_vocabulary=True)[1] == "dangling":
            matches = [s for s in self._local_slugs() if s.rsplit("/", 1)[-1] == ref]
            if len(matches) > 1:
                raise ValueError(f"vocabulary ref '{ref}' is ambiguous: "
                                 f"{', '.join(matches)}")
            if matches:
                ref = matches[0]
        self._require_ref(ref, "vocabulary", expect_vocabulary=True)
        return ref

    def check(self, identifier: str | None = None) -> list[str]:
        problems: list[str] = []
        top_level = {s.split("/")[0] for s in self._local_slugs()}
        for project_id in self._federation_cycles():
            problems.append(f"extends '{project_id}': cycle in taxonomy federation")
        for project_id in self._inherited_stores():
            if project_id in top_level:
                problems.append(
                    f"project ID '{project_id}' collides with local top-level term"
                )
        if identifier is None:
            # About the store, not any one term — left out of a scoped check,
            # which is how `tcw serve` validates the object it just wrote.
            problems += self._legacy_config_problems()

        if identifier is not None:
            selected = self.get(identifier)
            if selected is None:
                return [f"no such term: {identifier}"]
            terms = [selected]
        else:
            terms = self.list_all(local_only=True)
        for term in terms:
            if term.kind not in TAXONOMY_KINDS:
                problems.append(f"{term.slug}: unknown kind '{term.kind}'")
            for ref in term.relates_to:
                if (problem := self._ref_problem(ref)[1]):
                    problems.append(f"{term.slug}: {problem} relatesTo ref '{ref}'")
            if term.kind == "Feature":
                if not term.vocabulary:
                    problems.append(f"{term.slug}: Feature requires at least one vocabulary ref")
                for ref in term.vocabulary:
                    target, problem = self._ref_problem(ref, expect_vocabulary=True)
                    if problem == "kind":
                        problems.append(f"{term.slug}: {_wrong_kind_ref(ref, target.kind)}")
                    elif problem:
                        problems.append(f"{term.slug}: {problem} vocabulary ref '{ref}'")
        return problems

    def _validation_resources(self, identifier: str) -> list[Path]:
        """Filesystem resources bounded to one taxonomy object."""
        try:
            identifier = _safe_store_id(identifier, "taxonomy target")
        except ValueError:
            return []
        local_folder = self.root / identifier
        if local_folder.is_dir() and self._within_store(local_folder):
            owner, folder = self, local_folder
        else:
            term = self.get(identifier)
            if term is None:
                return []
            owner = (
                self if term.origin == "local"
                else self._inherited_stores()[term.origin]
            )
            folder = owner.root / term.slug
        # Asked of the *owning* store: an inherited term's files are bounded by
        # its own root, not this one.
        return [path for path in (folder / "meta.yaml", folder / "description.md")
                if path.is_file() and owner._within_store(path)]

    # -- revision-bearing detail + update --

    def get_term_detail(self, ref: str) -> "TermDetail" | None:
        term = self.get(ref)
        if term is None:
            return None
        # Inherited terms' files live under the source store's root, not ours.
        owner = (
            self if term.origin == "local"
            else self._inherited_stores()[term.origin]
        )
        d = owner.root / term.slug
        meta_text, desc_text = owner._node_texts(d)
        return TermDetail(term=term, core_revision=_revision_multi(meta_text, desc_text))

    def update_term(self, ref: str, *,
                    name=_UNSET, description=_UNSET, relates_to=_UNSET,
                    vocabulary=_UNSET, kind=_UNSET,
                    core_revision: str | None = None) -> "TermDetail":
        # Resolve the term (must be local)
        term = self.get(ref)
        if term is None:
            raise ValueError(f"no such term: {ref}")
        if term.origin != "local":
            raise ValueError(f"cannot update inherited term '{term.qualified}' "
                             f"(edit it at its source)")
        d = self.root / term.slug

        # Validate provided fields against the editable set
        provided = {}
        for key, val in [("name", name), ("description", description),
                         ("relates_to", relates_to), ("vocabulary", vocabulary),
                         ("kind", kind)]:
            if val is not _UNSET:
                if key not in TAXONOMY_EDITABLE_FIELDS:
                    raise ValueError(f"field '{key}' is not editable")
                provided[key] = val

        # Stale revision check
        if core_revision is not None:
            detail = self.get_term_detail(ref)
            if detail and detail.core_revision != core_revision:
                raise StaleRevision(
                    f"stale revision for term '{ref}' "
                    f"(expected {core_revision}, got {detail.core_revision})")

        # Read current state
        meta, desc_text = load_yaml(d / "meta.yaml"), ""
        if (d / "description.md").is_file() and self._within_store(d / "description.md"):
            desc_text = (d / "description.md").read_text(encoding="utf-8")

        # Apply changes
        if "name" in provided:
            meta["name"] = provided["name"] if provided["name"] is not None else ""
        if "description" in provided:
            desc_text = provided["description"] if provided["description"] is not None else ""
        if "relates_to" in provided:
            meta["relatesTo"] = (provided["relates_to"]
                                 if provided["relates_to"] is not None else [])
        if "vocabulary" in provided:
            meta["vocabulary"] = (provided["vocabulary"]
                                  if provided["vocabulary"] is not None else [])
        if "kind" in provided:
            new_kind = _normalize_taxonomy_kind(provided["kind"])
            if provided["kind"] is not None and new_kind not in TAXONOMY_KINDS:
                raise ValueError(f"invalid taxonomy kind '{new_kind}' "
                                 f"(choose: {', '.join(sorted(TAXONOMY_KINDS))})")
            meta["kind"] = new_kind if provided["kind"] is not None else "Vocabulary"

        # Validate taxonomy refs (relatesTo, vocabulary)
        for r in meta.get("relatesTo", []):
            self._require_ref(r, "relatesTo")
        if meta.get("kind", "Vocabulary") == "Feature":
            vocs = meta.get("vocabulary", [])
            if not vocs:
                raise ValueError("Feature requires at least one vocabulary ref")
            for r in vocs:
                self._require_ref(r, "vocabulary", expect_vocabulary=True)

        # Write atomically
        self._write_node(d, meta, desc_text)

        # Return fresh detail
        return _require_detail(self.get_term_detail(ref), "term", ref)


# ── FsCapabilitiesStore ──────────────────────────────────────────────────────

# Meta keys that are structural (not part of the locked CAP_FIELDS vocabulary).
_CAP_STRUCTURAL = {"id", "name", "overrides", "prependedDocs", "appendedDocs"}


def heading_slug(text: str) -> str:
    """GitHub-flavored heading anchor: lowercased, punctuation stripped, spaces→'-'.

    Still used by the serve viewer for anchors; no longer part of capability
    identity (capabilities are path-addressed folders).
    """
    s = re.sub(r"[^\w\s-]", "", text.strip().lower())
    return re.sub(r"\s+", "-", s)


def _mint_cap_id() -> str:
    """A fresh opaque, immutable capability id (`cap-` + 6 hex). Not path-derived."""
    return "cap-" + uuid.uuid4().hex[:6]


def _as_list(v) -> list[str]:
    """Normalize a scalar / list / comma-string meta value to a list of strings."""
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return [s.strip() for s in str(v).split(",") if s.strip()]


class FsCapabilitiesStore(FsTreeStore, _FederationCycles, CapabilitiesStore):
    """`CapabilitiesStore` over folder-per-capability nodes under
    `docs/capabilities/`, optionally federated via `extends`.

    A capability is a folder with `meta.yaml` (`id` + `name` + the locked
    metadata vocabulary) and `description.md` (the body). A directory is a
    capability iff it holds a `meta.yaml`; dirs without one are pure grouping
    parents. Mirrors `FsTaxonomyStore` on the shared tree-store core.
    """
    COMPONENT = "capabilities"
    LEGACY_CONFIG_NAME = ".config.yaml"

    def __init__(self, root: Path, *,
                 _walk: "_FederationWalk | None" = None,
                 node_root: Path | None = None, store_git_root: Path | None = None):
        super().__init__(root, node_root=node_root, store_git_root=store_git_root)
        self.extends: dict[str, "FsCapabilitiesStore"] = {}
        # Reused, never rebuilt: the resolution below already constructed each
        # store with the right node root and the right walk state. There is no
        # second filter on the results — the `_seen` set that used to be one was
        # dead once recursion moved into `_extended_component_stores`, since the
        # only case it could refuse is a self-extend the identity check there
        # already refuses by project id.
        self.extends, self.extends_cycles = _extended_component_stores(
            self.node_root, self.config, self._extends_label(), "capabilities",
            walk=_walk,
        )

    # -- resolution --

    def _is_capability(self, d: Path) -> bool:
        return (d / "meta.yaml").is_file()

    def _all_meta_dirs(self) -> list[str]:
        """Every folder holding a meta.yaml (capabilities + overrides), minus dot-dirs."""
        out = []
        for p in sorted(self.root.rglob("*")):
            if not p.is_dir():
                continue
            rel = p.relative_to(self.root)
            if any(part.startswith(".") for part in rel.parts):
                continue
            if not self._node_readable(p):
                continue                      # before the _is_capability stat
            if self._is_capability(p):
                out.append(str(rel))
        return out

    def _local_paths(self) -> list[str]:
        """Standalone local capabilities — meta.yaml folders WITHOUT an `overrides`
        pointer (those are deltas, not caps; see `_override_index`)."""
        return [p for p in self._all_meta_dirs()
                if not load_yaml(self.root / p / "meta.yaml").get("overrides")]

    def _override_fields(self) -> list[tuple[str, dict]]:
        """`(path, fields)` for every local override: the fields it sets on the
        capability it overrides — its meta minus the structural keys and minus
        `null`, which clears an inherited field and so references nothing.

        The one definition of an override's references, read by `check` and by
        the taxonomy's refusal to remove a term something still names; an
        override's `Subject` becomes the composed capability's (`_apply_override`),
        so leaving it out of either lets a reference dangle unreported."""
        out = []
        for p in self._all_meta_dirs():
            meta = load_yaml(self.root / p / "meta.yaml")
            if meta.get("overrides"):
                out.append((p, self._set_fields(meta)))
        return out

    @staticmethod
    def _set_fields(meta: dict) -> dict:
        """The fields an override's meta sets (see `_override_fields`)."""
        return {k: v for k, v in meta.items()
                if k not in _CAP_STRUCTURAL and v is not None}

    def _override_index(self) -> dict[str, tuple[Path, dict]]:
        """`overrides` target string → (override folder, override meta)."""
        idx: dict[str, tuple[Path, dict]] = {}
        for p in self._all_meta_dirs():
            meta = load_yaml(self.root / p / "meta.yaml")
            target = meta.get("overrides")
            if target:
                idx[str(target)] = (self.root / p, meta)
        return idx

    def _compose_body(self, d: Path, meta: dict, raw_desc: str) -> str:
        """Effective body = prependedDocs + description + appendedDocs (bounded lists)."""
        parts = []
        # `_within_store` on each attachment: these are read by name from meta,
        # so they never pass through `_load_node`'s filtered name list.
        for fn in _as_list(meta.get("prependedDocs")):
            f = d / fn
            if f.is_file() and self._within_store(f):
                parts.append(f.read_text(encoding="utf-8").strip())
        if raw_desc.strip():
            parts.append(raw_desc.strip())
        for fn in _as_list(meta.get("appendedDocs")):
            f = d / fn
            if f.is_file() and self._within_store(f):
                parts.append(f.read_text(encoding="utf-8").strip())
        return "\n\n".join(parts)

    def _capability(self, path: str, origin: str = "local") -> Capability:
        d = self.root / path
        meta, description, _attachments = self._load_node(d)
        fields = {k: v for k, v in meta.items() if k not in _CAP_STRUCTURAL}
        if "Subject" in fields:
            fields["Subject"] = _as_list(fields["Subject"])
        return Capability(
            path=path,
            name=meta.get("name") or path.rsplit("/", 1)[-1].replace("-", " ").title(),
            id=str(meta.get("id") or ""),
            fields=fields,
            body=self._compose_body(d, meta, description),
            origin=origin,
            modified=_modified_timestamp(_capability_resources(d, meta)),
        )

    def _apply_override(self, base: Capability, alias: str,
                        ov_index: dict[str, tuple[Path, dict]]) -> Capability:
        """Merge a local override (if any) onto an inherited capability `base`.

        Override matches by upstream id (bare `<id>` or `<alias>/<id>`). Fields
        partial-merge (YAML null clears); body = child.prepend + (child
        description.md if present else upstream raw description.md) + child.append.
        """
        ov = ov_index.get(base.id) or ov_index.get(f"{alias}/{base.id}")
        if ov is None:
            return base                                   # inherited verbatim
        d, meta = ov
        merged = dict(base.fields)
        for k, v in meta.items():
            if k in _CAP_STRUCTURAL:
                continue
            if v is None:
                merged.pop(k, None)                       # null clears inherited field
            else:
                merged[k] = _as_list(v) if k == "Subject" else v
        up_store = self.extends[alias]
        up_desc = up_store.root / base.path / "description.md"
        upstream_raw = (up_desc.read_text(encoding="utf-8")
                        if up_desc.exists() and up_store._within_store(up_desc) else "")
        child_desc = d / "description.md"
        child_raw = (child_desc.read_text(encoding="utf-8")
                     if child_desc.exists() and self._within_store(child_desc) else "")
        mid = child_raw if child_raw.strip() else upstream_raw
        return Capability(
            path=base.path,
            name=meta.get("name") or base.name,
            id=base.id,
            fields=merged,
            body=self._compose_body(d, meta, mid),
            origin=alias,
            modified=max(
                filter(
                    None,
                    [
                        base.modified,
                        _modified_timestamp(_capability_resources(d, meta)),
                    ],
                ),
                default="",
            ),
        )

    def get_local(self, path: str) -> Capability | None:
        d = self.root / path
        # Reordered rather than extended: the old one-expression form called
        # `load_yaml` inside the condition, so a containment test appended to
        # the end would parse a meta.yaml outside the store before rejecting it.
        # The stat stays first so a miss pays no `resolve()`.
        if not (path and self._is_capability(d) and self._node_readable(d)):
            return None
        return None if load_yaml(d / "meta.yaml").get("overrides") else self._capability(path)

    def get_by_id(self, cap_id: str) -> Capability | None:
        """Resolve an opaque id to its local capability (keyed lookup)."""
        for p in self._local_paths():
            c = self._capability(p)
            if c.id and c.id == cap_id:
                return c
        return None

    def list_all(self, status=None, namespace=None, local_only=False) -> list[Capability]:
        caps = [self._capability(p) for p in self._local_paths()]
        if not local_only:
            ov_index = self._override_index()
            for alias, st in self.extends.items():
                caps += [self._apply_override(st._capability(p, origin=alias), alias, ov_index)
                         for p in st._local_paths()]
        out = []
        for c in caps:
            if status and c.status != status:
                continue
            if namespace and c.path.split("/")[0] != namespace:
                continue
            out.append(c)
        return out

    def get(self, identifier: str) -> Capability | None:
        head, _, rest = identifier.partition("/")
        if head in self.extends:                         # prefixed
            return self.get_inherited(head, rest)
        local = self.get_local(identifier)               # bare-wins-local
        if local is not None:
            return local
        matches = [(a, c) for a, st in self.extends.items()
                   if (c := st.get_local(identifier)) is not None]
        if len(matches) == 1:
            a = matches[0][0]
            return self._apply_override(self.extends[a]._capability(identifier, origin=a),
                                        a, self._override_index())
        if len(matches) > 1:
            raise AmbiguousRef(identifier)
        return None

    def get_inherited(self, alias: str, path: str) -> Capability | None:
        st = self.extends.get(alias)
        if not (st and st.get_local(path)):
            return None
        return self._apply_override(st._capability(path, origin=alias),
                                    alias, self._override_index())

    def _status_is_local(self, cap: Capability) -> bool:
        """True iff `cap`'s Status is a local decision, not an inherited default.
        A local capability always is; an inherited one only if a local override
        matches its upstream id (exactly as `_apply_override` keys) AND that
        override sets `Status` (an override editing only a body/field re-inherits
        the master's Status — `tcw/store/fs.py` `_apply_override`)."""
        if cap.origin == "local":
            return True
        ov = self._override_index()
        hit = ov.get(cap.id) or ov.get(f"{cap.origin}/{cap.id}")
        return hit is not None and "Status" in hit[1]

    def unreviewed_inherited(self) -> list[Capability]:
        return [c for c in self.list_all()
                if c.origin != "local" and not self._status_is_local(c)]

    def search(self, query: str) -> list[Capability]:
        q = query.lower()
        return [c for c in self.list_all()
                if q in c.name.lower() or q in c.body.lower()]

    # -- writes --

    def add(self, identifier, name=None, status="Missing", body="",
            fields=None) -> Capability:
        path = _safe_store_id(identifier, "path")
        if status not in CAP_STATUSES:
            raise ValueError(f"invalid Status '{status}' "
                             f"(choose: {', '.join(sorted(CAP_STATUSES))})")
        d = self.root / path
        if not self._within_store(d):
            raise ValueError(f"no such capability: {path}")
        if d.exists() or d.is_symlink():   # a dangling/looping link reads absent
            raise ValueError(f"capability already exists: {path}")
        # After the cheap string and stat refusals, because this one may open a
        # taxonomy store — and before `_write_node`, which is the point: a create
        # carrying a field the store would reject must leave nothing behind.
        norm = self._validate_fields(fields or {})
        display = name or path.rsplit("/", 1)[-1].replace("-", " ").title()
        meta = {"id": _mint_cap_id(), "name": display, "Status": status}
        # Field values win over the `status` parameter — what create-then-set
        # did. A None clears, rather than being skipped: there *is* something to
        # clear, the Status seeded a line above, and `_merge_meta` pops the key
        # on a local node. Skipping it would keep a Status the caller asked to
        # remove, which create-then-set did not.
        for k, v in norm.items():
            if v is None:
                meta.pop(k, None)
            else:
                meta[k] = v
        self._write_node(d, meta, body)
        return self._capability(path)

    def remove(self, identifier: str) -> None:
        cap = self.get(identifier)
        # The exact listed spelling only. `get` resolves `routes/`, `./routes`,
        # or `Routes` on a case-insensitive disk, to the `routes` folder but
        # echoes the spelling back as the path, so everything below that works
        # from the path would be working from the wrong one.
        if cap is not None and cap.origin == "local" and cap.path not in self._local_paths():
            cap = None
        if cap is None:
            raise ValueError(f"no such capability: {identifier}")
        if cap.origin != "local":
            raise ValueError(f"cannot remove inherited capability '{cap.qualified}' "
                             f"(edit it at its source; to drop a local override use "
                             f"`tcw capabilities reset`)")
        d = self.root / cap.path
        # Refused, never cascaded: `_rm` deletes the whole folder. Asked of the
        # folder itself rather than `_all_meta_dirs`, which skips dot-directories
        # and unreadable nodes that `git rm -rf` would delete all the same.
        nested = sorted(str(m.parent.relative_to(self.root))
                        for m in d.rglob("meta.yaml") if m.parent != d)
        if nested:
            raise ValueError(f"cannot remove '{cap.path}': nested under it: "
                             f"{', '.join(nested)} (remove those first)")
        referrers = self._referrers(d)
        if referrers:
            raise ValueError(f"cannot remove '{cap.path}': still referenced by "
                             f"{', '.join(referrers)} (repoint or clear those fields first)")
        self._rm(d)

    def _referrers(self, target: Path) -> list[str]:
        """`<folder> (<field>)` for every other local capability or override whose
        reference fields resolve to the local capability folder `target`.

        Each field is read exactly as `check` reads it (`_ref_problems`,
        `_check_globals`), so this refuses on precisely the references `check`
        would report as dangling afterwards. A hit is compared by folder identity,
        not spelling: `a/b/`, `x/../a/b` and a differently-cased `A/B` all
        resolve, and `set` accepts each.
        """
        def tokens(field: str, raw) -> list[str]:
            if field in ("Superseded by", "Blocked by"):
                return [str(raw)]
            ns = "roles" if field == "Roles" else "conditions"
            toks = raw if isinstance(raw, list) else str(raw).split(",")
            refs = [str(s).strip().lstrip("!") for s in toks if str(s).strip()]
            return [r for r in refs if r.startswith(f"{ns}/")]

        def same(a: Path) -> bool:
            return _same_folder(a, target)

        out = []
        for p in self._all_meta_dirs():
            folder = self.root / p
            if same(folder):
                continue
            meta = load_yaml(folder / "meta.yaml")
            for field in ("Superseded by", "Blocked by", "Roles", "When"):
                if field not in meta:
                    continue
                for ref in tokens(field, meta[field]):
                    try:
                        hit = self.get(ref)
                    except RefError:
                        continue
                    if hit is not None and hit.origin == "local" and same(self.root / hit.path):
                        out.append(f"{p} ({field})")
                        break
        return out

    def reset(self, identifier: str) -> None:
        # A standalone local capability is not an override — `remove` deletes it.
        if self.get_local(identifier) is not None:
            raise ValueError(f"'{identifier}' is a local capability, not an override "
                             f"(use `tcw capabilities rm` to delete it)")
        cap = self.get(identifier)                     # federated; may raise AmbiguousRef
        if cap is None:
            raise ValueError(f"no such capability: {identifier}")
        # Find the override by the same upstream-id keys `_write_target` writes,
        # so we drop whatever folder `set` materialized (bare or alias-qualified).
        ov_index = self._override_index()
        ov = ov_index.get(cap.id) or ov_index.get(f"{cap.origin}/{cap.id}")
        if ov is None:
            raise ValueError(f"no local override at '{identifier}' to reset "
                             f"(it inherits '{cap.qualified}' verbatim)")
        self._rm(ov[0])                                # remove only the local override folder

    def _validate_fields(self, fields: dict) -> dict:
        out = {}
        for k, v in fields.items():
            if k not in CAP_FIELDS:
                raise ValueError(f"unknown field '{k}' (not in the locked vocabulary)")
            if v is None:
                out[k] = None                            # clear sentinel
                continue
            if k == "Status" and v not in CAP_STATUSES:
                raise ValueError(f"invalid Status '{v}' "
                                 f"(choose: {', '.join(sorted(CAP_STATUSES))})")
            out[k] = _as_list(v) if k == "Subject" else v
        # Fail closed on refs, in the one seam both `set` and `update_capability`
        # call before touching disk — so the CLI, `tcw serve`'s PATCH and any
        # future caller inherit it rather than each remembering to check.
        #
        # `out`, not `fields`: Subject must be resolved after `_as_list`, so
        # `Subject=a,b` is two refs. `v is not None`: None is the documented
        # clear sentinel, and passing it through would make `_check_globals`
        # stringify it into a bogus problem about a field just cleared. Only the
        # refs this write *supplies*, never the merged node, or a capability with
        # one bad ref could not be repaired by the very command that repairs it.
        supplied = {k: v for k, v in out.items() if v is not None}
        # A taxonomy store is opened only when a field needing one was supplied:
        # the other four resolve against `self`, and a status-only repair should
        # not start failing because the node's taxonomy config is malformed.
        needs_taxonomy = bool(supplied.get("Subject")) or bool(supplied.get("Feature"))
        problems = self._ref_problems(
            supplied, self._taxonomy() if needs_taxonomy else None)
        if problems:
            # All of them, joined — `check` reports every problem, and a write
            # that reported one at a time would cost a round trip per bad ref.
            # No message contains "no such", so `_map_store_error` keeps these
            # at 422 rather than 404.
            raise ValueError("; ".join(problems))
        return out

    def _write_meta(self, d: Path, meta: dict, *,
                    also_stage: tuple[Path, ...] = ()) -> None:
        """Write a node's meta, staged, rolling back what this call created.

        Owns the `mkdir` so it can prove whether the directory is its own:
        `set` materializing a *fresh* override is the path where a refused write
        would otherwise leave an empty folder behind, and an update of an
        existing capability is the path where removing the folder would take
        files this call never wrote.
        """
        self._require_repository()
        owned = _mkdir_owned(d)
        self._write_staged(
            [(d / "meta.yaml",
              yaml.safe_dump(meta, sort_keys=False, allow_unicode=True))],
            owned_dir=d if owned else None, also_stage=also_stage)

    def _write_target(self, identifier: str) -> tuple[Path, dict, bool]:
        """Resolve a write to `(folder, meta, is_override)`.

        A local capability writes to its own folder. An *inherited* one writes to
        a local override — the existing one for its upstream id if there is any
        (wherever the author put it), else a fresh delta mirroring the upstream
        path. Materializing the override here is what lets `set` accept every path
        `show` accepts; the placement is an FS detail (another store would record
        the same delta keyed by the upstream id its own way).
        """
        local = self.get_local(identifier)
        if local is not None:
            d = self.root / local.path
            return d, load_yaml(d / "meta.yaml"), False
        cap = self.get(identifier)                     # federated; may raise AmbiguousRef
        if cap is None:
            raise ValueError(f"no such capability: {identifier}")
        ov_index = self._override_index()
        ov = ov_index.get(cap.id) or ov_index.get(f"{cap.origin}/{cap.id}")
        if ov is not None:
            return ov[0], ov[1], True                  # update in place
        d = self.root / cap.path                       # mirror the upstream path
        if self._is_capability(d):
            # Taken — by a local capability, or by another alias's override of
            # the same path. Qualify by origin rather than refusing: `show`
            # accepts this ref, so `set` has to as well.
            d = self.root / cap.origin / cap.path
        if self._is_capability(d):
            raise ValueError(
                f"cannot override '{cap.qualified}': both '{cap.path}' and "
                f"'{cap.origin}/{cap.path}' are already taken")
        # The mirror is the one write not downstream of a guarded lookup: a local
        # symlink shadowing the first segment of the upstream path would have it
        # create the folder and its meta.yaml outside the store.
        if not self._within_store(d):
            raise ValueError(f"no such capability: {identifier}")
        return d, {"overrides": f"{cap.origin}/{cap.id}"}, True

    def _merge_meta(self, meta: dict, norm: dict, is_override: bool) -> dict:
        """Merge validated fields into a node's meta.

        On an override a None writes an explicit YAML null — `_apply_override`
        reads that as *clear the inherited field*, where popping the key would
        mean *re-inherit it*. On a local node None pops, as it always has.
        """
        for k, v in norm.items():
            if v is None and not is_override:
                meta.pop(k, None)
            else:
                meta[k] = v
        return meta

    def set(self, identifier: str, fields: dict) -> Capability:
        self._require_repository()
        norm = self._validate_fields(fields)           # validate before touching disk
        d, meta, is_override = self._write_target(identifier)
        # `_write_meta` owns the mkdir and the rollback: `_write_target` can
        # materialize a fresh override directory, and a refused write must not
        # leave an empty one behind.
        self._write_meta(d, self._merge_meta(meta, norm, is_override))
        return self.get(identifier)                    # the composed (post-merge) entry

    # -- federation config --

    def extends_add(self, project_id: str) -> None:
        self._require_repository()
        project_id = validate_project_id(project_id)
        extends = _extends_ids(self.config, self._extends_label())
        if project_id in extends:
            raise ValueError(f"extends project already exists: {project_id}")
        registry = FsProjectRegistry.open(self.node_root).require_valid()
        project = registry.get(project_id)
        if project is None:
            note = unreachable_project_note(registry, project_id)
            raise ValueError(note or f"project '{project_id}' is not registered")
        if project_id == registry.current.id:
            raise ValueError("a capabilities store cannot extend itself")
        if not (Path(project.locator) / "docs" / "capabilities").is_dir():
            raise ValueError(f"project '{project_id}' has no docs/capabilities/")
        extends.append(project_id)
        self._persist_extends(extends)

    def extends_remove(self, project_id: str) -> None:
        self._require_repository()
        extends = _extends_ids(self.config, self._extends_label())
        if project_id not in extends:
            raise ValueError(f"no such extends project: {project_id}")
        extends.remove(project_id)
        self._persist_extends(extends)

    # -- validation --

    def _taxonomy(self) -> "FsTaxonomyStore | None":
        """The sibling taxonomy store for this node, or None if it has none.

        The FS adapter's answer to "where does this store's taxonomy live";
        another adapter answers it from its own connection, so nothing about
        this belongs on the abstract interface. Putting it on the store rather
        than in the call is what makes it impossible to forget: `set`,
        `update_capability` and `check` all reach the same handle.
        """
        # A taxonomy that is present and cannot open raises: that is a broken
        # configuration, not "this node has no taxonomy".
        return (FsTaxonomyStore.open(self.node_root)
                if tree_store_present(self.node_root, "taxonomy") else None)

    def check(self, taxonomy=None, identifier: str | None = None) -> list[str]:
        # `is not None`, not `or`: an explicitly injected store must win even
        # when it is falsey. Without the fallback, `check()` called bare skips
        # Subject/Feature entirely, so the write path and `check` could disagree
        # about *whether* a ref is checked even once they agree about what a
        # problem is.
        problems: list[str] = []
        unchecked = ""
        if taxonomy is None:
            try:
                taxonomy = self._taxonomy()
            except ValueError as e:
                # A taxonomy that is configured and will not open — declared and
                # not yet provisioned, say — costs the Subject/Feature checks, not
                # every other problem this ledger has. Said once, and only if a
                # capability checked here names a Subject or Feature: otherwise
                # nothing went unchecked, and every save would carry the line.
                unchecked = f"Subject and Feature not checked: {e}"
        top_level = {s.split("/")[0] for s in self._local_paths()}
        for project_id in self._federation_cycles():
            problems.append(f"extends '{project_id}': cycle in capability federation")
        for project_id in self.extends:
            if project_id in top_level:
                problems.append(
                    f"project ID '{project_id}' collides with local top-level capability"
                )
        if identifier is None:
            problems += self._legacy_config_problems()     # see FsTaxonomyStore.check

        selected = self.get(identifier) if identifier is not None else None
        if identifier is not None and selected is None:
            return [f"no such capability: {identifier}"]
        if selected is not None:
            seen_ids: dict[str, str] = {}
            for path in self._local_paths():
                if path == selected.path:
                    continue
                try:
                    candidate_id = str(load_yaml(self.root / path / "meta.yaml").get("id") or "")
                except yaml.YAMLError:
                    continue
                if candidate_id:
                    seen_ids[candidate_id] = path
            caps = [selected]
        else:
            seen_ids = {}
            caps = self.list_all(local_only=True)
        for cap in caps:
            where = cap.path
            f = cap.fields
            if not cap.id:
                problems.append(f"{where}: missing id")
            elif cap.id in seen_ids:
                problems.append(f"{where}: duplicate id '{cap.id}' (also {seen_ids[cap.id]})")
            else:
                seen_ids[cap.id] = where
            for key in f:
                if key not in CAP_FIELDS:
                    problems.append(f"{where}: unknown field '{key}'")
            status = f.get("Status")
            if status is None:
                problems.append(f"{where}: missing Status")
            elif status not in CAP_STATUSES:
                problems.append(f"{where}: invalid Status '{status}'")
            if "Priority" in f and f["Priority"] not in CAP_PRIORITIES:
                problems.append(f"{where}: invalid Priority '{f['Priority']}'")
            if "Lifecycle" in f and f["Lifecycle"] not in CAP_LIFECYCLES:
                problems.append(f"{where}: invalid Lifecycle '{f['Lifecycle']}'")
            if status == "Partial" and "Gaps" not in f:
                problems.append(f"{where}: Partial requires Gaps")
            if status == "Blocked" and "Blocked by" not in f:
                problems.append(f"{where}: Blocked requires Blocked by")
            problems += [f"{where}: {p}" for p in self._ref_problems(f, taxonomy)]
            if unchecked and (f.get("Subject") or f.get("Feature")):
                problems.append(unchecked)
                unchecked = ""

        # Override + attachment validation (every meta dir, incl. override folders).
        meta_dirs = self._all_meta_dirs()
        if selected is not None:
            meta_dirs = [selected.path]
        for p in meta_dirs:
            d = self.root / p
            # `is_dir` because an inherited capability's path is upstream's, and
            # a local folder of that name exists only when its override sits there.
            if not d.is_dir() or not self._node_readable(d):
                continue          # `selected` bypasses the _all_meta_dirs filter
            meta = load_yaml(d / "meta.yaml")
            listed = _as_list(meta.get("prependedDocs")) + _as_list(meta.get("appendedDocs"))
            for fn in listed:
                if not (d / fn).is_file():
                    problems.append(f"{p}: missing attachment '{fn}'")
            for f in d.iterdir():
                if (f.is_file() and f.suffix == ".md" and f.name != "description.md"
                        and f.name not in listed):
                    problems.append(f"{p}: unlisted extra doc '{f.name}'")
            target = meta.get("overrides")
            if target and (e := self._override_problem(str(target))):
                problems.append(f"{p}: {e}")
            if target and selected is None:
                # The references it sets, checked as a local capability's are:
                # they become the composed capability's own. A selected
                # capability's composed fields, override included, were checked
                # above; checking them here too reported each problem twice.
                fields = self._set_fields(meta)
                problems += [f"{p}: {e}" for e in self._ref_problems(fields, taxonomy)]
                if unchecked and (fields.get("Subject") or fields.get("Feature")):
                    problems.append(unchecked)
                    unchecked = ""
        return problems

    def _validation_resources(self, identifier: str) -> list[Path]:
        """Filesystem resources bounded to one capability object."""
        try:
            identifier = _safe_store_id(identifier, "capability target")
        except ValueError:
            return []
        local_folder = self.root / identifier
        if (local_folder / "meta.yaml").is_file() and self._node_readable(local_folder):
            owner, folder = self, local_folder
        else:
            cap = self.get(identifier)
            if cap is None:
                return []
            owner = self if cap.origin == "local" else self.extends[cap.origin]
            folder = owner.root / cap.path
        try:
            meta = load_yaml(folder / "meta.yaml")
        except yaml.YAMLError:
            meta = {}
        names = ["meta.yaml", "description.md", *_as_list(meta.get("prependedDocs")),
                 *_as_list(meta.get("appendedDocs"))]
        # `validate()` parses and reads whatever comes back, so a listed
        # attachment that is a symlink out of the store would be read there —
        # the folder guard above cannot see it. Asked of the *owning* store,
        # because an inherited folder is bounded by its own root, not this one.
        return [folder / name for name in names
                if (folder / name).is_file() and owner._within_store(folder / name)]

    def _override_problem(self, target: str) -> str | None:
        """Validate an `overrides: <target>` pointer (dangling / ambiguous / local)."""
        if "/" in target:                                 # alias-qualified <alias>/<id>
            alias, _, cid = target.partition("/")
            st = self.extends.get(alias)
            if st is None:
                # On the store being checked, an alias missing here is always
                # one `<component>.extends` does not declare: a declared alias
                # that cannot be resolved fails the open, and a cycle's back
                # edge is recorded on the deepest store, never this one.
                return (f"overrides → unknown alias '{alias}' "
                        f"(not declared in {self._extends_label()})")
            return None if st.get_by_id(cid) else f"overrides → dangling id '{target}'"
        if self.get_by_id(target):
            return f"overrides → '{target}' targets a local capability (must be inherited)"
        hits = [a for a, st in self.extends.items() if st.get_by_id(target)]
        if not hits:
            return f"overrides → dangling id '{target}'"
        if len(hits) > 1:
            return f"overrides → ambiguous id '{target}' (in {', '.join(hits)})"
        return None

    def _ref_problems(self, f: dict, taxonomy) -> list[str]:
        """Every cross-object ref problem in `f`, worded exactly as `check`
        reports it, minus the `<path>: ` location prefix.

        The single renderer: `check` prefixes these, the write path raises them.
        Two callers cannot disagree about what a problem *is* because there is
        only one place that says it.
        """
        out = []
        for key in ("Superseded by", "Blocked by"):
            if key in f and (e := self._ref_error(str(f[key]))):
                out.append(f"{key} → {e}")
        return (out + self._check_globals(f)
                + self._check_subject(f, taxonomy)
                + self._check_feature(f, taxonomy))

    def _ref_error(self, identifier: str) -> str | None:
        try:
            if self.get(identifier) is None:
                return f"dangling identifier '{identifier}'"
        except AmbiguousRef:
            return f"ambiguous identifier '{identifier}'"
        return None

    def _check_globals(self, f) -> list[str]:
        out = []
        for ns, field in (("roles", "Roles"), ("conditions", "When")):
            raw = f.get(field, "")
            toks = raw if isinstance(raw, list) else str(raw).split(",")
            for tok in (str(s).strip() for s in toks if str(s).strip()):
                ref = tok.lstrip("!")
                if not ref.startswith(f"{ns}/"):
                    out.append(f"{field} '{tok}' must be a {ns}/ slug")
                elif (e := self._ref_error(ref)):
                    out.append(f"{field} → {e}")
        return out

    @staticmethod
    def _term_refs(f) -> list[tuple[str, str]]:
        """`(field, ref)` for every taxonomy reference a capability makes — the
        one definition of which references count, read by `check` and by the
        taxonomy's refusal to remove a term a capability names.

        `str(...)`, as the other four ref fields already do: a ref resolver
        takes a string, and a non-string here used to escape as AttributeError
        out of `taxonomy.get` rather than as a refusal the caller can read."""
        refs = [("Subject", str(s)) for s in _as_list(f.get("Subject"))]
        if f.get("Feature"):
            refs.append(("Feature", str(f["Feature"])))
        return refs

    def _check_subject(self, f, taxonomy) -> list[str]:
        subjects = [ref for field, ref in self._term_refs(f) if field == "Subject"]
        if not subjects or taxonomy is None:
            return []
        out = []
        for subj in subjects:
            try:
                if taxonomy.get(subj) is None:
                    out.append(f"Subject → dangling ref '{subj}'")
            except AmbiguousRef:
                out.append(f"Subject → ambiguous ref '{subj}'")
        return out

    def _check_feature(self, f, taxonomy) -> list[str]:
        feature = next((ref for field, ref in self._term_refs(f)
                        if field == "Feature"), None)
        if not feature or taxonomy is None:
            return []
        try:
            target = taxonomy.get(feature)
        except AmbiguousRef:
            return [f"Feature → ambiguous ref '{feature}'"]
        if target is None:
            return [f"Feature → dangling ref '{feature}'"]
        if target.kind != "Feature":
            return [f"Feature → ref '{feature}' points to "
                    f"{target.kind}, expected Feature"]
        return []

    # -- revision-bearing detail + update --

    def get_capability_detail(self, identifier: str) -> "CapabilityDetail" | None:
        cap = self.get(identifier)
        if cap is None:
            return None
        owner = self if cap.origin == "local" else self.extends[cap.origin]
        texts = self._node_texts(owner.root / cap.path)
        if cap.origin != "local":
            # The local override's files are part of what the caller sees, so
            # they are part of the revision — else two edits to the same
            # override hash identically and a stale write sails through.
            ov_index = self._override_index()
            ov = ov_index.get(cap.id) or ov_index.get(f"{cap.origin}/{cap.id}")
            texts += self._node_texts(ov[0]) if ov else ["", ""]
        return CapabilityDetail(capability=cap, core_revision=_revision_multi(*texts))

    def update_capability(self, identifier, *, body=_UNSET, fields=_UNSET,
                          core_revision: str | None = None) -> "CapabilityDetail":
        self._require_repository()
        norm = self._validate_fields(fields) \
            if fields is not _UNSET and fields is not None else {}

        if core_revision is not None:
            detail = self.get_capability_detail(identifier)
            if detail and detail.core_revision != core_revision:
                raise StaleRevision(f"stale revision for capability '{identifier}'")

        d, meta, is_override = self._write_target(identifier)
        desc = d / "description.md"
        desc_text = desc.read_text(encoding="utf-8") if desc.exists() else ""
        if body is not _UNSET:
            desc_text = body if body is not None else ""
        meta = self._merge_meta(meta, norm, is_override)

        # No mkdir and no outer guard here any more: `_write_meta` and
        # `_write_node` each own their directory and roll back what they
        # created. Doing it here as well would double-delete — and, worse, the
        # old guard had to key on `meta.yaml` being absent precisely because it
        # wrapped a callee that stages internally.
        if is_override and not desc_text.strip():
            # An override's description.md is a *body delta*, and an empty one
            # means "no delta" — `_apply_override` falls back to the upstream
            # body (which is what makes append-only overrides work). So clearing
            # an override's body drops the delta and re-inherits, rather than
            # leaving an empty file that silently means the same thing.
            desc.unlink(missing_ok=True)
            # `also_stage=(d,)` rather than a second `self._stage(d)` after the
            # write: staging the directory is what records the unlink above, and
            # a separate call would sit outside `_write_meta`'s rollback — so a
            # refusal there left a freshly materialized override behind, which
            # is the class this item exists to close.
            self._write_meta(d, meta, also_stage=(d,))
        elif body is _UNSET and not desc.exists():
            self._write_meta(d, meta)          # pure delta — no empty body file
        else:
            self._write_node(d, meta, desc_text)
        return _require_detail(self.get_capability_detail(identifier),
                               "capability", identifier)


# ── provisioning (FS adapter: a declared store is a git checkout) ────────────
#
# Everything below realizes `StoreProvisioner` for the filesystem. Clones, refs
# and cache directories are named *here and nowhere else* — a store-interface
# signature that mentioned one would put the seam in the wrong layer.


def _git_subcommand(argv: list[str]) -> str:
    """The verb in a git argv, for an error message.

    `argv[1]` is not it. Every call here is built as
    `["git", "-C", <path>, <verb>, …]`, so naming `argv[1]` reported "git -C
    failed" for every failure the adapter has ever produced.
    """
    tokens = iter(argv[1:] if argv and argv[0] == "git" else argv)
    for token in tokens:
        if token == "-C":
            next(tokens, None)                 # skip the path it takes
            continue
        if not token.startswith("-"):
            return token
    return "command"


def _git_reason(done) -> str:
    """The line of git's output worth showing.

    Git puts the diagnosis first and the boilerplate last — an unreachable remote
    ends with "and the repository exists.", which is what taking the *last* line
    used to report. Prefer the first line git itself marked as the failure.
    """
    lines = [line.strip()
             for line in (done.stderr or done.stdout or "").strip().splitlines()
             if line.strip()]
    for line in lines:
        if line.startswith(("fatal:", "error:")):
            return line
    return lines[0] if lines else ""


def _normalize_remote(url: str) -> str:
    """A remote URL reduced to the differences that matter for identity here:
    surrounding whitespace, a trailing slash, and a `.git` suffix. Nothing more —
    see `_require_declared_checkout` for why this stays deliberately literal."""
    cleaned = (url or "").strip().rstrip("/")
    return cleaned[:-4] if cleaned.endswith(".git") else cleaned


# What a *node* is, for the provisioner: a directory carrying a sentinel. Not a
# component, and deliberately not spelled as one anywhere it could be mistaken
# for a store — `PROVISION_COMPONENTS` never contains it.
NODE_TARGET = "node"


def _is_store_layout(root: Path, component: str) -> bool:
    """Whether `root` holds `component`'s store, as far as the filesystem can say.

    The answer has two strengths, because the components differ in what they can
    honestly claim.

    A **work** store names nothing either (TCW-70 Design 3.5): it is present
    when its directory is, the same answer `WorkLocation.open` gives, so a
    provisioned store and an opened one agree.

    A **tree** store — taxonomy, capabilities — names nothing. `init` scaffolds
    it as a bare directory (see `init`'s plan loop), it holds no config file of its
    own at all now that `extends` lives in the node's `tcw-config.yaml`, and the
    only file reliably left behind is a `.gitkeep`, which is git's answer to
    empty directories and means nothing here. So "the directory is there" is the strongest honest answer, and it is
    shared by the work store: a declared tree store that clones
    into an empty directory reads as usable, because an empty taxonomy is a real
    state and nothing distinguishes the two. What this still refuses — a
    `repository.path` naming nothing at all — is what keeps "a failure leaves
    nothing behind" true for every component.

    `component` is required rather than defaulted: a caller that forgets it
    should not silently get a store's answer for a node.
    """
    if not root.is_dir():
        return False
    if component == NODE_TARGET:
        # A node names one file and it is the same file everywhere, which is
        # exactly how much a node can honestly claim.
        return (root / SENTINEL).is_file()
    return True


def _registry_checkout_root(
    node_root: Path, declaration: "RepositoryDeclaration"
) -> Path | None:
    """Where the declared store sits inside a project this machine already has.

    The join the ladder's rung 1.5 needs: ask the project registry which project
    is a checkout of the declared repository, then descend to the store's path
    within it. None when the registry cannot answer, which sends the ladder on
    to the provisioned copy.

    **Every failure here is "no answer", never an error.** This rung is a
    fallback reached only after a configured path has already failed, and a
    graph problem must not turn a working provisioned store into a refusal. So
    the registry is opened without `require_valid()` — the shape `run_provision`
    already uses for the same reason — and anything raised is swallowed.
    """
    try:
        found = FsProjectRegistry.open(node_root).checkout_of(declaration.url)
    except Exception:
        return None
    if found is None:
        return None
    return (found / declaration.path) if declaration.path else found


def resolve_store(store_cls, node_root: Path, _walk=None):
    """This node's store for `store_cls`'s component, in one ordered ladder.

    1. the local store (`<component>.path`, else `docs/<component>`) when it is
       usable;
    1.5. else inside a project the registry has already located here, when one
       is a checkout of the declared repository — local before remote, the same
       rule `ConnectedProject` states for a project's own location. Numbered as
       a half because it was added after the others and renumbering them would
       silently rewrite what every message and comment elsewhere calls "rule 2";
    2. else the declared home repository's provisioned location, if usable;
    3. else `StoreNotProvisioned`, when a home repository is declared;
    4. else exactly what the component did before a declaration existed — the
       same checks, in the same order, with the same messages.

    **A declaration is a fallback, never an override.** Rule 1 runs first so a
    checkout that already has the store keeps using it and nothing about that
    machine changes; the declaration answers only for a machine that does not
    have it. Rules 3 and 4 are the same failure told two ways: with a
    declaration it is actionable, so it says what to run.

    **Only `StoreLocationUnusable` falls through.** Rules 1 and 2 mean "try here,
    and if there is no store here try the next place" — which is a statement
    about the *location*, not about every way opening can fail. A store that is
    present and raises while opening has to surface, or the ladder answers a
    config error with `tcw provision`.

    One function for every component, because the ladder is the contract and
    three copies of a contract drift. The two things that genuinely differ are
    hooks on the store class: `_local_root`, which knows the component's default
    location and how a relative path re-anchors, and `_open_at`, which decides
    what "usable" means and builds the store. `COMPONENT` names the config
    section.
    """
    node_root = node_root.resolve()
    config_path = node_root / SENTINEL
    config = load_config(config_path)
    component = store_cls.COMPONENT
    section = config.get(component) or {} if isinstance(config, dict) else {}
    if not isinstance(section, dict):
        section = {}
    configured = section.get("path")
    if configured is not None and (not isinstance(configured, str) or not configured.strip()):
        raise ValueError(
            f"{config_path}: {component}.path must be a non-empty path string")
    raw_root = store_cls._local_root(node_root, configured)
    declaration, declaration_problems = parse_repository_declaration(
        section.get("repository"), f"{component}.repository")

    # Whether a candidate location has to prove it holds a store. It does once
    # anything points at it — a configured path, or a declaration that gives the
    # ladder somewhere else to fall to. It does not for a component's bare
    # default with nothing configured: that is rule 4, and for the tree stores
    # "return `docs/<component>` whether or not it exists" is the behaviour that
    # predates this ladder and must survive it.
    #
    # `declaration_problems` counts too, and that is not an edge case. A
    # malformed declaration parses to `(None, problems)`, so the ladder sees no
    # declaration and takes rule 4 — and a tree store's rule 4 validates nothing
    # and therefore cannot fail, which dropped the problems on a path that never
    # raised. The user got "no tcw taxonomy node here" for a typo in the block
    # right in front of them. A candidate allowed to mask a configuration error
    # has to be a real store, not a directory that might not exist.
    must_exist = (configured is not None or declaration is not None
                  or bool(declaration_problems))

    if declaration is None:                                     # rule 4
        try:
            return store_cls._open_at(
                raw_root, node_root, config_path,
                external=configured is not None, must_exist=must_exist,
                _walk=_walk)
        except ValueError:
            # A valid local store keeps reads working even when an unused
            # declaration is malformed. When no local store can open, however,
            # the declaration is the actionable config error and must not be
            # hidden behind the dead local path.
            if declaration_problems:
                raise StoreDeclarationError(
                    f"{config_path}: {'; '.join(declaration_problems)}") from None
            raise

    try:                                                        # rule 1
        return store_cls._open_at(
            raw_root, node_root, config_path,
            external=configured is not None, must_exist=must_exist,
            _walk=_walk)
    except StoreLocationUnusable as unusable:
        # Only this. A store that is *there* and fails to open — a federation
        # error, a malformed `extends` — is a real error, and swallowing it here
        # reported "not provisioned; run `tcw provision`", which then succeeded
        # and left the store exactly as unopenable. `_extended_component_stores`
        # raises for many more reasons than it used to, so the hole widened.
        #
        # The reason is carried rather than discarded, but **only when the
        # configured path is actually there**. A path that does not exist,
        # beside a declaration, is the ordinary case the declaration exists for
        # — reporting it would make every provisioned node noisy. A path that
        # exists and holds no store is a second configuration problem, and it
        # used to vanish behind rule 3's message entirely.
        #
        # Presence is tested here rather than read out of the message: `_open_at`
        # raises the same "is not a directory" for an absent path and for one
        # that is a file, so the message cannot tell them apart.
        local_failure = str(unusable) if raw_root.exists() else None
        prefix = f"{config_path}: "
        if local_failure and local_failure.startswith(prefix):
            local_failure = local_failure[len(prefix):]
    local = _registry_checkout_root(node_root, declaration)
    if local is not None:
        try:                                                    # rule 1.5
            # No `declaration=`, and that omission is the whole of "must not
            # publish". This store is on the user's own disk and they push it
            # themselves — the same reasoning rule 1 relies on. `publishes`
            # consults nothing else.
            return store_cls._open_at(
                local, node_root, config_path,
                external=True, must_exist=True, _walk=_walk)
        except StoreLocationUnusable:
            # The project is here but holds no store at the declared path.
            # A location that did not work out, so the ladder carries on —
            # the same rule rules 1 and 2 follow.
            pass
    try:                                                        # rule 2
        # The declaration travels with the store *only* here. Rules 1 and 1.5
        # above resolved without it, so a store built there carries None.
        return store_cls._open_at(
            provisioned_store_root(node_root, declaration), node_root, config_path,
            external=True, must_exist=True, declaration=declaration,
            _walk=_walk)
    except StoreLocationUnusable:
        pass                                                    # same rule
    raise StoreNotProvisioned(                                  # rule 3
        f"{config_path}: the {component} store is declared in "
        f"{declaration.url} but has not been provisioned here; "
        f"run `tcw provision` to obtain it"
        + (f" — and the configured {local_failure}" if local_failure else ""))


def declared_repository(
    node_root: Path, component: str
) -> tuple["RepositoryDeclaration | None", list[str]]:
    """A component's declared home repository, read straight from the config.

    Deliberately not a store method: the whole point is to answer for a component
    whose store cannot be opened, which is exactly when a store method would be
    unavailable. Component-generic from the start — it reads `<component>.repository`
    for any component, so extending provisioning past `work` adds a caller, not a
    reader.
    """
    try:
        config = load_config(node_root / SENTINEL)
    except ValueError:
        return None, []          # a config too broken to read declares nothing
    section = config.get(component) if isinstance(config, dict) else None
    if not isinstance(section, dict):
        return None, []
    return parse_repository_declaration(section.get("repository"),
                                        f"{component}.repository")


def declared_connected_projects(
    node_root: Path,
) -> tuple[list[tuple[str, RepositoryDeclaration, str]], list[str]]:
    """This node's connected projects that declare a repository, with problems.

    Each entry is (project id, declaration, relation): the relation is how the
    caller tells an upstream — obtained, but not read past — from the family.

    Reads the config directly, exactly as `declared_repository` does and for the
    same reason: it must answer for a graph that cannot be fully loaded, which is
    the only situation in which anyone asks.

    Returns every declared entry, provisioned or not — the caller decides what to
    do about one that is already here, because "already available" is a result
    worth printing rather than a silence.
    """
    try:
        config = load_config(node_root / SENTINEL)
    except ValueError:
        return [], []            # likewise: it declares no connected project
    connected = config.get("connected-projects") if isinstance(config, dict) else None
    if not isinstance(connected, dict):
        return [], []
    declared: list[tuple[str, RepositoryDeclaration, str]] = []
    problems: list[str] = []
    # `upstream` too: obtaining a read-only project into this machine's own
    # checkout area writes nothing into it, and a reader holding only its own
    # repository has no other way to reach one.
    for label in ("parent", "children", "upstream"):
        relation = connected.get(label)
        if not isinstance(relation, dict):
            continue
        for project_id, raw in relation.items():
            if not isinstance(project_id, str):
                continue
            entry, entry_problems = parse_connected_entry(
                project_id, raw, f"connected-projects.{label}.{project_id}")
            problems.extend(entry_problems)
            if entry is not None and entry.repository is not None:
                declared.append((entry.id, entry.repository, label))
    return declared, problems


class FsStoreProvisioner(StoreProvisioner):
    """A declared store, realized as a git checkout.

    Obtains into a temporary directory beside the target and renames it into
    place, so a failed or interrupted fetch is never visible as a store. That is
    what makes "leaves nothing behind" true rather than aspirational.
    """

    def __init__(self, node_root: Path, component: str,
                 declaration: RepositoryDeclaration | None):
        self.node_root = node_root.resolve()
        self.component = component
        self.declaration = declaration

    # -- StoreProvisioner --

    def describe(self) -> str:
        if self.declaration is None:
            return f"{self.component}: no home repository declared"
        d = self.declaration
        at = f" at {d.ref}" if d.ref else ""
        thing = "node" if self.component == NODE_TARGET else "store"
        within = f", {thing} at {d.path}" if d.path else ""
        return (f"{self.component}: {d.url}{at}{within} → "
                f"{provisioned_store_root(self.node_root, d)}")

    def is_available(self) -> bool:
        if self.declaration is None:
            return False
        target = provisioned_store_root(self.node_root, self.declaration)
        checkout = checkout_root(self.node_root, self.declaration)
        # A directory is not enough: the store needs a checkout of its own.
        # Check the filesystem marker rather than invoking Git: an
        # already-available second run is deliberately a zero-subprocess no-op.
        return (_is_store_layout(target, self.component)
                and (checkout / ".git").exists())

    def ensure_available(self, *, refresh: bool = False,
                         dry_run: bool = False) -> ProvisionResult:
        if self.declaration is None:
            return ProvisionResult(action="undeclared", available=False,
                                   detail=f"{self.component}: nothing declared")
        target = provisioned_store_root(self.node_root, self.declaration)
        checkout = checkout_root(self.node_root, self.declaration)

        if self.is_available() and not refresh:
            return ProvisionResult(action="available", available=True,
                                   location=str(target),
                                   detail=f"{self.component}: already available")
        if dry_run:
            verb = "refresh" if checkout.exists() else "obtain"
            # Short on purpose: the caller prints `describe()` immediately above,
            # and repeating it here read as "work: would obtain work: …".
            return ProvisionResult(action="planned", available=False,
                                   location=str(target),
                                   detail=f"{self.component}: would {verb} into {target}")

        if checkout.exists():
            # Before any network call: this working copy must be the declared
            # repository's. Otherwise the command prints one remote and contacts
            # another — and fetches into a checkout that is not ours to touch.
            self._require_declared_checkout(checkout)
            self._refresh(checkout)
            action = "refreshed"
        else:
            self._obtain(checkout)
            action = "obtained"

        # Still checked after a refresh: only `_obtain` can validate before
        # publishing, and a pre-existing checkout is the user's, so a bad layout
        # there is reported without deleting anything.
        self._require_store_layout(target)
        return ProvisionResult(action=action, available=True, location=str(target),
                               detail=f"{self.component}: {action} at {target}")

    def _require_store_layout(self, root: Path) -> None:
        """Refuse a repository that carries no store where the declaration says.

        Two shapes of refusal, because the two predicates fail differently: a
        tree store can only be absent, while a work store can also be present
        and incomplete, and naming the folders it lacks is what makes that
        message worth reading.
        """
        if _is_store_layout(root, self.component):
            return
        where = self.declaration.path or "."
        if self.component == NODE_TARGET:
            raise ValueError(
                f"connected-projects: {self.declaration.url} has no tcw node at "
                f"'{where}': no {SENTINEL} there")
        prefix = (f"{self.component}.repository: {self.declaration.url} has no "
                  f"{self.component} store at '{where}'")
        raise ValueError(f"{prefix}: no such directory in the repository")

    # -- git plumbing (adapter-private; nothing above this class names it) --

    def _obtain(self, checkout: Path) -> None:
        """Clone beside the target, then rename in. The rename is what makes a
        failure leave nothing behind — a half-clone is never at the real path.

        **Everything that can refuse runs before the rename**, the store-layout
        check included. Validating after publishing left a cloned repository at
        the target whenever it carried no store at the declared path: the command
        reported a failure and the directory stayed, so a re-run then took the
        *refresh* branch on a checkout that was never usable.
        """
        checkout.parent.mkdir(parents=True, exist_ok=True)
        staging = checkout.parent / f".{checkout.name}.tcw-{uuid.uuid4().hex[:8]}"
        try:
            self._run(["git", "clone", "--quiet", self.declaration.url, str(staging)])
            if self.declaration.ref:
                self._run(["git", "-C", str(staging), "checkout", "--quiet",
                           self.declaration.ref])
            self._require_store_layout(
                (staging / self.declaration.path) if self.declaration.path else staging)
            staging.rename(checkout)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise

    def _require_declared_checkout(self, checkout: Path) -> None:
        """Refuse to refresh a working copy that is not the declared repository's.

        Entering the refresh branch on `checkout.exists()` alone was enough to
        make `tcw provision` fetch some *other* repository's origin while having
        printed the declared URL — the one guarantee the explicit-verb design
        exists to provide. A declared `checkout` is an arbitrary user-chosen
        directory, so it can hold anything at all.

        Comparison is on the URL as spelled, normalized only for a trailing
        slash and a `.git` suffix. Deliberately not smarter: treating `ssh` and
        `https` spellings of one host as equal means deciding two URLs are the
        same repository, which this cannot know. The error says so, because the
        fix in that case is to point `checkout` somewhere else.
        """
        probe = _git(["git", "-C", str(checkout), "rev-parse", "--git-dir"],
                     capture_output=True, text=True)
        if probe.returncode != 0:
            raise ValueError(
                f"{self.component}.repository: {checkout} already exists and is not a "
                f"git repository; move it aside or point `checkout` elsewhere")
        origin = _git(["git", "-C", str(checkout), "remote", "get-url", "origin"],
                      capture_output=True, text=True)
        found = origin.stdout.strip() if origin.returncode == 0 else ""
        if _normalize_remote(found) != _normalize_remote(self.declaration.url):
            raise ValueError(
                f"{self.component}.repository: {checkout} is a checkout of "
                f"{found or '(no origin)'}, not the declared "
                f"{self.declaration.url}; nothing was contacted. Point `checkout` at a "
                f"different directory, or spell the declared url the way that "
                f"checkout's origin does")

    def _refresh(self, checkout: Path) -> None:
        """Fetch, then bring the working copy to the declared version.

        No `pull`: the target may be a tag or a commit, where merging is
        meaningless. Fast-forwarding is attempted only when the checked-out ref
        actually tracks a remote branch, and its absence is not an error.

        **Something else now depends on the ff-only part.** A published store
        refreshes here before every transition, so a remote that has moved
        incompatibly surfaces as a refused fast-forward *before* the item moves —
        that refusal is how divergence is reported, and it is the reason a
        transition never creates a merge commit inside somebody's work store.
        Relaxing this to a real merge for the tags-and-commits reason above would
        silently move divergence from a clean refusal into an automatic merge of
        two people's work items.
        """
        self._run(["git", "-C", str(checkout), "fetch", "--quiet", "--prune", "origin"])
        target = self.declaration.ref or self._remote_head(checkout)
        if target:
            self._run(["git", "-C", str(checkout), "checkout", "--quiet", target])
        upstream = _git(["git", "-C", str(checkout), "rev-parse", "--abbrev-ref",
                         "--symbolic-full-name", "@{u}"],
                        capture_output=True, text=True)
        if upstream.returncode == 0 and upstream.stdout.strip():
            self._run(["git", "-C", str(checkout), "merge", "--ff-only", "--quiet",
                       upstream.stdout.strip()])

    def _remote_head(self, checkout: Path) -> str | None:
        """The remote's default branch, or None when the remote never advertised
        one. None is a legitimate answer: the working copy simply stays put."""
        probe = _git(["git", "-C", str(checkout), "symbolic-ref", "--quiet",
                      "refs/remotes/origin/HEAD"], capture_output=True, text=True)
        if probe.returncode != 0:
            return None
        return probe.stdout.strip().rpartition("/")[2] or None

    def _run(self, argv: list[str]) -> None:
        """Every git call goes through `_git`, so stdin stays closed and a remote
        demanding credentials fails instead of hanging on a terminal nobody is
        watching."""
        done = _git(argv, capture_output=True, text=True)
        if done.returncode != 0:
            raise ValueError(
                f"{self.component}.repository: git {_git_subcommand(argv)} failed: "
                f"{_git_reason(done) or f'exit {done.returncode}'}")
