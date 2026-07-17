"""Epic completability: flag when all children resolve, complete from backlog,
reconcile --complete-when-ready (spec: 2026-07-15-flag-or-auto-advance-an-epic-…)."""

import subprocess
from pathlib import Path

import pytest

from tcw.store.base import IllegalTransition
from tcw.store.fs import FsWorkStore, init
from tcw.work.recursion import reconcile


def mk_node(base: Path, name: str = "repo") -> Path:
    root = base / name
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "--initial-branch=main", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root)
    return root


def make_epic(st: FsWorkStore, n_done: int, n_open: int) -> str:
    """A backlog epic with `n_done` completed + `n_open` open initiative children."""
    epic = st.create("Epic", created="2026-01-01")
    st.set_field(epic.slug, "type", "epic")
    for i in range(n_done):
        c = st.create(f"done {i}", created="2026-01-01")
        st.set_field(c.slug, "initiative", epic.slug)
        st.start(c.slug, force=True)              # bypass "epic must be active" gate
        st.complete(c.slug, "done", [])
    for i in range(n_open):
        c = st.create(f"open {i}", created="2026-01-01")
        st.set_field(c.slug, "initiative", epic.slug)
    return epic.slug


# ── predicate ────────────────────────────────────────────────────────────────

def test_completable_when_all_children_done(tmp_path):
    st = FsWorkStore.open(mk_node(tmp_path))
    epic = make_epic(st, n_done=2, n_open=0)
    assert st.epic_completable(st.get(epic)) is True


def test_not_completable_with_open_child(tmp_path):
    st = FsWorkStore.open(mk_node(tmp_path))
    epic = make_epic(st, n_done=1, n_open=1)
    assert st.epic_completable(st.get(epic)) is False


def test_empty_epic_not_completable(tmp_path):
    st = FsWorkStore.open(mk_node(tmp_path))
    epic = make_epic(st, n_done=0, n_open=0)
    assert st.epic_completable(st.get(epic)) is False       # nothing resolved yet


def test_non_epic_not_completable(tmp_path):
    st = FsWorkStore.open(mk_node(tmp_path))
    item = st.create("plain", created="2026-01-01")
    assert st.epic_completable(st.get(item.slug)) is False


# ── complete from backlog ────────────────────────────────────────────────────

def test_completable_epic_completes_from_backlog(tmp_path):
    st = FsWorkStore.open(mk_node(tmp_path))
    epic = make_epic(st, n_done=2, n_open=0)
    assert st.get(epic).status == "backlog"
    st.complete(epic, "done", [])                           # no start-just-to-complete
    assert st.get(epic).status == "completed"


def test_non_completable_epic_refused_from_backlog(tmp_path):
    st = FsWorkStore.open(mk_node(tmp_path))
    epic = make_epic(st, n_done=1, n_open=1)                # an open child
    with pytest.raises((IllegalTransition, ValueError)):
        st.complete(epic, "done", [])
    assert st.get(epic).status == "backlog"


def test_plain_item_still_refused_from_backlog(tmp_path):
    st = FsWorkStore.open(mk_node(tmp_path))
    item = st.create("plain", created="2026-01-01")
    with pytest.raises(IllegalTransition):
        st.complete(item.slug, "done", [])


def test_empty_epic_still_refused_from_backlog(tmp_path):
    st = FsWorkStore.open(mk_node(tmp_path))
    epic = make_epic(st, n_done=0, n_open=0)
    with pytest.raises(IllegalTransition):
        st.complete(epic, "done", [])


# ── reconcile flag + rollup line ─────────────────────────────────────────────

def test_reconcile_flags_ready_to_close(tmp_path):
    root = mk_node(tmp_path)
    epic = make_epic(FsWorkStore.open(root), n_done=2, n_open=0)
    block = reconcile(root, epic)
    assert "Ready to close" in block


def test_reconcile_complete_when_ready(tmp_path):
    root = mk_node(tmp_path)
    st = FsWorkStore.open(root)
    epic = make_epic(st, n_done=1, n_open=0)
    reconcile(root, epic, complete_when_ready=True)
    assert FsWorkStore.open(root).get(epic).status == "completed"


def test_reconcile_complete_when_ready_noop_if_open(tmp_path):
    root = mk_node(tmp_path)
    st = FsWorkStore.open(root)
    epic = make_epic(st, n_done=1, n_open=1)
    reconcile(root, epic, complete_when_ready=True)
    assert FsWorkStore.open(root).get(epic).status == "backlog"   # unchanged


# ── cross-node ───────────────────────────────────────────────────────────────

def test_cross_node_open_child_blocks_completable(tmp_path):
    parent = mk_node(tmp_path, "parent")
    subprocess.run(["git", "-C", str(parent), "add", "docs"], check=True)
    subprocess.run(["git", "-C", str(parent), "commit", "-qm", "init"], check=True)
    child_node = mk_node(parent, "child")

    pst = FsWorkStore.open(parent)
    epic = pst.create("Epic", created="2026-01-01")
    pst.set_field(epic.slug, "type", "epic")
    # an OPEN initiative child living in the descendant node
    cst = FsWorkStore.open(child_node)
    c = cst.create("far child", created="2026-01-01")
    cst.set_field(c.slug, "initiative", epic.slug)

    assert pst.epic_completable(pst.get(epic.slug)) is False
    with pytest.raises((IllegalTransition, ValueError)):
        pst.complete(epic.slug, "done", [])
