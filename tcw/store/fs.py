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
import tempfile
import uuid
from datetime import date
from pathlib import Path

import yaml

from tcw.store.base import (
    CAP_FIELDS, CAP_LIFECYCLES, CAP_PRIORITIES, CAP_STATUSES, DEFAULT_DOD,
    TAXONOMY_EDITABLE_FIELDS, WORK_ARTIFACTS, WORK_SIDECARS, WORK_STATUSES, _UNSET,
    AmbiguousRef, Artifact, ArtifactResource, Capability, CapabilitiesStore,
    CapabilityDetail, MultipleMatch, RefError,
    InboxEntry, InboxEntryDetail, InboxResource, SidecarResource, StaleRevision,
    TaxonomyStore, Term, TermDetail,
    WorkDetail, WorkItem, WorkStore, normalize_tag, normalize_work_level,
)
from tcw.store.project import FsProjectRegistry, validate_project_id

# Component trees `tcw init` scaffolds. `work` gets a status-folder skeleton;
# `taxonomy` and `capabilities` are flat trees that fill in per their phases.
COMPONENTS = ("taxonomy", "capabilities", "work")


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
    return nr if (nr / "docs" / component).is_dir() else None


def child_nodes(root: Path) -> list[Path]:
    """Direct registered children that contain a work store."""
    registry = FsProjectRegistry.open(root).require_valid()
    return [
        Path(project.locator)
        for project in registry.children()
        if (Path(project.locator) / "docs" / "work").is_dir()
    ]


def parent_node(root: Path) -> Path | None:
    """Direct registered parent that contains a work store."""
    registry = FsProjectRegistry.open(root).require_valid()
    parent = registry.parent()
    if parent is None:
        return None
    path = Path(parent.locator)
    return path if (path / "docs" / "work").is_dir() else None


