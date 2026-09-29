"""A damaged `state.yaml` must not switch off the gates that stop an item
resolving over open work (spec:
2026-09-29-keep-a-child-whose-state-yaml-cannot-be-read-visible-to-its-parent-s-completion-gate)."""

import pytest

from tcw.store.fs import FsWorkStore
from tcw.work.recursion import reconcile
from test_routing_nodes import node, slice_of


def damage(st: FsWorkStore, slug: str, how: bytes = b"\xff\xfe") -> None:
    path = st._find(slug) / "state.yaml"
    path.write_bytes(path.read_bytes() + how)


@pytest.fixture
def graph(tmp_path):
    root = node(tmp_path / "root", "root", board=True, children={"kid": "kid"})
    node(root / "kid", "kid", board=True, parent="root")
    return root


def epic_with_slices(root, where):
    st = FsWorkStore.open(root)
    epic = st.create("Epic", created="2026-01-01").slug
    st.set_field(epic, "type", "epic")
    done = slice_of(root, epic, title="Done slice")
    st.complete(done, "wontfix", [])
    open_slug = slice_of(where, epic, title="Open slice")
    return epic, open_slug


def test_an_epic_refuses_over_a_damaged_open_slice(graph):
    epic, open_slug = epic_with_slices(graph, graph)
    damage(FsWorkStore.open(graph), open_slug)
    st = FsWorkStore.open(graph)
    with pytest.raises(ValueError) as refused:
        st.complete(epic, "done", [])
    assert open_slug in str(refused.value)
    assert "cannot be read" in str(refused.value)
    assert st.get(epic).status == "backlog"


def test_an_epic_refuses_over_a_damaged_slice_in_a_child_node(graph):
    epic, open_slug = epic_with_slices(graph, graph / "kid")
    damage(FsWorkStore.open(graph / "kid"), open_slug)
    st = FsWorkStore.open(graph)
    with pytest.raises(ValueError) as refused:
        st.complete(epic, "done", [])
    assert open_slug in str(refused.value) and "kid" in str(refused.value)
    assert st.get(epic).status == "backlog"
    st.complete(epic, "done", [], force=True)
    assert st.get(epic).status == "completed"


@pytest.mark.parametrize("resolution,force", [("wontfix", False), ("wontfix", True)])
def test_a_parent_refuses_over_a_damaged_open_child(graph, resolution, force):
    st = FsWorkStore.open(graph)
    parent = st.create("Parent", created="2026-01-01").slug
    child = st.create("Child", created="2026-01-01", parent=parent).slug
    damage(st, child, b"\n: : [unclosed\n")
    with pytest.raises(ValueError) as refused:
        st.complete(parent, resolution, [], force=force)
    assert child in str(refused.value) and "cannot be read" in str(refused.value)
    assert st.get(parent).status == "backlog"


def test_a_parent_in_review_refuses_to_complete_as_done(graph):
    st = FsWorkStore.open(graph)
    parent = st.create("Parent", created="2026-01-01").slug
    child = st.create("Child", created="2026-01-01", parent=parent).slug
    st.transition(parent, "active")
    st.transition(parent, "review")
    damage(st, child)
    with pytest.raises(ValueError, match="cannot be read"):
        st.complete(parent, "done", [])
    assert st.get(parent).status == "review"


def test_a_damaged_resolved_item_blocks_nothing(graph):
    st = FsWorkStore.open(graph)
    parent = st.create("Parent", created="2026-01-01").slug
    child = st.create("Child", created="2026-01-01", parent=parent).slug
    st.complete(child, "wontfix", [])
    epic, _ = epic_with_slices(graph, graph)
    st.complete(_, "wontfix", [])
    damage(st, child)
    st.complete(parent, "wontfix", [])
    st.complete(epic, "done", [])
    assert st.get(epic).status == "completed"


def test_reconcile_leaves_the_epic_open(graph):
    epic, open_slug = epic_with_slices(graph, graph)
    damage(FsWorkStore.open(graph), open_slug)
    with pytest.raises(ValueError, match="cannot be read"):
        reconcile(graph, epic, complete_when_ready=True)
    assert FsWorkStore.open(graph).get(epic).status == "backlog"
