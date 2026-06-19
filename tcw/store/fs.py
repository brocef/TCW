"""Filesystem store adapters + the FS-local helpers they share.

`git_root`/`init` (Phase 1) scaffold; `FsTaxonomyStore` (Phase 2) realizes the
`TaxonomyStore` interface over `docs/taxonomy/`. The capabilities and work
adapters land here in their phases; the genuinely-shared primitives get factored
into a tree-store core in Phase 4 (don't pre-abstract — AGENTS.md).
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import yaml

from tcw.store.base import AmbiguousRef, TaxonomyStore, Term

# Component trees `tcw init` scaffolds. `work` gets a status-folder skeleton;
# `taxonomy` and `capabilities` are flat trees that fill in per their phases.
COMPONENTS = ("taxonomy", "capabilities", "work")
WORK_STATUSES = ("inbox", "backlog", "active", "blocked", "completed")


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


def git_stage(node_root: Path, *paths: Path) -> None:
    subprocess.run(["git", "-C", str(node_root), "add", "--", *map(str, paths)], check=True)


def git_rm(node_root: Path, path: Path) -> None:
    # -f so a term staged-but-not-yet-committed (just `add`ed) can still be removed.
    subprocess.run(["git", "-C", str(node_root), "rm", "-rfq", "--", str(path)], check=True)


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


# ── FsTaxonomyStore ─────────────────────────────────────────────────────────

_TAX_RESERVED = {"config.yaml", "meta.yaml", "description.md"}


class FsTaxonomyStore(TaxonomyStore):
    """`TaxonomyStore` over nested dirs under `docs/taxonomy/` (Phase 2 B.3).

    A term's slug is its directory path under the taxonomy root. `extends`
    aliases (local-path repo roots) are realized as nested stores.
    """

    def __init__(self, root: Path, _seen: set[Path] | None = None):
        self.root = root                       # docs/taxonomy/
        self.node_root = root.parent.parent    # repo root
        self.config = load_yaml(root / "config.yaml")
        self.extends: dict[str, "FsTaxonomyStore"] = {}
        seen = (_seen or set()) | {root.resolve()}
        for alias, repo_path in (self.config.get("extends") or {}).items():
            ext = (self.node_root / repo_path / "docs" / "taxonomy").resolve()
            if ext.is_dir() and ext not in seen:        # broken/cyclic → check() reports
                self.extends[alias] = FsTaxonomyStore(ext, _seen=seen)

    @classmethod
    def open(cls, node_root: Path) -> "FsTaxonomyStore":
        return cls(node_root / "docs" / "taxonomy")

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
        git_stage(self.node_root, d / "meta.yaml", d / "description.md")
        return self._term(full)

    def remove(self, ref: str) -> None:
        term = self.get(ref)
        if term is None:
            raise ValueError(f"no such term: {ref}")
        if term.origin != "local":
            raise ValueError(f"cannot remove inherited term '{term.qualified}' "
                             f"(edit it at its source)")
        git_rm(self.node_root, self.root / term.slug)

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
