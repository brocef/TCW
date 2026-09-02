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
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import date, datetime, timezone
from contextlib import suppress
from functools import cached_property
from pathlib import Path
from typing import NoReturn

import yaml

from tcw.store.base import (
    BODY_ORDER, CAP_FIELDS, CAP_LIFECYCLES, CAP_PRIORITIES, CAP_STATUSES,
    DEFAULT_DOD,
    RESOLVED_STATUSES, TAXONOMY_EDITABLE_FIELDS, WORK_ARTIFACTS, WORK_SIDECARS,
    WORK_STATUSES, _UNSET, resolution_status,
    AmbiguousRef, Artifact, ArtifactResource, Capability, CapabilitiesStore,
    CapabilityDetail, MultipleMatch, RefError, AlreadyClaimed, IllegalTransition,
    InboxEntry, InboxEntryDetail, InboxResource, PlanStage, PlanStageResource,
    LifecyclePolicy, SidecarResource, StaleRevision, TransitionCommitError,
    Binding, DocEntry, body_title, frontmatter_end,
    parse_documentation_entries, parse_lifecycle_policy,
    parse_repository_declaration, ProvisionResult, RepositoryDeclaration,
    PublicationError, StoreDeclarationError, StoreNotProvisioned, StoreProvisioner,
    TaxonomyStore, Term, TermDetail, Tombstone,
    WorkDetail, WorkItem, WorkStore, normalize_tag, normalize_work_level,
)
from tcw.store.project import FsProjectRegistry, validate_project_id, worktree_anchors

# Component trees `tcw init` scaffolds. `work` gets a status-folder skeleton;
# `taxonomy` and `capabilities` are flat trees that fill in per their phases.
COMPONENTS = ("taxonomy", "capabilities", "work")


def _store_classes() -> dict:
    """Component → filesystem store class. A function, and consulted through the
    `STORE_CLASSES` mapping below, because the classes are defined further down
    this module than the helpers that need them."""
    return {"taxonomy": FsTaxonomyStore,
            "capabilities": FsCapabilitiesStore,
            "work": FsWorkStore}


class _StoreClasses:
    """Lazy view over `_store_classes()`, so `find_node` and `run_provision` name
    one mapping instead of each growing its own `if component ==` ladder — the
    shape that left `run_provision` calling `FsWorkStore.open` for every
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
    """Create or backfill the node sentinel without discarding configuration."""
    p = root / SENTINEL
    existing = load_yaml(p, unique=True) if p.exists() else {}
    if not isinstance(existing, dict):
        raise ValueError(f"{p}: config must be a mapping")
    configured = existing.get("id")
    if configured is not None:
        if not isinstance(configured, str):
            raise ValueError(f"{p}: project ID must be a string")
        configured = validate_project_id(configured)
        if project_id is not None and validate_project_id(project_id) != configured:
            raise ValueError(
                f"project already has id '{configured}'; refusing conflicting id '{project_id}'"
            )
        return False
    # Direct adapter callers (principally isolated store tests) receive a stable
    # fixture identity. The public CLI enforces explicit --id before calling us.
    project_id = project_id or "test-project"
    existing = {"id": validate_project_id(project_id), **existing}
    dump_yaml(p, existing)
    return True


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
    except ValueError:
        return None
    # A work store that opened is a work store; a tree store's `open` validates
    # nothing when nothing is configured (rule 4), so the "is this component
    # here at all?" question is still this function's to ask. Asked of the
    # resolved root rather than the default one, which is the whole point.
    return nr if component == "work" or store.root.is_dir() else None


def child_nodes(root: Path) -> list[Path]:
    """Direct registered children that contain a work store."""
    registry = FsProjectRegistry.open(root).require_valid()
    return [
        Path(project.locator)
        for project in registry.children()
        if _has_work_store(Path(project.locator))
    ]


def parent_node(root: Path) -> Path | None:
    """Direct registered parent that contains a work store."""
    registry = FsProjectRegistry.open(root).require_valid()
    parent = registry.parent()
    if parent is None:
        return None
    path = Path(parent.locator)
    return path if _has_work_store(path) else None


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
        FsWorkStore.open(node_root)
        return True
    except ValueError:                     # StoreNotProvisioned included, by design
        return False


def registered_project_id(anchor: Path, target: Path) -> str:
    """Return the canonical ID for a project reachable from ``anchor``."""
    target = target.resolve()
    registry = FsProjectRegistry.open(anchor).require_valid()
    projects = [registry.current, *registry.ancestors(), *registry.descendants()]
    for project in projects:
        if Path(project.locator).resolve() == target:
            return project.id
    raise ValueError(f"{target} is not registered from project '{registry.current.id}'")


def resolve_qualified_work_ref(anchor: Path, ref: str) -> "tuple[FsWorkStore, str] | None":
    """Resolve a (possibly qualified) work ref against `anchor`.

    Bare slug (no '/')      -> (anchor store, slug)             [unchanged]
    '<status>/…/<slug>'     -> (anchor store, <slug>)           [status-path locator]
    '<project-id>/<slug>'   -> (that node's store, <slug>)      [cross-node addressing]

    A leading segment in `WORK_STATUSES` marks a status-path locator (the path a
    board/`work path` prints): the last segment is the bare slug, intermediate
    segments are ignored, and the status segment must equal the item's real
    status (else the ref doesn't resolve). This is addressing sugar — the slug
    stays the identity. (A subproject literally named after a status is not
    addressable via the bare status-prefix form; use its slug.)

    The qualifier is a **canonical project ID**, and it resolves against the whole
    registered graph in any direction — descendant, ancestor, or sibling. Cross-node
    epic slices live in a child node and point at an epic in the parent, so a
    downward-only rule made that relation machine-trackable but unlinkable. IDs are
    unique and cycle-checked, and connections must be reciprocal
    (`_validate_reciprocity`), so admitting the whole graph adds no ambiguity and no
    new trust: an unregistered project stays unreachable.

    A slug never contains '/' (slugify -> [a-z0-9-]), so the final '/'-segment is
    always the bare slug and everything before it the qualifier — unambiguous. If
    that invariant changes, revisit this split.

    Returns None when the qualifier is not a registered project ID, or names one
    with no work component. Path-shaped qualifiers therefore never resolve — a
    nested-but-unregistered node, a traversal/absolute escape, and a `.git` /
    `.worktrees` path (a `start --worktree` checkout copies the sentinel) all fail
    because none of them is an ID in the graph. Resolving an ID to a store root is
    a filesystem concern, so this belongs in the FS adapter, not the abstract store.
    """
    anchor = anchor.resolve()
    ref = ref.strip()
    if ref.startswith("./"):
        ref = ref[2:]
    if "/" not in ref:                             # bare slug -> anchor node (unchanged)
        return FsWorkStore.open(anchor), ref
    if ref.split("/", 1)[0] in WORK_STATUSES:      # status-path locator (anchor node)
        bare = ref.rpartition("/")[2]
        if not bare:
            return None
        store = FsWorkStore.open(anchor)
        item = store.get(bare)                     # MultipleMatch propagates
        if item is None or item.status != ref.split("/", 1)[0]:
            return None                            # unknown slug or wrong status segment
        return store, bare
    qualifier, _, bare = ref.partition("/")
    if not qualifier or not bare or "/" in bare:
        return None
    registry = FsProjectRegistry.open(anchor).require_valid()
    target_project = registry.get(qualifier)       # any node in the registered graph
    if target_project is None:
        return None
    target = Path(target_project.locator)
    if not _has_work_store(target):
        return None
    return FsWorkStore.open(target), bare


def qualified_work_ref_problem(anchor: Path, ref: str) -> str:
    """Why `resolve_qualified_work_ref(anchor, ref)` failed, as a user-facing
    message. Cold path only — callers use it after a `None`, so the extra registry
    open costs nothing that matters.

    Names the *cause* rather than the symptom: "no such work item" reads like a
    typo when the real problem is an unregistered project. Degrades to the generic
    message on a broken graph, so a caller contractually forbidden from raising
    (`resolve_tcw_ref`) stays safe.
    """
    generic = f"no such work item: {ref}"
    qualifier, _, bare = ref.partition("/")
    if not qualifier or not bare or "/" in bare or qualifier in WORK_STATUSES:
        return generic                             # bare slug or status-path locator
    try:
        project = FsProjectRegistry.open(anchor).require_valid().get(qualifier)
    except Exception:
        return generic
    if project is None:
        return f"no such project in this graph: {qualifier}"
    if not _has_work_store(Path(project.locator)):
        return f"{qualifier} has no work component"
    return generic                                 # project resolved; the slug didn't


def _warn_hidden(node_root: Path, *paths: Path) -> None:
    """Say on stderr that an ignore rule is hiding a write we just made.

    `init` refuses a store whose items the rules would hide, but only at
    configure time — it cannot see a rule written afterwards, one naming a
    single slug, or one arriving with a later pull. This is the write-time half:
    the item is still written (a node may deliberately ignore a status folder,
    and refusing would break that), the user is just told git has no record.

    Advisory, on stderr, warn-and-proceed — the same shape as `_warn_off_trunk`,
    and the channel `tcw work` already uses for its `→ created at …` hints.

    `completed`/`discarded` are silent: TCW ignores their contents on purpose,
    and a line on every `tcw work complete` would train the user to stop reading
    this one. Existence is deliberately *not* tested here — `git_mv` warns about
    a destination that does not exist yet — so each call site applies its own.

    # ponytail: component match, not store-relative — a repo path containing
    # 'completed' silences the warning; take the store root as an argument if
    # that ever bites. Biased toward silence on purpose: the only way this can
    # be wrong is by staying quiet, and a false warning on `complete` would be
    # worse than the bug.
    # ponytail: no de-duplication — a command staging two hidden paths in two
    # calls prints two lines. Only happens in an already-broken setup, and a
    # cache is state this function does not otherwise carry.
    """
    hidden = [p for p in paths if not set(p.parts) & set(RESOLVED_STATUSES)]
    if not hidden:
        return
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
    """Stage paths, dropping any git ignores. Ignored status folders are the
    default (see `resolved_ignore_rules`), so a write into `completed/` has
    nothing to stage — and `git add` on an ignored path fails outright rather
    than no-opping. A drop outside those defaults is reported — see
    `_warn_hidden`."""
    ignored = [p for p in paths if git_ignored(node_root, p)]
    # Only paths that are actually there: `start` stages the *vacated* source
    # folder as a deletion, and warning about one that no longer exists would
    # be false. Sound as well as convenient — plain `check-ignore` reports a
    # tracked path as not ignored, so a dropped path is always untracked.
    live = [str(p) for p in paths if p not in ignored]
    if live:
        _git(["git", "-C", str(node_root), "add", "--", *live], check=True)
    # After the `git add`, not before: if staging the live paths is refused the
    # caller rolls the whole write back, and a warning already on stderr saying
    # the dropped path "is on disk" would be false by the time it is read.
    _warn_hidden(node_root, *(p for p in ignored if p.exists() or p.is_symlink()))


def git_rm(node_root: Path, path: Path) -> None:
    # -f so a term staged-but-not-yet-committed (just `add`ed) can still be removed.
    _git(["git", "-C", str(node_root), "rm", "-rfq", "--", str(path)], check=True)


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


def git_mv(node_root: Path, src: Path, dst: Path) -> None:
    """Move a tracked path, staging the rename. Untracked contents are staged
    first so `git mv` doesn't orphan them (the transition mechanic — Phase 5).

    **An ignored destination is untracked rather than moved.** `git mv` does not
    consult `.gitignore` for its destination: it stages the rename happily, so a
    node that gitignores `completed/` to keep resolved work out of the tracked
    tree would have every completion re-add the item it just ignored. So when the
    destination is ignored we drop the source from the index and move it outside
    git, which makes the scoped transition commit record a deletion. The
    destination pathspec then holds nothing committable and `git_commit_result`
    filters it out — the reason that filter exists.
    """
    if git_ignored(node_root, dst):
        # Untracking is deliberate for `completed/`/`discarded/` — that is how a
        # resolved item leaves the tracked tree — and indiscriminate about which
        # destination. On a live status folder it turns a routine transition
        # into a silent removal of something git already had, auto-committed
        # under a message saying the item moved. The existence test is on `src`,
        # what is on disk and about to become invisible; the path reported is
        # `dst`, which is what the rule actually names and does not exist yet.
        if src.exists() or src.is_symlink():
            _warn_hidden(node_root, dst)
        # --ignore-unmatch: an item created but never committed is not in the
        # index at all, and that is not an error here. -f: an item's own writes
        # are staged as they are made (`create_work`, `set_field`), so the index
        # legitimately differs from both HEAD and the worktree, which `rm`
        # otherwise refuses. With --cached it still only touches the index; the
        # files stay on disk.
        _git(["git", "-C", str(node_root), "rm", "-rqf", "--cached",
              "--ignore-unmatch", "--", str(src)], check=True)
        shutil.move(str(src), str(dst))
        return
    _git(["git", "-C", str(node_root), "add", "--", str(src)], check=True)
    _git(["git", "-C", str(node_root), "mv", "--", str(src), str(dst)], check=True)


WORKTREES_DIR = ".worktrees"


class _Moved(Exception):
    """Internal: the item was renamed mid-read, so the whole snapshot restarts.

    Private to this adapter and never raised past it — "the folder moved" has no
    abstract analog, and callers get a settled snapshot or `None`.
    """

def git_commit(node_root: Path, message: str, *paths: str) -> None:
    """Commit staged changes. With paths, a scoped (partial) commit so unrelated
    staged changes are left alone — used by start --worktree (Spec 2 §3.4)."""
    cmd = ["git", "-C", str(node_root), "commit", "-q", "-m", message]
    if paths:
        cmd += ["--", *paths]
    _git(cmd, check=True)


def _has_committable_changes(node_root: Path, path: str) -> bool:
    """Whether `path` has changes a scoped commit would actually record.

    Untracked (`??`) entries are excluded: a scoped `git commit -- <paths>`
    records tracked content only, so a pathspec holding nothing else has nothing
    to commit — and calling `git commit` anyway produces a benign failure that
    would then be misreported as a real one. Callers wanting untracked content
    committed stage it first, which is what `git_mv` already does.
    """
    r = _git(
        ["git", "-C", str(node_root), "status", "--porcelain", "--", path],
        capture_output=True, text=True)
    if r.returncode != 0:                              # unknown to git — nothing to record
        return False
    return any(ln.strip() and not ln.startswith("??") for ln in r.stdout.splitlines())


def git_commit_result(node_root: Path, message: str, *paths: str) -> str | None:
    """Scoped commit that distinguishes *benign* from *real* failure.

    Returns None when the commit succeeded or when there was legitimately nothing
    to do; returns an error message otherwise. `git_commit` raises on everything,
    which is right for a caller that knows there are changes — auto-commit does
    not know that, and must not treat "already committed" as an error nor a held
    `index.lock` as success.

    Three outcomes, deliberately not collapsed:

    - **Not a repository** — a `tmp_path` store in a test, or a node whose repo
      was removed. Skip silently; committing was never possible.
    - **Nothing to do** — the pathspec is clean, or (after an already-committed
      move) names a path git no longer knows. Skip silently.
    - **Anything else** — `index.lock` held, no write permission, a failing
      pre-commit hook, a corrupt repo. Report it.

    The nothing-to-do case is detected with `git status --porcelain` rather than
    by matching `git commit`'s stderr. Three different English sentences cover it
    ("nothing to commit" for a clean pathspec, "pathspec ... did not match" for a
    vanished one, "nothing added to commit but untracked files present"), all are
    localized, and all have changed across git versions; porcelain output is
    contractually stable and exits 0 in every case.

    **Untracked entries are excluded from that check.** A scoped
    `git commit -- <paths>` commits tracked content only, so a pathspec holding
    nothing but untracked files has nothing to commit — porcelain would report
    `??` lines and mislead the check into calling `git commit`, which then fails
    benignly and would be reported as a real error. Callers that want untracked
    content committed must stage it first, which is what `git_mv` already does.
    """
    if _git(["git", "-C", str(node_root), "rev-parse", "--git-dir"],
            capture_output=True).returncode != 0:
        return None                                    # not a repo — nothing to commit into
    # Filter to the pathspecs git actually has committable changes for, and pass
    # only those. `git commit` fails outright if *any* pathspec matches nothing,
    # so a transition's now-empty source folder — which git may never have known,
    # if the item was created but not yet committed — would otherwise abort a
    # commit whose destination path is perfectly valid.
    live = [p for p in paths if _has_committable_changes(node_root, p)]
    if not live:
        return None                                    # genuinely nothing to commit
    r = _git(
        ["git", "-C", str(node_root), "commit", "-q", "-m", message, "--", *live],
        capture_output=True, text=True)
    if r.returncode != 0:
        return (r.stderr or r.stdout).strip() or f"git commit failed ({r.returncode})"
    return None


def git_current_branch(node_root: Path) -> str | None:
    """The checked-out branch name, or None outside a repo / on a detached HEAD."""
    r = _git(["git", "-C", str(node_root), "rev-parse", "--abbrev-ref", "HEAD"],
             capture_output=True, text=True)
    if r.returncode != 0:
        return None
    name = r.stdout.strip()
    return None if not name or name == "HEAD" else name


def ensure_ignored(node_root: Path, *lines: str) -> bool:
    """Append whichever `lines` the node's .gitignore lacks. Returns whether it
    wrote (so a caller that must stage the file knows to). Line-wise, so a rule
    the user deleted on purpose only comes back if the caller runs again."""
    gi = node_root / ".gitignore"
    existing = gi.read_text(encoding="utf-8") if gi.exists() else ""
    missing = [ln for ln in lines if ln not in existing.splitlines()]
    if not missing:
        return False
    gi.write_text((existing.rstrip("\n") + "\n" if existing else "")
                  + "\n".join(missing) + "\n", encoding="utf-8")
    return True


def ensure_worktree_ignored(node_root: Path) -> bool:
    """Add `.worktrees/` to the node's .gitignore (a linked worktree dir is
    untracked otherwise and would clutter/be staged). Idempotent; stages it.
    Returns whether `.gitignore` changed, so a caller committing in a *different*
    repository knows whether the code node still owes a commit."""
    changed = ensure_ignored(node_root, f"{WORKTREES_DIR}/")
    if changed:
        git_stage(node_root, node_root / ".gitignore")
    return changed


def add_worktree(node_root: Path, slug: str) -> tuple[Path, str]:
    """Create the item's git worktree + branch from HEAD. Returns (path, branch)."""
    wt = node_root / WORKTREES_DIR / slug
    branch = f"work/{slug}"
    _git(["git", "-C", str(node_root), "worktree", "add", "-q",
          "-b", branch, str(wt)], check=True)
    return wt, branch


def merge_worktree(node_root: Path, branch: str) -> str | None:
    """Merge the work branch into the primary checkout's current branch — the
    "merge-back on complete" half of the split-ownership model. Runs *before* the
    active→completed rename, so it never collides with `complete`'s own move — but
    it can still meet a rename an *earlier* transition left behind: `submit` moves
    `active/<slug>/` to `review/<slug>/` on the primary checkout while the branch
    goes on committing under the old path. Hence the pinned rename setting below.
    Fail closed: a missing branch is a quiet no-op (e.g. a recovery re-run), any
    merge failure aborts the half-merge and returns an error so teardown is
    skipped and the branch is left intact. Returns None on success, else an error
    message."""
    # Ahead of the branch lookup, because that lookup cannot tell the two apart:
    # `rev-parse --verify --quiet` exits non-zero both for "no such branch" and
    # for "not a repository", and reading the second as the first turned a
    # skipped merge-back into a reported completion — the item reached
    # `completed` with the work branch unmerged and nothing said so. An external
    # `work.path` is what makes this reachable: the store guard passes because
    # the store's repository is fine, while the merge-back's is gone.
    if git_root(node_root) is None:
        return (f"the primary checkout at {node_root} is not in a git repository, "
                f"so {branch} cannot be merged back — restore it and re-run")
    if _git(["git", "-C", str(node_root), "rev-parse", "--verify", "--quiet",
             f"refs/heads/{branch}"], capture_output=True).returncode != 0:
        return None                                   # branch already gone — nothing to merge
    # `merge.directoryRenames` defaults to `conflict` for merges: git works out
    # that a file added under a renamed directory belongs at the new path, stages
    # it there, and *still* exits non-zero so a human confirms the relocation.
    # That is indistinguishable here from a real conflict, so the merge-back
    # refused items it could have finished. Pinned with `-c` rather than read from
    # config: where TCW's own lifecycle moved the folder, relocating is the answer
    # on every machine. `true`, not `false` — `false` disables rename detection
    # and would strand the file in a directory the transition deleted.
    r = _git(["git", "-C", str(node_root),
              "-c", "merge.directoryRenames=true",
              "merge", "--no-edit", branch],
             capture_output=True, text=True)
    if r.returncode != 0:
        _git(["git", "-C", str(node_root), "merge", "--abort"],
             capture_output=True, text=True)
        return (f"merge of {branch} into the primary checkout failed; branch left "
                f"intact — resolve and re-run:\n{(r.stderr or r.stdout).strip()}")
    return None


def remove_worktree(node_root: Path, slug: str, branch: str | None = None) -> list[str]:
    """Best-effort teardown (Spec 2 §3.4): `git worktree remove` refuses on a
    dirty worktree — the safety net against losing uncommitted work. Returns
    warnings (empty == clean)."""
    warns: list[str] = []
    wt = node_root / WORKTREES_DIR / slug
    r = _git(["git", "-C", str(node_root), "worktree", "remove", str(wt)],
             capture_output=True, text=True)
    if r.returncode != 0:
        if "is not a working tree" not in r.stderr:   # already absent — tolerate quietly
            warns.append(f"worktree remove failed for {slug}: {r.stderr.strip()}")
    elif branch:
        rb = _git(["git", "-C", str(node_root), "branch", "-D", branch],
                  capture_output=True, text=True)
        if rb.returncode != 0:
            warns.append(f"branch delete failed for {branch}: {rb.stderr.strip()}")
    return warns


RESOLVED_IGNORE_COMMENT = "# Resolved work: kept on disk and in history, out of the tracked tree."

def resolved_ignore_rules(work_root: Path | None = None, repository: Path | None = None) -> list[str]:
    """The .gitignore rules that make the end-state work folders untracked while
    keeping the folders themselves. `<dir>/*` rather than `<dir>/`: git cannot
    re-include a file whose *parent directory* is excluded, which would make the
    `.gitkeep` negation inert."""
    prefix = "docs/work"
    if work_root is not None and repository is not None:
        prefix = work_root.resolve().relative_to(repository.resolve()).as_posix()
    return [RESOLVED_IGNORE_COMMENT,
            *(rule for s in RESOLVED_STATUSES
              for rule in (f"{prefix}/{s}/*", f"!{prefix}/{s}/.gitkeep"))]


def init(components: list[str], root: Path, project_id: str | None = None,
         work_path: Path | None = None,
         paths: dict[str, Path] | None = None) -> list[Path]:
    """Scaffold `docs/<component>/` skeletons under `root` and mark it a node.
    Returns leaf dirs made. A `.gitkeep` lands in each leaf so the empty skeleton
    survives a commit (git doesn't track empty directories).

    Scaffolding `work` also gitignores the resolved status folders, so completing
    or discarding an item takes it *out* of the tracked tree instead of
    accumulating it there — `git_mv` untracks rather than moves when the
    destination is ignored. Unstaged, like everything else init writes.
    """
    # Read ahead of `write_sentinel`, so its own mapping check no longer runs
    # first — a malformed config used to come back from it as a `ValueError` and
    # would otherwise surface here as an `AttributeError` from `.get`.
    existing_config = load_yaml(root / SENTINEL, unique=True)
    if not isinstance(existing_config, dict):
        raise ValueError(f"{root / SENTINEL}: config must be a mapping")
    # `work_path` kept as its own parameter rather than folded into `paths`:
    # it is the fourth positional argument every existing caller passes, and
    # this component's location has a name in the CLI (`--work-path`,
    # `tcw work init --path`) that predates the mapping.
    paths = dict(paths or {})
    if work_path is not None:
        paths["work"] = work_path
    work_path = paths.get("work")
    if work_path is None and "work" in components:
        configured_work = existing_config.get("work") or {}
        # `in`, not truthiness: `work.path: []` and `work.path: false` used to
        # fall through to the default store without a word, so a configuration
        # mistake read as a deliberate choice.
        if isinstance(configured_work, dict) and "path" in configured_work:
            configured_path = configured_work["path"]
            if not isinstance(configured_path, str) or not configured_path:
                raise ValueError(f"{root / SENTINEL}: work.path must be a string")
            work_path = paths["work"] = Path(configured_path).expanduser()
    # Everything `init` can refuse over, decided before it writes anything at
    # all — the sentinel included. It writes two locations, and each of these
    # checks used to sit next to the write it protects rather than ahead of all
    # of them, so a refusal left `tcw-config.yaml` rewritten with the bad path,
    # or a new sentinel in a project that had none, or the whole status tree.
    default_root = root / "docs" / "work"
    replacing_default_store = False
    # Which repository answers the ignore question for the work leaves. The
    # node's own, unless `work.path` sends the store somewhere else — and it is
    # asked for the default store too, which is the layout most projects use and
    # the one the check originally skipped entirely.
    ignore_root: Path | None = git_root(root)
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
        ignore_root = target_git                      # the store's, not the node's
        if default_root.exists() and default_root.resolve() != target.resolve():
            expected = {"inbox", *WORK_STATUSES}
            actual = {entry.name for entry in default_root.iterdir()}
            # `is_symlink` first: a symlinked `docs/work` reads as pristine
            # through the link and then meets `shutil.rmtree`, which refuses a
            # symlink. Replacing a default store means deleting it, and a symlink
            # is someone else's directory.
            pristine = not default_root.is_symlink() and actual == expected and all(
                child.is_dir() and {entry.name for entry in child.iterdir()} <= {".gitkeep"}
                for child in default_root.iterdir()
            )
            if not pristine:
                raise ValueError(
                    f"refusing to replace non-pristine {default_root}; move existing work "
                    "manually, update work.path, then re-run init"
                )
            replacing_default_store = True
    # The exact directories this call will create, worked out before it creates
    # any of them — the pre-flight below needs the list, and so does the loop
    # that makes them, so there is only one of it.
    plan: list[tuple[str, Path, list[Path]]] = []
    for c in components:
        configured = paths.get(c)
        base = ((configured if configured.is_absolute() else root / configured)
                if configured is not None else root / "docs" / c)
        plan.append((c, base, [base / "inbox", *(base / s for s in WORK_STATUSES)]
                     if c == "work" else [base]))
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
            # Inside a repository is not the same as tracked by one: `git_stage`
            # drops ignored paths from the `git add` it builds, so items filed
            # under one are real on disk and invisible to git — the outcome the
            # external-store contract exists to prevent. Asked of each status
            # folder, not just the store root, because a rule naming one folder
            # leaves the root visible and hides only what lands inside it.
            #
            # Would an *item* written here be recorded? Asked of a representative
            # payload rather than of the folder or its `.gitkeep`, both of which
            # answer a different question: `<status>/*` with a `!<status>/.gitkeep`
            # negation — TCW's own shape for the resolved statuses, and an
            # ordinary thing for a person to write — leaves the marker visible
            # while hiding every item, and `git check-ignore` matches a
            # trailing-slash path against a `dir/*` rule, so asking about the
            # folder would make TCW's own scaffolding refuse itself.
            #
            # *Two* differently-named payloads, refused only when **both** are
            # hidden. One fixed name makes the guard answerable by a rule naming
            # that one literal (`an-item*`), which would refuse a store every
            # real item would be tracked in. No plausible single glob matches
            # both names unless it is the broad rule this exists to catch. The
            # file name is deliberately not varied: `state.yaml` is fixed by the
            # layout, so a rule hiding it hides every item's status record and
            # must still refuse.
            #
            # `completed` and `discarded` are skipped because TCW ignores their
            # contents deliberately: that is how a resolved item leaves the
            # tracked tree.
            #
            # ponytail: a configure-time guard against a footgun, not a boundary.
            # It cannot see a `.gitignore` written after `init`, a rule naming a
            # specific slug, or one that arrives with a later `git pull`. Catching
            # those means checking at write time, in `git_stage`, which is a
            # different change.
            if component == "work" and ignore_root is not None \
                    and leaf.name not in RESOLVED_STATUSES:
                probes = [leaf / f"{name}.md" if leaf.name == "inbox"
                          else leaf / name / "state.yaml"
                          for name in ("an-item", "some-slug")]
                if all(git_ignored(ignore_root, p, no_index=True) for p in probes):
                    raise ValueError(
                        f"items written in {leaf} would be gitignored, so work "
                        f"filed there would not be tracked"
                    )
    write_sentinel(root, project_id)
    configured = {c: p for c, p in paths.items() if c in components}
    if configured:
        if work_path is not None and "work" in components and replacing_default_store:
            shutil.rmtree(default_root)
        config_path = root / SENTINEL
        config = load_yaml(config_path, unique=True)
        for component, location in configured.items():
            section = (config.get(component)
                       if isinstance(config.get(component), dict) else {})
            config[component] = {**section, "path": str(location)}
        dump_yaml(config_path, config)
    created: list[Path] = []
    for c, base, leaves in plan:
        for leaf in leaves:
            leaf.mkdir(parents=True, exist_ok=True)
            (leaf / ".gitkeep").touch()
            created.append(leaf)
        if c == "work":
            target_git = git_root(base)
            if target_git is None and work_path is not None:
                raise ValueError(f"work.path target is not inside a Git repository: {base}")
            if target_git is None:
                ensure_ignored(root, *resolved_ignore_rules())
            else:
                ensure_ignored(target_git, *resolved_ignore_rules(base, target_git))
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


def load_yaml(path: Path, unique: bool = False) -> dict:
    """Load a YAML mapping (empty dict if the file is absent/empty)."""
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    data = yaml.load(text, Loader=_UniqueKeyLoader if unique else yaml.SafeLoader)
    return data or {}


def dump_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")


_DATE_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}-")


