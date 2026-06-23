from tcw.store.fs import SENTINEL, find_node, find_node_root, init, write_sentinel


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
