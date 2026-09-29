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
    assert "its initiative children" in str(refused.value)
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
    with pytest.raises(ValueError, match="its initiative children"):
        reconcile(graph, epic, complete_when_ready=True)
    assert FsWorkStore.open(graph).get(epic).status == "backlog"


def test_a_damaged_slice_on_the_epic_s_own_board_is_not_forceable(graph):
    """The epic gate yields to --force; the parent gate, which sees the same
    item on this board, does not."""
    epic, open_slug = epic_with_slices(graph, graph)
    damage(FsWorkStore.open(graph), open_slug)
    with pytest.raises(ValueError, match="beneath it"):
        FsWorkStore.open(graph).complete(epic, "done", [], force=True)


def test_the_damaged_item_itself_gets_the_move_s_own_refusal(graph):
    st = FsWorkStore.open(graph)
    slug = st.create("Damaged", created="2026-01-01").slug
    damage(st, slug)
    with pytest.raises(ValueError) as refused:
        st.complete(slug, "wontfix", [])
    assert "fix or replace it before changing the item" in str(refused.value)
    assert "beneath it" not in str(refused.value)


def test_drop_refuses_over_a_damaged_open_item_but_not_on_itself(graph):
    st = FsWorkStore.open(graph)
    parent = st.create("Parent", created="2026-01-01").slug
    child = st.create("Child", created="2026-01-01", parent=parent).slug
    damage(st, child)
    with pytest.raises(ValueError, match=f"Cannot drop {parent}.*{child}"):
        st.drop(parent)
    assert st.get(parent) is not None
    st.drop(child)
    st.drop(parent)


def test_the_cli_refuses_before_the_worktree_merge(tmp_path, monkeypatch, capsys):
    from test_worktree_completion import (_field_child, branch_commit, commit_all,
                                          new_item, refused_before_merge, repo,
                                          run_in, start_worktree)
    root = repo(tmp_path)
    slug = new_item(root, monkeypatch, capsys, "Parent")
    wt = start_worktree(root, slug, monkeypatch, capsys)
    tip = branch_commit(wt)
    _field_child(root, slug)
    child = root / "docs" / "work" / "backlog" / "2026-01-01-child" / "state.yaml"
    child.write_bytes(child.read_bytes() + b"\xff\xfe")
    commit_all(root, "damaged child in the primary checkout")
    code, _out, err = run_in(root, monkeypatch, capsys, "work", "complete", slug,
                             "--resolution", "done", "--confirm")
    assert code == 1 and "cannot be read" in err and "2026-01-01-child" in err
    refused_before_merge(root, wt, slug, tip)
