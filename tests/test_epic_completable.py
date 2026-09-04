"""Epic completability: flag when all children resolve, complete from backlog,
reconcile --complete-when-ready (spec: 2026-07-15-flag-or-auto-advance-an-epic-…)."""

import subprocess
from pathlib import Path

import pytest

from tcw.store.base import IllegalTransition
from tcw.store.fs import FsCapabilitiesStore, FsWorkStore, init
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
    st2 = FsWorkStore.open(root)
    assert st2.get(epic).status == "completed"
    # the persisted rollup must not keep a stale "Ready to close" instruction
    assert "Ready to close" not in st2.read_sidecar(epic, "rollup.md").content


def test_reconcile_complete_when_ready_noop_if_open(tmp_path):
    root = mk_node(tmp_path)
    st = FsWorkStore.open(root)
    epic = make_epic(st, n_done=1, n_open=1)
    reconcile(root, epic, complete_when_ready=True)
    assert FsWorkStore.open(root).get(epic).status == "backlog"   # unchanged


# ── auto-complete honors the capability gate ─────────────────────────────────

def test_reconcile_auto_complete_blocked_by_missing_capability(tmp_path):
    """A ready epic that declares a still-Missing `new:` capability is NOT
    auto-completed — the capability gate runs on this path too."""
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", "--initial-branch=main", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work", "capabilities"], root)
    FsCapabilitiesStore.open(root).add("foo/bar", "Foo bar", status="Missing")

    st = FsWorkStore.open(root)
    epic = make_epic(st, n_done=1, n_open=0)
    (st.path(epic) / "capabilities.yaml").write_text("new:\n  - foo/bar\n")

    with pytest.raises(ValueError, match="capabilities not reconciled"):
        reconcile(root, epic, complete_when_ready=True)
    assert FsWorkStore.open(root).get(epic).status == "backlog"   # not completed

    FsCapabilitiesStore.open(root).set("foo/bar", {"Status": "Supported"})
    reconcile(root, epic, complete_when_ready=True)
    assert FsWorkStore.open(root).get(epic).status == "completed"  # now allowed


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


def _partial_graph(tmp_path):
    """A node whose registered child's repository is not in this checkout."""
    import subprocess
    import yaml
    from tcw.store.fs import init

    root = tmp_path / "top"
    root.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root, "top-project")
    doc = yaml.safe_load((root / "tcw-config.yaml").read_text())
    doc["connected-projects"] = {"children": {"away-project": str(tmp_path / "away")}}
    (root / "tcw-config.yaml").write_text(yaml.safe_dump(doc, sort_keys=False))
    return root


def test_an_epic_is_not_completed_over_slices_this_checkout_cannot_see(tmp_path):
    """Slices live in child nodes. A checkout missing one cannot see whether
    they are resolved, and this gate exists to refuse closing an epic over
    them — so an empty answer from a partial graph must not read as "none"."""
    import pytest as _pytest
    from tcw.store.fs import FsWorkStore

    root = _partial_graph(tmp_path)
    st = FsWorkStore.open(root)
    epic = st.create("Epic", created="2026-01-01")
    st.set_field(epic.slug, "type", "epic")
    st.start(epic.slug)

    with _pytest.raises(ValueError) as excinfo:
        st.complete(epic.slug, "done", [], force=False)
    message = str(excinfo.value)
    assert "Cannot verify the initiative children" in message
    assert "away-project" in message
    assert FsWorkStore.open(root).get(epic.slug).status == "active"

    # --force is still the documented way past every gate here.
    st.complete(epic.slug, "done", [], force=True)
    assert FsWorkStore.open(root).tombstone(epic.slug) is not None


def test_epic_completable_is_false_when_the_graph_is_partial(tmp_path):
    from tcw.store.fs import FsWorkStore

    root = _partial_graph(tmp_path)
    st = FsWorkStore.open(root)
    epic = st.create("Epic", created="2026-01-01")
    st.set_field(epic.slug, "type", "epic")
    st.start(epic.slug)
    child = st.create("Slice", created="2026-01-01")
    st.set_field(child.slug, "initiative", epic.slug)
    st.start(child.slug)
    st.complete(child.slug, "done", [], force=True)
    # Every child this checkout can see is resolved, and the answer is still
    # "not knowable from here" rather than "ready".
    assert st.epic_completable(FsWorkStore.open(root).get(epic.slug)) is False


