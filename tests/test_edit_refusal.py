"""A refused `tcw work edit` changes nothing, and `update_work` refuses a new
self-block or cycle as `add_blocker` does
(spec: 2026-09-24-make-a-refused-tcw-work-edit-change-nothing)."""

import pytest

from tcw.store.fs import FsWorkStore
from test_epic_completable import mk_node


def run(root, monkeypatch, capsys, *argv):
    from tcw.cli import main
    monkeypatch.chdir(root)
    code = main(["work", *argv])
    out, err = capsys.readouterr()
    return code, out, err


def states(st, *slugs) -> dict[str, bytes]:
    return {s: (st.path(s) / "state.yaml").read_bytes() for s in slugs}


def assert_refused_leaving_unchanged(st, before: dict[str, bytes], code: int) -> None:
    assert code == 1
    assert states(st, *before) == before


@pytest.fixture
def board(tmp_path):
    st = FsWorkStore.open(mk_node(tmp_path))
    x, a, y = (st.create(t, created="2026-01-01").slug for t in ("X", "A", "Y"))
    st.add_blocker(x, a)
    return st, x, a, y


# ── tcw work edit ────────────────────────────────────────────────────────────

def test_a_refused_tag_leaves_a_new_blocker_unwritten(board, monkeypatch, capsys):
    st, x, a, y = board
    before = states(st, x, y)
    code, _, err = run(st.node_root, monkeypatch, capsys,
                       "edit", x, "--blocked-by", y, "--tag", "not-registered")
    assert "not-registered" in err
    assert_refused_leaving_unchanged(st, before, code)


def test_a_refused_self_block_leaves_a_removal_unwritten(board, monkeypatch, capsys):
    st, x, a, y = board
    before = states(st, x)
    code, _, err = run(st.node_root, monkeypatch, capsys,
                       "edit", x, "--unblocked-by", a, "--blocked-by", x)
    assert "cannot block itself" in err
    assert_refused_leaving_unchanged(st, before, code)


def test_blocked_by_and_blocks_the_same_item_is_refused_whole(board, monkeypatch, capsys):
    st, x, a, y = board
    before = states(st, x, y)
    code, _, err = run(st.node_root, monkeypatch, capsys,
                       "edit", x, "--blocked-by", y, "--blocks", y)
    assert "cycle" in err
    assert_refused_leaving_unchanged(st, before, code)


def test_a_refused_tag_leaves_a_reverse_link_unwritten(board, monkeypatch, capsys):
    """`--blocks` writes another item, so it is the write most easily left behind.
    (A bad `--effort` never gets this far: argument parsing refuses it.)"""
    st, x, a, y = board
    before = states(st, x, y)
    code, _, err = run(st.node_root, monkeypatch, capsys,
                       "edit", x, "--blocks", y, "--tag", "not-registered")
    assert "not-registered" in err
    assert_refused_leaving_unchanged(st, before, code)


def test_a_blocks_that_would_close_a_cycle_through_an_existing_blocker(board, monkeypatch, capsys):
    st, x, a, y = board                              # x is blocked by a
    before = states(st, x, a)
    code, _, err = run(st.node_root, monkeypatch, capsys,
                       "edit", x, "--blocks", a, "--title", "Renamed")
    assert "cycle" in err
    assert_refused_leaving_unchanged(st, before, code)


def test_removing_a_blocker_lets_blocks_name_it(board, monkeypatch, capsys):
    """Checked against the item's proposed blockers, not its stored ones."""
    st, x, a, y = board
    code, _, _ = run(st.node_root, monkeypatch, capsys,
                     "edit", x, "--unblocked-by", a, "--blocks", a)
    assert code == 0
    assert st.get(x).blocked_by == []
    assert st.get(a).blocked_by == [{"slug": x}]


def test_remove_then_add_the_same_blocker_still_succeeds(board, monkeypatch, capsys):
    st, x, a, y = board
    code, _, _ = run(st.node_root, monkeypatch, capsys,
                     "edit", x, "--unblocked-by", a, "--blocked-by", a, "--title", "T")
    assert code == 0
    item = st.get(x)
    assert (item.blocked_by, item.title) == ([{"slug": a}], "T")


def test_an_accepted_edit_writes_every_part(board, monkeypatch, capsys):
    st, x, a, y = board
    code, _, _ = run(st.node_root, monkeypatch, capsys, "edit", x,
                     "--unblocked-by", a, "--blocked-by", "vendor fix",
                     "--blocks", y, "--effort", "low")
    assert code == 0
    assert st.get(x).blocked_by == [{"external": "vendor fix"}]
    assert st.get(x).effort == "low"
    assert st.get(y).blocked_by == [{"slug": x}]


# ── update_work(blockers=...) — the web app's path ────────────────────────────

def test_update_work_refuses_a_self_block(board):
    st, x, a, y = board
    before = states(st, x)
    with pytest.raises(ValueError, match="cannot block itself"):
        st.update_work(x, blockers=[a, x])
    assert states(st, x) == before


def test_update_work_refuses_a_new_cycle(board):
    st, x, a, y = board                              # x is blocked by a
    before = states(st, a)
    with pytest.raises(ValueError, match="cycle"):
        st.update_work(a, blockers=[x], title="Changed")
    assert states(st, a) == before


def test_update_work_keeps_an_existing_cycle_saveable(board):
    """Only new entries are checked, so an item already in a cycle can still be
    saved — and edited to break the cycle."""
    st, x, a, y = board
    st.set_field(a, "blocked_by", [{"slug": x}])     # a cycle made by hand
    assert st.update_work(a, blockers=[x], title="Kept").item.title == "Kept"
    assert st.update_work(a, blockers=[]).item.blocked_by == []


# ── check_blocker_edits — the store operation, directly ──────────────────────

def test_check_blocker_edits_writes_nothing_and_accepts_a_valid_set(board):
    st, x, a, y = board
    before = states(st, x, a, y)
    st.check_blocker_edits(x, add=[y], remove=[a], blocks=[a])
    assert states(st, x, a, y) == before


@pytest.mark.parametrize("edits, message", [
    ({"remove": ["not-a-blocker"]}, "no such blocker"),
    ({"remove": ["A", "A"]}, "no such blocker"),         # the second finds nothing
    ({"add": ["X"]}, "cannot block itself"),
    ({"blocks": ["X"]}, "cannot block itself"),
    ({"blocks": ["A"]}, "cycle"),                       # A already blocks X
    ({"add": ["Y"], "blocks": ["Y"]}, "cycle"),         # only together
])
def test_check_blocker_edits_refuses(board, edits, message):
    st, x, a, y = board
    names = {"X": x, "A": a, "Y": y}
    edits = {k: [names.get(r, r) for r in v] for k, v in edits.items()}
    with pytest.raises(ValueError, match=message):
        st.check_blocker_edits(x, **edits)


def test_blocks_is_not_refused_through_a_blocker_the_edit_removes(board):
    """X sits in a cycle with E and is also blocked by R, which waits on T.
    Removing R and making X block T is valid: only the stored edge X → R led to
    T, and the edit removes it."""
    st, x, a, y = board
    e, r, t = (st.create(n, created="2026-01-01").slug for n in ("E", "R", "T"))
    st.set_field(x, "blocked_by", [{"slug": e}, {"slug": r}])
    st.set_field(e, "blocked_by", [{"slug": x}])       # a cycle made by hand
    st.set_field(r, "blocked_by", [{"slug": t}])
    st.check_blocker_edits(x, remove=[r], blocks=[t])
