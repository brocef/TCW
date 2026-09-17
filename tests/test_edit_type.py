"""Changing an item's type to or from epic after it was created
(spec: 2026-09-15-let-tcw-work-edit-change-an-item-s-type-to-or-from-epic)."""

import pytest

from tcw.store.fs import FsWorkStore
from test_epic_completable import _partial_graph, mk_node
from test_recursion import mk_node as mk_graph_node


def run(root, monkeypatch, capsys, *argv):
    from tcw.cli import main
    monkeypatch.chdir(root)
    code = main(["work", *argv])
    out, err = capsys.readouterr()
    return code, out, err


def epic_with_child(st, *, resolved=False):
    epic = st.create("Epic", created="2026-01-01")
    st.set_field(epic.slug, "type", "epic")
    child = st.create("Slice", created="2026-01-01")
    st.set_field(child.slug, "initiative", epic.slug)
    if resolved:
        st.start(child.slug, force=True)
        st.complete(child.slug, "done", [])
    return epic.slug, child.slug


# ── store ────────────────────────────────────────────────────────────────────

def test_update_work_promotes_and_demotes(tmp_path):
    st = FsWorkStore.open(mk_node(tmp_path))
    item = st.create("Initiative", created="2026-01-01")
    assert st.update_work(item.slug, type="epic").item.type == "epic"
    assert st.update_work(item.slug, type="epic").item.type == "epic"   # same type: no-op
    assert st.update_work(item.slug, type="").item.type == ""
    assert "type" not in (st.path(item.slug) / "state.yaml").read_text()


def test_update_work_refuses_an_unknown_type_and_writes_nothing(tmp_path):
    st = FsWorkStore.open(mk_node(tmp_path))
    item = st.create("Item", created="2026-01-01")
    with pytest.raises(ValueError, match="invalid type 'story'"):
        st.update_work(item.slug, type="story", title="Changed")
    assert st.get(item.slug).title == "Item"


@pytest.mark.parametrize("resolved", [False, True])
def test_demotion_refuses_while_a_child_points_at_the_epic(tmp_path, resolved):
    st = FsWorkStore.open(mk_node(tmp_path))
    epic, child = epic_with_child(st, resolved=resolved)
    with pytest.raises(ValueError, match=child):
        st.update_work(epic, type="", title="Changed")
    item = st.get(epic)
    assert (item.type, item.title) == ("epic", "Epic")


def test_demotion_sees_a_child_in_a_descendant_project(tmp_path):
    parent = mk_graph_node(tmp_path, "parent")
    child_root = mk_graph_node(parent, "child")
    top = FsWorkStore.open(parent)
    epic = top.create("Epic", created="2026-01-01")
    top.set_field(epic.slug, "type", "epic")
    below = FsWorkStore.open(child_root)
    slice_ = below.create("Slice", created="2026-01-02")
    below.set_field(slice_.slug, "initiative", epic.slug)
    with pytest.raises(ValueError, match=slice_.slug):
        top.update_work(epic.slug, type="")
    assert top.get(epic.slug).type == "epic"


def test_demotion_refuses_over_a_partial_graph(tmp_path):
    st = FsWorkStore.open(_partial_graph(tmp_path))
    epic = st.create("Epic", created="2026-01-01")
    st.set_field(epic.slug, "type", "epic")
    with pytest.raises(ValueError, match="away-project"):
        st.update_work(epic.slug, type="")
    assert st.get(epic.slug).type == "epic"


def test_promotion_and_a_plain_no_op_are_not_refused_over_a_partial_graph(tmp_path):
    st = FsWorkStore.open(_partial_graph(tmp_path))
    item = st.create("Item", created="2026-01-01")
    assert st.update_work(item.slug, type="").item.type == ""
    assert st.update_work(item.slug, type="epic").item.type == "epic"


# ── CLI ──────────────────────────────────────────────────────────────────────

def test_cli_promotes_then_demotes(tmp_path, monkeypatch, capsys):
    root = mk_node(tmp_path)
    slug = FsWorkStore.open(root).create("Initiative", created="2026-01-01").slug
    assert run(root, monkeypatch, capsys, "edit", slug, "--type", "epic")[0] == 0
    assert "type: epic" in run(root, monkeypatch, capsys, "show", slug)[1]
    assert run(root, monkeypatch, capsys, "edit", slug, "--type", "")[0] == 0
    assert FsWorkStore.open(root).get(slug).type == ""


def test_cli_refused_demotion_changes_nothing_else(tmp_path, monkeypatch, capsys):
    root = mk_node(tmp_path)
    st = FsWorkStore.open(root)
    epic, child = epic_with_child(st)
    code, _out, err = run(root, monkeypatch, capsys, "edit", epic, "--type", "",
                          "--blocked-by", "something external", "--title", "New")
    assert code == 1
    assert child in err
    item = FsWorkStore.open(root).get(epic)
    assert (item.type, item.title, item.blocked_by) == ("epic", "Epic", [])


def test_a_promoted_item_groups_its_children_and_becomes_ready_to_close(
        tmp_path, monkeypatch, capsys):
    root = mk_node(tmp_path)
    st = FsWorkStore.open(root)
    initiative = st.create("Initiative", created="2026-01-01").slug
    child = st.create("Slice", created="2026-01-02").slug
    st.set_field(child, "initiative", initiative)
    assert f"\n  {child} |" not in run(root, monkeypatch, capsys, "list", "-i")[1]
    assert run(root, monkeypatch, capsys, "edit", initiative, "--type", "epic")[0] == 0
    assert f"\n  {child} |" in run(root, monkeypatch, capsys, "list", "-i")[1]
    st.start(child, force=True)
    st.complete(child, "done", [])
    board = run(root, monkeypatch, capsys, "list")[1]
    assert f"{initiative} | backlog | - | - | Initiative | ready-to-close" in board