def _extends_ids(config: dict, config_path: Path) -> list[str]:
    value = config.get("extends") or []
    if isinstance(value, dict):
        raise ValueError(
            f"{config_path}: legacy extends map is unsupported; replace it with "
            "a list of registered project IDs"
        )
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        raise ValueError(f"{config_path}: extends must be a list of project IDs")
    ids = [validate_project_id(v) for v in value]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{config_path}: extends contains duplicate project IDs")
    return ids


def _extended_component_roots(
    node_root: Path, config: dict, config_path: Path, component: str
) -> dict[str, Path]:
    registry = FsProjectRegistry.open(node_root).require_valid()
    roots: dict[str, Path] = {}
    for project_id in _extends_ids(config, config_path):
        project = registry.get(project_id)
        if project is None:
            raise ValueError(
                f"{config_path}: extends project '{project_id}' is not reachable "
                "through connected-projects"
            )
        target = Path(project.locator) / "docs" / component
        if not target.is_dir():
            raise ValueError(f"project '{project_id}' has no docs/{component}/")
        if Path(project.locator).resolve() == node_root.resolve():
            raise ValueError(f"a {component} store cannot extend itself")
        roots[project_id] = target.resolve()
    return roots


# ── Revision tokens & atomic writes (FS-adapter private details) ─────────────

