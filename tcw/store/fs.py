"""Filesystem store adapters + the FS-local helpers they share.

`git_root`/`init` (Phase 1) scaffold; `FsTaxonomyStore` (Phase 2) realizes the
`TaxonomyStore` interface over `docs/taxonomy/`. The capabilities and work
adapters land here in their phases; the genuinely-shared primitives get factored
into a tree-store core in Phase 4 (don't pre-abstract — AGENTS.md).
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
from pathlib import Path

import yaml

from tcw.store.base import (
    CAP_FIELDS, CAP_LIFECYCLES, CAP_PRIORITIES, CAP_STATUSES, DEFAULT_DOD,
    RESOLVED_STATUSES, TAXONOMY_EDITABLE_FIELDS, WORK_ARTIFACTS, WORK_SIDECARS,
    WORK_STATUSES, _UNSET, resolution_status,
    AmbiguousRef, Artifact, ArtifactResource, Capability, CapabilitiesStore,
    CapabilityDetail, MultipleMatch, RefError, AlreadyClaimed, IllegalTransition,
    InboxEntry, InboxEntryDetail, InboxResource, PlanStage, PlanStageResource,
    LifecyclePolicy, SidecarResource, StaleRevision, TransitionCommitError,
    parse_lifecycle_policy,
    TaxonomyStore, Term, TermDetail,
    WorkDetail, WorkItem, WorkStore, normalize_tag, normalize_work_level,
)
from tcw.store.project import FsProjectRegistry, validate_project_id, worktree_anchors

# Component trees `tcw init` scaffolds. `work` gets a status-folder skeleton;
# `taxonomy` and `capabilities` are flat trees that fill in per their phases.
COMPONENTS = ("taxonomy", "capabilities", "work")


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

def git_root(start: Path | None = None) -> Path | None:
    """Top of the git work-tree containing `start` (cwd by default), or None.

    Shells out to git so worktrees/submodules resolve correctly — more correct
    on edge cases than walking up looking for a literal `.git` dir.
    """
    start = (start or Path.cwd()).resolve()
    try:
        out = subprocess.run(
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
    """The node owning `docs/<component>/`, or None. A node is the nearest
    ancestor marked by a `tcw-config.yaml` sentinel (FS-adapter-local). Returns
    the node iff it has that component, preserving the prior contract."""
    nr = find_node_root(start)
    if nr is None:
        return None
    FsProjectRegistry.open(nr).require_valid()
    if component != "work":
        return nr if (nr / "docs" / component).is_dir() else None
    try:
        FsWorkStore.open(nr)
    except ValueError:
        return None
    return nr


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
    if (node_root / "docs" / "work").is_dir():
        return True
    try:
        FsWorkStore.open(node_root)
        return True
    except ValueError:
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


def git_stage(node_root: Path, *paths: Path) -> None:
    """Stage paths, dropping any git ignores. Ignored status folders are the
    default (see `resolved_ignore_rules`), so a write into `completed/` has
    nothing to stage — and `git add` on an ignored path fails outright rather
    than no-opping."""
    live = [str(p) for p in paths if not git_ignored(node_root, p)]
    if live:
        subprocess.run(["git", "-C", str(node_root), "add", "--", *live], check=True)


def git_rm(node_root: Path, path: Path) -> None:
    # -f so a term staged-but-not-yet-committed (just `add`ed) can still be removed.
    subprocess.run(["git", "-C", str(node_root), "rm", "-rfq", "--", str(path)], check=True)


def git_ignored(node_root: Path, path: Path) -> bool:
    """Whether `.gitignore` excludes `path`. False outside a repository."""
    return subprocess.run(
        ["git", "-C", str(node_root), "check-ignore", "-q", "--", str(path)],
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
        # --ignore-unmatch: an item created but never committed is not in the
        # index at all, and that is not an error here. -f: the transition stages
        # the item's own state before moving it, so the index legitimately
        # differs from both HEAD and the worktree, which `rm` otherwise refuses.
        # With --cached it still only touches the index; the files stay on disk.
        subprocess.run(["git", "-C", str(node_root), "rm", "-rqf", "--cached",
                        "--ignore-unmatch", "--", str(src)], check=True)
        shutil.move(str(src), str(dst))
        return
    subprocess.run(["git", "-C", str(node_root), "add", "--", str(src)], check=True)
    subprocess.run(["git", "-C", str(node_root), "mv", "--", str(src), str(dst)], check=True)


WORKTREES_DIR = ".worktrees"

def git_commit(node_root: Path, message: str, *paths: str) -> None:
    """Commit staged changes. With paths, a scoped (partial) commit so unrelated
    staged changes are left alone — used by start --worktree (Spec 2 §3.4)."""
    cmd = ["git", "-C", str(node_root), "commit", "-q", "-m", message]
    if paths:
        cmd += ["--", *paths]
    subprocess.run(cmd, check=True)


def _has_committable_changes(node_root: Path, path: str) -> bool:
    """Whether `path` has changes a scoped commit would actually record.

    Untracked (`??`) entries are excluded: a scoped `git commit -- <paths>`
    records tracked content only, so a pathspec holding nothing else has nothing
    to commit — and calling `git commit` anyway produces a benign failure that
    would then be misreported as a real one. Callers wanting untracked content
    committed stage it first, which is what `git_mv` already does.
    """
    r = subprocess.run(
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
    if subprocess.run(["git", "-C", str(node_root), "rev-parse", "--git-dir"],
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
    r = subprocess.run(
        ["git", "-C", str(node_root), "commit", "-q", "-m", message, "--", *live],
        capture_output=True, text=True)
    if r.returncode != 0:
        return (r.stderr or r.stdout).strip() or f"git commit failed ({r.returncode})"
    return None


def git_current_branch(node_root: Path) -> str | None:
    """The checked-out branch name, or None outside a repo / on a detached HEAD."""
    r = subprocess.run(["git", "-C", str(node_root), "rev-parse", "--abbrev-ref", "HEAD"],
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


def ensure_worktree_ignored(node_root: Path) -> None:
    """Add `.worktrees/` to the node's .gitignore (a linked worktree dir is
    untracked otherwise and would clutter/be staged). Idempotent; stages it."""
    if ensure_ignored(node_root, f"{WORKTREES_DIR}/"):
        git_stage(node_root, node_root / ".gitignore")


def add_worktree(node_root: Path, slug: str) -> tuple[Path, str]:
    """Create the item's git worktree + branch from HEAD. Returns (path, branch)."""
    wt = node_root / WORKTREES_DIR / slug
    branch = f"work/{slug}"
    subprocess.run(["git", "-C", str(node_root), "worktree", "add", "-q",
                    "-b", branch, str(wt)], check=True)
    return wt, branch


