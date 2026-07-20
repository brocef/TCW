import yaml

from tcw.store.fs import (
    SENTINEL,
    child_nodes,
    descendant_nodes,
    find_node,
    find_node_root,
    init,
    parent_node,
    write_sentinel,
)


def work_node(path, project_id):
    path.mkdir(parents=True, exist_ok=True)
    init(["work"], path, project_id)
    return path.resolve()


def connect(parent, child, parent_id, child_id, locator=None):
    parent_cfg = yaml.safe_load((parent / SENTINEL).read_text()) or {}
    parent_cfg.setdefault("connected-projects", {}).setdefault("children", {})[
        child_id
    ] = locator or str(child)
    (parent / SENTINEL).write_text(yaml.safe_dump(parent_cfg, sort_keys=False))
    child_cfg = yaml.safe_load((child / SENTINEL).read_text()) or {}
    child_cfg["connected-projects"] = {
        "parent": {parent_id: str(parent)}
    }
    (child / SENTINEL).write_text(yaml.safe_dump(child_cfg, sort_keys=False))


def test_find_node_root_nearest(tmp_path):
    write_sentinel(tmp_path, "root-project")
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    assert find_node_root(sub) == tmp_path.resolve()


def test_find_node_root_nested_resolves_innermost(tmp_path):
    write_sentinel(tmp_path, "root-project")
    inner = tmp_path / "proj"
    inner.mkdir()
    write_sentinel(inner, "inner-project")
    deep = inner / "x"
    deep.mkdir()
    assert find_node_root(deep) == inner.resolve()


def test_find_node_root_none_when_absent(tmp_path):
    assert find_node_root(tmp_path) is None


def test_find_node_root_requires_file(tmp_path):
    (tmp_path / SENTINEL).mkdir()
    assert find_node_root(tmp_path) is None


def test_find_node_gates_on_component_and_valid_id(tmp_path):
    init(["work"], tmp_path, "root-project")
    assert find_node("work", tmp_path) == tmp_path.resolve()
    assert find_node("taxonomy", tmp_path) is None


def test_write_sentinel_idempotent_and_conflict(tmp_path):
    assert write_sentinel(tmp_path, "root-project") is True
    assert write_sentinel(tmp_path, "root-project") is False


def test_registered_topology_is_transitive_and_layout_independent(tmp_path):
    root = work_node(tmp_path / "root", "root-project")
    child = work_node(tmp_path / "elsewhere" / "child", "child-project")
    deep = work_node(tmp_path / "another" / "deep", "deep-project")
    connect(root, child, "root-project", "child-project")
    connect(child, deep, "child-project", "deep-project")
    assert child_nodes(root) == [child]
    assert descendant_nodes(root) == [child, deep]
    assert parent_node(deep) == child


def test_valid_unregistered_nodes_and_decoy_trees_are_ignored(tmp_path):
    root = work_node(tmp_path / "root", "root-project")
    child = work_node(tmp_path / "child", "child-project")
    decoy = work_node(tmp_path / "root" / "node_modules" / "decoy", "decoy-project")
    worktree = work_node(tmp_path / "root" / ".worktrees" / "copy", "copy-project")
    connect(root, child, "root-project", "child-project")
    assert descendant_nodes(root) == [child]
    assert decoy not in descendant_nodes(root)
    assert worktree not in descendant_nodes(root)