def _revision(content: str) -> str:
    """Cheap content-hash revision token (16 hex chars of SHA-256)."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


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
            tmp.write_text(content, encoding="utf-8")
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
    if node_root.is_relative_to(top) and not resolved.is_relative_to(top):
        return main / node_root.relative_to(top)
    return node_root


class FsTreeStore:
    """Common FS-adapter base for the three bounded-tree stores.

    Captures the boilerplate every component shares — the store root, the
    enclosing node (repo) root, config loading, the `open(node_root)` entry
    point, and the git-plumbing methods that *effect* transitions. Component
    specifics (node = dir vs file, identifier resolution, the status state
    machine) stay in the subclasses (phase-4-shared-core: don't over-pull).

    Subclasses set `COMPONENT` (the `docs/<COMPONENT>/` dir) and optionally
    `CONFIG_NAME` (a root config file to load into `self.config`).
    """
    COMPONENT: str
    CONFIG_NAME: str | None = None

    def __init__(self, root: Path, *, node_root: Path | None = None,
                 store_git_root: Path | None = None):
        self.root = root                       # docs/<component>/, or wherever configured
        # Two roots, because they answer different questions and diverge the
        # moment a store leaves its node's repository — the same split
        # `FsWorkStore` has carried since `work.path` existed.
        #
        # `node_root` is the *node*: whose config this is, and what federation
        # resolves `extends` against. `store_git_root` is the repository a write
        # here has to land in. They are the same directory for a store sitting
        # in its own node, and are not for a configured or provisioned one.
        self.node_root = node_root or root.parent.parent
        self.store_git_root = store_git_root or git_root(root) or self.node_root
        self.config = load_yaml(root / self.CONFIG_NAME) if self.CONFIG_NAME else {}

    @classmethod
    def open(cls, node_root: Path):
        """Resolve this node's store for this component. The ladder is
        `resolve_store`, shared with the work store."""
        return resolve_store(cls, node_root)

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
                 declaration: "RepositoryDeclaration | None" = None):
        """Build the store at a candidate root, validating it only when
        something points at it.

        `declaration` is accepted and deliberately ignored: a tree store never
        publishes. A taxonomy term or a capability status is a claim *about the
        code*, realized when the code implementing it merges, so the edit belongs
        to that change and lands with it. Publishing one on its own would
        announce a capability to everyone reading the ledger while the code
        making it true is still unmerged. Work is different — an item's state is
        the record of a session and changes independently of any code — which is
        why `FsWorkStore` takes the same argument and uses it.

        A tree store has no layout to check — see `_is_store_layout` — so
        "usable" is "the directory is there", and that is the strongest honest
        answer rather than a shortcut. When `must_exist` is false this validates
        nothing at all, which is the pre-ladder behaviour for a component's bare
        default and the contract every existing project relies on.
        """
        if must_exist:
            if raw_root.is_symlink() and not raw_root.exists():
                raise ValueError(
                    f"{config_path}: {cls.COMPONENT}.path is a broken symlink: {raw_root}")
            if not raw_root.is_dir():
                raise ValueError(
                    f"{config_path}: {cls.COMPONENT}.path is not a directory: {raw_root}")
        root = raw_root.resolve() if raw_root.exists() else raw_root
        owner = (git_root(root) if external else node_root) or node_root
        # The node stays the node — federation resolves `extends` against it —
        # while writes follow the store into whatever repository holds it.
        return cls(root, node_root=node_root, store_git_root=owner)

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

        A `cached_property` rather than an `__init__` assignment on purpose:
        `FsWorkStore.__init__` does not chain to this class's, so anything set
        in the base initializer would be missing there, while an inherited
        descriptor resolves through normal MRO lookup. Cached for the life of
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

    def _stage(self, *paths: Path) -> None:
        self._require_repository()
        git_stage(self.store_git_root, *paths)

    def _write_staged(self, pairs: list[tuple[Path, str]], *,
                      owned_dir: Path | None = None,
                      also_stage: tuple[Path, ...] = ()) -> None:
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
        """
        # `exists() or is_symlink()`: `exists()` follows the link, so a
        # pre-existing *dangling* symlink read as absent, was replaced by a real
        # file, and was then unlinked here — destroying a path this call did not
        # create. Same idiom `init`'s ancestor walk uses for the same reason.
        new = [p for p, _ in pairs if not (p.exists() or p.is_symlink())]
        try:
            _atomic_write_all(pairs)
            self._stage(*(p for p, _ in pairs), *also_stage)
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

    def _mv(self, src: Path, dst: Path) -> None:
        self._require_repository()
        git_mv(self.store_git_root, src, dst)

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
        """Filenames in a node folder that are not attachments."""
        names = {"meta.yaml", "description.md"}
        if self.CONFIG_NAME:
            names.add(self.CONFIG_NAME)
        return names

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

_TAX_RESERVED = {"config.yaml", "meta.yaml", "description.md"}
TAXONOMY_KINDS = {"Vocabulary", "Feature"}


def _normalize_taxonomy_kind(kind: str | None) -> str:
    if not kind:
        return "Vocabulary"
    by_lower = {k.lower(): k for k in TAXONOMY_KINDS}
    return by_lower.get(str(kind).lower(), str(kind))


def _wrong_kind_ref(ref: str, kind: str) -> str:
    """The one wording for "this vocabulary ref points at the wrong kind"."""
    return f"vocabulary ref '{ref}' points to {kind}, expected Vocabulary"


class FsTaxonomyStore(FsTreeStore, TaxonomyStore):
    """`TaxonomyStore` over nested dirs under `docs/taxonomy/` (Phase 2 B.3).

    A term's slug is its directory path under the taxonomy root. `extends`
    aliases (local-path repo roots) are realized as nested stores.
    """
    COMPONENT = "taxonomy"
    CONFIG_NAME = "config.yaml"

    def __init__(self, root: Path, _seen: set[Path] | None = None, *,
                 node_root: Path | None = None, store_git_root: Path | None = None):
        super().__init__(root, node_root=node_root, store_git_root=store_git_root)
        self.extends: dict[str, "FsTaxonomyStore"] = {}
        seen = (_seen or set()) | {root.resolve()}
        for project_id, ext in _extended_component_roots(
            self.node_root, self.config, self.root / self.CONFIG_NAME, "taxonomy"
        ).items():
            if ext.is_dir() and ext not in seen:        # broken/cyclic → check() reports
                self.extends[project_id] = FsTaxonomyStore(ext, _seen=seen)

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
        if term is None:
            raise ValueError(f"no such term: {ref}")
        if term.origin != "local":
            raise ValueError(f"cannot remove inherited term '{term.qualified}' "
                             f"(edit it at its source)")
        self._rm(self.root / term.slug)

    def extends_add(self, project_id: str) -> None:
        self._require_repository()
        project_id = validate_project_id(project_id)
        extends = _extends_ids(self.config, self.root / self.CONFIG_NAME)
        if project_id in extends:
            raise ValueError(f"extends project already exists: {project_id}")
        registry = FsProjectRegistry.open(self.node_root).require_valid()
        project = registry.get(project_id)
        if project is None:
            raise ValueError(f"project '{project_id}' is not registered")
        if project_id == registry.current.id:
            raise ValueError("a taxonomy cannot extend itself")
        if not (Path(project.locator) / "docs" / "taxonomy").is_dir():
            raise ValueError(f"project '{project_id}' has no docs/taxonomy/")
        extends.append(project_id)
        # Update in-memory config so a later add/rm in the same process sees this
        # write; term *resolution* (self.extends) is load-time only — reopen to use.
        self.config["extends"] = extends
        cfg = self.root / "config.yaml"
        self._write_staged([(cfg, yaml.safe_dump(self.config, sort_keys=False,
                                                 allow_unicode=True))])

    def extends_remove(self, project_id: str) -> None:
        self._require_repository()
        extends = _extends_ids(self.config, self.root / self.CONFIG_NAME)
        if project_id not in extends:
            raise ValueError(f"no such extends project: {project_id}")
        extends.remove(project_id)
        if extends:
            self.config["extends"] = extends
        else:
            self.config.pop("extends", None)
        cfg = self.root / "config.yaml"
        self._write_staged([(cfg, yaml.safe_dump(self.config, sort_keys=False,
                                                 allow_unicode=True))])

    def relators(self, slug: str) -> list[str]:
        """Local term slugs whose `relatesTo` points at `slug` (for rm warnings)."""
        return [t.slug for t in self.list_all(local_only=True)
                if any(r == slug or r.rsplit("/", 1)[-1] == slug for r in t.relates_to)]

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
        cfg_path = self.root / "config.yaml"
        try:
            load_yaml(cfg_path, unique=True)
        except yaml.YAMLError as e:
            problems.append(f"config.yaml: {e}")

        top_level = {s.split("/")[0] for s in self._local_slugs()}
        for project_id, store in self.extends.items():
            if self._cycles(store.root.resolve(), {self.root.resolve()}):
                problems.append(f"extends '{project_id}': cycle in taxonomy federation")
        for project_id in self._inherited_stores():
            if project_id in top_level:
                problems.append(
                    f"project ID '{project_id}' collides with local top-level term"
                )

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

    def _cycles(self, taxonomy_root: Path, seen: set[Path]) -> bool:
        if taxonomy_root in seen:
            return True
        if not taxonomy_root.is_dir():
            return False
        cfg = load_yaml(taxonomy_root / "config.yaml")
        node_root = taxonomy_root.parent.parent
        try:
            roots = _extended_component_roots(
                node_root, cfg, taxonomy_root / self.CONFIG_NAME, "taxonomy"
            )
        except ValueError:
            return False
        for nxt in roots.values():
            if self._cycles(nxt, seen | {taxonomy_root}):
                return True
        return False

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


class FsCapabilitiesStore(FsTreeStore, CapabilitiesStore):
    """`CapabilitiesStore` over folder-per-capability nodes under
    `docs/capabilities/`, optionally federated via `extends`.

    A capability is a folder with `meta.yaml` (`id` + `name` + the locked
    metadata vocabulary) and `description.md` (the body). A directory is a
    capability iff it holds a `meta.yaml`; dirs without one are pure grouping
    parents. Mirrors `FsTaxonomyStore` on the shared tree-store core.
    """
    COMPONENT = "capabilities"
    CONFIG_NAME = ".config.yaml"

    def __init__(self, root: Path, _seen: set[Path] | None = None, *,
                 node_root: Path | None = None, store_git_root: Path | None = None):
        super().__init__(root, node_root=node_root, store_git_root=store_git_root)
        self.extends: dict[str, "FsCapabilitiesStore"] = {}
        seen = (_seen or set()) | {root.resolve()}
        for project_id, ext in _extended_component_roots(
            self.node_root, self.config, self.root / self.CONFIG_NAME, "capabilities"
        ).items():
            if ext.is_dir() and ext not in seen:        # broken/cyclic → check() reports
                self.extends[project_id] = FsCapabilitiesStore(ext, _seen=seen)

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
        if cap is None:
            raise ValueError(f"no such capability: {identifier}")
        if cap.origin != "local":
            raise ValueError(f"cannot remove inherited capability '{cap.qualified}' "
                             f"(edit it at its source)")
        self._rm(self.root / cap.path)

    def reset(self, identifier: str) -> None:
        # A standalone local capability is not an override — `remove` deletes it.
        if self.get_local(identifier) is not None:
            raise ValueError(f"'{identifier}' is a local capability, not an override "
                             f"(use `remove` to delete it)")
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
        extends = _extends_ids(self.config, self.root / self.CONFIG_NAME)
        if project_id in extends:
            raise ValueError(f"extends project already exists: {project_id}")
        registry = FsProjectRegistry.open(self.node_root).require_valid()
        project = registry.get(project_id)
        if project is None:
            raise ValueError(f"project '{project_id}' is not registered")
        if project_id == registry.current.id:
            raise ValueError("a capabilities store cannot extend itself")
        if not (Path(project.locator) / "docs" / "capabilities").is_dir():
            raise ValueError(f"project '{project_id}' has no docs/capabilities/")
        extends.append(project_id)
        self.config["extends"] = extends
        cfg = self.root / self.CONFIG_NAME
        self._write_staged([(cfg, yaml.safe_dump(self.config, sort_keys=False,
                                                 allow_unicode=True))])

    def extends_remove(self, project_id: str) -> None:
        self._require_repository()
        extends = _extends_ids(self.config, self.root / self.CONFIG_NAME)
        if project_id not in extends:
            raise ValueError(f"no such extends project: {project_id}")
        extends.remove(project_id)
        if extends:
            self.config["extends"] = extends
        else:
            self.config.pop("extends", None)
        cfg = self.root / self.CONFIG_NAME
        self._write_staged([(cfg, yaml.safe_dump(self.config, sort_keys=False,
                                                 allow_unicode=True))])

    # -- validation --

    def _cycles(self, cap_root: Path, seen: set[Path]) -> bool:
        if cap_root in seen:
            return True
        if not cap_root.is_dir():
            return False
        cfg = load_yaml(cap_root / self.CONFIG_NAME)
        node_root = cap_root.parent.parent
        try:
            roots = _extended_component_roots(
                node_root, cfg, cap_root / self.CONFIG_NAME, "capabilities"
            )
        except ValueError:
            return False
        for nxt in roots.values():
            if self._cycles(nxt, seen | {cap_root}):
                return True
        return False

    def _taxonomy(self) -> "FsTaxonomyStore | None":
        """The sibling taxonomy store for this node, or None if it has none.

        The FS adapter's answer to "where does this store's taxonomy live";
        another adapter answers it from its own connection, so nothing about
        this belongs on the abstract interface. Putting it on the store rather
        than in the call is what makes it impossible to forget: `set`,
        `update_capability` and `check` all reach the same handle.
        """
        return (FsTaxonomyStore.open(self.node_root)
                if (self.node_root / "docs" / "taxonomy").is_dir() else None)

    def check(self, taxonomy=None, identifier: str | None = None) -> list[str]:
        # `is not None`, not `or`: an explicitly injected store must win even
        # when it is falsey. Without the fallback, `check()` called bare skips
        # Subject/Feature entirely, so the write path and `check` could disagree
        # about *whether* a ref is checked even once they agree about what a
        # problem is.
        taxonomy = taxonomy if taxonomy is not None else self._taxonomy()
        problems: list[str] = []
        cfg_path = self.root / self.CONFIG_NAME
        try:
            load_yaml(cfg_path, unique=True)
        except yaml.YAMLError as e:
            problems.append(f"{self.CONFIG_NAME}: {e}")

        top_level = {s.split("/")[0] for s in self._local_paths()}
        for project_id, store in self.extends.items():
            if self._cycles(store.root.resolve(), {self.root.resolve()}):
                problems.append(f"extends '{project_id}': cycle in capability federation")
            if project_id in top_level:
                problems.append(
                    f"project ID '{project_id}' collides with local top-level capability"
                )

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

        # Override + attachment validation (every meta dir, incl. override folders).
        meta_dirs = self._all_meta_dirs()
        if selected is not None:
            meta_dirs = [selected.path]
        for p in meta_dirs:
            d = self.root / p
            if not self._node_readable(d):
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
                return f"overrides → unknown alias '{alias}'"
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

    def _check_subject(self, f, taxonomy) -> list[str]:
        # `str(...)`, as the other four ref fields already do: a ref resolver
        # takes a string, and a non-string here used to escape as AttributeError
        # out of `taxonomy.get` rather than as a refusal the caller can read.
        subjects = [str(s) for s in _as_list(f.get("Subject"))]
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
        feature = f.get("Feature")
        if not feature or taxonomy is None:
            return []
        feature = str(feature)          # see `_check_subject`
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

STORE_LAYOUT = ("inbox", *WORK_STATUSES)


def _cache_root() -> Path:
    """Where working copies land when a declaration names no `checkout`.

    XDG, so it is outside every checkout and survives between sessions on one
    machine. Read from the environment on each call rather than at import: a
    test — and a user's shell — may set it after this module loads.
    """
    base = os.environ.get("XDG_CACHE_HOME") or "~/.cache"
    return Path(base).expanduser() / "tcw" / "stores"


def _cache_key(declaration: RepositoryDeclaration) -> str:
    """A directory name for one (url, ref) pair: readable, then unambiguous.

    The readable half is the tail of the URL, so a user browsing the cache can
    tell whose repository a directory holds. The hash is what actually keeps two
    declarations apart, because the readable half is lossy by design.

    Keyed on url *and* ref: two projects naming the same repository at the same
    ref should share one working copy, and two refs of it must not fight over
    one checkout.
    """
    cleaned = declaration.url.strip().rstrip("/")
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]
    tokens = [token.rpartition("@")[2]                 # drop any `git@` user part
              for token in re.split(r"[/:]", cleaned) if token]
    slug = "-".join(re.sub(r"[^A-Za-z0-9._-]+", "-", token).strip("-.")
                    for token in tokens[-3:])
    slug = (slug.strip("-").lower() or "store")[:60]
    digest = hashlib.sha256(
        f"{declaration.url}\n{declaration.ref or ''}".encode("utf-8")).hexdigest()[:12]
    return f"{slug}-{digest}"


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


def checkout_root(node_root: Path, declaration: RepositoryDeclaration) -> Path:
    """The working copy's root for `declaration` — the declared `checkout`, or a
    per-machine cache directory. `~` expands; a relative path is the node's."""
    if declaration.checkout:
        value = Path(declaration.checkout).expanduser()
        return value if value.is_absolute() else (node_root / value)
    return _cache_root() / _cache_key(declaration)


def provisioned_store_root(node_root: Path, declaration: RepositoryDeclaration) -> Path:
    """Where a provisioned store *would* live. Pure: computes a path, probes
    nothing. `FsWorkStore.open` and the provisioner share it, so they can never
    disagree about where a declared store is."""
    root = checkout_root(node_root, declaration)
    return (root / declaration.path) if declaration.path else root


def _is_store_layout(root: Path, component: str) -> bool:
    """Whether `root` holds `component`'s store, as far as the filesystem can say.

    The answer has two strengths, because the components differ in what they can
    honestly claim.

    A **work** store names six folders, so this is the same question
    `FsWorkStore.open` asks and a provisioned store and an opened one agree.

    A **tree** store — taxonomy, capabilities — names nothing. `init` scaffolds
    it as a bare directory (see `init`'s plan loop, which gives work its status
    leaves and the tree components only `[base]`), its `CONFIG_NAME` file is
    optional and commonly absent, and the only file reliably left behind is a
    `.gitkeep`, which is git's answer to empty directories and means nothing
    here. So "the directory is there" is the strongest honest answer, and it is
    deliberately weaker than the work store's: a declared tree store that clones
    into an empty directory reads as usable, because an empty taxonomy is a real
    state and nothing distinguishes the two. What this still refuses — a
    `repository.path` naming nothing at all — is what keeps "a failure leaves
    nothing behind" true for every component.

    `component` is required rather than defaulted: a caller that forgets it
    should not silently get the work store's answer for a tree store.
    """
    if not root.is_dir():
        return False
    if component != "work":
        return True
    return all((root / name).is_dir() for name in STORE_LAYOUT)


def resolve_store(store_cls, node_root: Path):
    """This node's store for `store_cls`'s component, in one ordered ladder.

    1. the local store (`<component>.path`, else `docs/<component>`) when it is
       usable;
    2. else the declared home repository's provisioned location, if usable;
    3. else `StoreNotProvisioned`, when a home repository is declared;
    4. else exactly what the component did before a declaration existed — the
       same checks, in the same order, with the same messages.

    **A declaration is a fallback, never an override.** Rule 1 runs first so a
    checkout that already has the store keeps using it and nothing about that
    machine changes; the declaration answers only for a machine that does not
    have it. Rules 3 and 4 are the same failure told two ways: with a
    declaration it is actionable, so it says what to run.

    One function for every component, because the ladder is the contract and
    three copies of a contract drift. The two things that genuinely differ are
    hooks on the store class: `_local_root`, which knows the component's default
    location and how a relative path re-anchors, and `_open_at`, which decides
    what "usable" means and builds the store. `COMPONENT` names the config
    section.
    """
    node_root = node_root.resolve()
    config_path = node_root / SENTINEL
    config = load_yaml(config_path, unique=True)
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
                external=configured is not None, must_exist=must_exist)
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
            external=configured is not None, must_exist=must_exist)
    except ValueError:
        pass
    try:                                                        # rule 2
        # The declaration travels with the store *only* here. Rule 1 above
        # resolved without it, so a store built there carries None and does not
        # publish — see `FsWorkStore.publishes`.
        return store_cls._open_at(
            provisioned_store_root(node_root, declaration), node_root, config_path,
            external=True, must_exist=True, declaration=declaration)
    except ValueError:
        pass
    raise StoreNotProvisioned(                                  # rule 3
        f"{config_path}: the {component} store is declared in "
        f"{declaration.url} but has not been provisioned here; "
        f"run `tcw provision` to obtain it")


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
    config = load_yaml(node_root / SENTINEL, unique=True)
    section = config.get(component) if isinstance(config, dict) else None
    if not isinstance(section, dict):
        return None, []
    return parse_repository_declaration(section.get("repository"),
                                        f"{component}.repository")


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
        within = f", store at {d.path}" if d.path else ""
        return (f"{self.component}: {d.url}{at}{within} → "
                f"{provisioned_store_root(self.node_root, d)}")

    def is_available(self) -> bool:
        if self.declaration is None:
            return False
        target = provisioned_store_root(self.node_root, self.declaration)
        checkout = checkout_root(self.node_root, self.declaration)
        # A directory with the right folder names is not enough: work-store
        # writes need a checkout to own their commits. Check the filesystem
        # marker rather than invoking Git: an already-available second run is
        # deliberately a zero-subprocess no-op. ``FsWorkStore._open_at`` remains
        # the full validation authority when the store is actually opened.
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
        prefix = (f"{self.component}.repository: {self.declaration.url} has no "
                  f"{self.component} store at '{where}'")
        if not root.is_dir():
            raise ValueError(f"{prefix}: no such directory in the repository")
        missing = [n for n in STORE_LAYOUT if not (root / n).is_dir()]
        raise ValueError(f"{prefix}; missing: {', '.join(missing)}")

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
        two people's work items. If that becomes necessary, the transition path
        needs its own answer first (`FsWorkStore.refresh`).
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