def merge_worktree(node_root: Path, branch: str) -> str | None:
    """Merge the work branch into the primary checkout's current branch — the
    "merge-back on complete" half of the split-ownership model. Runs *before* the
    active→completed rename so the merge sees the item docs still under
    `active/<slug>/` (no rename/modify overlap). Fail closed: a missing branch is
    a quiet no-op (e.g. a recovery re-run), any merge failure aborts the
    half-merge and returns an error so teardown is skipped and the branch is left
    intact. Returns None on success, else an error message."""
    if subprocess.run(["git", "-C", str(node_root), "rev-parse", "--verify", "--quiet",
                       f"refs/heads/{branch}"], capture_output=True).returncode != 0:
        return None                                   # branch already gone — nothing to merge
    r = subprocess.run(["git", "-C", str(node_root), "merge", "--no-edit", branch],
                       capture_output=True, text=True)
    if r.returncode != 0:
        subprocess.run(["git", "-C", str(node_root), "merge", "--abort"],
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
    r = subprocess.run(["git", "-C", str(node_root), "worktree", "remove", str(wt)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        if "is not a working tree" not in r.stderr:   # already absent — tolerate quietly
            warns.append(f"worktree remove failed for {slug}: {r.stderr.strip()}")
    elif branch:
        rb = subprocess.run(["git", "-C", str(node_root), "branch", "-D", branch],
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
         work_path: Path | None = None) -> list[Path]:
    """Scaffold `docs/<component>/` skeletons under `root` and mark it a node.
    Returns leaf dirs made. A `.gitkeep` lands in each leaf so the empty skeleton
    survives a commit (git doesn't track empty directories).

    Scaffolding `work` also gitignores the resolved status folders, so completing
    or discarding an item takes it *out* of the tracked tree instead of
    accumulating it there — `git_mv` untracks rather than moves when the
    destination is ignored. Unstaged, like everything else init writes.
    """
    write_sentinel(root, project_id)
    existing_config = load_yaml(root / SENTINEL, unique=True)
    if work_path is None and "work" in components:
        configured_work = existing_config.get("work") or {}
        if isinstance(configured_work, dict) and configured_work.get("path"):
            work_path = Path(configured_work["path"]).expanduser()
    if work_path is not None and "work" in components:
        default_root = root / "docs" / "work"
        target = work_path if work_path.is_absolute() else root / work_path
        if default_root.exists() and default_root.resolve() != target.resolve():
            expected = {"inbox", *WORK_STATUSES}
            actual = {entry.name for entry in default_root.iterdir()}
            pristine = actual == expected and all(
                child.is_dir() and {entry.name for entry in child.iterdir()} <= {".gitkeep"}
                for child in default_root.iterdir()
            )
            if not pristine:
                raise ValueError(
                    f"refusing to replace non-pristine {default_root}; move existing work "
                    "manually, update work.path, then re-run init"
                )
            shutil.rmtree(default_root)
        config_path = root / SENTINEL
        config = load_yaml(config_path, unique=True)
        work_config = config.get("work") if isinstance(config.get("work"), dict) else {}
        config["work"] = {**work_config, "path": str(work_path)}
        dump_yaml(config_path, config)
    created: list[Path] = []
    for c in components:
        base = ((work_path if work_path.is_absolute() else root / work_path)
                if c == "work" and work_path is not None else root / "docs" / c)
        leaves = [base / "inbox", *(base / s for s in WORK_STATUSES)] if c == "work" else [base]
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


def _atomic_write(path: Path, content: str) -> None:
    """Write *content* to *path* via temp-file + atomic replace.

    Cleans up the temp file on failure.  The caller is responsible for staging
    the result with ``_stage()``.
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def _atomic_write_all(pairs: list[tuple[Path, str]]) -> None:
    """Write several files as one unit: stage every temp, then promote each.

    `pairs` is `(target path, content)` in promote order. The failure class this
    closes is content production — ENOSPC, EACCES, a serialization error — which
    can only happen in the staging phase, before anything is promoted, so the
    targets are left untouched. One handler spans both phases and unlinks every
    temp, so no `.tmp` is left beside a real file in the user's git tree.
    `BaseException` matches `_atomic_write`: a `KeyboardInterrupt` mid-batch
    still cleans up.

    # ponytail: the promote loop is not atomic across files — a process death
    # between two replace() calls still leaves a partial update. Upgrade path is
    # a journal or a whole-directory swap (the `accept_inbox` shape, fs.py:2246);
    # neither is worth its cost for the failure class actually reachable here.
    """
    staged = [(p.with_suffix(p.suffix + ".tmp"), p, c) for p, c in pairs]
    try:
        for tmp, _, content in staged:
            tmp.write_text(content, encoding="utf-8")
        for tmp, path, _ in staged:
            tmp.replace(path)
    except BaseException:
        for tmp, _, _ in staged:
            tmp.unlink(missing_ok=True)
        raise


# ── Shared tree-store core (Phase 4) ─────────────────────────────────────────

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

    def __init__(self, root: Path):
        self.root = root                       # docs/<component>/
        self.node_root = root.parent.parent    # repo root
        self.config = load_yaml(root / self.CONFIG_NAME) if self.CONFIG_NAME else {}

    @classmethod
    def open(cls, node_root: Path):
        return cls(node_root / "docs" / cls.COMPONENT)

    def _stage(self, *paths: Path) -> None:
        git_stage(self.node_root, *paths)

    def _rm(self, path: Path) -> None:
        git_rm(self.node_root, path)

    def _mv(self, src: Path, dst: Path) -> None:
        git_mv(self.node_root, src, dst)

    # -- shared folder-node anatomy (meta.yaml + description.md + attachments) --
    #
    # A "node" is a folder holding a `meta.yaml` (named fields), a
    # `description.md` (the body), and zero or more named attachment files. Both
    # the taxonomy and capabilities adapters realize their items this way; the
    # read/write mechanics live here so they are defined once. (Abstract spine:
    # body + named fields + named attachments — bounded, never globbed open.)

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
        meta = load_yaml(d / "meta.yaml")
        desc = d / "description.md"
        description = desc.read_text(encoding="utf-8") if desc.exists() else ""
        reserved = self._node_reserved()
        attachments = sorted(
            f.name for f in d.iterdir()
            if f.is_file() and f.name not in reserved and not f.name.startswith("."))
        return meta, description, attachments

    def _write_node(self, d: Path, meta: dict, description: str) -> None:
        """Create/overwrite a folder node's meta + description, atomically, staged.

        **Callers wrapping this in a rollback:** it stages internally, so your
        `except` also catches a `git add` failure that happened *after* both
        files landed. Key the rollback on whether content landed (`meta.yaml`
        exists) rather than on who created the directory, or you will delete
        files that were written fine. Same applies to `_write_meta`.
        """
        existed = d.exists()
        d.mkdir(parents=True, exist_ok=True)
        try:
            _atomic_write_all([
                (d / "meta.yaml",
                 yaml.safe_dump(meta, sort_keys=False, allow_unicode=True)),
                (d / "description.md", description),
            ])
        except BaseException:
            # Only roll back a directory we created; on an existing node the
            # staging phase is the protection. `ignore_errors=True` so a
            # rollback that cannot proceed never masks the real failure.
            #
            # ponytail: `existed` is TOCTOU-racy — a second writer creating the
            # node between our check and our failure would get its directory
            # removed here. Closing it needs an ownership signal that survives
            # the check-to-write gap (a create-only `mkdir(exist_ok=False)`, or
            # a lock), which is the design of the separate
            # `2026-06-22-concurrency-safe-work-claims-for-multi-agent-repos`
            # item — building it here would be that item, half-done, in the
            # wrong place.
            if not existed:
                shutil.rmtree(d, ignore_errors=True)
            raise
        # Staging stays outside the rollback: a git failure after both files
        # landed leaves a fully valid object on disk, and deleting it would
        # destroy content the caller just wrote.
        self._stage(d / "meta.yaml", d / "description.md")


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

    def __init__(self, root: Path, _seen: set[Path] | None = None):
        super().__init__(root)
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
        return self._term(slug) if (self.root / slug).is_dir() else None

    def _local_slugs(self) -> list[str]:
        return sorted(
            str(p.relative_to(self.root)) for p in self.root.rglob("*") if p.is_dir())

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
        if d.exists():
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
        dump_yaml(cfg, self.config)
        self._stage(cfg)

    def extends_remove(self, project_id: str) -> None:
        extends = _extends_ids(self.config, self.root / self.CONFIG_NAME)
        if project_id not in extends:
            raise ValueError(f"no such extends project: {project_id}")
        extends.remove(project_id)
        if extends:
            self.config["extends"] = extends
        else:
            self.config.pop("extends", None)
        cfg = self.root / "config.yaml"
        dump_yaml(cfg, self.config)
        self._stage(cfg)

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
        if local_folder.is_dir():
            folder = local_folder
        else:
            term = self.get(identifier)
            if term is None:
                return []
            owner = (
                self if term.origin == "local"
                else self._inherited_stores()[term.origin]
            )
            folder = owner.root / term.slug
        return [path for path in (folder / "meta.yaml", folder / "description.md")
                if path.is_file()]

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
        meta_text = (d / "meta.yaml").read_text(encoding="utf-8")
        desc_text = (d / "description.md").read_text(encoding="utf-8")
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
        meta = load_yaml(d / "meta.yaml")
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
        return self.get_term_detail(ref)


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

    def __init__(self, root: Path, _seen: set[Path] | None = None):
        super().__init__(root)
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
        for fn in _as_list(meta.get("prependedDocs")):
            f = d / fn
            if f.is_file():
                parts.append(f.read_text(encoding="utf-8").strip())
        if raw_desc.strip():
            parts.append(raw_desc.strip())
        for fn in _as_list(meta.get("appendedDocs")):
            f = d / fn
            if f.is_file():
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
        up_desc = self.extends[alias].root / base.path / "description.md"
        upstream_raw = up_desc.read_text(encoding="utf-8") if up_desc.exists() else ""
        child_desc = d / "description.md"
        child_raw = child_desc.read_text(encoding="utf-8") if child_desc.exists() else ""
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
        return self._capability(path) if path and self._is_capability(self.root / path) \
            and not load_yaml(self.root / path / "meta.yaml").get("overrides") else None

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

    def add(self, identifier, name=None, status="Missing", body="") -> Capability:
        path = _safe_store_id(identifier, "path")
        if status not in CAP_STATUSES:
            raise ValueError(f"invalid Status '{status}' "
                             f"(choose: {', '.join(sorted(CAP_STATUSES))})")
        d = self.root / path
        if d.exists():
            raise ValueError(f"capability already exists: {path}")
        display = name or path.rsplit("/", 1)[-1].replace("-", " ").title()
        meta = {"id": _mint_cap_id(), "name": display, "Status": status}
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
        return out

    def _write_meta(self, d: Path, meta: dict) -> None:
        # Stages internally — see the rollback warning on `_write_node`.
        _atomic_write(d / "meta.yaml",
                      yaml.safe_dump(meta, sort_keys=False, allow_unicode=True))
        self._stage(d / "meta.yaml")

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
        norm = self._validate_fields(fields)           # validate before touching disk
        d, meta, is_override = self._write_target(identifier)
        existed = d.exists()
        d.mkdir(parents=True, exist_ok=True)           # _write_meta does not mkdir
        try:
            self._write_meta(d, self._merge_meta(meta, norm, is_override))
        except BaseException:
            # `_write_target` can materialize a *fresh* override directory, so a
            # failed write would otherwise leave an empty one behind. Same guard
            # as `update_capability`: roll back only a directory this call made,
            # and only when nothing landed — `_write_meta` stages internally, so
            # a failed `git add` must not delete a `meta.yaml` written fine.
            if not existed and not (d / "meta.yaml").exists():
                shutil.rmtree(d, ignore_errors=True)
            raise
        return self.get(identifier)                    # the composed (post-merge) entry

    # -- federation config --

    def extends_add(self, project_id: str) -> None:
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
        dump_yaml(cfg, self.config)
        self._stage(cfg)

    def extends_remove(self, project_id: str) -> None:
        extends = _extends_ids(self.config, self.root / self.CONFIG_NAME)
        if project_id not in extends:
            raise ValueError(f"no such extends project: {project_id}")
        extends.remove(project_id)
        if extends:
            self.config["extends"] = extends
        else:
            self.config.pop("extends", None)
        cfg = self.root / self.CONFIG_NAME
        dump_yaml(cfg, self.config)
        self._stage(cfg)

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

    def check(self, taxonomy=None, identifier: str | None = None) -> list[str]:
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
            if "Superseded by" in f and (e := self._ref_error(str(f["Superseded by"]))):
                problems.append(f"{where}: Superseded by → {e}")
            if "Blocked by" in f and (e := self._ref_error(str(f["Blocked by"]))):
                problems.append(f"{where}: Blocked by → {e}")
            problems += self._check_globals(where, f)
            problems += self._check_subject(where, f, taxonomy)
            problems += self._check_feature(where, f, taxonomy)

        # Override + attachment validation (every meta dir, incl. override folders).
        meta_dirs = self._all_meta_dirs()
        if selected is not None:
            meta_dirs = [selected.path]
        for p in meta_dirs:
            d = self.root / p
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
        if (local_folder / "meta.yaml").is_file():
            folder = local_folder
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
        return [folder / name for name in names if (folder / name).is_file()]

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

    def _ref_error(self, identifier: str) -> str | None:
        try:
            if self.get(identifier) is None:
                return f"dangling identifier '{identifier}'"
        except AmbiguousRef:
            return f"ambiguous identifier '{identifier}'"
        return None

    def _check_globals(self, where, f) -> list[str]:
        out = []
        for ns, field in (("roles", "Roles"), ("conditions", "When")):
            raw = f.get(field, "")
            toks = raw if isinstance(raw, list) else str(raw).split(",")
            for tok in (str(s).strip() for s in toks if str(s).strip()):
                ref = tok.lstrip("!")
                if not ref.startswith(f"{ns}/"):
                    out.append(f"{where}: {field} '{tok}' must be a {ns}/ slug")
                elif (e := self._ref_error(ref)):
                    out.append(f"{where}: {field} → {e}")
        return out

    def _check_subject(self, where, f, taxonomy) -> list[str]:
        subjects = _as_list(f.get("Subject"))
        if not subjects or taxonomy is None:
            return []
        out = []
        for subj in subjects:
            try:
                if taxonomy.get(subj) is None:
                    out.append(f"{where}: Subject → dangling ref '{subj}'")
            except AmbiguousRef:
                out.append(f"{where}: Subject → ambiguous ref '{subj}'")
        return out

    def _check_feature(self, where, f, taxonomy) -> list[str]:
        feature = f.get("Feature")
        if not feature or taxonomy is None:
            return []
        try:
            target = taxonomy.get(feature)
        except AmbiguousRef:
            return [f"{where}: Feature → ambiguous ref '{feature}'"]
        if target is None:
            return [f"{where}: Feature → dangling ref '{feature}'"]
        if target.kind != "Feature":
            return [f"{where}: Feature → ref '{feature}' points to "
                    f"{target.kind}, expected Feature"]
        return []

    # -- revision-bearing detail + update --

    def _node_texts(self, d: Path) -> list[str]:
        """A folder node's [meta, description] texts; empty strings when absent."""
        return [f.read_text(encoding="utf-8") if f.is_file() else ""
                for f in (d / "meta.yaml", d / "description.md")]

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

        existed = d.exists()
        d.mkdir(parents=True, exist_ok=True)   # _write_meta does not mkdir
        try:
            if is_override and not desc_text.strip():
                # An override's description.md is a *body delta*, and an empty one
                # means "no delta" — `_apply_override` falls back to the upstream
                # body (which is what makes append-only overrides work). So clearing
                # an override's body drops the delta and re-inherits, rather than
                # leaving an empty file that silently means the same thing.
                desc.unlink(missing_ok=True)
                self._write_meta(d, meta)
                self._stage(d)                 # picks up the removal
            elif body is _UNSET and not desc.exists():
                self._write_meta(d, meta)      # pure delta — no empty body file
            else:
                self._write_node(d, meta, desc_text)
        except BaseException:
            # The rollback has to live here, not in `_write_node`: we made the
            # directory, so `_write_node`'s own `existed` is True by the time it
            # runs, and the two `_write_meta` branches roll nothing back at all.
            # Fresh-override materialization is the path this covers. Same
            # `ignore_errors=True` and TOCTOU caveats as `_write_node`.
            #
            # Keyed on whether content actually landed, not just on who made the
            # directory: staging runs *inside* this guard (via `_write_node`),
            # and a failed `git add` must not delete files that were written
            # fine — the rest of this change is careful never to destroy content
            # the caller just wrote. A content failure promotes nothing, so
            # `meta.yaml` being absent is exactly "nothing landed".
            if not existed and not (d / "meta.yaml").exists():
                shutil.rmtree(d, ignore_errors=True)
            raise
        return self.get_capability_detail(identifier)


# ── FsWorkStore ──────────────────────────────────────────────────────────────

class FsWorkStore(FsTreeStore, WorkStore):
    """`WorkStore` over `docs/work/` — the filesystem-as-state-machine (Phase 5).

    Status is the top-level status folder an item lives under; a transition is a
    `git mv` of the item folder. The stable id is the slug; an item folder is any
    dir holding a `state.yaml`, found at any nesting depth — a child item is a
    folder nested inside its parent's (the node relation, derived from nesting).
    """
    COMPONENT = "work"

    def __init__(self, root: Path, *, node_root: Path | None = None,
                 store_git_root: Path | None = None):
        self.root = root.resolve()
        self.node_root = (node_root or root.parent.parent).resolve()
        self.store_git_root = (store_git_root or git_root(self.root) or self.node_root).resolve()
        self.config = {}

    @classmethod
    def open(cls, node_root: Path) -> "FsWorkStore":
        node_root = node_root.resolve()
        config_path = node_root / SENTINEL
        config = load_yaml(config_path, unique=True)
        work = config.get("work") or {} if isinstance(config, dict) else {}
        if not isinstance(work, dict):
            work = {}
        configured = work.get("path")
        if configured is not None and (not isinstance(configured, str) or not configured.strip()):
            raise ValueError(f"{config_path}: work.path must be a non-empty path string")
        if configured is None:
            raw_root = node_root / "docs" / "work"
        else:
            value = Path(configured).expanduser()
            base = node_root
            anchors = worktree_anchors(node_root)
            if not value.is_absolute() and anchors is not None:
                base = anchors[1]
            raw_root = value if value.is_absolute() else base / value
        if raw_root.is_symlink() and not raw_root.exists():
            raise ValueError(f"{config_path}: work.path is a broken symlink: {raw_root}")
        if not raw_root.is_dir():
            raise ValueError(f"{config_path}: work.path is not a directory: {raw_root}")
        root = raw_root.resolve()
        missing = [name for name in ("inbox", *WORK_STATUSES) if not (root / name).is_dir()]
        if missing:
            raise ValueError(f"{config_path}: work.path is not a work store; missing: {', '.join(missing)}")
        repository = node_root if configured is None else git_root(root)
        if repository is None and configured is not None:
            raise ValueError(f"{config_path}: work.path is not inside a Git repository: {root}")
        return cls(root, node_root=node_root, store_git_root=repository or node_root)

    def _stage(self, *paths: Path) -> None:
        git_stage(self.store_git_root, *paths)

    def _rm(self, path: Path) -> None:
        git_rm(self.store_git_root, path)

    def _mv(self, src: Path, dst: Path) -> None:
        git_mv(self.store_git_root, src, dst)

    # -- discovery (state.yaml-keyed, depth-agnostic) --

    def _item_dirs(self) -> list[Path]:
        """Every item folder (dir with a `state.yaml`), at any depth. Sorted by
        path so a parent precedes its children."""
        return sorted(
            p.parent
            for status in WORK_STATUSES
            for p in (self.root / status).rglob("state.yaml")
        )

    def start(self, slug: str, force: bool = False, *, owner: str = "",
              take_over: bool = False) -> WorkItem:
        """Publish a stamped backlog claim with a single atomic source rename."""
        item = self._require(slug)
        started = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        if item.status == "active":
            if not take_over:
                raise AlreadyClaimed(slug, item.owner, item.started)
            if not owner:
                raise ValueError("takeover requires an owner")
            self.set_field(slug, "owner", owner)
            self.set_field(slug, "started", started)
            if self.auto_commit_transitions():
                rel = str(self._find(slug).relative_to(self.store_git_root))
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
            os.replace(src, private)
        except FileNotFoundError:
            for _ in range(50):
                current = self.get(slug)
                if current is not None and current.status == "active":
                    raise AlreadyClaimed(slug, current.owner, current.started)
                time.sleep(0.01)
            raise ValueError(f"{slug} has an interrupted claim; use --take-over --owner <identity>")
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
        return self._require(slug)

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
        matches = [d for d in self._item_dirs() if d.name == slug]
        if len(matches) > 1:
            raise MultipleMatch(f"slug resolves to {len(matches)} items: {slug}")
        return matches[0] if matches else None

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

    def body_path(self, slug: str) -> Path | None:
        d = self._find(slug)                          # initial-request.md: FS realization of body surface
        return d / "initial-request.md" if d is not None else None

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
            out.append(Artifact(
                name=name,
                present=p.is_file() and bool(p.read_text(encoding="utf-8").strip()),
            ))
        return out

    def artifact_locator(self, slug: str, name: str) -> str | None:
        if name not in WORK_ARTIFACTS:
            return None
        d = self._find(slug)
        if d is None:
            return None
        return str(d / self._artifact_filename(name))

    @staticmethod
    def _plan_manifest(content: str) -> list[dict] | None:
        if not content.startswith("---\n"):
            return None
        end = content.find("\n---\n", 4)
        if end < 0:
            raise ValueError("plan.md: malformed YAML frontmatter")
        try:
            metadata = yaml.safe_load(content[4:end])
        except yaml.YAMLError as exc:
            raise ValueError(f"plan.md: malformed YAML frontmatter: {exc}") from exc
        if metadata is None:
            return None
        if not isinstance(metadata, dict):
            raise ValueError("plan.md: frontmatter must be a mapping")
        if "stages" not in metadata:
            return None
        stages = metadata["stages"]
        if not isinstance(stages, list):
            raise ValueError("plan.md: stages must be a list")
        return stages

    def _declared_plan_stages(self, slug: str) -> list[PlanStage]:
        d = self._find(slug)
        if d is None:
            raise ValueError(f"no such work item: {slug}")
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
        return self._find(slug) / "plan" / f"{stage_id}.md"

    def read_plan_stage(self, slug: str, stage_id: str) -> PlanStageResource | None:
        path = self._plan_stage_path(slug, stage_id)
        if not path.is_file():
            return None
        content = path.read_text(encoding="utf-8")
        return PlanStageResource(stage_id, content, revision=_revision(content))

    def write_plan_stage(self, slug: str, stage_id: str, content: str,
                         revision: str | None = None) -> PlanStageResource:
        if not isinstance(content, str):
            raise ValueError("stage content must be text")
        path = self._plan_stage_path(slug, stage_id)
        if revision is not None:
            current = _revision(path.read_text(encoding="utf-8")) if path.is_file() else ""
            if current != revision:
                raise StaleRevision(f"stale revision for plan stage '{stage_id}' of '{slug}'")
        path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write(path, content)
        self._stage(path)
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
        base = f"{created}-{slugify(title)}"
        slug, n = base, 2
        while self._find(slug) is not None:
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

    def _item_from_dir(self, d: Path) -> WorkItem:
        state = self._safe_yaml(d / "state.yaml")
        request = d / "initial-request.md"
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
            body=request.read_text(encoding="utf-8") if request.exists() else "",
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

    def get(self, slug: str) -> WorkItem | None:
        d = self._find(slug)
        return self._item_from_dir(d) if d is not None else None

    def query(self, status: str | None = None) -> list[WorkItem]:
        items = [self._item_from_dir(d) for d in self._item_dirs()]
        return [i for i in items if status is None or i.status == status]

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

    def lifecycle_problems(self) -> list[str]:
        """Policy problems, prefixed with the file they came from — for `check`."""
        _policy, problems = parse_lifecycle_policy(self._work_config().get("lifecycle"))
        return [f"{SENTINEL}: {p}" for p in problems]

    def trunk_branch(self) -> str | None:
        """The branch transitions are expected to land on, or None when unset.
        Advisory only — TCW warns and commits where it is."""
        value = self._work_config().get("trunk-branch")
        return value.strip() or None if isinstance(value, str) else None

    def _write_tags(self, tags: set[str]) -> list[str]:
        """Read-modify-write `work.tags` (preserving other config keys), stage
        the file. `dump_yaml` rewrites the sentinel wholesale, dropping its stub
        comments — accepted per plan."""
        config = self._config()
        work = config.get("work")
        if not isinstance(work, dict):
            work = {}
        result = sorted(tags)
        work["tags"] = result
        config["work"] = work
        dump_yaml(self._config_path(), config)
        self._stage(self._config_path())
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
                    folder = self._find(item.slug)
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
        the resolution, so no code path can produce a disagreement — but the
        filesystem adapter stores status as a folder, and a hand-run `mv` or a
        bad merge can. This is the detector for that, not a second source of
        truth."""
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
        resources = [folder / name for name in names if (folder / name).is_file()]
        plan_folder = folder / "plan"
        if plan_folder.is_dir():
            resources.extend(sorted(plan_folder.glob("*.md")))
        return resources

    # -- raw inbox intake (separate from formal WorkItem status) --

    @property
    def inbox_root(self) -> Path:
        return self.root / "inbox"

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
        detail, _primary = self._inbox_detail(ref)
        return detail

    def inbox_accept(self, ref: str, title: str | None = None) -> WorkItem:
        source = self._inbox_path(ref)
        detail, primary = self._inbox_detail(ref)
        accepted_title = (title or detail.entry.title).strip()
        if not accepted_title:
            raise ValueError("title is required and must be non-empty")
        created = date.today().isoformat()
        slug = self._unique_slug(created, accepted_title)
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
                    manifest.append("initial-request.md")
                else:
                    manifest.append(f"attachments/{name}")
                    attachments.append((name, path))
        manifest = sorted(manifest)
        origin = primary or source.name
        manifest_lines = []
        for name in manifest:
            suffix = f" — accepted from `{origin}`" if name == "initial-request.md" else ""
            manifest_lines.append(f"- `{name}`{suffix}")
        body = detail.body if detail.body is not None else "Binary intake preserved as an attachment."
        request = (
            f"# {accepted_title}\n\n## Product changes\n\nTBD\n\n"
            "## Technical changes\n\nTBD\n\n## Meta changes\n\nTBD\n\n"
            "## Inbox contents\n\n### Inbox manifest\n\n"
            + "\n".join(manifest_lines) + "\n\n### Inbox body\n\n" + body
        )
        if not request.endswith("\n"):
            request += "\n"
        temp = Path(tempfile.mkdtemp(prefix=f".{slug}-", dir=self.root / "backlog"))
        try:
            state = {"slug": slug, "title": accepted_title,
                     "created": created, "resolution": None}
            dump_yaml(temp / "state.yaml", state)
            (temp / "initial-request.md").write_text(request, encoding="utf-8")
            for name, path in attachments:
                target = temp / "attachments" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target, follow_symlinks=False)
            os.replace(temp, destination)
            self._stage(destination)
            tracked = subprocess.run(
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
               priority: int | None = None, parent: str | None = None) -> WorkItem:
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
                                priority=priority, parent=parent).item

    def set_field(self, slug: str, key: str, value) -> None:
        d = self._find(slug)
        if d is None:
            raise ValueError(f"no such work item: {slug}")
        state = load_yaml(d / "state.yaml")
        state[key] = value
        dump_yaml(d / "state.yaml", state)
        self._stage(d / "state.yaml")

    def _effect_transition(self, slug: str, to_status: str) -> None:
        # Read the item *before* the move: afterwards `_find` points at the new
        # location and the pre-move branch/worktree fields are what the
        # trunk-branch check needs.
        item = self.get(slug)
        src = self._find(slug)
        # Nodes created before a status existed have no folder for it, and
        # `git mv` refuses when the destination's parent is missing. Creating it
        # here is an adapter detail with no abstract analog (the prime directive
        # sends "ensure a directory exists" straight into the adapter), and it is
        # status-agnostic on purpose: it also repairs a hand-deleted folder
        # rather than special-casing whichever status was added last.
        (self.root / to_status).mkdir(parents=True, exist_ok=True)
        dst = self.root / to_status / slug
        self._mv(src, dst)
        if self.auto_commit_transitions():
            self._commit_transition(slug, src, dst, to_status, item)

    def _commit_transition(self, slug: str, src: Path, dst: Path,
                           to_status: str, item: "WorkItem | None") -> None:
        """Commit the status move, scoped to the two folders it touched.

        Scoped to `src` and `dst` rather than the whole work root: a scoped
        `git commit -- <paths>` takes *working-tree* state, so a broad pathspec
        would sweep every other item's uncommitted edits into a status commit.

        The move is never rolled back on a commit failure. The `git mv` already
        landed in both the index and the working tree, and undoing it introduces
        a second failure mode worse than the first — so the error says the item
        moved and the commit did not.
        """
        self._warn_off_trunk(item)
        rel = [str(p.relative_to(self.store_git_root)) for p in (src, dst)]
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
        d = self._find(slug)
        if d is None:
            raise ValueError(f"no such work item: {slug}")
        self._rm(d)

    # -- revision-bearing detail + composite create/update --

    def get_detail(self, slug: str) -> "WorkDetail" | None:
        item = self.get(slug)
        if item is None:
            return None
        d = self._find(slug)
        # Core revision = hash of state.yaml + body (initial-request.md)
        state_text = (d / "state.yaml").read_text(encoding="utf-8")
        body_path = d / "initial-request.md"
        body_text = body_path.read_text(encoding="utf-8") if body_path.exists() else ""
        core_rev = _revision_multi(state_text, body_text)

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
                    tags: list[str] | None = None) -> "WorkDetail":
        """Composite create: all fields validated before any write."""
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

        # Generate slug
        created_date = created or date.today().isoformat()
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

        # Build body content
        body_content = (
            f"# {title}\n\n## Product changes\n\n## Technical changes\n\n## Meta changes\n\n"
            f"{body}\n"
        )

        # Write atomically (both files must succeed). `mkdir` without
        # `exist_ok` proves the directory did not exist, so the rollback is
        # unconditional. `ignore_errors=True` is deliberate: if the rollback
        # itself cannot proceed the caller still sees the real failure, at the
        # price of a leftover directory. `parents=True` may also have created an
        # intermediate `backlog/`; rollback removes only the leaf, and an empty
        # `backlog/` is inert (git does not track it, every read path tolerates
        # it). Staging stays outside — see `_write_node`.
        d.mkdir(parents=True)
        try:
            _atomic_write(d / "state.yaml", state_text)
            _atomic_write(d / "initial-request.md", body_content)
        except BaseException:
            shutil.rmtree(d, ignore_errors=True)
            raise
        self._stage(d / "state.yaml", d / "initial-request.md")

        return self.get_detail(slug)

    def update_work(self, slug: str, *,
                    title=_UNSET, body=_UNSET, priority=_UNSET,
                    effort=_UNSET, complexity=_UNSET, blockers=_UNSET,
                    initiative=_UNSET, parent=_UNSET, tags=_UNSET,
                    core_revision: str | None = None) -> "WorkDetail":
        """Partial-merge update with revision guard."""
        d = self._find(slug)
        if d is None:
            raise ValueError(f"no such work item: {slug}")

        # Stale revision check
        if core_revision is not None:
            detail = self.get_detail(slug)
            if detail and detail.core_revision != core_revision:
                raise StaleRevision(
                    f"stale revision for work item '{slug}' "
                    f"(expected {core_revision}, got {detail.core_revision})")

        # Read current state
        state = load_yaml(d / "state.yaml")
        body_path = d / "initial-request.md"
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
            return self.get_detail(slug)

        # Write atomically
        state_text = yaml.safe_dump(state, sort_keys=False, allow_unicode=True)
        writes = [(d / "state.yaml", state_text)]
        if body is not _UNSET:
            writes.append((body_path, body_text))
        # No directory rollback: the item directory already exists, so the
        # staging phase is the protection.
        _atomic_write_all(writes)

        self._stage(d / "state.yaml")
        if body is not _UNSET:
            self._stage(body_path)

        # Effect the re-parent last: a git-aware folder rename that moves the
        # whole item directory (including any nested children) and stages it,
        # leaving no orphaned source directory.
        if move_to is not None:
            move_to.parent.mkdir(parents=True, exist_ok=True)
            self._mv(d, move_to)

        return self.get_detail(slug)

    # -- artifact read / write --

    def read_artifact(self, slug: str, name: str) -> "ArtifactResource" | None:
        if name not in WORK_ARTIFACTS:
            raise ValueError(
                f"unknown artifact '{name}' "
                f"(choose from {', '.join(WORK_ARTIFACTS)})")
        d = self._find(slug)
        if d is None:
            raise ValueError(f"no such work item: {slug}")
        p = d / self._artifact_filename(name)
        if not p.is_file():
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
        if name not in WORK_ARTIFACTS:
            raise ValueError(
                f"unknown artifact '{name}' "
                f"(choose from {', '.join(WORK_ARTIFACTS)})")
        d = self._find(slug)
        if d is None:
            raise ValueError(f"no such work item: {slug}")
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

        _atomic_write(p, content)
        self._stage(p)

        return ArtifactResource(
            name=name,
            content=content,
            media_type="text/markdown",
            revision=_revision(content),
        )

    # -- sidecar read / write --

    def read_sidecar(self, slug: str, name: str) -> "SidecarResource" | None:
        if name not in WORK_SIDECARS:
            raise ValueError(
                f"unknown sidecar '{name}' "
                f"(choose from {', '.join(WORK_SIDECARS.keys())})")
        d = self._find(slug)
        if d is None:
            raise ValueError(f"no such work item: {slug}")
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
        if name not in WORK_SIDECARS:
            raise ValueError(
                f"unknown sidecar '{name}' "
                f"(choose from {', '.join(WORK_SIDECARS.keys())})")
        d = self._find(slug)
        if d is None:
            raise ValueError(f"no such work item: {slug}")
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

        _atomic_write(p, content)
        self._stage(p)

        return SidecarResource(
            name=name,
            content=content,
            media_type=mt,
            revision=_revision(content),
        )
