"""resolve_qualified_work_ref — the cross-node addressing resolver (fs.py).

A qualified work ref is `sub/proj/<slug>`; the qualifier is the descendant
node's path relative to the anchor. Slugs never contain '/', so the last
'/'-segment is always the bare slug. The security-relevant guards (traversal,
absolute, `.git`/`.worktrees`) must fail closed on the *resolved* path, not the
raw qualifier string.
"""

import os
import subprocess
from pathlib import Path

from tcw.store.fs import WORKTREES_DIR, FsWorkStore, init, resolve_qualified_work_ref


def node(tmp_path: Path, name: str = "repo") -> Path:
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root)
    return root


def subnode(parent: Path, rel: str) -> Path:
    d = parent / rel
    d.mkdir(parents=True)
    init(["work"], d)
    return d


# ── positive resolution ──────────────────────────────────────────────────────

def test_bare_slug_resolves_to_anchor(tmp_path):
    root = node(tmp_path)
    store, bare = resolve_qualified_work_ref(root, "2026-01-01-foo")
    assert store.node_root.resolve() == root.resolve()
    assert bare == "2026-01-01-foo"


def test_qualified_slug_resolves_to_descendant(tmp_path):
    root = node(tmp_path)
    sub = subnode(root, "Project-A")
    store, bare = resolve_qualified_work_ref(root, "Project-A/2026-01-01-foo")
    assert store.node_root.resolve() == sub.resolve()
    assert bare == "2026-01-01-foo"


def test_nested_two_level_qualifier(tmp_path):
    root = node(tmp_path)
    deep = subnode(root, "Project-A/Nested")
    store, bare = resolve_qualified_work_ref(root, "Project-A/Nested/2026-01-01-deep")
    assert store.node_root.resolve() == deep.resolve()
    assert bare == "2026-01-01-deep"


def test_leading_dot_slash_stripped(tmp_path):
    root = node(tmp_path)
    sub = subnode(root, "Project-A")
    store, bare = resolve_qualified_work_ref(root, "./Project-A/2026-01-01-foo")
    assert store.node_root.resolve() == sub.resolve()
    assert bare == "2026-01-01-foo"


def test_render_resolve_round_trip(tmp_path):
    """The exact `f"{rel}/{slug}"` string _list/serve produce must round-trip."""
    root = node(tmp_path)
    sub = subnode(root, "Project-A")
    slug = FsWorkStore.open(sub).create("a feature", created="2026-01-01").slug
    rel = sub.resolve().relative_to(root.resolve())          # what _list computes
    store, bare = resolve_qualified_work_ref(root, f"{rel}/{slug}")
    assert store.node_root.resolve() == sub.resolve()
    assert bare == slug
    assert store.get(bare) is not None                       # the item is really there


# ── rejections: unknown / non-node ───────────────────────────────────────────

def test_unknown_qualifier_is_none(tmp_path):
    root = node(tmp_path)
    assert resolve_qualified_work_ref(root, "nope/2026-01-01-foo") is None


def test_plain_subdir_non_node_is_none(tmp_path):
    root = node(tmp_path)
    (root / "plain").mkdir()                                 # exists but no sentinel
    assert resolve_qualified_work_ref(root, "plain/2026-01-01-foo") is None


# ── rejections: traversal / absolute / malformed ─────────────────────────────

def test_traversal_escape_is_none(tmp_path):
    root = node(tmp_path)
    assert resolve_qualified_work_ref(root, "../escape/2026-01-01-foo") is None


def test_deep_traversal_escape_is_none(tmp_path):
    root = node(tmp_path)
    (root / "sub").mkdir()
    assert resolve_qualified_work_ref(root, "sub/../../etc/passwd") is None


def test_absolute_qualifier_is_none(tmp_path):
    root = node(tmp_path)
    assert resolve_qualified_work_ref(root, "/etc/passwd") is None


def test_malformed_refs_are_none(tmp_path):
    root = node(tmp_path)
    for ref in ("/", "/slug", "slug/"):
        assert resolve_qualified_work_ref(root, ref) is None, ref


# ── rejections: .git / .worktrees (resolved-segment guard) ───────────────────

def test_git_and_worktrees_segments_rejected(tmp_path):
    root = node(tmp_path)
    assert resolve_qualified_work_ref(root, f"{WORKTREES_DIR}/x/2026-01-01-foo") is None
    assert resolve_qualified_work_ref(root, ".git/config/2026-01-01-foo") is None


def test_dotdot_recombination_into_git_rejected(tmp_path):
    """`sub/../.git/<slug>` must be caught on the *resolved* segments."""
    root = node(tmp_path)
    (root / "sub").mkdir()
    assert resolve_qualified_work_ref(root, "sub/../.git/2026-01-01-foo") is None


def test_symlink_into_worktrees_rejected(tmp_path):
    """An innocently-named in-tree symlink pointing into .worktrees (which a
    --worktree checkout populates with a copied sentinel) is a *real node* the
    board never emits. A raw-qualifier check ('link') would miss it; the
    resolved-segment guard must reject it."""
    root = node(tmp_path)
    wt_node = subnode(root, f"{WORKTREES_DIR}/x")            # copied-sentinel node
    link = root / "link"
    os.symlink(wt_node, link)
    assert (link / "docs" / "work").is_dir()                # the symlink IS a real node
    assert resolve_qualified_work_ref(root, "link/2026-01-01-foo") is None