# ── FsWorkStore ──────────────────────────────────────────────────────────────

class FsWorkStore(FsTreeStore, WorkStore):
    """`WorkStore` over `docs/work/` — the filesystem-as-state-machine (Phase 5).

    Status is the top-level status folder an item lives under; a transition is a
    `git mv` of the item folder. The stable id is the slug; an item folder is any
    dir holding a `state.yaml`, found at any nesting depth — a child item is a
    folder nested inside its parent's (the node relation, derived from nesting).
    """
    COMPONENT = "work"

    # The graveyard sits at the store root, beside the status folders rather than
    # inside one: it outlives every item it records, and a status folder is a
    # place items *are*. Tracked unconditionally and never gitignorable — an
    # ignorable graveyard is invisible in exactly the clones that need it, which
    # is the defect it exists to fix, one level up.
    GRAVEYARD_NAME = "graveyard.yaml"

    def __init__(self, root: Path, *, node_root: Path | None = None,
                 store_git_root: Path | None = None,
                 declaration: "RepositoryDeclaration | None" = None):
        self.root = root.resolve()
        self.node_root = (node_root or root.parent.parent).resolve()
        self.store_git_root = (store_git_root or git_root(self.root) or self.node_root).resolve()
        self.config = {}
        # Set only when the resolution ladder reached this store *through* the
        # declaration — rule 2, the provisioned location. A store found at a
        # local path keeps this None even when the node declares a repository,
        # because the declaration did not answer the read and therefore does not
        # get to cause a write. See `publishes`.
        self.declaration = declaration

    @classmethod
    def open(cls, node_root: Path) -> "FsWorkStore":
        """Resolve this node's work store. The ladder is `resolve_store`, shared
        with every other component; this class supplies `_local_root` and
        `_open_at`."""
        return resolve_store(cls, node_root)

    @classmethod
    def _local_root(cls, node_root: Path, configured: str | None) -> Path:
        """Where the store lives on this machine per `<component>.path`, or the
        default `docs/<component>`.

        A relative path re-anchors per `anchor_configured_path`, which the tree
        stores share — the rule is identical for every component, and keeping a
        second copy here is what let the two drift apart in the first place.
        """
        if configured is None:
            return node_root / "docs" / cls.COMPONENT
        value = Path(configured).expanduser()
        if value.is_absolute():            # names a place, not an offset
            return value
        return anchor_configured_path(node_root, value) / value

    @classmethod
    def _open_at(cls, raw_root: Path, node_root: Path, config_path: Path, *,
                 external: bool, must_exist: bool = True,
                 declaration: "RepositoryDeclaration | None" = None) -> "FsWorkStore":
        """Validate a candidate root and build the store. `external` means the
        store is not the node's own `docs/work`, so the repository that owns its
        commits has to be discovered rather than assumed.

        `must_exist` is accepted and ignored: a work store has always validated
        its location, with or without a declaration, and nothing here relaxes
        that. The parameter exists because the shared ladder asks every
        component the same question."""
        if raw_root.is_symlink() and not raw_root.exists():
            raise ValueError(f"{config_path}: work.path is a broken symlink: {raw_root}")
        if not raw_root.is_dir():
            raise ValueError(f"{config_path}: work.path is not a directory: {raw_root}")
        root = raw_root.resolve()
        missing = [name for name in ("inbox", *WORK_STATUSES) if not (root / name).is_dir()]
        if missing:
            raise ValueError(f"{config_path}: work.path is not a work store; missing: {', '.join(missing)}")
        repository = git_root(root) if external else node_root
        if repository is None and external:
            raise ValueError(f"{config_path}: work.path is not inside a Git repository: {root}")
        return cls(root, node_root=node_root, store_git_root=repository or node_root,
                   declaration=declaration)

    def _write_git_root(self) -> Path:
        return self.store_git_root          # may differ from the node's (work.path)

    def _stage(self, *paths: Path) -> None:
        self._require_repository()
        git_stage(self.store_git_root, *paths)

    def _rm(self, path: Path) -> None:
        self._require_repository()
        git_rm(self.store_git_root, path)

    def _mv(self, src: Path, dst: Path) -> None:
        self._require_repository()
        git_mv(self.store_git_root, src, dst)

    # -- discovery (state.yaml-keyed, depth-agnostic) --

    def _item_dirs(self) -> list[Path]:
        """Every item folder (dir with a `state.yaml`), at any depth. Sorted by
        path so a parent precedes its children.

        Retried, because the walk is not atomic and a claim moves folders under
        it. `rglob` reaches the directory through `scandir`, which raises rather
        than skipping when it has gone — so one item leaving `backlog` mid-scan
        takes down a read of the whole board. Re-walking is the cheap answer: the
        window is a single rename wide, and a scan that fails five times running
        is reporting something other than a transition.
        """
        for attempt in range(5):
            try:
                return sorted(
                    p.parent
                    for status in WORK_STATUSES
                    for p in (self.root / status).rglob("state.yaml")
                    # `rglob` never descends a symlinked *directory*, so a
                    # symlinked item folder is already invisible. A symlink
                    # *named* state.yaml matches by name, and its parent would
                    # then be read as an item folder.
                    if self._within_store(p)
                )
            except FileNotFoundError:
                if attempt == 4:
                    raise
        raise AssertionError("unreachable")                # for the type checker

    def start(self, slug: str, force: bool = False, *, owner: str = "",
              take_over: bool = False) -> WorkItem:
        """Publish a stamped backlog claim with a single atomic source rename."""
        # The literal first statement, not merely an early one: both the
        # take-over branch and the main claim call `git_stage` directly rather
        # than through `_stage`, and both rename before they stage, so `_mv`'s
        # guard reaches neither.
        self._require_repository()
        self._refresh_before_transition()
        started = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        # `_get_now`: the take-over branch below exists precisely for the state
        # the stabilizing `get` raises on, so probing through `get` would make
        # `--take-over` — the documented remedy for an interrupted claim —
        # unreachable the moment there was something to recover.
        item = self._get_now(slug)
        if item is None and take_over:
            interrupted = self._claiming_dirs(slug)
            if len(interrupted) != 1:
                raise ValueError(f"no recoverable interrupted claim for {slug}")
            if not owner:
                raise ValueError("takeover requires an owner")
            state_path = interrupted[0] / "state.yaml"
            state = load_yaml(state_path)
            state["owner"], state["started"] = owner, started
            dump_yaml(state_path, state)
            dst = self.root / "active" / slug
            os.replace(interrupted[0], dst)
            src = self.root / "backlog" / slug
            git_stage(self.store_git_root, src, dst)
            if self.auto_commit_transitions():
                self._commit_transition(slug, src, dst, "active", None)
                self._publish_after_transition(slug, "active")
            return self._require(slug)
        if item is None:
            # Empty has two meanings: no such slug, or a competitor moved the
            # folder mid-read. Answering "no such work item" for the second is a
            # worse lie than the crash it replaced, so look for the claim before
            # denying the item exists — in `.claiming/` if the winner is still
            # mid-flight, in `active/` if it landed while we were asking.
            if self._claiming_dirs(slug):
                self._lost_the_claim(slug)            # always raises
            item = self.get(slug)
        if item is None:
            raise ValueError(f"no such work item: {slug}")
        if item.status == "active":
            if not take_over:
                raise AlreadyClaimed(slug, item.owner, item.started)
            if not owner:
                raise ValueError("takeover requires an owner")
            self._set_fields_at(self._require_dir(slug),
                                {"owner": owner, "started": started})
            if self.auto_commit_transitions():
                rel = str(self._require_dir(slug).relative_to(self.store_git_root))
                err = git_commit_result(self.store_git_root, f"tcw work: take over {slug}", rel)
                if err:
                    raise TransitionCommitError(f"{slug} was taken over, but committing it failed:\n{err}")
            return self._require(slug)
        if item.status != "backlog":
            raise IllegalTransition(f"{item.status} → active is not a legal transition")
        if not force:
            if item.initiative:
                epic = self.initiative_epic(item)
                if epic is None or epic.status != "active":
                    raise ValueError(f"Cannot start work item {slug} before epic {item.initiative} is active")
            blockers = self.unresolved_blockers(item)
            if blockers:
                raise ValueError("blocked by: " + ", ".join(blockers) + " (use --force to override)")
        src = self._find(slug)
        claiming = self.root / ".claiming"
        claiming.mkdir(exist_ok=True)
        private = claiming / f"{slug}-{uuid.uuid4().hex}"
        try:
            # Losing the race has three tells a moment apart: `_find` came back
            # empty because the winner's folder is in `.claiming/` where nothing
            # looks; it pointed at a folder the winner had already published to
            # `active/`; or it was still in `backlog` and `os.replace` lost. Same
            # event, so normalize to one signal.
            #
            # The middle one is the dangerous one. `_find` searches every status
            # folder, so it can hand back the winner's *published* item — and
            # renaming that into our private area steals a settled claim, with
            # every contender republishing over the last. A claim moves an item
            # out of `backlog` and nowhere else; anything else means we lost.
            if src is None or self._status_of(src) != "backlog":
                raise FileNotFoundError(slug)
            os.replace(src, private)
        except FileNotFoundError:
            self._lost_the_claim(slug)                # always raises
        state_path = private / "state.yaml"
        state = load_yaml(state_path)
        state["owner"], state["started"] = owner, started
        dump_yaml(state_path, state)
        dst = self.root / "active" / slug
        try:
            os.replace(private, dst)
        except BaseException:
            os.replace(private, src)
            raise
        git_stage(self.store_git_root, src, dst)
        if self.auto_commit_transitions():
            self._commit_transition(slug, src, dst, "active", item)
            self._publish_after_transition(slug, "active")
        return self._require(slug)

    def _claiming_dirs(self, slug: str) -> list[Path]:
        """The adapter-private folders of claims for `slug` still mid-flight.

        Matched against the uuid suffix, not `-*`: `*` spans `-`, so a claim on
        a longer slug would answer for a shorter one — and slugs are prefixes of
        each other by construction, since `_unique_slug` mints `{base}-2` for a
        duplicate title. A loose glob makes `start()` on an absent slug stall and
        then claim there is an interrupted claim to recover.
        """
        return sorted((self.root / ".claiming").glob(f"{slug}-" + "[0-9a-f]" * 32))

    def _lost_the_claim(self, slug: str) -> NoReturn:
        """Report a lost race once the winner publishes, or an abandoned claim.

        Every way of losing arrives here: `os.replace` raising, `_find` coming
        back empty, or the item vanishing under a read. The winner is mid-move,
        so wait briefly for it to reappear in `active` and name it; a claim that
        never lands is one whose claimant died holding it.
        """
        for _ in range(50):
            # `_get_now`, not `get`: this loop *is* the bounded wait, and reading
            # through the stabilizing `get` would nest another 500 ms window
            # inside each of these 50 iterations.
            current = self._get_now(slug)
            if current is not None and current.status == "active":
                raise AlreadyClaimed(slug, current.owner, current.started)
            time.sleep(0.01)
        raise ValueError(f"{slug} has an interrupted claim; use --take-over --owner <identity>")

    def _status_of(self, d: Path) -> str:
        """Status = the first path component under the work root (`backlog/p/c`
        → `backlog`), so a nested child reports its top-level status folder."""
        return d.relative_to(self.root).parts[0]

    def _parent_slug(self, d: Path) -> str:
        """Parent = the nearest `state.yaml`-bearing ancestor's name; "" if the
        nearest ancestor is a status folder (the relation derived from nesting)."""
        anc = d.parent
        while anc != self.root and self.root in anc.parents:
            if (anc / "state.yaml").exists():
                return anc.name
            anc = anc.parent
        return ""

    # -- slug resolution (the stable-id resolver, A.5) --

    def _find(self, slug: str) -> Path | None:
        """Resolve a slug to its folder. `None` if absent — including the instant
        it is mid-move, which callers on the claim path disambiguate.

        Two matches does not mean two items. `_item_dirs` walks the status
        folders in order, so an item moving from an earlier one to a later one —
        `backlog` → `active`, which is precisely what a claim does — is counted
        once where it was and once where it landed. Raising `MultipleMatch` there
        turns the most ordinary concurrent operation TCW has into a traceback.
        A genuine duplicate slug survives a re-walk; a transition does not.
        """
        for _ in range(5):
            matches = [d for d in self._item_dirs() if d.name == slug]
            if len(matches) <= 1:
                return matches[0] if matches else None
        raise MultipleMatch(f"slug resolves to {len(matches)} items: {slug}")

    def _require_dir(self, slug: str) -> Path:
        d = self._find(slug)
        if d is None:
            raise ValueError(f"no such work item: {slug}")
        return d

    def path(self, slug: str) -> Path | None:
        return self._find(slug)

    def locate(self, slug: str) -> str | None:
        p = self.path(slug)
        if p is None:
            return None
        try:
            return str(p.relative_to(self.node_root))
        except ValueError:
            return str(p)                             # outside node_root: absolute, don't crash

    def _present(self, p: Path) -> bool:
        """The **lifecycle** presence rule: exists and has non-whitespace content.

        Answers *did this stage produce anything?* Mere existence would let an
        empty file claim its stage ran, which is what `intake` made visible.

        Deliberately **not** the rule used by the read / write / delete /
        revision surface, which asks a different question — *is there a resource
        at this name?* — and answers it with a bare `is_file()`.  A blank file is
        a real resource there: readable, versioned, deletable.  Routing that
        surface through this rule would make `read_artifact` and `write_artifact`
        contradict each other (the read reports absent, so the caller sends
        `revision=""`, and the write refuses it as stale).  Both rules are stated
        on `WorkStore.artifacts` and `WorkStore.read_artifact`, which is where an
        adapter author will look; `tests/test_work.py` pins them against each
        other so neither can drift into the other by accident."""
        # Containment before the read: `_item_dirs` bounds *discovery* via
        # state.yaml, but a legitimately discovered item can still hold an
        # artifact that is a symlink out of the store. An escaped resource is
        # not present — the same fail-closed shape the node stores use.
        return (p.is_file() and self._within_store(p)
                and bool(p.read_text(encoding="utf-8").strip()))

    def _resolve_body(self, d: Path) -> tuple[str | None, str]:
        """The body surface: (artifact name, text), or (None, "") when neither is
        present. Reads fall back request → intake; writes never do (`update_work`)."""
        for name in BODY_ORDER:
            p = d / self._artifact_filename(name)
            try:
                if self._present(p):
                    return name, p.read_text(encoding="utf-8")
            except FileNotFoundError:
                continue                              # claimed out from under us
        return None, ""

    def body_path(self, slug: str) -> Path | None:
        d = self._find(slug)                          # FS realization of the body surface
        if d is None:
            return None
        name, _ = self._resolve_body(d)
        return d / self._artifact_filename(name) if name else None

    @staticmethod
    def _artifact_filename(name: str) -> str:
        return f"{name}.md"

    def artifacts(self, slug: str) -> list[Artifact]:
        d = self._find(slug)
        if d is None:
            return []
        out: list[Artifact] = []
        for name in WORK_ARTIFACTS:
            p = d / self._artifact_filename(name)
            try:
                present = self._present(p)
            except FileNotFoundError:
                return []                             # claimed out from under us
            out.append(Artifact(name=name, present=present))
        return out

    def artifact_locator(self, slug: str, name: str) -> str | None:
        if name not in WORK_ARTIFACTS:
            return None
        d = self._find(slug)
        if d is None:
            return None
        return str(d / self._artifact_filename(name))

    @staticmethod
    def _frontmatter(content: str, label: str) -> dict | None:
        """The leading `---` YAML block as a mapping, or None when absent/empty.

        `label` names the document in errors — this reads both `plan.md` and
        inbox entries, and "malformed YAML frontmatter" is useless without
        saying which file.
        """
        if not content.startswith("---\n"):
            return None
        end = frontmatter_end(content)
        if end == 0:
            raise ValueError(f"{label}: malformed YAML frontmatter")
        try:
            metadata = yaml.safe_load(content[4:end - 5])
        except yaml.YAMLError as exc:
            raise ValueError(f"{label}: malformed YAML frontmatter: {exc}") from exc
        if metadata is None:
            return None
        if not isinstance(metadata, dict):
            raise ValueError(f"{label}: frontmatter must be a mapping")
        return metadata

    @staticmethod
    def _plan_manifest(content: str) -> list[dict] | None:
        metadata = FsWorkStore._frontmatter(content, "plan.md")
        if metadata is None or "stages" not in metadata:
            return None
        stages = metadata["stages"]
        if not isinstance(stages, list):
            raise ValueError("plan.md: stages must be a list")
        return stages

    def _declared_plan_stages(self, slug: str) -> list[PlanStage]:
        d = self._require_dir(slug)
        plan = d / "plan.md"
        if not plan.is_file():
            return []
        declarations = self._plan_manifest(plan.read_text(encoding="utf-8"))
        if declarations is None:
            return []
        registered = set(self.registered_tags())
        seen: set[str] = set()
        raw: list[tuple[str, str, tuple[str, ...], str, str, int | None, tuple[str, ...]]] = []
        for index, value in enumerate(declarations, 1):
            prefix = f"plan.md: stage {index}"
            if not isinstance(value, dict):
                raise ValueError(f"{prefix} must be a mapping")
            stage_id, title, dependencies = value.get("id"), value.get("title"), value.get("depends_on")
            if not isinstance(stage_id, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", stage_id):
                raise ValueError(f"{prefix} has unsafe id")
            if stage_id in seen:
                raise ValueError(f"plan.md: duplicate stage id '{stage_id}'")
            if not isinstance(title, str) or not title.strip():
                raise ValueError(f"{prefix} title must be non-empty")
            if not isinstance(dependencies, list) or not all(isinstance(dep, str) for dep in dependencies):
                raise ValueError(f"{prefix} depends_on must be a list of stage ids")
            if stage_id in dependencies:
                raise ValueError(f"plan.md: stage '{stage_id}' depends on itself")
            effort = value.get("effort", "")
            complexity = value.get("complexity", "")
            if effort and (not isinstance(effort, str) or normalize_work_level(effort) not in {"low", "medium", "high", "very-high"}):
                raise ValueError(f"{prefix} has invalid effort")
            if complexity and (not isinstance(complexity, str) or normalize_work_level(complexity) not in {"low", "medium", "high", "very-high"}):
                raise ValueError(f"{prefix} has invalid complexity")
            priority = value.get("priority")
            if priority is not None and (not isinstance(priority, int) or isinstance(priority, bool)):
                raise ValueError(f"{prefix} priority must be an integer")
            tags = value.get("tags", [])
            if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
                raise ValueError(f"{prefix} tags must be a list")
            stale = [tag for tag in tags if tag not in registered]
            if stale:
                raise ValueError(f"{prefix} has unregistered tag '{stale[0]}'")
            seen.add(stage_id)
            raw.append((stage_id, title.strip(), tuple(dependencies), normalize_work_level(effort) if effort else "", normalize_work_level(complexity) if complexity else "", priority, tuple(tags)))
        for stage_id, _title, dependencies, *_rest in raw:
            unknown = [dep for dep in dependencies if dep not in seen]
            if unknown:
                raise ValueError(f"plan.md: stage '{stage_id}' has unknown dependency '{unknown[0]}'")
        visiting: set[str] = set()
        visited: set[str] = set()
        graph = {stage_id: dependencies for stage_id, _title, dependencies, *_rest in raw}
        def visit(stage_id: str) -> None:
            if stage_id in visiting:
                raise ValueError("plan.md: stage dependencies contain a cycle")
            if stage_id in visited:
                return
            visiting.add(stage_id)
            for dependency in graph[stage_id]:
                visit(dependency)
            visiting.remove(stage_id)
            visited.add(stage_id)
        for stage_id in graph:
            visit(stage_id)
        folder = d / "plan"
        return [PlanStage(stage_id, title, dependencies, effort, complexity, priority, tags,
                          (folder / f"{stage_id}.md").is_file(),
                          _revision((folder / f"{stage_id}.md").read_text(encoding="utf-8")) if (folder / f"{stage_id}.md").is_file() else "")
                for stage_id, title, dependencies, effort, complexity, priority, tags in raw]

    def plan_stages(self, slug: str) -> list[PlanStage]:
        return self._declared_plan_stages(slug)

    def _plan_stage_path(self, slug: str, stage_id: str) -> Path:
        stages = {stage.id for stage in self._declared_plan_stages(slug)}
        if stage_id not in stages:
            raise ValueError(f"undeclared plan stage '{stage_id}'")
        return self._require_dir(slug) / "plan" / f"{stage_id}.md"

    def read_plan_stage(self, slug: str, stage_id: str) -> PlanStageResource | None:
        path = self._plan_stage_path(slug, stage_id)
        if not path.is_file():
            return None
        content = path.read_text(encoding="utf-8")
        return PlanStageResource(stage_id, content, revision=_revision(content))

    def write_plan_stage(self, slug: str, stage_id: str, content: str,
                         revision: str | None = None) -> PlanStageResource:
        self._require_repository()
        if not isinstance(content, str):
            raise ValueError("stage content must be text")
        path = self._plan_stage_path(slug, stage_id)
        if revision is not None:
            current = _revision(path.read_text(encoding="utf-8")) if path.is_file() else ""
            if current != revision:
                raise StaleRevision(f"stale revision for plan stage '{stage_id}' of '{slug}'")
        owned = _mkdir_owned(path.parent)
        self._write_staged([(path, content)],
                           owned_dir=path.parent if owned else None)
        return PlanStageResource(stage_id, content, revision=_revision(content))

    def delete_plan_stage(self, slug: str, stage_id: str,
                          revision: str | None = None) -> None:
        path = self._plan_stage_path(slug, stage_id)
        if not path.is_file():
            raise ValueError(f"plan stage '{stage_id}' is not present")
        if revision is not None and _revision(path.read_text(encoding="utf-8")) != revision:
            raise StaleRevision(f"stale revision for plan stage '{stage_id}' of '{slug}'")
        self._rm(path)

    def plan_stage_locator(self, slug: str, stage_id: str) -> str | None:
        try:
            return str(self._plan_stage_path(slug, stage_id))
        except ValueError:
            return None

    def _unique_slug(self, created: str, title: str) -> str:
        # ponytail: 120 chars, not a computed budget. A path component holds 255
        # bytes; the date prefix costs 11, `mkdtemp(prefix=f".{slug}-")`
        # (inbox_accept) costs 10 more, and the collision suffix a few — so 120
        # leaves >100 bytes spare. `slugify` emits only `[a-z0-9-]`, so a
        # character is a byte here. Raise it if a real title ever gets clipped.
        body = slugify(title)[:120].rstrip("-") or "untitled"
        base = f"{created}-{body}"
        slug, n = base, 2
        # Live items *and* the graveyard. `_find` sees only what the store still
        # holds, and a resolved item's folder is gitignored — so in any clone but
        # the one that resolved it, a matching date and title would be handed the
        # very slug it used, and every existing reference to the resolved item
        # would resolve, silently, to this new one. The tombstone is the only
        # trace that survives into that clone, which makes it the only thing that
        # can prevent the collision there.
        #
        # A YAML read per candidate, not per call: the loop body runs only on a
        # real collision, and `_find` already walks the store on every iteration.
        while self._find(slug) is not None or self.tombstone(slug) is not None:
            slug, n = f"{base}-{n}", n + 1
        return slug

    # -- reads --

    @staticmethod
    def _safe_yaml(path: Path) -> dict:
        """Tolerant load: a malformed state file degrades to empty rather than
        crashing the board (the item still lists, status comes from the dir)."""
        try:
            return load_yaml(path)
        except yaml.YAMLError:
            return {}

    def _item_from_dir(self, d: Path) -> WorkItem | None:
        """`None` when the folder went away mid-read — a concurrent claim moved
        it between the `_find`/`_item_dirs` scan and this read.

        Every guarded read below (`load_yaml`, `read_text`, `stat`) checks for
        the file and then opens it, so each is its own window; a competing
        claim's `os.replace` lands in any of them. Catching the vanish once,
        here, is what keeps `get()`, `query()`, and the claim-recovery loop from
        needing the same guard twenty times over.

        Two conditions, because the failure has two shapes. The exception is the
        narrow one — the folder went while a read was open. The re-check is the
        wide one: `load_yaml` answers `{}` for an absent file and `_safe_yaml`
        tolerates a malformed one, so a folder already gone reads as a *valid*
        item full of defaults, still sitting in its old status. That silent
        phantom is worse than the crash it would replace, and only an explicit
        look for `state.yaml` after the read catches it. Both callers reach here
        from a scan that required `state.yaml`, so its absence now means moved.
        """
        try:
            item = self._read_item(d)
        except FileNotFoundError:
            return None
        return item if (d / "state.yaml").exists() else None

    def _read_item(self, d: Path) -> WorkItem:
        state = self._safe_yaml(d / "state.yaml")
        _, body_text = self._resolve_body(d)
        caps = d / "capabilities.yaml"
        capabilities = None
        if caps.exists():
            try:
                capabilities = load_yaml(caps)
            except yaml.YAMLError as e:
                capabilities = {"_tcw_parse_error": str(e)}
        return WorkItem(
            slug=d.name,
            title=state.get("title", d.name),
            status=self._status_of(d),
            created=state.get("created", ""),
            modified=self._modified_timestamp(d),
            resolution=state.get("resolution"),
            priority=state.get("priority"),
            effort=state.get("effort") or "",        # `or ""`: bare YAML `effort:` (null) → ""
            complexity=state.get("complexity") or "",
            tags=list(state.get("tags") or []),
            body=body_text,
            blocked_by=list(state.get("blocked_by") or []),
            capabilities=capabilities,
            initiative=state.get("initiative", ""),
            type=state.get("type", ""),
            worktree=state.get("worktree", ""),
            branch=state.get("branch", ""),
            parent=self._parent_slug(d),
            owner=state.get("owner", ""),
            started=state.get("started", ""),
        )

    @staticmethod
    def _modified_timestamp(folder: Path) -> str:
        names = [
            "state.yaml",
            *[f"{name}.md" for name in WORK_ARTIFACTS],
            *WORK_SIDECARS,
        ]
        resources = [folder / name for name in names]
        plan_folder = folder / "plan"
        if plan_folder.is_dir():
            resources.extend(sorted(plan_folder.glob("*.md")))
        return _modified_timestamp(resources)

    def _get_now(self, slug: str) -> WorkItem | None:
        """One immediate probe: the item as it is on disk this instant, or None.

        The read for callers whose job *is* the unstable state — claim recovery,
        lost-race detection, the blocker loop's error handling. They must see the
        raw None that `get` stabilizes away.

        "Immediate" still means *correct*: locating the folder and reading it are
        two steps, so a rename between them leaves a stale path that reads as
        absent. One re-probe settles it. This window is not the claim window and
        has no `.claiming/` evidence to key on — an ordinary `git mv` transition
        opens it — so it has to close here rather than in `get`.
        """
        d = self._find(slug)
        if d is None:
            return None
        item = self._item_from_dir(d)
        if item is None:                       # the folder went while we read it
            d = self._find(slug)               # once: it has a new home, or none
            item = self._item_from_dir(d) if d is not None else None
        return item

    def _graveyard_path(self) -> Path:
        return self.root / self.GRAVEYARD_NAME

    def _require_writable_graveyard(self, slug: str) -> None:
        """Refuse a resolving transition when the graveyard cannot be safely
        rewritten. Called *before* the move, so a refusal moves nothing.

        Two refusals, both about not destroying someone else's record:

        **Unparseable, or a document that is not a mapping.** The write is
        read-modify-write; parsing a broken file as empty and writing one entry
        back would silently delete every record before it. Reading tolerates
        this shape (see `tombstone`) because a reader answering None costs a
        single lookup — a writer clobbering costs the whole file.

        **Uncommitted changes, when auto-commit is on.** The transition commit
        is scoped to the item's folders plus this one shared path, so a
        concurrent agent's in-flight graveyard edit would be committed under
        *this* item's message. Since every graveyard write commits itself, a
        dirty graveyard means something already went wrong. Skipped when
        `auto-commit-transitions` is off: there the user manages commits and an
        uncommitted graveyard is the expected steady state, so refusing would
        make the setting unusable after the first resolution.
        """
        path = self._graveyard_path()
        if not path.exists():
            return
        try:
            doc = load_yaml(path)
        except yaml.YAMLError as e:
            raise ValueError(
                f"cannot record {slug}: the graveyard at {path} does not parse "
                f"({e.__class__.__name__}). Recording over it would delete every "
                f"item already in it — repair the file, then retry.")
        if doc and not isinstance(doc, dict):
            raise ValueError(
                f"cannot record {slug}: the graveyard at {path} is not a mapping "
                f"of slugs. Recording over it would delete its contents — repair "
                f"the file, then retry.")
        if not self.auto_commit_transitions():
            return
        rel = str(path.relative_to(self.store_git_root))
        # Not `_has_committable_changes`, which is the obvious reuse and is the
        # wrong rule here by exactly one line: it excludes untracked (`??`)
        # paths, and an untracked graveyard is precisely the state this refuses
        # — a first write someone else made and has not committed. Not `_git`
        # either, because that raises on a non-zero exit and this wants to fall
        # through to "assume clean" when git cannot answer (see the returncode
        # check below). `stdin` is closed explicitly so `_git`'s guarantee about
        # never inheriting a terminal still holds here.
        out = subprocess.run(
            ["git", "-C", str(self.store_git_root), "status", "--porcelain", "--", rel],
            stdin=subprocess.DEVNULL, capture_output=True, text=True)
        if out.returncode == 0 and out.stdout.strip():
            raise ValueError(
                f"cannot record {slug}: the graveyard at {rel} has uncommitted "
                f"changes, and this transition's commit would carry them. TCW "
                f"commits every graveyard write itself, so these are someone "
                f"else's — commit or discard them, then retry.")

    def _write_tombstone(self, slug: str, resolution: str,
                         resolved: str = "") -> None:
        """Record `slug` in the graveyard, preserving every entry already there.

        Read-modify-write rather than append: one file serves the whole store, so
        two agents resolving different items rewrite the same document.
        `_require_writable_graveyard` has already refused the shapes where the
        read half would lose data.

        **This is not concurrency-safe, and read-modify-write is not what makes
        it safe.** The read and the write are separate steps with no lock across
        them, so two processes can both read the same mapping and the second
        write wins, dropping the first one's entry — an item left in `completed/`
        with no record anywhere, which is exactly what `_unique_slug` then fails
        to protect against. The window is one YAML parse plus one atomic write,
        so it needs two resolutions within milliseconds of each other. What
        read-modify-write actually buys is the *sequential* case — a second
        resolution preserving the first — and a merge between two clones, where
        the conflict is a plain YAML one a human can settle.

        Sorted keys, unlike the ordered documents elsewhere in this store: this
        mapping has no meaningful order, and a stable one keeps the diff of a
        resolution to a single added block and makes a merge conflict between two
        concurrent resolutions a plain, settleable one.
        """
        path = self._graveyard_path()
        doc: dict = {}
        if path.exists():
            loaded = load_yaml(path)
            if isinstance(loaded, dict):
                doc = loaded
        doc[slug] = {"resolution": resolution or "",
                     "resolved": resolved or date.today().isoformat()}
        self._write_staged([(path, yaml.safe_dump(doc, sort_keys=True,
                                                  allow_unicode=True))])

    def record_tombstone(self, slug: str, resolution: str = "",
                         resolved: str = "") -> Tombstone:
        """Backfill one record, committing it the way a transition commits.

        `resolution` is optional and may stay empty: a repository adopting this
        is recording slugs whose resolution nobody kept, and inventing one would
        be worse than admitting it is unknown. When given it is validated
        through `resolution_status`, the same function `complete` uses, so the
        two cannot drift.

        `resolved` likewise defaults to today rather than guessing a real date —
        the honest reading of the record is "known resolved by this date".

        Two refusals, and the first is narrower than it looks. `get()` answers
        for `completed/` and `discarded/` as well as the live statuses, so "the
        store can find it" is not the same as "it is still live" — and the
        machine an adopter backfills from is precisely the one where a resolved
        item's folder is still on disk. Refusing on `get()` alone rejected the
        migration path this command exists to provide, telling the user to
        "resolve the item instead" of an item already resolved. Only a genuinely
        live status is refused.

        The second refusal is what that first change makes reachable.
        `_write_tombstone` assigns `doc[slug]` outright — correct for a
        transition, which should record what just happened — so a second
        `tombstone add` for the same slug would overwrite a good record with this
        call's defaults, an empty resolution and today's date, and report
        success. A scripted backfill re-run over the same list is the ordinary
        way to hit that, so an existing record is left alone and the command
        says what is already there.
        """
        self._require_repository()
        # A blank or path-shaped slug can never name an item this store held, and
        # there is no `tombstone rm` — an entry written under one is permanent
        # short of the hand-edit the graveyard exists to make unnecessary. The
        # guard is deliberately this narrow: a backfilled slug comes from an
        # older version of this tool and need not match what `slugify` mints
        # today, so anything stricter would refuse legitimate history.
        slug = slug.strip()
        if not slug or "/" in slug:
            raise ValueError(
                "cannot record an empty or path-shaped slug: a tombstone names "
                "one work item this store held.")
        if resolution:
            resolution_status(resolution)          # raises on an unknown one
        if resolved:
            # Normalized, not just validated: `date.fromisoformat` accepts
            # `20260601` on 3.11+, and storing that raw would put a shape in the
            # graveyard that nothing else in the store writes or reads.
            resolved = date.fromisoformat(resolved).isoformat()
        item = self.get(slug)
        if item is not None and item.status not in RESOLVED_STATUSES:
            raise ValueError(
                f"cannot record {slug}: it is a live work item ({item.status}). "
                f"A tombstone says the store is finished with a slug; resolve the "
                f"item instead.")
        existing = self.tombstone(slug)
        if existing is not None:
            raise ValueError(
                f"cannot record {slug}: it is already in the graveyard "
                f"(resolution {existing.resolution or 'unrecorded'}, resolved "
                f"{existing.resolved or 'unrecorded'}). Recording it again would "
                f"replace that with this call's values.")
        self._require_writable_graveyard(slug)
        self._write_tombstone(slug, resolution, resolved)
        if self.auto_commit_transitions():
            path = self._graveyard_path()
            err = git_commit_result(
                self.store_git_root, f"tcw work: tombstone {slug}",
                str(path.relative_to(self.store_git_root)))
            if err:
                raise TransitionCommitError(
                    f"{slug} was recorded in the graveyard, but committing it "
                    f"failed:\n{err}")
        recorded = self.tombstone(slug)
        assert recorded is not None                # just written, above
        return recorded

    def tombstone(self, slug: str) -> Tombstone | None:
        """Read `slug`'s record out of the store's `graveyard.yaml`.

        One file for the whole store rather than one per record: it keeps a
        long-lived store from accumulating thousands of near-empty files, and it
        is one greppable artifact. The cost is that every resolving transition
        writes the same path — see `_write_tombstone`, which is why that write is
        read-modify-write and refuses a dirty file.

        Tolerant on every degraded shape — absent file, unparseable YAML, a
        document that is not a mapping, an entry missing its fields. Two reasons,
        and they point the same way: `_safe_yaml`'s stated degrade-don't-crash
        rule, and `resolve_tcw_ref`'s contract never to propagate a store
        exception to a caller scanning many links. A hand-edited graveyard must
        not take `tcw validate` down with it.

        An entry that is present but malformed still answers *yes, this slug
        existed* — the fields are context, and reporting None for a damaged
        record would call finished work a typo.
        """
        path = self.root / self.GRAVEYARD_NAME
        if not path.exists():
            return None
        try:
            doc = self._safe_yaml(path)
        except (OSError, UnicodeDecodeError):
            # `_safe_yaml` catches a YAML syntax error and nothing else, so a
            # file that is unreadable or not valid UTF-8 came back out of it —
            # and from here it would surface inside `_unique_slug`, turning
            # `tcw work new` into a traceback about a file the user never
            # touched. Every caller of this method wants "answer None and carry
            # on", so the tolerance the docstring promises is completed here.
            return None
        if not isinstance(doc, dict):
            return None
        if slug not in doc:
            return None
        entry = doc[slug]
        if not isinstance(entry, dict):
            entry = {}
        return Tombstone(
            slug=slug,
            resolution=str(entry.get("resolution") or ""),
            resolved=str(entry.get("resolved") or ""),
        )

    def get(self, slug: str) -> WorkItem | None:
        """The settled item, or None if it is genuinely absent.

        `start` moves an item through an adapter-private `.claiming/` folder
        between two renames, and during that interval a naive read answers None —
        which storage-neutral callers correctly read as "absent", and so a blocker
        mid-claim silently stopped blocking. So: answer a hit immediately, answer
        a miss with *no claim evidence* immediately, and only wait when this exact
        slug is provably mid-flight.

        The claim folder never reaches `WorkStore`; the abstract contract is still
        "the current item or None", and an adapter is free to settle a transient
        move before answering. A transactional adapter draws the same line between
        reading a committed value and inspecting an in-flight transaction.
        """
        item = self._get_now(slug)
        if item is not None or not self._claiming_dirs(slug):
            return item                        # hit, or an ordinary miss: no wait
        for _ in range(50):                    # the publication window, 500 ms
            time.sleep(0.01)
            item = self._get_now(slug)
            if item is not None:
                return item
        raise ValueError(f"{slug} has an interrupted claim; use --take-over --owner <identity>")

    def query(self, status: str | None = None) -> list[WorkItem]:
        items = [self._item_from_dir(d) for d in self._item_dirs()]
        return [i for i in items
                if i is not None and (status is None or i.status == status)]

    def initiative_epic(self, item: WorkItem) -> WorkItem | None:
        if not item.initiative:
            return None
        local = self.get(item.initiative)
        if local is not None:
            return local
        parent = parent_node(self.node_root)
        while parent is not None:
            got = FsWorkStore.open(parent).get(item.initiative)
            if got is not None:
                return got
            parent = parent_node(parent)
        return None

    def initiative_children(self, epic_slug: str) -> list[WorkItem]:
        children = [i for i in self.query() if i.initiative == epic_slug]
        for node in child_nodes(self.node_root):
            children.extend(i for i in FsWorkStore.open(node).query()
                            if i.initiative == epic_slug)
        return children

    def dod_checklist(self) -> list[str]:
        p = self.root / "dod.yaml"
        if p.exists():
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [str(x) for x in data]
            if isinstance(data, dict) and isinstance(data.get("checklist"), list):
                return [str(x) for x in data["checklist"]]
        return list(DEFAULT_DOD)

    # -- tag registry (node-root `tcw-config.yaml` → `work.tags`) --

    def _config_path(self) -> Path:
        return self.node_root / SENTINEL

    def _config(self) -> dict:
        """Read the node sentinel config, tolerant of absence/emptiness. A
        malformed file raises a clear error naming the path rather than a raw
        YAML traceback. Plain board listing never calls this, so a broken config
        only fails operations that actually need the tag registry."""
        try:
            data = load_yaml(self._config_path())
        except yaml.YAMLError as e:
            raise ValueError(f"malformed {self._config_path()}: {e}") from e
        if not isinstance(data, dict):                 # valid YAML, wrong shape
            raise ValueError(f"malformed {self._config_path()}: expected a mapping")
        return data

    def registered_tags(self) -> list[str]:
        work = self._config().get("work")
        if not isinstance(work, dict):                 # absent or hand-edited to a scalar/list
            return []
        return sorted(str(t) for t in (work.get("tags") or []))

    # -- transition-commit policy (node-root `tcw-config.yaml` → `work.*`) --

    def _work_config(self) -> dict:
        """The `work:` mapping, or {} when absent or hand-edited to a non-mapping.
        Tolerant by design: a malformed key must not break transitions."""
        try:
            work = self._config().get("work")
        except ValueError:                             # malformed sentinel
            return {}
        return work if isinstance(work, dict) else {}

    @property
    def publishes(self) -> bool:
        """Whether a committed transition here is pushed to a remote.

        True only for a store the resolution ladder reached **through its
        declaration** — the provisioned copy, on a machine that has no other. Two
        stores are deliberately excluded, and the second is the important one:

        - a store found at a local `<component>.path` while a declaration also
          exists. The declaration is a fallback, never an override; one that did
          not answer the read does not get to cause a write. That copy is on the
          user's own disk and they can push it themselves.
        - a store with no declaration at all. Its Git repository very often
          *does* have an `origin` — it is usually the user's own project — so a
          publication decision made by looking for a remote, rather than for a
          declaration, would make TCW push the user's repository on every status
          change. `self.declaration` is the only thing consulted here for
          exactly that reason.
        """
        return self.declaration is not None and self.publish_transitions()

    def refresh(self) -> None:
        """Bring the provisioned working copy to the declared remote's state.

        Delegates to the provisioner rather than reimplementing the plumbing, so
        a transition's refresh and `tcw provision --refresh` can never disagree
        about what "up to date" means — including the fast-forward-only
        behaviour that this store's divergence semantics now rest on.

        Then checks that the copy is *actually* level with the remote, which the
        provisioner's refresh does not promise. Two ways it can come back behind:
        the fast-forward was refused because the histories diverged, and — quieter
        — the branch has no upstream, in which case `_refresh` fetches and skips
        integration entirely, reporting success while changing nothing. Both end
        the same way: every push from here is rejected, and every later
        transition hits the same wall. So the check is here, and the message
        names the way out rather than only the symptom.
        """
        checkout = checkout_root(self.node_root, self.declaration)
        provisioner = FsStoreProvisioner(self.node_root, self.COMPONENT,
                                         self.declaration)
        try:
            provisioner.ensure_available(refresh=True)
        except ValueError as error:
            if "fast-forward" not in str(error):
                raise
            raise self._diverged(checkout) from None
        branch = self._publish_branch(checkout)
        counts = _git(["git", "-C", str(checkout), "rev-list", "--count",
                       "--left-right", f"origin/{branch}...{branch}"],
                      capture_output=True, text=True)
        if counts.returncode == 0 and counts.stdout.split():
            behind = int(counts.stdout.split()[0])
            if behind:
                raise self._diverged(checkout)

    def _diverged(self, checkout: Path) -> ValueError:
        """The one message a wedged user meets on every transition until they act.

        It says what happened, where, and what to run — because "Not possible to
        fast-forward, aborting" is git telling the truth to someone who did not
        ask git anything.
        """
        return ValueError(
            f"{self.COMPONENT}.repository: the provisioned store at {checkout} has "
            f"diverged from its remote — both have commits the other does not, so "
            f"it cannot be brought up to date without choosing how to combine "
            f"them, and TCW will not choose that for you. Until it is reconciled "
            f"every transition will stop here.\n"
            f"Reconcile it in {checkout} — `git -C {checkout} log --oneline "
            f"--left-right HEAD...@{{u}}` shows both sides — then re-run the "
            f"transition."
        )

    def publish(self) -> None:
        """Push this store's committed transitions to the declared remote.

        Verifies the checkout against the declaration before contacting anything,
        for the reason `_require_declared_checkout` already gives about fetching:
        a declared `checkout` is an arbitrary user-chosen directory and can hold
        an unrelated repository. Pushing into the wrong one is worse than fetching
        from it, because it writes.

        Raises on failure and undoes nothing. The move and the commit have
        already landed, and reversing them would be a second failure worse than
        the first — the same reasoning `_commit_transition` gives, one step
        further out.
        """
        provisioner = FsStoreProvisioner(self.node_root, self.COMPONENT,
                                         self.declaration)
        checkout = checkout_root(self.node_root, self.declaration)
        provisioner._require_declared_checkout(checkout)
        branch = self._publish_branch(checkout)
        provisioner._run(["git", "-C", str(checkout), "push", "--quiet",
                          "origin", f"{branch}:{branch}"])

    def _publish_branch(self, checkout: Path) -> str:
        """The branch a push would update, or a refusal naming why there is none.

        A declaration pinning `ref` to a tag or a commit leaves the checkout on a
        detached HEAD, so there is no branch to push and nothing sensible to
        invent.
        """
        branch = _git(["git", "-C", str(checkout), "rev-parse", "--abbrev-ref", "HEAD"],
                      capture_output=True, text=True).stdout.strip()
        if not branch or branch == "HEAD":
            raise ValueError(
                f"{self.COMPONENT}.repository: the provisioned checkout is not on a "
                f"branch, so there is nothing to publish to. A declaration pinned "
                f"to a tag or a commit is read-only by nature; point `ref` at a "
                f"branch to publish transitions, or set "
                f"`{self.COMPONENT}.publish-transitions: false` to work locally.")
        return branch

    def _publish_after_transition(self, slug: str, to_status: str) -> None:
        """Step 4 of four, after the commit has landed.

        The failure message is the whole point of this wrapper. "Your item moved,
        it is committed here, and it is not on the remote" is a state this CLI has
        never had to describe, and the user's next question is always whether
        their work is safe. So it says where the work is before it says what
        failed.
        """
        if not self.publishes:
            return
        try:
            self.publish()
        except (ValueError, OSError, subprocess.CalledProcessError) as error:
            raise PublicationError(
                f"{slug} moved to {to_status} and was committed in "
                f"{self.store_git_root} — your work is saved there — but "
                f"publishing it to the declared remote failed:\n{error}\n"
                f"Re-run the transition, or push {self.store_git_root} yourself, "
                f"once the remote is reachable."
            ) from None

    def _refresh_before_transition(self) -> None:
        """Step 1 of four, at the top of every path that moves an item.

        Before anything moves, because a refresh that fails here has nothing to
        explain: no folder has moved, no commit exists, and the transition simply
        refuses. Every later step's failure leaves state behind and has to
        describe it — see `_commit_transition`.

        **Called from two places, not one.** `start` does not route through
        `_effect_transition`: it has its own claim-based path with its own
        commits (the `.claiming/` rename is what makes concurrent starts safe),
        so a hook in `_effect_transition` alone would leave `tcw work start` —
        the transition most likely to happen in a fresh session — unrefreshed and
        unpublished. Both call this as their first statement after
        `_require_repository`. A third transition path must call it too; the
        parametrized transition-surface tests in `tests/test_store_publication.py`
        are what will say so.
        """
        if not self.publishes:
            return
        # Whether a push is *possible* is a precondition, so it is answered here
        # rather than after the item has moved. A declaration pinned to a tag or
        # a commit can never publish, and discovering that at step 4 left the
        # user with a moved, committed, unpublishable item on *every* transition
        # — the same error each time, after the damage rather than instead of it.
        self._publish_branch(checkout_root(self.node_root, self.declaration))
        self.refresh()

    def publish_transitions(self) -> bool:
        """Whether publication is switched on. Default True.

        Default True because a store only reaches `publishes` by having been
        provisioned, which is already an explicit opt-in to the declaration; a
        second opt-in nobody knows to look for would mean nobody gets this.

        Any non-boolean reads as the default rather than as false, for the same
        reason `auto_commit_transitions` gives: a typo silently disabling the
        mechanism is a worse failure than one that is ignored, because nothing
        looks wrong until someone notices the work never left the machine.
        """
        value = self._work_config().get("publish-transitions")
        return value if isinstance(value, bool) else True

    def auto_commit_transitions(self) -> bool:
        """Whether a transition commits its own status move. Default True.

        Any non-boolean value reads as the default rather than as false: a typo
        in the config silently disabling the commit is a worse failure than
        ignoring it, because nothing would look wrong until someone noticed the
        repository full of uncommitted moves."""
        value = self._work_config().get("auto-commit-transitions")
        return value if isinstance(value, bool) else True

    def lifecycle_policy(self) -> LifecyclePolicy:
        """The node's configured stage/transition bindings.

        **Problems are discarded here on purpose.** Reading a policy must not
        break `tcw work list` because someone mistyped a key; `tcw validate` is
        where malformed configuration surfaces. Both call the same pure parser,
        so they can never disagree about what is legal.
        """
        policy, _problems = parse_lifecycle_policy(self._work_config().get("lifecycle"))
        return policy

    def documentation(self) -> list[DocEntry]:
        """Configured documentation entries, problems discarded — same contract
        as `lifecycle_policy`: a malformed key must not break `tcw work list`."""
        entries, _problems = parse_documentation_entries(
            self._work_config().get("documentation"))
        return entries

    def documentation_problems(self) -> list[str]:
        """Documentation-entry problems, prefixed with the file they came from —
        for `check`. Mirrors `lifecycle_problems`, and shares its parser, so the
        two surfaces can never disagree about what is legal."""
        _entries, problems = parse_documentation_entries(
            self._work_config().get("documentation"))
        return [f"{SENTINEL}: {p}" for p in problems]

    def repository_declaration(self) -> "RepositoryDeclaration | None":
        """The store's declared home repository, or None — problems discarded.

        Same contract as `lifecycle_policy` and `documentation`: a mistyped key
        must not break `tcw work list`. It fails *closed* rather than partially,
        because the parser returns None on any problem — a half-read repository
        is one nobody declared.
        """
        declaration, _problems = parse_repository_declaration(
            self._work_config().get("repository"), f"{self.COMPONENT}.repository")
        return declaration

    def repository_problems(self) -> list[str]:
        """Declaration problems, prefixed with the file they came from — for
        `check`. Mirrors `documentation_problems` and shares its parser."""
        _declaration, problems = parse_repository_declaration(
            self._work_config().get("repository"), f"{self.COMPONENT}.repository")
        return [f"{SENTINEL}: {p}" for p in problems]

    def lifecycle_problems(self) -> list[str]:
        """Policy problems, prefixed with the file they came from — for `check`."""
        policy, problems = parse_lifecycle_policy(self._work_config().get("lifecycle"))
        problems += self._file_binding_problems(policy)
        return [f"{SENTINEL}: {p}" for p in problems]

    def _file_binding_problems(self, policy: LifecyclePolicy) -> list[str]:
        """`file:` bindings that do not exist or leave the node.

        Here rather than in `parse_lifecycle_policy` because the parser is pure —
        it takes a loaded object and touches no filesystem, which is what lets
        `lifecycle_policy` and `tcw validate` share it. Resolving a path is
        adapter knowledge by definition, and `file:` is declared a node-local
        source kind for the same reason: a remote policy store can hold a named
        prompt resource but cannot honor an arbitrary local path.

        Confinement resolves **both** sides with symlinks followed. A lexical
        `..` check passes a symlink inside the node that points out of it, and
        then reads exactly the file the check exists to prevent.
        """
        problems: list[str] = []
        root = self.node_root.resolve()

        def check(b: "Binding", where: str) -> None:
            if b.kind != "file":
                return
            target = (root / b.value).resolve()
            if target != root and root not in target.parents:
                problems.append(f"{where}: file '{b.value}' resolves outside the "
                                f"node root ({target})")
            elif not target.is_file():
                problems.append(f"{where}: file '{b.value}' does not exist "
                                f"({target})")

        for sid, sb in policy.stages.items():
            for i, b in enumerate(sb.prompt):
                check(b, f"work.lifecycle.stages.{sid}[{i}]")
            for i, b in enumerate(sb.pre):
                check(b, f"work.lifecycle.stages.{sid}.pre[{i}]")
        for name, bindings in policy.artifacts.items():
            for i, b in enumerate(bindings):
                check(b, f"work.lifecycle.artifacts.{name}[{i}]")
        return problems

    def trunk_branch(self) -> str | None:
        """The branch transitions are expected to land on, or None when unset.
        Advisory only — TCW warns and commits where it is."""
        value = self._work_config().get("trunk-branch")
        return value.strip() or None if isinstance(value, str) else None

    def _write_tags(self, tags: set[str]) -> list[str]:
        """Read-modify-write `work.tags` (preserving other config keys), stage
        the file. `dump_yaml` rewrites the sentinel wholesale, dropping its stub
        comments — accepted per plan."""
        self._require_repository()
        config = self._config()
        work = config.get("work")
        if not isinstance(work, dict):
            work = {}
        result = sorted(tags)
        work["tags"] = result
        config["work"] = work
        self._write_staged([(self._config_path(),
                             yaml.safe_dump(config, sort_keys=False,
                                            allow_unicode=True))])
        return result

    def register_tags(self, tags: list[str]) -> list[str]:
        return self._write_tags(set(self.registered_tags())
                                | {normalize_tag(t) for t in tags})

    def unregister_tags(self, tags: list[str]) -> list[str]:
        return self._write_tags(set(self.registered_tags())
                                - {normalize_tag(t) for t in tags})

    def _validate_tags(self, tags: list[str]) -> list[str]:
        """Normalize each tag and reject any not in the registered set (fail
        closed). Dedupes, preserving first-seen order."""
        registered = set(self.registered_tags())
        out: list[str] = []
        for t in tags:
            norm = normalize_tag(t)
            if norm not in registered:
                raise ValueError(
                    f"unregistered tag '{norm}'; register it with "
                    f"`tcw work tags add {norm}`")
            if norm not in out:
                out.append(norm)
        return out

    def check(self, identifier: str | None = None) -> list[str]:
        registered = set(self.registered_tags())
        problems: list[str] = []
        if identifier is None:                         # node-wide config, not per-item
            problems.extend(self.lifecycle_problems())
            problems.extend(self.documentation_problems())
            problems.extend(self.repository_problems())
        if identifier is not None:
            item = self.get(identifier)
            if item is None:
                return [f"no such work item: {identifier}"]
            items = [item]
        else:
            items = self.query()
        for item in items:
            for tag in item.tags:
                if tag not in registered:
                    problems.append(f"{item.slug}: unregistered tag '{tag}'")
            problems.extend(self._status_resolution_problems(item))
            try:
                stages = self._declared_plan_stages(item.slug)
                if stages:
                    folder = self._require_dir(item.slug)
                    plan_content = (folder / "plan.md").read_text(encoding="utf-8")
                    for heading in ("Overview", "Stage ordering"):
                        if not self._nonempty_markdown_section(plan_content, heading):
                            problems.append(f"{item.slug}: plan.md requires non-empty '{heading}' section")
                    declared = {stage.id for stage in stages}
                    stage_folder = folder / "plan"
                    if stage_folder.is_dir():
                        for path in sorted(stage_folder.glob("*.md")):
                            if path.stem not in declared:
                                problems.append(f"{item.slug}: undeclared plan stage resource '{path.name}'")
                    for stage in stages:
                        if not stage.present:
                            problems.append(f"{item.slug}: plan stage '{stage.id}' document is missing")
                            continue
                        content = (stage_folder / f"{stage.id}.md").read_text(encoding="utf-8")
                        for heading in ("Objective", "Pre-stage checks", "Implementation", "Post-stage checks"):
                            if not self._nonempty_markdown_section(content, heading):
                                problems.append(f"{item.slug}: plan stage '{stage.id}' requires non-empty '{heading}' section")
            except ValueError as exc:
                problems.append(f"{item.slug}: {exc}")
        return problems

    @staticmethod
    def _status_resolution_problems(item) -> list[str]:
        """Status and resolution must agree. `complete()` derives the status from
        the resolution and writes it as part of the move, so a transition that
        runs to completion cannot disagree with itself. Three things still can: a
        hand-run `mv`, a bad merge, and a transition interrupted between its move
        and its field write — which leaves a resolved item with no resolution and
        is reported below. This is the detector, not a second source of truth."""
        terminal = item.status in RESOLVED_STATUSES
        if not terminal:
            if item.resolution:
                return [f"{item.slug}: status '{item.status}' carries a "
                        f"resolution '{item.resolution}' (only a closed item has one)"]
            return []
        try:
            expected = resolution_status(item.resolution)
        except ValueError:
            return [f"{item.slug}: status '{item.status}' with missing or invalid "
                    f"resolution {item.resolution!r}"]
        if expected != item.status:
            return [f"{item.slug}: resolution '{item.resolution}' belongs in "
                    f"'{expected}' but the item is in '{item.status}'"]
        return []

    @staticmethod
    def _nonempty_markdown_section(content: str, heading: str) -> bool:
        match = re.search(rf"(?m)^##\s+{re.escape(heading)}\s*$", content)
        if match is None:
            return False
        following = content[match.end():]
        next_heading = re.search(r"(?m)^##\s+", following)
        body = following[:next_heading.start()] if next_heading else following
        return bool(body.strip())

    def _validation_resources(self, identifier: str) -> list[Path]:
        """Filesystem resources bounded to one work object."""
        folder = self._find(identifier)
        if folder is None:
            return []
        names = ["state.yaml", *[f"{name}.md" for name in WORK_ARTIFACTS],
                 *WORK_SIDECARS]
        resources = [folder / name for name in names
                     if (folder / name).is_file() and self._within_store(folder / name)]
        plan_folder = folder / "plan"
        if plan_folder.is_dir() and self._within_store(plan_folder):
            resources.extend(sorted(q for q in plan_folder.glob("*.md")
                                    if self._within_store(q)))
        return resources

    # -- raw inbox intake (separate from formal WorkItem status) --

    @property
    def inbox_root(self) -> Path:
        return self.root / "inbox"

    def _resolve_inbox_ref(self, ref: str) -> str:
        """The canonical `InboxEntry.ref` for an identifier `inbox list` printed.

        `list` prints two usable identifiers per row — the ref and the derived
        title — so both resolve, in a fixed order:

        1. the exact ref;
        2. `<ref>.md`, the common case where the title is the stem;
        3. a unique listed title.

        Exact wins outright: a folder named `example` stays addressable as
        `example` even once `example.md` lands beside it. Ambiguity is therefore
        only reachable at step 3 — several listed titles, no exact ref, no `.md`
        — and it raises rather than picking by iteration order, because accepting
        consumes the entry and the wrong guess is not undoable.
        """
        safe = ref and ref not in {".", ".."} and "/" not in ref \
            and "\\" not in ref and not ref.startswith(".")
        if safe:
            exact = self.inbox_root / ref
            if exact.exists() and not exact.is_symlink() and exact.parent == self.inbox_root:
                return ref
            dotmd = self.inbox_root / f"{ref}.md"
            if dotmd.is_file() and not dotmd.is_symlink():
                return f"{ref}.md"
            titled = sorted(e.ref for e in self.inbox_list() if e.title == ref)
            if len(titled) > 1:
                raise ValueError(f"ambiguous inbox entry: {ref} matches "
                                 + ", ".join(titled))
            if titled:
                return titled[0]
        raise ValueError(f"no such inbox entry: {ref}")

    def _inbox_path(self, ref: str) -> Path:
        if not ref or ref in {".", ".."} or "/" in ref or "\\" in ref or ref.startswith("."):
            raise ValueError(f"no such inbox entry: {ref}")
        path = self.inbox_root / ref
        if not path.exists() or path.is_symlink() or path.parent != self.inbox_root:
            raise ValueError(f"no such inbox entry: {ref}")
        return path

    @staticmethod
    def _readable_text(path: Path) -> str | None:
        try:
            data = path.read_bytes()
            if b"\0" in data:
                return None
            return data.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            return None

    @staticmethod
    def _resource(path: Path, name: str) -> InboxResource:
        readable = FsWorkStore._readable_text(path) is not None
        media_type = mimetypes.guess_type(path.name)[0] or (
            "text/plain" if readable else "application/octet-stream")
        return InboxResource(name=name, size=path.stat().st_size,
                             media_type=media_type, readable=readable)

    def _folder_files(self, folder: Path) -> list[tuple[str, Path]]:
        files: list[tuple[str, Path]] = []
        for path in folder.rglob("*"):
            rel = path.relative_to(folder)
            if any(part.startswith(".") for part in rel.parts) or path.is_symlink():
                continue
            if path.is_file():
                files.append((rel.as_posix(), path))
        return sorted(files)

    def _inbox_detail(self, ref: str) -> tuple[InboxEntryDetail, str | None]:
        path = self._inbox_path(ref)
        entry = InboxEntry(ref=ref, title=path.stem if path.is_file() else path.name,
                           kind="file" if path.is_file() else "folder")
        if path.is_file():
            body = self._readable_text(path)
            resources = (self._resource(path, path.name),)
            return InboxEntryDetail(entry, body, resources), path.name if body is not None else None
        if not path.is_dir():
            raise ValueError(f"unsupported inbox entry: {ref}")
        files = self._folder_files(path)
        indexes = [(name, p) for name, p in files if name in {"INDEX.md", "INDEX.txt"}]
        if not indexes:
            raise ValueError(f"folder inbox entry {ref} requires INDEX.md or INDEX.txt")
        if len(indexes) > 1:
            raise ValueError(f"folder inbox entry {ref} has both INDEX.md and INDEX.txt")
        index_name, index_path = indexes[0]
        body = self._readable_text(index_path)
        if body is None:
            raise ValueError(f"folder inbox entry {ref} index must be readable UTF-8 text")
        resources = tuple(self._resource(p, name) for name, p in files)
        return InboxEntryDetail(entry, body, resources), index_name

    def inbox_list(self) -> list[InboxEntry]:
        if not self.inbox_root.exists():
            return []
        out: list[InboxEntry] = []
        for path in sorted(self.inbox_root.iterdir(), key=lambda p: p.name):
            if path.name.startswith(".") or path.is_symlink():
                continue
            if path.is_file() or path.is_dir():
                out.append(InboxEntry(path.name, path.stem if path.is_file() else path.name,
                                      "file" if path.is_file() else "folder"))
        return out

    def inbox_show(self, ref: str) -> InboxEntryDetail:
        detail, _primary = self._inbox_detail(self._resolve_inbox_ref(ref))
        return detail

    @staticmethod
    def _inbox_initiative(body: str | None, ref: str) -> str | None:
        """The `initiative` back-pointer a delegated entry carries, if any.

        Only this one key crosses from intake into work-item state. Inbox
        frontmatter is a requester's text, not trusted model data, so a
        structured value is refused rather than serialized into `state.yaml`.
        """
        metadata = FsWorkStore._frontmatter(body or "", f"inbox entry {ref}")
        value = (metadata or {}).get("initiative")
        if value is None:
            return None
        if isinstance(value, (list, dict, tuple, set)):
            raise ValueError(
                f"inbox entry {ref}: initiative must be a single value, not "
                f"{type(value).__name__}")
        return str(value).strip() or None

    def inbox_accept(self, ref: str, title: str | None = None) -> WorkItem:
        self._require_repository()
        ref = self._resolve_inbox_ref(ref)   # once — both reads must see one entry
        source = self._inbox_path(ref)
        detail, primary = self._inbox_detail(ref)
        # Before anything is created or consumed: a bad initiative must not leave
        # a half-accepted item behind.
        initiative = self._inbox_initiative(detail.body, ref)
        # `--title` wins, then the entry's own H1, then its name with TCW's
        # `YYYY-MM-DD-` filing prefix removed — that prefix is our convention,
        # not a title, and re-dating it into the slug is what dated it twice.
        stripped = _DATE_PREFIX.sub("", detail.entry.title).strip()
        accepted_title = (title or body_title(detail.body)
                          or stripped or detail.entry.title).strip()
        if not accepted_title:
            raise ValueError("title is required and must be non-empty")
        created = date.today().isoformat()
        # Slug from the label when the title has no ASCII to slugify — the H1
        # stays the title, but `<date>-untitled` is a worse identifier than the
        # entry's own name.
        # The *stripped* label, never the dated one: falling back to the raw
        # filename here would put the entry's date back into the slug beside
        # the acceptance date, which is the bug this is all here to kill.
        slug = self._unique_slug(
            created, accepted_title if slugify(accepted_title) else stripped)
        destination = self.root / "backlog" / slug
        manifest: list[str] = []
        attachments: list[tuple[str, Path]] = []
        if source.is_file():
            manifest.append(source.name if primary else f"attachments/{source.name}")
            if primary is None:
                attachments.append((source.name, source))
        else:
            for name, path in self._folder_files(source):
                if name == primary:
                    manifest.append("intake.md")
                else:
                    manifest.append(f"attachments/{name}")
                    attachments.append((name, path))
        manifest = sorted(manifest)
        origin = primary or source.name
        manifest_lines = []
        for name in manifest:
            suffix = f" — accepted from `{origin}`" if name == "intake.md" else ""
            manifest_lines.append(f"- `{name}`{suffix}")
        body = detail.body if detail.body is not None else "Binary intake preserved as an attachment."
        # Intake, not a request: accepting an entry preserves what arrived and
        # leaves the `request` stage still to run. The manifest and the binary
        # fallback above are the parts worth keeping — this used to wrap them in
        # a three-heading TBD skeleton that made the item look already written up.
        intake = ("## Inbox manifest\n\n" + "\n".join(manifest_lines)
                  + "\n\n## Inbox body\n\n" + body)
        if not intake.endswith("\n"):
            intake += "\n"
        temp = Path(tempfile.mkdtemp(prefix=f".{slug}-", dir=self.root / "backlog"))
        try:
            state = {"slug": slug, "title": accepted_title,
                     "created": created, "resolution": None}
            if initiative:                   # absent key when there is none, as before
                state["initiative"] = initiative
            dump_yaml(temp / "state.yaml", state)
            (temp / "intake.md").write_text(intake, encoding="utf-8")
            for name, path in attachments:
                target = temp / "attachments" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target, follow_symlinks=False)
            os.replace(temp, destination)
            self._stage(destination)
            tracked = _git(
                ["git", "-C", str(self.store_git_root), "ls-files", "--error-unmatch", "--", str(source)],
                capture_output=True,
            ).returncode == 0
            if tracked:
                self._rm(source)
            elif source.is_dir():
                shutil.rmtree(source)
            else:
                source.unlink()
        except Exception:
            shutil.rmtree(temp, ignore_errors=True)
            if destination.exists() and source.exists():
                shutil.rmtree(destination, ignore_errors=True)
            raise
        return self.get(slug)

    # -- writes --

    def create(self, title: str, created: str | None = None, body: str = "",
               priority: int | None = None, parent: str | None = None,
               intake: str = "") -> WorkItem:
        """Create a work item — the `WorkItem`-returning face over `create_work`.

        `get_detail(...).item` *is* the `self.get(slug)` this used to end with —
        `get_detail` returns it untouched, so every field is identical.

        # ponytail: one create path. This used to be a second, weaker copy of
        # `create_work`'s — same slug, parent resolution, directory and body
        # template, but plain writes and no rollback. It stays as a thin face
        # because `WorkStore.create` (base.py:931) declares it and the existing
        # call sites use it; the upgrade path is retiring it once they move to
        # `create_work`, not hardening a duplicate.
        """
        return self.create_work(title, created=created, body=body,
                                priority=priority, parent=parent,
                                intake=intake).item

    def set_field(self, slug: str, key: str, value) -> None:
        self._set_fields_at(self._require_dir(slug), {key: value})

    def _set_fields_at(self, d: Path, fields: dict) -> None:
        """Apply `fields` to the item living at `d`, in one read-modify-write.

        Takes a folder rather than a slug because its callers already know where
        the item is — a transition that just moved it, or a claim holding it
        privately. Re-resolving the slug would reopen the window they closed.
        Multi-key so a pair like `owner`/`started` cannot be torn across two
        locations by a move landing between them.
        """
        self._require_repository()
        state = load_yaml(d / "state.yaml")
        state.update(fields)
        self._write_staged([(d / "state.yaml",
                             yaml.safe_dump(state, sort_keys=False,
                                            allow_unicode=True))])

    def _effect_transition(self, slug: str, to_status: str,
                           fields: dict | None = None) -> None:
        self._require_repository()
        self._refresh_before_transition()
        # Before anything moves: a resolving transition has to write the shared
        # graveyard, and a refusal has to mean nothing happened.
        resolving = to_status in RESOLVED_STATUSES
        if resolving:
            self._require_writable_graveyard(slug)
        # Read the item *before* the move: afterwards `_find` points at the new
        # location and the pre-move branch/worktree fields are what the
        # trunk-branch check needs.
        item = self.get(slug)
        src = self._find(slug)
        if src is None:
            # `_get_now`: this branch is already reporting a lost race, so it
            # wants the raw state to describe. Settling here would trade an
            # accurate "another process moved it first" for an interrupted-claim
            # error about the same instant.
            current = self._get_now(slug)
            where = (f"it is now in '{current.status}'" if current is not None
                     else "it no longer exists")
            raise ValueError(
                f"cannot move {slug} to {to_status}: another process moved it first "
                f"({where}). This process changed nothing; re-read the item before "
                f"retrying."
            )
        # Nodes created before a status existed have no folder for it, and
        # `git mv` refuses when the destination's parent is missing. Creating it
        # here is an adapter detail with no abstract analog (the prime directive
        # sends "ensure a directory exists" straight into the adapter), and it is
        # status-agnostic on purpose: it also repairs a hand-deleted folder
        # rather than special-casing whichever status was added last.
        (self.root / to_status).mkdir(parents=True, exist_ok=True)
        dst = self.root / to_status / slug
        self._mv(src, dst)
        if fields:
            # After the move, before the commit. After, because the move is where
            # this process learns it won — a write before it lands on whatever
            # folder the winner moved. Before, because the transition commit is
            # scoped to these two paths and takes working-tree state, so this is
            # what keeps the fields and the move in one commit.
            try:
                self._set_fields_at(dst, fields)
            except subprocess.CalledProcessError as e:
                # `git add` refused (a held index.lock, most likely — which is
                # what the concurrent agents in this scenario produce). The item
                # has already moved, so this is the error that already means
                # exactly that; CalledProcessError is not in the CLI's handled
                # set and would exit as a traceback.
                raise TransitionCommitError(
                    f"{slug} moved to {to_status}, but writing its fields "
                    f"failed:\n{e}")
        if resolving:
            # After the move for the same reason the fields are: the move is
            # where this process learns it won the race, and a tombstone written
            # before it would record a resolution that another process's move
            # actually performed.
            try:
                self._write_tombstone(slug, (fields or {}).get("resolution") or "")
            except subprocess.CalledProcessError as e:
                raise TransitionCommitError(
                    f"{slug} moved to {to_status}, but recording it in the "
                    f"graveyard failed:\n{e}")
        if self.auto_commit_transitions():
            self._commit_transition(slug, src, dst, to_status, item,
                                    extra=(self._graveyard_path(),) if resolving else ())
            # Inside the commit branch, not beside it: with auto-commit off the
            # move is uncommitted, so a push would contact the remote and
            # publish nothing. Nothing to commit means nothing to publish.
            self._publish_after_transition(slug, to_status)

    def _commit_transition(self, slug: str, src: Path, dst: Path,
                           to_status: str, item: "WorkItem | None",
                           extra: tuple[Path, ...] = ()) -> None:
        """Commit the status move, scoped to the two folders it touched.

        Scoped to `src` and `dst` rather than the whole work root: a scoped
        `git commit -- <paths>` takes *working-tree* state, so a broad pathspec
        would sweep every other item's uncommitted edits into a status commit.

        `extra` widens that pathspec by the graveyard on a resolving transition —
        the one path here not owned by this item.

        `_require_writable_graveyard` is what makes that acceptable, but it is
        not a guarantee, and the difference matters. It runs before the move and
        the pathspec is used after the write, so the state it checked can change
        in between — "time of check to time of use", and this code opens that
        window itself. With two agents resolving different items in one working
        tree, the second one's commit can carry the first one's graveyard entry
        under its own message. Nothing is lost when that happens; the entries are
        merged, just attributed to the wrong commit. The guard removes the case
        it can see — a graveyard already dirty when the transition starts — and
        narrows the rest to the window between the check and the commit.
        Serializing that window needs a lock held across check, write and commit,
        which this does not have.

        The move is never rolled back on a commit failure. The `git mv` already
        landed in both the index and the working tree, and undoing it introduces
        a second failure mode worse than the first — so the error says the item
        moved and the commit did not.
        """
        self._warn_off_trunk(item)
        rel = [str(p.relative_to(self.store_git_root)) for p in (src, dst, *extra)]
        err = git_commit_result(self.store_git_root,
                                f"tcw work: {slug} → {to_status}", *rel)
        if err:
            raise TransitionCommitError(
                f"{slug} moved to {to_status}, but committing it failed:\n{err}")

    def _warn_off_trunk(self, item: "WorkItem | None") -> None:
        """`work.trunk-branch` is advisory: warn on a mismatch and commit where we
        are. TCW never checks out, never commits to another branch, and never
        refuses — that plumbing is not worth it for what is already an operator
        mistake worth surfacing.

        Suppressed inside a TCW-created worktree, detected by the *item's* own
        `branch` field rather than by probing the checkout: a `--worktree` item is
        supposed to be on `work/<slug>`, so warning there would fire constantly
        on the one workflow behaving correctly. Probing for a linked worktree
        would also catch worktrees TCW knows nothing about, which is not the case
        being excused.
        """
        trunk = self.trunk_branch()
        if not trunk:
            return
        current = git_current_branch(self.store_git_root)
        if current is None or current == trunk:
            return
        if item is not None and item.branch and item.branch == current:
            return                                     # a TCW work branch, as intended
        print(f"tcw work: on branch '{current}', but work.trunk-branch is "
              f"'{trunk}'; committing the transition here.", file=sys.stderr)

    def _delete(self, slug: str) -> None:
        d = self._require_dir(slug)
        self._rm(d)

    # -- revision-bearing detail + composite create/update --

    def get_detail(self, slug: str) -> "WorkDetail" | None:
        """A whole-snapshot read: item and every revision from one location.

        Composite, so it has a find-then-read window a transition can move the
        item through. Retried rather than guarded per-file, because the fix has
        to be all-or-nothing — pairing the first item with files re-read from its
        *new* status would hand out revisions that never coexisted, and a caller
        would then write against them.
        """
        for _ in range(5):
            try:
                return self._detail_snapshot(slug)
            except _Moved:
                continue                               # it went somewhere; look again
            except FileNotFoundError:
                continue                               # a path *inside* the item went
        return None

    def _detail_snapshot(self, slug: str) -> "WorkDetail" | None:
        item = self.get(slug)
        if item is None:
            return None
        d = self._find(slug)
        if d is None:                                  # moved out from under us
            raise _Moved
        # Core revision = state.yaml + *which* file the body resolved to + its
        # text. The name matters: promoting an intake to a request with identical
        # text changes the editable resource, and a revision that ignored the name
        # would let a guarded write succeed against a stale view of what it edits.
        state_text = (d / "state.yaml").read_text(encoding="utf-8")
        body_name, body_text = self._resolve_body(d)
        core_rev = _revision_multi(state_text, body_name or "", body_text)

        # Artifact revisions
        art_revs: dict[str, str] = {}
        for name in WORK_ARTIFACTS:
            p = d / self._artifact_filename(name)
            if p.is_file():
                art_revs[name] = _revision(p.read_text(encoding="utf-8"))

        # Sidecar revisions
        sc_revs: dict[str, str] = {}
        for sc_name, sc_info in WORK_SIDECARS.items():
            p = d / sc_name
            if p.is_file():
                sc_revs[sc_name] = _revision(p.read_text(encoding="utf-8"))

        return WorkDetail(
            item=item,
            core_revision=core_rev,
            artifact_revisions=art_revs,
            sidecar_revisions=sc_revs,
        )

    def create_work(self, title: str, *,
                    created: str | None = None,
                    body: str = "",
                    priority: int | None = None,
                    effort: str = "",
                    complexity: str = "",
                    blockers: list[str] | None = None,
                    parent: str | None = None,
                    initiative: str = "",
                    type: str = "",
                    tags: list[str] | None = None,
                    intake: str = "") -> "WorkDetail":
        """Composite create: all fields validated before any write."""
        self._require_repository()
        if not title:
            raise ValueError("title is required and must be non-empty")

        # Validate effort / complexity
        if effort and effort != "":
            effort = normalize_work_level(effort)
        if complexity and complexity != "":
            complexity = normalize_work_level(complexity)

        # Validate tags against the registered set (fail closed before any write)
        if tags is None:
            tag_list = []
        elif isinstance(tags, list):
            tag_list = self._validate_tags(tags)
        else:
            raise ValueError("tags must be a list or None")

        # Validate type
        if type and type != "epic":
            raise ValueError(f"invalid type '{type}' (only 'epic' is supported)")

        # Validate parent
        parent_dir: Path | None = None
        if parent:
            parent_dir = self._find(parent)
            if parent_dir is None:
                raise ValueError(f"no such parent work item: {parent}")

        # Resolve blockers
        blocked_by: list[dict] = []
        if blockers:
            for ref in blockers:
                if not isinstance(ref, str):
                    raise ValueError(
                        "blocker refs must be strings")
                blocked_by.append(self._entry_for(ref))

        # Generate slug. `created` arrives from a caller (`tcw serve`'s POST
        # body among them), and it prefixes the slug — parsing it bounds the
        # slug's own prefix and keeps a non-date out of `state.yaml`.
        created_date = date.fromisoformat(created).isoformat() if created \
            else date.today().isoformat()
        slug = self._unique_slug(created_date, title)

        # Determine directory
        if parent_dir:
            d = parent_dir / slug
        else:
            d = self.root / "backlog" / slug

        # Build state.yaml content
        state: dict = {
            "slug": slug,
            "title": title,
            "created": created_date,
            "resolution": None,
        }
        if priority is not None:
            state["priority"] = priority
        if effort:
            state["effort"] = effort
        if complexity:
            state["complexity"] = complexity
        if tag_list:
            state["tags"] = tag_list
        if blocked_by:
            state["blocked_by"] = blocked_by
        if initiative:
            state["initiative"] = initiative
        if type:
            state["type"] = type

        state_text = yaml.safe_dump(state, sort_keys=False, allow_unicode=True)

        # Only what the caller actually supplied gets a file. Creation used to
        # template a three-heading request unconditionally, which made every
        # item look like its `request` stage had run.
        written = {"state.yaml": state_text}
        if body:
            written["initial-request.md"] = body if body.endswith("\n") else body + "\n"
        if intake:
            written["intake.md"] = intake if intake.endswith("\n") else intake + "\n"

        # `mkdir` without `exist_ok` proves the directory did not exist, so the
        # rollback is unconditional — and a slug collision keeps raising
        # `FileExistsError`, which is how `_unique_slug` failures surface, so
        # this site keeps its bare `mkdir` rather than adopting `_mkdir_owned`.
        # `parents=True` may also have created an intermediate `backlog/`;
        # rollback removes only the leaf, and an empty `backlog/` is inert (git
        # does not track it, every read path tolerates it).
        d.mkdir(parents=True)
        self._write_staged([(d / name, content) for name, content in written.items()],
                           owned_dir=d)

        return _require_detail(self.get_detail(slug), "work item", slug)

    def update_work(self, slug: str, *,
                    title=_UNSET, body=_UNSET, priority=_UNSET,
                    effort=_UNSET, complexity=_UNSET, blockers=_UNSET,
                    initiative=_UNSET, parent=_UNSET, tags=_UNSET,
                    core_revision: str | None = None) -> "WorkDetail":
        """Partial-merge update with revision guard."""
        d = self._require_dir(slug)

        # Stale revision check
        if core_revision is not None:
            detail = self.get_detail(slug)
            if detail and detail.core_revision != core_revision:
                raise StaleRevision(
                    f"stale revision for work item '{slug}' "
                    f"(expected {core_revision}, got {detail.core_revision})")

        # Read current state. A body write always targets the request, never the
        # read fallback: following it would either mutate raw intake or quietly
        # satisfy the `request` stage with text the author meant as an edit.
        state = load_yaml(d / "state.yaml")
        body_path = d / "initial-request.md"
        had_request = self._present(body_path)
        body_text = body_path.read_text(encoding="utf-8") if body_path.exists() else ""

        # Validate effort / complexity before applying
        if effort is not _UNSET and effort is not None and effort != "":
            try:
                effort = normalize_work_level(effort)
            except ValueError:
                raise

        if complexity is not _UNSET and complexity is not None and complexity != "":
            try:
                complexity = normalize_work_level(complexity)
            except ValueError:
                raise

        # Validate tags before applying (fail closed on unregistered)
        new_tags = None
        if tags is not _UNSET:
            if tags is None:
                new_tags = []
            elif isinstance(tags, list):
                new_tags = self._validate_tags(tags)
            else:
                raise ValueError("tags must be a list or None")

        # Resolve blockers before applying
        new_blocked_by = None
        if blockers is not _UNSET:
            if blockers is None:
                new_blocked_by = []
            elif isinstance(blockers, list):
                for ref in blockers:
                    if not isinstance(ref, str):
                        raise ValueError(
                            "blocker refs must be strings")
                new_blocked_by = [self._entry_for(ref) for ref in blockers]
            else:
                raise ValueError("blockers must be a list or None")

        # Handle parent change: validate the target here, but effect the folder
        # move AFTER the state/body writes (below) so edits land in the current
        # location and the re-parent stays a single git-atomic rename that also
        # carries any nested children. Parent is derived from nesting, not stored.
        move_to: Path | None = None
        if parent is not _UNSET:
            if parent is None or parent == "":
                # Denest: move to top-level of the item's current status folder.
                new_parent_dir = self.root / self._status_of(d) / slug
            else:
                pd = self._find(parent)
                if pd is None:
                    raise ValueError(f"no such parent work item: {parent}")
                if pd.resolve() == d.resolve() or d.resolve() in pd.resolve().parents:
                    raise ValueError(
                        "cannot re-parent an item under itself or a descendant")
                new_parent_dir = pd / slug
            if new_parent_dir.resolve() != d.resolve():
                move_to = new_parent_dir

        # Apply field changes to state dict
        changed = False
        if title is not _UNSET:
            state["title"] = title if title is not None else ""
            changed = True
        if priority is not _UNSET:
            state["priority"] = priority  # None clears it
            changed = True
        if effort is not _UNSET:
            state["effort"] = effort if effort is not None else ""
            changed = True
        if complexity is not _UNSET:
            state["complexity"] = complexity if complexity is not None else ""
            changed = True
        if new_tags is not None:
            if new_tags:
                state["tags"] = new_tags
            else:
                state.pop("tags", None)          # omit when empty (like effort)
            changed = True
        if new_blocked_by is not None:
            state["blocked_by"] = new_blocked_by
            changed = True
        if initiative is not _UNSET:
            state["initiative"] = initiative if initiative is not None else ""
            changed = True

        # Apply body change
        if body is not _UNSET:
            body_text = body if body is not None else ""
            changed = True

        if not changed and parent is _UNSET:
            return _require_detail(self.get_detail(slug), "work item", slug)

        # Here rather than at the top of the method: the no-change return above
        # writes nothing, and guarding before it would turn a read-shaped call
        # into a refusal outside a repository.
        self._require_repository()

        # Write atomically
        state_text = yaml.safe_dump(state, sort_keys=False, allow_unicode=True)
        writes = [(d / "state.yaml", state_text)]
        if body is not _UNSET:
            writes.append((body_path, body_text))
        # `owned_dir=None`: the item directory already exists (`_require_dir`
        # resolved it), so a refused stage undoes only the files this call
        # created — `initial-request.md` when the item had no body — and leaves
        # the rewritten `state.yaml` with what this call wrote.
        self._write_staged(writes)

        # Effect the re-parent last: a git-aware folder rename that moves the
        # whole item directory (including any nested children) and stages it,
        # leaving no orphaned source directory.
        if move_to is not None:
            move_to.parent.mkdir(parents=True, exist_ok=True)
            self._mv(d, move_to)

        detail = _require_detail(self.get_detail(slug), "work item", slug)
        if body is not _UNSET and not had_request and bool(body_text.strip()):
            detail.promoted = True          # this write created the request
        return detail

    # -- artifact read / write --

    def read_artifact(self, slug: str, name: str) -> "ArtifactResource" | None:
        if name not in WORK_ARTIFACTS:
            raise ValueError(
                f"unknown artifact '{name}' "
                f"(choose from {', '.join(WORK_ARTIFACTS)})")
        d = self._require_dir(slug)
        p = d / self._artifact_filename(name)
        # Mere existence, not `_present`: this is the resource question, and a
        # blank artifact is a real resource. See `WorkStore.read_artifact`.
        if not (p.is_file() and self._within_store(p)):
            return None
        text = p.read_text(encoding="utf-8")
        return ArtifactResource(
            name=name,
            content=text,
            media_type="text/markdown",
            revision=_revision(text),
        )

    def write_artifact(self, slug: str, name: str, content: str,
                       revision: str | None = None) -> "ArtifactResource":
        self._require_repository()
        if name not in WORK_ARTIFACTS:
            raise ValueError(
                f"unknown artifact '{name}' "
                f"(choose from {', '.join(WORK_ARTIFACTS)})")
        d = self._require_dir(slug)
        p = d / self._artifact_filename(name)

        # Stale revision check
        if revision is not None:
            if p.is_file():
                current = _revision(p.read_text(encoding="utf-8"))
                if current != revision:
                    raise StaleRevision(
                        f"stale revision for artifact '{name}' of '{slug}' "
                        f"(expected {revision}, got {current})")
            else:
                # Artifact doesn't exist yet — revision should be empty
                if revision != "":
                    raise StaleRevision(
                        f"artifact '{name}' of '{slug}' does not exist yet "
                        f"(revision {revision} has no target)")

        self._write_staged([(p, content)])

        return ArtifactResource(
            name=name,
            content=content,
            media_type="text/markdown",
            revision=_revision(content),
        )

    def write_draft(self, slug: str, artifact: str, content: str, *,
                    force: bool = False) -> str:
        self._require_repository()
        if artifact not in WORK_ARTIFACTS:
            raise ValueError(
                f"unknown artifact '{artifact}' "
                f"(choose from {', '.join(WORK_ARTIFACTS)})")
        d = self._require_dir(slug)
        # The one place this filename shape exists. `artifacts()` looks up
        # `<name>.md` from the registry and never sees it, so presence stays
        # honest with no new machinery.
        p = d / f"{artifact}.draft.md"
        if not force and self._present(p):
            raise ValueError(
                f"a draft is already there: {p} — type into it, or pass "
                f"--force to replace it")
        self._write_staged([(p, content)])
        return str(p)

    def delete_artifact(self, slug: str, name: str) -> None:
        if name not in WORK_ARTIFACTS:
            raise ValueError(
                f"unknown artifact '{name}' "
                f"(choose from {', '.join(WORK_ARTIFACTS)})")
        p = self._require_dir(slug) / self._artifact_filename(name)
        if p.is_file():
            self._rm(p)

    # -- sidecar read / write --

    def read_sidecar(self, slug: str, name: str) -> "SidecarResource" | None:
        if name not in WORK_SIDECARS:
            raise ValueError(
                f"unknown sidecar '{name}' "
                f"(choose from {', '.join(WORK_SIDECARS.keys())})")
        d = self._require_dir(slug)
        p = d / name
        if not p.is_file():
            return None
        text = p.read_text(encoding="utf-8")
        sc_info = WORK_SIDECARS[name]
        return SidecarResource(
            name=name,
            content=text,
            media_type=sc_info["media_type"],
            revision=_revision(text),
        )

    def write_sidecar(self, slug: str, name: str, content: str,
                      media_type: str | None = None,
                      revision: str | None = None) -> "SidecarResource":
        self._require_repository()
        if name not in WORK_SIDECARS:
            raise ValueError(
                f"unknown sidecar '{name}' "
                f"(choose from {', '.join(WORK_SIDECARS.keys())})")
        d = self._require_dir(slug)
        p = d / name

        # Resolve media type
        sc_info = WORK_SIDECARS[name]
        mt = media_type or sc_info["media_type"]

        # Validate content against the registry rule
        validation = sc_info.get("validation")
        if validation == "yaml_mapping":
            try:
                parsed = yaml.safe_load(content)
                if parsed is not None and not isinstance(parsed, dict):
                    raise ValueError(
                        f"sidecar '{name}' must be a YAML mapping, "
                        f"got {type(parsed).__name__}")
            except yaml.YAMLError as e:
                raise ValueError(f"sidecar '{name}' is not valid YAML: {e}")

        # Stale revision check
        if revision is not None:
            if p.is_file():
                current = _revision(p.read_text(encoding="utf-8"))
                if current != revision:
                    raise StaleRevision(
                        f"stale revision for sidecar '{name}' of '{slug}' "
                        f"(expected {revision}, got {current})")
            else:
                if revision != "":
                    raise StaleRevision(
                        f"sidecar '{name}' of '{slug}' does not exist yet "
                        f"(revision {revision} has no target)")

        self._write_staged([(p, content)])

        return SidecarResource(
            name=name,
            content=content,
            media_type=mt,
            revision=_revision(content),
        )