def test_a_backlog_epic_in_a_partial_checkout_is_refused_for_the_right_reason(tmp_path):
    """Folding the partial-graph refusal into `epic_completable` made a backlog
    epic unreachable by any route: `from_backlog_epic` went False, the
    `IllegalTransition` fired *before* the force check, and it blamed the status
    transition for a condition that has nothing to do with it."""
    from tcw.store.fs import FsWorkStore

    root = _partial_graph(tmp_path)
    st = FsWorkStore.open(root)
    epic = st.create("Epic", created="2026-01-01")
    st.set_field(epic.slug, "type", "epic")
    child = st.create("Slice", created="2026-01-01")
    st.set_field(child.slug, "initiative", epic.slug)
    st.start(child.slug, force=True)          # the epic stays in backlog
    st.complete(child.slug, "done", [], force=True)

    st = FsWorkStore.open(root)
    epic = st.get(epic.slug)
    assert epic.status == "backlog"
    with pytest.raises(ValueError) as excinfo:
        st.complete(epic.slug, "done", [], force=False)
    message = str(excinfo.value)
    assert "away-project" in message
    assert "cannot complete from backlog" not in message


def test_a_backlog_epic_in_a_partial_checkout_can_be_forced(tmp_path):
    """The escape hatch the sibling gate advertises has to actually be reachable
    from the same state."""
    from tcw.store.fs import FsWorkStore

    root = _partial_graph(tmp_path)
    st = FsWorkStore.open(root)
    epic = st.create("Epic", created="2026-01-01")
    st.set_field(epic.slug, "type", "epic")
    child = st.create("Slice", created="2026-01-01")
    st.set_field(child.slug, "initiative", epic.slug)
    st.start(child.slug, force=True)          # the epic stays in backlog
    st.complete(child.slug, "done", [], force=True)

    st = FsWorkStore.open(root)
    assert st.get(epic.slug).status == "backlog"
    st.complete(epic.slug, "done", [], force=True)
    assert FsWorkStore.open(root).get(epic.slug).status == "completed"


def test_the_missing_projects_are_listed_once_each(tmp_path):
    """`_unreachable_edge` records one entry per declaring config, so a project
    two present configs both name rendered as `proj-c, proj-c`."""
    import subprocess
    import yaml
    from tcw.store.fs import FsWorkStore, init

    root = tmp_path / "top"
    child = tmp_path / "here"
    for path, project_id in ((root, "top-project"), (child, "here-project")):
        path.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(path)], check=True)
        subprocess.run(["git", "-C", str(path), "config", "user.email", "t@t"], check=True)
        subprocess.run(["git", "-C", str(path), "config", "user.name", "t"], check=True)
        init(["work"], path, project_id)
    away = str(tmp_path / "away")
    for path, doc in (
        (root, {"children": {"here-project": str(child), "away-project": away}}),
        (child, {"parent": {"top-project": str(root)},
                 "children": {"away-project": away}}),
    ):
        config = yaml.safe_load((path / "tcw-config.yaml").read_text())
        config["connected-projects"] = doc
        (path / "tcw-config.yaml").write_text(yaml.safe_dump(config, sort_keys=False))

    note = FsWorkStore.open(root).incomplete_graph_note()
    assert note.count("away-project") == 1


def test_a_graph_that_cannot_be_read_is_not_reported_complete(tmp_path,
                                                              monkeypatch):
    """`except Exception: return ""` told every caller the graph was complete in
    the one state where that is least likely — failing the completion gate open,
    the direction it exists to prevent."""
    from tcw.store import fs as fs_module
    from tcw.store.fs import FsWorkStore

    root = _partial_graph(tmp_path)
    st = FsWorkStore.open(root)

    def _boom(_node_root):
        raise RuntimeError("registry is unreadable")

    monkeypatch.setattr(fs_module.FsProjectRegistry, "open",
                        staticmethod(_boom))
    note = st.incomplete_graph_note()
    assert note != ""
    assert "could not be read" in note
