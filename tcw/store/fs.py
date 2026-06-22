"""Filesystem store adapters + the FS-local helpers they share.

`git_root`/`init` (Phase 1) scaffold; `FsTaxonomyStore` (Phase 2) realizes the
`TaxonomyStore` interface over `docs/taxonomy/`. The capabilities and work
adapters land here in their phases; the genuinely-shared primitives get factored
into a tree-store core in Phase 4 (don't pre-abstract — AGENTS.md).
"""

import re
import subprocess
from datetime import date
from pathlib import Path

import yaml

from tcw.store.base import (
    CAP_FIELDS, CAP_LIFECYCLES, CAP_PRIORITIES, CAP_STATUSES, DEFAULT_DOD,
    AmbiguousRef, Capability, CapabilitiesStore, CapabilityFile, Collision,
    MultipleMatch, RefError, TaxonomyStore, Term, WorkItem, WorkStore,
)

# Component trees `tcw init` scaffolds. `work` gets a status-folder skeleton;
# `taxonomy` and `capabilities` are flat trees that fill in per their phases.
COMPONENTS = ("taxonomy", "capabilities", "work")
WORK_STATUSES = ("inbox", "backlog", "active", "completed")


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


def find_node(component: str, start: Path | None = None) -> Path | None:
    """The node (git work-tree root) that owns `docs/<component>/`, or None.

    ponytail: the single-node tools resolve to the enclosing repo root and check
    for `docs/<component>/`. Walking *across* nested git repos to a different
    node is the cross-node concern (Phase 6) — not needed here.
    """
    root = git_root(start)
    if root is None:
        return None
    return root if (root / "docs" / component).is_dir() else None


def _git_common_dir(path: Path) -> Path | None:
    """Absolute shared `.git` dir for the repo containing `path` (None if outside
    a work-tree). A linked worktree resolves to its MAIN repo's `.git`; a
    standalone repo resolves to its own — the basis for excluding own worktrees.
    --path-format=absolute is required: the default is cwd-relative and would
    mis-compare (Spec 2 §3.1)."""
    try:
        out = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--path-format=absolute",
             "--git-common-dir"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return Path(out).resolve()


def child_nodes(root: Path) -> list[Path]:
    """Nearest descendant nodes (git work-tree + docs/work/) under `root`.

    Descent stops at each found node (its children are its own — A.2). Excludes
    `root`'s own linked worktrees: a candidate whose git-common-dir equals
    `root`'s is the same logical node, not a child. FS-adapter-local.
    ponytail: shells out per dir and walks the whole tree — fine for a docs
    repo; prune by .gitignore only if it ever bites.
    """
    root = root.resolve()
    own_common = _git_common_dir(root)
    found: list[Path] = []

    def walk(d: Path) -> None:
        for child in sorted(p for p in d.iterdir() if p.is_dir() and p.name != ".git"):
            top = git_root(child)
            is_node = (top is not None and top.resolve() == child.resolve()
                       and (child / "docs" / "work").is_dir())
            if is_node and _git_common_dir(child) != own_common:
                found.append(child)        # genuine child node — don't descend
            else:
                walk(child)                # plain subdir or our own worktree
    walk(root)
    return found


def parent_node(root: Path) -> Path | None:
    """Nearest ancestor node above `root`, or None. FS-adapter-local."""
    root = root.resolve()
    search = git_root(root.parent)
    while search is not None:
        search = search.resolve()
        if search != root and (search / "docs" / "work").is_dir():
            return search
        nxt = git_root(search.parent)      # climb above this enclosing repo
        if nxt is None or nxt.resolve() == search:
            return None
        search = nxt
    return None


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


def init(components: list[str], root: Path) -> list[Path]:
    """Scaffold `docs/<component>/` skeletons under `root`. Returns leaf dirs made.

    A `.gitkeep` lands in each leaf so the empty skeleton survives a commit
    (git doesn't track empty directories).
    """
    created: list[Path] = []
    for c in components:
        base = root / "docs" / c
        leaves = [base / s for s in WORK_STATUSES] if c == "work" else [base]
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


# ── FsTaxonomyStore ─────────────────────────────────────────────────────────

