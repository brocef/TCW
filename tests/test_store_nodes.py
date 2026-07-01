from tcw.store.fs import (
    SENTINEL, child_nodes, descendant_nodes, find_node, find_node_root, init,
    write_sentinel,
)


def _work_node(d):
    """Mark `d` a work node (sentinel + docs/work) with no git init."""
    d.mkdir(parents=True, exist_ok=True)
    (d / "docs" / "work").mkdir(parents=True, exist_ok=True)
    write_sentinel(d)
    return d.resolve()


def test_find_node_root_nearest(tmp_path):
    write_sentinel(tmp_path)
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    assert find_node_root(sub) == tmp_path.resolve()


def test_find_node_root_nested_resolves_innermost(tmp_path):
    write_sentinel(tmp_path)
    inner = tmp_path / "proj"
    inner.mkdir()
    write_sentinel(inner)
    deep = inner / "x"
    deep.mkdir()
    assert find_node_root(deep) == inner.resolve()


def test_find_node_root_none_when_absent(tmp_path):
    assert find_node_root(tmp_path) is None


def test_find_node_root_requires_a_file_not_a_dir(tmp_path):
    (tmp_path / SENTINEL).mkdir()       # a *directory* named tcw-config.yaml
    assert find_node_root(tmp_path) is None


def test_find_node_gates_on_component(tmp_path):
    write_sentinel(tmp_path)
    (tmp_path / "docs" / "work").mkdir(parents=True)
    assert find_node("work", tmp_path) == tmp_path.resolve()
    assert find_node("taxonomy", tmp_path) is None


def test_write_sentinel_idempotent(tmp_path):
    assert write_sentinel(tmp_path) is True
    assert write_sentinel(tmp_path) is False
    assert (tmp_path / SENTINEL).is_file()


def test_init_writes_sentinel(tmp_path):
    init(["work"], tmp_path)
    assert (tmp_path / SENTINEL).is_file()


# ── descendant_nodes (sentinel-based, transitive) ────────────────────────────

def test_descendant_nodes_sentinel_based(tmp_path):
    _work_node(tmp_path)
    a = _work_node(tmp_path / "Project-A")          # plain subdir, no git repo
    assert descendant_nodes(tmp_path) == [a]
    assert child_nodes(tmp_path) == []              # git-root-based → misses same-repo subdirs


def test_descendant_nodes_transitive_and_sorted(tmp_path):
    _work_node(tmp_path)
    a = _work_node(tmp_path / "Project-A")
    nested = _work_node(tmp_path / "Project-A" / "Nested")
    b = _work_node(tmp_path / "Project-B")
    assert descendant_nodes(tmp_path) == [a, nested, b]   # depth-first, path-sorted


def test_descendant_nodes_skips_worktrees_and_git(tmp_path):
    _work_node(tmp_path)
    _work_node(tmp_path / ".worktrees" / "item")    # a --worktree checkout copies the sentinel
    (tmp_path / ".git").mkdir()
    assert descendant_nodes(tmp_path) == []


def test_descendant_nodes_skips_symlink_cycle(tmp_path):
    _work_node(tmp_path)
    a = _work_node(tmp_path / "Project-A")
    (a / "loop").symlink_to(tmp_path)               # naive walk would recurse forever
    assert descendant_nodes(tmp_path) == [a]        # terminates; symlink not followed
