import yaml
import subprocess

from tcw.store.fs import (
    FsWorkStore, init, qualified_work_ref_problem, resolve_qualified_work_ref,
)


def node(path, project_id):
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    init(["work"], path, project_id)
    return path


def connect(parent, child, parent_id, child_id):
    p = yaml.safe_load((parent / "tcw-config.yaml").read_text()) or {}
    p.setdefault("connected-projects", {}).setdefault("children", {})[
        child_id
    ] = str(child)
    (parent / "tcw-config.yaml").write_text(yaml.safe_dump(p, sort_keys=False))
    c = yaml.safe_load((child / "tcw-config.yaml").read_text()) or {}
    c["connected-projects"] = {"parent": {parent_id: str(parent)}}
    (child / "tcw-config.yaml").write_text(yaml.safe_dump(c, sort_keys=False))


def test_bare_and_status_refs_remain_local(tmp_path):
    root = node(tmp_path / "root", "root-project")
    item = FsWorkStore.open(root).create("foo", created="2026-01-01")
    store, bare = resolve_qualified_work_ref(root, item.slug)
    assert store.node_root == root.resolve() and bare == item.slug
    store, bare = resolve_qualified_work_ref(root, f"backlog/{item.slug}")
    assert store.node_root == root.resolve() and bare == item.slug
    assert resolve_qualified_work_ref(root, f"active/{item.slug}") is None


def test_descendant_id_resolves_regardless_of_layout(tmp_path):
    root = node(tmp_path / "root", "root-project")
    child = node(tmp_path / "outside" / "child", "child-project")
    connect(root, child, "root-project", "child-project")
    item = FsWorkStore.open(child).create("foo", created="2026-01-01")
    store, bare = resolve_qualified_work_ref(root, f"child-project/{item.slug}")
    assert store.node_root == child.resolve() and bare == item.slug


def test_deep_descendant_uses_own_id_not_path(tmp_path):
    root = node(tmp_path / "root", "root-project")
    child = node(tmp_path / "child", "child-project")
    deep = node(tmp_path / "far" / "deep", "deep-project")
    connect(root, child, "root-project", "child-project")
    connect(child, deep, "child-project", "deep-project")
    item = FsWorkStore.open(deep).create("foo", created="2026-01-01")
    assert resolve_qualified_work_ref(root, f"deep-project/{item.slug}") is not None
    assert resolve_qualified_work_ref(
        root, f"child-project/deep-project/{item.slug}"
    ) is None


def test_parent_id_resolves_upward_from_child(tmp_path):
    """A cross-node epic slice lives in the child and points at the parent's epic."""
    root = node(tmp_path / "root", "root-project")
    child = node(tmp_path / "child", "child-project")
    connect(root, child, "root-project", "child-project")
    epic = FsWorkStore.open(root).create("Epic", created="2026-01-01")
    store, bare = resolve_qualified_work_ref(child, f"root-project/{epic.slug}")
    assert store.node_root == root.resolve() and bare == epic.slug


def test_sibling_id_resolves(tmp_path):
    root = node(tmp_path / "root", "root-project")
    a = node(tmp_path / "a", "a-project")
    b = node(tmp_path / "b", "b-project")
    connect(root, a, "root-project", "a-project")
    connect(root, b, "root-project", "b-project")
    item = FsWorkStore.open(b).create("foo", created="2026-01-01")
    store, bare = resolve_qualified_work_ref(a, f"b-project/{item.slug}")
    assert store.node_root == b.resolve() and bare == item.slug


def test_deep_upward_resolves_to_root(tmp_path):
    root = node(tmp_path / "root", "root-project")
    child = node(tmp_path / "child", "child-project")
    deep = node(tmp_path / "deep", "deep-project")
    connect(root, child, "root-project", "child-project")
    connect(child, deep, "child-project", "deep-project")
    item = FsWorkStore.open(root).create("foo", created="2026-01-01")
    store, bare = resolve_qualified_work_ref(deep, f"root-project/{item.slug}")
    assert store.node_root == root.resolve() and bare == item.slug


def test_problem_message_names_the_cause(tmp_path):
    root = node(tmp_path / "root", "root-project")
    assert "no such project in this graph: ghost" == qualified_work_ref_problem(
        root, "ghost/some-slug")
    assert "no such work item" in qualified_work_ref_problem(root, "bare-slug")


def test_unregistered_and_legacy_path_qualifiers_fail(tmp_path):
    root = node(tmp_path / "root", "root-project")
    decoy = node(tmp_path / "root" / "nested", "decoy-project")
    item = FsWorkStore.open(decoy).create("foo", created="2026-01-01")
    for ref in (
        f"nested/{item.slug}",
        f"decoy-project/{item.slug}",
        f"../nested/{item.slug}",
        f"/absolute/{item.slug}",
    ):
        assert resolve_qualified_work_ref(root, ref) is None