_TAX_RESERVED = {"config.yaml", "meta.yaml", "description.md"}


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
        for alias, repo_path in (self.config.get("extends") or {}).items():
            ext = (self.node_root / repo_path / "docs" / "taxonomy").resolve()
            if ext.is_dir() and ext not in seen:        # broken/cyclic → check() reports
                self.extends[alias] = FsTaxonomyStore(ext, _seen=seen)

    # -- reads --

    def _term(self, slug: str, origin: str = "local") -> Term:
        d = self.root / slug
        meta = load_yaml(d / "meta.yaml")
        desc = (d / "description.md")
        attachments = sorted(
            f.name for f in d.iterdir()
            if f.is_file() and f.name not in _TAX_RESERVED and not f.name.startswith("."))
        return Term(
            slug=slug,
            name=meta.get("name") or slug.rsplit("/", 1)[-1].replace("-", " ").title(),
            description=desc.read_text(encoding="utf-8") if desc.exists() else "",
            relates_to=list(meta.get("relatesTo") or []),
            attachments=attachments,
            origin=origin,
        )

    def get_local(self, slug: str) -> Term | None:
        return self._term(slug) if slug and (self.root / slug).is_dir() else None

    def _local_slugs(self) -> list[str]:
        return sorted(
            str(p.relative_to(self.root)) for p in self.root.rglob("*") if p.is_dir())

    def list(self, local_only: bool = False) -> list[Term]:
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
        return [t for t in self.list()
                if q in t.name.lower() or q in t.description.lower()]

    # -- writes --

    def add(self, name: str, slug: str | None = None, parent: str | None = None,
            description: str = "") -> Term:
        leaf = slug or slugify(name)
        full = f"{parent.strip('/')}/{leaf}" if parent else leaf
        if parent and not (self.root / parent).is_dir():
            raise ValueError(f"parent term does not exist: {parent}")
        d = self.root / full
        if d.exists():
            raise ValueError(f"term already exists: {full}")
        d.mkdir(parents=True)
        dump_yaml(d / "meta.yaml", {"name": name, "relatesTo": []})
        (d / "description.md").write_text(description, encoding="utf-8")
        self._stage(d / "meta.yaml", d / "description.md")
        return self._term(full)

    def remove(self, ref: str) -> None:
        term = self.get(ref)
        if term is None:
            raise ValueError(f"no such term: {ref}")
        if term.origin != "local":
            raise ValueError(f"cannot remove inherited term '{term.qualified}' "
                             f"(edit it at its source)")
        self._rm(self.root / term.slug)

    def relators(self, slug: str) -> list[str]:
        """Local term slugs whose `relatesTo` points at `slug` (for rm warnings)."""
        return [t.slug for t in self.list(local_only=True)
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
        for alias, repo_path in (self.config.get("extends") or {}).items():
            ext_repo = self.node_root / repo_path
            ext_tax = ext_repo / "docs" / "taxonomy"
            if not ext_repo.exists():
                problems.append(f"extends '{alias}': path does not exist: {repo_path}")
            elif not ext_tax.is_dir():
                problems.append(f"extends '{alias}': no docs/taxonomy/ under {repo_path}")
            elif self._cycles(ext_tax.resolve(), {self.root.resolve()}):
                problems.append(f"extends '{alias}': cycle in taxonomy federation")
            if alias in top_level:
                problems.append(f"alias '{alias}' collides with local top-level term")

        for term in self.list(local_only=True):
            for ref in term.relates_to:
                try:
                    if self.get(ref) is None:
                        problems.append(f"{term.slug}: dangling relatesTo ref '{ref}'")
                except AmbiguousRef:
                    problems.append(f"{term.slug}: ambiguous relatesTo ref '{ref}'")
        return problems

    def _cycles(self, taxonomy_root: Path, seen: set[Path]) -> bool:
        if taxonomy_root in seen:
            return True
        if not taxonomy_root.is_dir():
            return False
        cfg = load_yaml(taxonomy_root / "config.yaml")
        node_root = taxonomy_root.parent.parent
        for _alias, p in (cfg.get("extends") or {}).items():
            nxt = (node_root / p / "docs" / "taxonomy").resolve()
            if self._cycles(nxt, seen | {taxonomy_root}):
                return True
        return False


# ── FsCapabilitiesStore ──────────────────────────────────────────────────────

_CAP_SIDECARS = {"errors.md", "states.md"}
_FIELD_RE = re.compile(r"^\*\*([^:*]+):\*\*\s*(.*)$")
_IDENT_RE = re.compile(r"^(?P<path>[^#\[\]]+?)(?:\[(?P<state>[^\]]+)\])?(?:#(?P<heading>[\w-]+))?$")


def heading_slug(text: str) -> str:
    """GitHub-flavored heading anchor: lowercased, punctuation stripped, spaces→'-'."""
    s = re.sub(r"[^\w\s-]", "", text.strip().lower())
    return re.sub(r"\s+", "-", s)


def parse_capability_file(file_id: str, text: str) -> CapabilityFile:
    """Parse `# Title` + one-or-more `## name` capabilities (inline `**Field:**` block + body)."""
    title = next((ln[2:].strip() for ln in text.splitlines() if ln.startswith("# ")), file_id)
    caps: list[Capability] = []
    for block in re.split(r"(?m)^##\s+", text)[1:]:
        lines = block.splitlines()
        name = lines[0].strip()
        fields: dict[str, str] = {}
        idx = 1
        while idx < len(lines):
            m = _FIELD_RE.match(lines[idx].strip())
            if not m:
                break
            fields[m.group(1).strip()] = m.group(2).strip()
            idx += 1
        body = "\n".join(lines[idx:]).strip()
        caps.append(Capability(file_id, name, heading_slug(name), fields, body))
    return CapabilityFile(file_id, title, caps)


def _set_inline_fields(text: str, target_slug: str, fields: dict[str, str]) -> str:
    """Update-or-insert `**K:** V` lines in the metadata run of the `## <name>`
    block whose heading_slug == target_slug. The run is the consecutive
    `_FIELD_RE` lines right after the heading; inserts land at its end (or right
    after the heading when empty), never keyed off a blank line — so the body and
    sibling blocks are untouched (Spec 3 §3.1)."""
    lines = text.splitlines()
    hi = next((i for i, ln in enumerate(lines)
               if ln.startswith("## ") and heading_slug(ln[3:].strip()) == target_slug), None)
    if hi is None:
        raise RefError(f"heading '#{target_slug}' not found")
    run_end, existing = hi + 1, {}
    while run_end < len(lines):
        fm = _FIELD_RE.match(lines[run_end].strip())
        if not fm:
            break
        existing[fm.group(1).strip()] = run_end
        run_end += 1
    remaining = dict(fields)
    for k in list(remaining):
        if k in existing:
            lines[existing[k]] = f"**{k}:** {remaining.pop(k)}"
    lines[run_end:run_end] = [f"**{k}:** {v}" for k, v in remaining.items()]
    out = "\n".join(lines)
    return out + "\n" if text.endswith("\n") else out


class FsCapabilitiesStore(FsTreeStore, CapabilitiesStore):
    """`CapabilitiesStore` over the bounded `docs/capabilities/` tree (Phase 3 B.3)."""
    COMPONENT = "capabilities"
    CONFIG_NAME = ".config.yaml"

    # -- resolution --

    def _state_prefixes(self) -> tuple[str, str]:
        sc = self.config.get("state-conventions") or {}
        return sc.get("with", "with-"), sc.get("without", "without-")

    def _resolve_file(self, path: str, state: str | None) -> Path | None:
        folder = self.root / path
        flat = self.root / f"{path}.md"
        entry = folder / "capabilities.md"
        if state and state != "*":
            with_p, without_p = self._state_prefixes()
            neg = state.startswith("!")
            prefix, base = (without_p, state[1:]) if neg else (with_p, state)
            vf = folder / f"{prefix}{base}.md"
            if not vf.is_file():
                raise RefError(f"no state variant: {path}[{state}]")
            return vf
        if flat.is_file() and entry.is_file():
            raise Collision(path)
        if flat.is_file():
            return flat
        if entry.is_file():
            return entry
        return None

    def _disk_id(self, path: Path) -> str:
        rel = path.relative_to(self.root)
        return str(rel.parent) if path.name == "capabilities.md" else str(rel)[:-3]

    def _is_variant(self, p: Path) -> bool:
        if not (p.parent / "capabilities.md").is_file():
            return False
        with_p, without_p = self._state_prefixes()
        return p.name.startswith(with_p) or p.name.startswith(without_p)

    def _cap_files(self, include_variants: bool = False) -> list[Path]:
        out = []
        for p in sorted(self.root.rglob("*.md")):
            if p.name in _CAP_SIDECARS:
                continue
            if p.name != "capabilities.md" and self._is_variant(p) and not include_variants:
                continue
            out.append(p)
        return out

    # -- reads --

    def get(self, identifier: str) -> CapabilityFile | None:
        m = _IDENT_RE.match(identifier)
        if not m:
            raise RefError(f"malformed identifier: {identifier}")
        fp = self._resolve_file(m.group("path"), m.group("state"))
        if fp is None:
            return None
        return parse_capability_file(self._disk_id(fp), fp.read_text(encoding="utf-8"))

    def list(self, status: str | None = None, namespace: str | None = None) -> list[Capability]:
        caps: list[Capability] = []
        for p in self._cap_files():
            for c in parse_capability_file(self._disk_id(p), p.read_text(encoding="utf-8")).capabilities:
                if status and c.status != status:
                    continue
                if namespace and c.file_id.split("/")[0] != namespace:
                    continue
                caps.append(c)
        return caps

    def search(self, query: str) -> list[Capability]:
        q = query.lower()
        caps: list[Capability] = []
        for p in self._cap_files(include_variants=True):
            for c in parse_capability_file(self._disk_id(p), p.read_text(encoding="utf-8")).capabilities:
                if q in c.name.lower() or q in c.body.lower():
                    caps.append(c)
        return caps

    # -- writes --

    def add(self, identifier: str, name: str | None = None, status: str = "Missing",
            body: str = "", folder: bool = False) -> CapabilityFile:
        path = _IDENT_RE.match(identifier).group("path")
        folder_dir = self.root / path
        flat = self.root / f"{path}.md"
        entry = folder_dir / "capabilities.md"
        if flat.is_file() or entry.is_file():
            raise ValueError(f"capability already exists: {path}")
        if folder and flat.is_file():
            raise ValueError(f"flat/folder collision: {path}.md exists")
        if not folder and folder_dir.is_dir():
            raise ValueError(f"flat/folder collision: folder {path}/ exists")
        target = entry if folder else flat
        target.parent.mkdir(parents=True, exist_ok=True)
        subject = path.rsplit("/", 1)[-1].replace("-", " ").title()
        target.write_text(
            f"# {subject} — capabilities\n\n## {name or subject}\n"
            f"**Status:** {status}\n\n{body}\n", encoding="utf-8")
        self._stage(target)
        return parse_capability_file(self._disk_id(target), target.read_text(encoding="utf-8"))

    def remove(self, identifier: str) -> None:
        fp = self._resolve_file(*_IDENT_RE.match(identifier).group("path", "state"))
        if fp is None:
            raise ValueError(f"no such capability: {identifier}")
        self._rm(fp.parent if fp.name == "capabilities.md" else fp)

    def set(self, identifier: str, fields: dict[str, str]) -> Capability:
        for k, v in fields.items():
            if k not in CAP_FIELDS:
                raise ValueError(f"unknown field '{k}' (not in the locked vocabulary)")
            if k == "Status" and v not in CAP_STATUSES:
                raise ValueError(f"invalid Status '{v}' "
                                 f"(choose: {', '.join(sorted(CAP_STATUSES))})")
        m = _IDENT_RE.match(identifier)
        if not m:
            raise RefError(f"malformed identifier: {identifier}")
        fp = self._resolve_file(m.group("path"), m.group("state"))
        if fp is None:
            raise ValueError(f"no such capability: {identifier}")
        text = fp.read_text(encoding="utf-8")
        cf = parse_capability_file(self._disk_id(fp), text)
        heading = m.group("heading")
        if heading:
            match = next((c for c in cf.capabilities if c.heading_slug == heading), None)
            if match is None:
                raise RefError(f"no heading '#{heading}' in {self._disk_id(fp)}")
        elif len(cf.capabilities) != 1:
            raise RefError(f"{identifier} resolves to {len(cf.capabilities)} "
                           f"capabilities; specify #heading")
        else:
            match = cf.capabilities[0]
        new_text = _set_inline_fields(text, match.heading_slug, fields)
        fp.write_text(new_text, encoding="utf-8")
        self._stage(fp)
        updated = parse_capability_file(self._disk_id(fp), new_text)
        return next(c for c in updated.capabilities if c.heading_slug == match.heading_slug)

    # -- validation --

    def _ref_error(self, identifier: str) -> str | None:
        m = _IDENT_RE.match(identifier)
        if not m:
            return f"malformed identifier '{identifier}'"
        try:
            fp = self._resolve_file(m.group("path"), m.group("state"))
        except Collision:
            return f"flat/folder collision at '{identifier}'"
        except RefError as e:
            return str(e)
        if fp is None:
            return f"dangling identifier '{identifier}'"
        heading = m.group("heading")
        if heading:
            cf = parse_capability_file(m.group("path"), fp.read_text(encoding="utf-8"))
            if not any(c.heading_slug == heading for c in cf.capabilities):
                return f"no heading '#{heading}' in '{m.group('path')}'"
        return None

    def check(self, taxonomy: TaxonomyStore | None = None) -> list[str]:
        problems: list[str] = []
        # flat/folder collisions
        for entry in self.root.rglob("capabilities.md"):
            if entry.parent.with_suffix(".md").is_file():
                problems.append(f"flat/folder collision: {self._disk_id(entry)}")

        for p in self._cap_files(include_variants=True):
            cf = parse_capability_file(self._disk_id(p), p.read_text(encoding="utf-8"))
            for cap in cf.capabilities:
                where = cap.ref
                f = cap.fields
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
                if "Superseded by" in f and (e := self._ref_error(f["Superseded by"])):
                    problems.append(f"{where}: Superseded by → {e}")
                problems += self._check_globals(where, f)
                problems += self._check_subject(where, f, taxonomy)
        return problems

    def _check_globals(self, where: str, f: dict) -> list[str]:
        out = []
        for ns, field in (("roles", "Roles"), ("conditions", "When")):
            for tok in (s.strip() for s in f.get(field, "").split(",") if s.strip()):
                ref = tok.lstrip("!")
                if not ref.startswith(f"{ns}/"):
                    out.append(f"{where}: {field} '{tok}' must be a {ns}/ slug")
                elif (e := self._ref_error(ref)):
                    out.append(f"{where}: {field} → {e}")
        return out

    def _check_subject(self, where: str, f: dict, taxonomy: TaxonomyStore | None) -> list[str]:
        subj = f.get("Subject")
        if not subj or taxonomy is None:
            return []
        try:
            return [] if taxonomy.get(subj) is not None else [f"{where}: Subject → dangling ref '{subj}'"]
        except AmbiguousRef:
            return [f"{where}: Subject → ambiguous ref '{subj}'"]


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
        return sorted(p.parent for p in self.root.rglob("state.yaml"))

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
        d = self._find(slug)                          # content.md filename: FS realization, kept here
        return d / "content.md" if d is not None else None

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
        content = d / "content.md"
        caps = d / "capabilities.yaml"
        return WorkItem(
            slug=d.name,
            title=state.get("title", d.name),
            status=self._status_of(d),
            phase=state.get("phase", ""),
            created=state.get("created", ""),
            resolution=state.get("resolution"),
            priority=state.get("priority"),
            body=content.read_text(encoding="utf-8") if content.exists() else "",
            blocked_by=list(state.get("blocked_by") or []),
            capabilities=load_yaml(caps) if caps.exists() else None,
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

    def dod_checklist(self) -> list[str]:
        p = self.root / "dod.yaml"
        if p.exists():
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [str(x) for x in data]
            if isinstance(data, dict) and isinstance(data.get("checklist"), list):
                return [str(x) for x in data["checklist"]]
        return list(DEFAULT_DOD)

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
        (d / "content.md").write_text(
            f"# {title}\n\n## Product changes\n\n## Technical changes\n\n## Meta changes\n\n"
            f"{body}\n", encoding="utf-8")
        dump_yaml(d / "state.yaml", {
            "slug": slug, "title": title, "phase": "", "created": created,
            "resolution": None, "priority": priority})
        self._stage(d / "content.md", d / "state.yaml")
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