def descendant_nodes(root: Path) -> list[Path]:
    """All registered descendants that contain a work store."""
    registry = FsProjectRegistry.open(root).require_valid()
    return [
        Path(project.locator)
        for project in registry.descendants()
        if (Path(project.locator) / "docs" / "work").is_dir()
    ]


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
    'sub/proj/<slug>'       -> (descendant-node store, <slug>)  [cross-node addressing]

    A leading segment in `WORK_STATUSES` marks a status-path locator (the path a
    board/`work path` prints): the last segment is the bare slug, intermediate
    segments are ignored, and the status segment must equal the item's real
    status (else the ref doesn't resolve). This is addressing sugar — the slug
    stays the identity. (A subproject literally named after a status is not
    addressable via the bare status-prefix form; use its slug.)

    The qualifier is the descendant node's path relative to `anchor`. A slug never
    contains '/' (slugify -> [a-z0-9-]), so the final '/'-segment is always the
    bare slug and everything before it the qualifier — unambiguous. If that
    invariant changes, revisit this split.

    Returns None when the qualifier is not a real node genuinely inside `anchor`:
    an unknown path, a traversal/absolute/symlink *escape*, or a path through
    `.git`/`.worktrees` (a `start --worktree` checkout copies the sentinel, so it
    would otherwise look like a real node the board never emits). Equivalent to
    `cd`-ing into the node, so it belongs in the FS adapter, not the abstract
    store — cross-node addressing realized over the filesystem tree.
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
    descendants = {project.id: project for project in registry.descendants()}
    target_project = descendants.get(qualifier)
    if target_project is None:
        return None
    target = Path(target_project.locator)
    if not (target / "docs" / "work").is_dir():
        return None
    return FsWorkStore.open(target), bare


def git_stage(node_root: Path, *paths: Path) -> None:
    subprocess.run(["git", "-C", str(node_root), "add", "--", *map(str, paths)], check=True)


def git_rm(node_root: Path, path: Path) -> None:
    # -f so a term staged-but-not-yet-committed (just `add`ed) can still be removed.
    subprocess.run(["git", "-C", str(node_root), "rm", "-rfq", "--", str(path)], check=True)


def git_mv(node_root: Path, src: Path, dst: Path) -> None:
    """Move a tracked path, staging the rename. Untracked contents are staged
    first so `git mv` doesn't orphan them (the transition mechanic — Phase 5)."""
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


def ensure_worktree_ignored(node_root: Path) -> None:
    """Add `.worktrees/` to the node's .gitignore (a linked worktree dir is
    untracked otherwise and would clutter/be staged). Idempotent; stages it."""
    gi = node_root / ".gitignore"
    line = f"{WORKTREES_DIR}/"
    existing = gi.read_text(encoding="utf-8") if gi.exists() else ""
    if line not in existing.splitlines():
        gi.write_text((existing.rstrip("\n") + "\n" if existing else "") + line + "\n",
                      encoding="utf-8")
        git_stage(node_root, gi)


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


def init(components: list[str], root: Path, project_id: str | None = None) -> list[Path]:
    """Scaffold `docs/<component>/` skeletons under `root` and mark it a node.
    Returns leaf dirs made. A `.gitkeep` lands in each leaf so the empty skeleton
    survives a commit (git doesn't track empty directories)."""
    write_sentinel(root, project_id)
    created: list[Path] = []
    for c in components:
        base = root / "docs" / c
        leaves = [base / "inbox", *(base / s for s in WORK_STATUSES)] if c == "work" else [base]
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
        """Create/overwrite a folder node's meta + description, atomically, staged."""
        d.mkdir(parents=True, exist_ok=True)
        _atomic_write(d / "meta.yaml",
                      yaml.safe_dump(meta, sort_keys=False, allow_unicode=True))
        _atomic_write(d / "description.md", description)
        self._stage(d / "meta.yaml", d / "description.md")


# ── FsTaxonomyStore ─────────────────────────────────────────────────────────

_TAX_RESERVED = {"config.yaml", "meta.yaml", "description.md"}
TAXONOMY_KINDS = {"Vocabulary", "Feature"}


def _normalize_taxonomy_kind(kind: str | None) -> str:
    if not kind:
        return "Vocabulary"
    by_lower = {k.lower(): k for k in TAXONOMY_KINDS}
    return by_lower.get(str(kind).lower(), str(kind))


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
        )

    def get_local(self, slug: str) -> Term | None:
        return self._term(slug) if slug and (self.root / slug).is_dir() else None

    def _local_slugs(self) -> list[str]:
        return sorted(
            str(p.relative_to(self.root)) for p in self.root.rglob("*") if p.is_dir())

    def list_all(self, local_only: bool = False) -> list[Term]:
        terms = [self._term(s) for s in self._local_slugs()]
        if not local_only:
            for alias, st in self.extends.items():
                terms += [self._term_via(st, s, alias) for s in st._local_slugs()]
        return terms

    @staticmethod
    def _term_via(store: "FsTaxonomyStore", slug: str, alias: str) -> Term:
        return store._term(slug, origin=alias)

    def get(self, ref: str) -> Term | None:
        head, _, rest = ref.partition("/")
        if head in self.extends:                       # prefixed (B.6.1)
            return self.get_inherited(head, rest)
        local = self.get_local(ref)                    # bare-wins-local (B.6.2)
        if local is not None:
            return local
        matches = [(a, t) for a, st in self.extends.items()
                   if (t := st.get_local(ref)) is not None]
        if len(matches) == 1:
            return self._term_via(self.extends[matches[0][0]], ref, matches[0][0])
        if len(matches) > 1:
            raise AmbiguousRef(ref)
        return None

    def get_inherited(self, alias: str, slug: str) -> Term | None:
        st = self.extends.get(alias)
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
        meta = {"name": name, "kind": kind, "relatesTo": []}
        if vocabulary:
            meta["vocabulary"] = list(vocabulary)
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

    def check(self) -> list[str]:
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
            if project_id in top_level:
                problems.append(
                    f"project ID '{project_id}' collides with local top-level term"
                )

        for term in self.list_all(local_only=True):
            if term.kind not in TAXONOMY_KINDS:
                problems.append(f"{term.slug}: unknown kind '{term.kind}'")
            for ref in term.relates_to:
                try:
                    if self.get(ref) is None:
                        problems.append(f"{term.slug}: dangling relatesTo ref '{ref}'")
                except AmbiguousRef:
                    problems.append(f"{term.slug}: ambiguous relatesTo ref '{ref}'")
            if term.kind == "Feature":
                if not term.vocabulary:
                    problems.append(f"{term.slug}: Feature requires at least one vocabulary ref")
                for ref in term.vocabulary:
                    try:
                        target = self.get(ref)
                    except AmbiguousRef:
                        problems.append(f"{term.slug}: ambiguous vocabulary ref '{ref}'")
                        continue
                    if target is None:
                        problems.append(f"{term.slug}: dangling vocabulary ref '{ref}'")
                    elif target.kind != "Vocabulary":
                        problems.append(f"{term.slug}: vocabulary ref '{ref}' "
                                        f"points to {target.kind}, expected Vocabulary")
        return problems

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
        owner = self if term.origin == "local" else self.extends[term.origin]
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
            try:
                if self.get(r) is None:
                    raise ValueError(
                        f"relatesTo ref '{r}' does not resolve")
            except AmbiguousRef:
                raise ValueError(f"relatesTo ref '{r}' is ambiguous")
        if meta.get("kind", "Vocabulary") == "Feature":
            vocs = meta.get("vocabulary", [])
            if not vocs:
                raise ValueError("Feature requires at least one vocabulary ref")
            for r in vocs:
                try:
                    target = self.get(r)
                except AmbiguousRef:
                    raise ValueError(f"vocabulary ref '{r}' is ambiguous")
                if target is None:
                    raise ValueError(f"vocabulary ref '{r}' does not resolve")
                if target.kind != "Vocabulary":
                    raise ValueError(
                        f"vocabulary ref '{r}' points to {target.kind}, "
                        f"expected Vocabulary")

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
        d.mkdir(parents=True, exist_ok=True)           # _write_meta does not mkdir
        self._write_meta(d, self._merge_meta(meta, norm, is_override))
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

    def check(self, taxonomy=None) -> list[str]:
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

        seen_ids: dict[str, str] = {}
        for cap in self.list_all(local_only=True):
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
            problems += self._check_globals(where, f)
            problems += self._check_subject(where, f, taxonomy)
            problems += self._check_feature(where, f, taxonomy)

        # Override + attachment validation (every meta dir, incl. override folders).
        for p in self._all_meta_dirs():
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

        d.mkdir(parents=True, exist_ok=True)
        if is_override and not desc_text.strip():
            # An override's description.md is a *body delta*, and an empty one
            # means "no delta" — `_apply_override` falls back to the upstream
            # body (which is what makes append-only overrides work). So clearing
            # an override's body drops the delta and re-inherits, rather than
            # leaving an empty file that silently means the same thing.
            desc.unlink(missing_ok=True)
            self._write_meta(d, meta)
            self._stage(d)                     # picks up the removal
        elif body is _UNSET and not desc.exists():
            self._write_meta(d, meta)          # pure delta — no empty body file
        else:
            self._write_node(d, meta, desc_text)
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

    # -- discovery (state.yaml-keyed, depth-agnostic) --

    def _item_dirs(self) -> list[Path]:
        """Every item folder (dir with a `state.yaml`), at any depth. Sorted by
        path so a parent precedes its children."""
        return sorted(
            p.parent
            for status in WORK_STATUSES
            for p in (self.root / status).rglob("state.yaml")
        )

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
            phase=state.get("phase", ""),
            created=state.get("created", ""),
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
        )

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

    def check(self) -> list[str]:
        registered = set(self.registered_tags())
        problems: list[str] = []
        for item in self.query():
            for tag in item.tags:
                if tag not in registered:
                    problems.append(f"{item.slug}: unregistered tag '{tag}'")
        return problems

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
            state = {"slug": slug, "title": accepted_title, "phase": "",
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
                ["git", "-C", str(self.node_root), "ls-files", "--error-unmatch", "--", str(source)],
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
        created = created or date.today().isoformat()
        slug = self._unique_slug(created, title)
        if parent:
            pd = self._find(parent)
            if pd is None:
                raise ValueError(f"no such parent work item: {parent}")
            d = pd / slug                          # child nests inside the parent
        else:
            d = self.root / "backlog" / slug
        d.mkdir(parents=True)
        (d / "initial-request.md").write_text(
            f"# {title}\n\n## Product changes\n\n## Technical changes\n\n## Meta changes\n\n"
            f"{body}\n", encoding="utf-8")
        dump_yaml(d / "state.yaml", {
            "slug": slug, "title": title, "phase": "", "created": created,
            "resolution": None, "priority": priority})
        self._stage(d / "initial-request.md", d / "state.yaml")
        return self.get(slug)

    def set_field(self, slug: str, key: str, value) -> None:
        d = self._find(slug)
        if d is None:
            raise ValueError(f"no such work item: {slug}")
        state = load_yaml(d / "state.yaml")
        state[key] = value
        dump_yaml(d / "state.yaml", state)
        self._stage(d / "state.yaml")

    def _effect_transition(self, slug: str, to_status: str) -> None:
        self._mv(self._find(slug), self.root / to_status / slug)

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
            "phase": "",
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

        # Write atomically (both files must succeed)
        d.mkdir(parents=True)
        _atomic_write(d / "state.yaml", state_text)
        _atomic_write(d / "initial-request.md", body_content)
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
        _atomic_write(d / "state.yaml", state_text)
        if body is not _UNSET:
            _atomic_write(body_path, body_text)

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
