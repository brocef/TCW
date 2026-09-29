"""One walk for an epic's slices, and `delegate` naming a node with no board
(spec: 2026-09-27-share-one-descendant-walk-and-say-when-delegate-names-a-node-with-no-board)."""

import pytest
import yaml

from tcw.store.fs import FsWorkStore
from tcw.work.recursion import _tasks_for, delegate
from test_routing_nodes import node, slice_of


@pytest.fixture
def routed(tmp_path):
    """root (board) → mid (no board) → pa, pb (boards); root → q (board)."""
    root = node(tmp_path / "root", "root", board=True, children={"mid": "mid", "q": "q"})
    node(root / "q", "q", board=True, parent="root")
    node(root / "mid", "mid", board=False, parent="root", children={"pa": "pa", "pb": "pb"})
    for name in ("pa", "pb"):
        node(root / "mid" / name, name, board=True, parent="mid")
    return root


def test_the_gate_and_the_table_read_the_same_slices(routed):
    epic = FsWorkStore.open(routed).create("Epic", created="2026-01-01").slug
    for n, where in enumerate((routed, routed / "mid" / "pa", routed / "mid" / "pb")):
        slice_of(where, epic, title=f"Slice {n}")
    gate = FsWorkStore.open(routed).initiative_children(epic)
    table = _tasks_for(routed, epic)
    assert [i.slug for i in gate] == [i.slug for _label, i in table]
    assert len(gate) == 3
    assert [label for label, _i in table][0] == "."
    assert sorted(label for label, _i in table) == [".", "pa", "pb"]


def test_delegate_to_a_node_with_no_board_says_so(routed):
    with pytest.raises(ValueError) as refused:
        delegate(routed, "mid", "x")
    message = str(refused.value)
    assert "keeps no board" in message and "below it: pa, pb." in message, message
    assert "q" not in message.split("below it:")[1]
    assert "no child node" not in message


def test_delegate_to_a_node_whose_board_is_not_provisioned_says_so(routed):
    cfg_path = routed / "mid" / "tcw-config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text())
    cfg["work"] = {"repository": {"url": "git@host:o/board.git"}}
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))
    with pytest.raises(ValueError, match="board is not available here"):
        delegate(routed, "mid", "x")


def test_an_unregistered_name_is_still_no_child_node(routed):
    with pytest.raises(ValueError, match="no child node 'nope'"):
        delegate(routed, "nope", "x")


def test_a_board_that_is_configured_but_broken_gives_its_reason(routed):
    cfg_path = routed / "mid" / "tcw-config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text())
    cfg["work"] = {"path": "nowhere"}
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))
    with pytest.raises(ValueError) as refused:
        delegate(routed, "mid", "x")
    assert "not available here" in str(refused.value)
    assert "keeps no board" not in str(refused.value)


def test_naming_a_boardless_ancestor_is_no_child_node(routed):
    with pytest.raises(ValueError, match="no child node 'mid'"):
        delegate(routed / "mid" / "pa", "mid", "x")
