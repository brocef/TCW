"""A child work item has its own status and records its parent.

Children made by earlier versions sit inside their parent's folder with no
`parent:` field ("legacy" children). They keep following the parent's status,
so these tests build them by hand with `_legacy_child`.
"""
import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.store.fs import FsWorkStore
from tests.test_work import node


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True, text=True).stdout


def _item(root: Path, rel: str, **state) -> Path:
    """Write an item folder by hand at `docs/work/<rel>`."""
    d = root / "docs" / "work" / rel
    d.mkdir(parents=True)
    body = {"slug": d.name, "title": d.name, "created": "2026-01-01",
            "resolution": None, **state}
    (d / "state.yaml").write_text(yaml.safe_dump(body, sort_keys=False))
    return d


def _legacy_child(root: Path, status: str, holder: str, child: str, **state) -> Path:
    """A child as earlier versions made it: nested inside `holder`'s folder, with
    no `parent:` field (unless a test passes one to fake a hand edit)."""
    return _item(root, f"{status}/{holder}/{child}", **state)


def _commit(root: Path) -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "fixture")


# ── Task 1: reading the relation ─────────────────────────────────────────────

def test_legacy_child_follows_its_parents_folder(tmp_path):
    root = node(tmp_path)
    _item(root, "active/p")
    _legacy_child(root, "active", "p", "c")
    got = FsWorkStore.open(root).get("c")
    assert (got.status, got.parent) == ("active", "p")


def test_parent_field_names_the_parent_of_a_top_level_item(tmp_path):
    root = node(tmp_path)
    _item(root, "active/p")
    _item(root, "backlog/c", parent="p")
    got = FsWorkStore.open(root).get("c")
    assert (got.status, got.parent) == ("backlog", "p")


def test_check_reports_a_parent_field_naming_nothing(tmp_path):
    root = node(tmp_path)
    _item(root, "backlog/c", parent="ghost")
    problems = FsWorkStore.open(root).check()
    assert "c: parent 'ghost' names no work item or tombstone in this store" in problems


def test_check_accepts_a_parent_field_naming_a_tombstone(tmp_path):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    st.record_tombstone("gone", "done")
    _item(root, "completed/c", parent="gone", resolution="done")
    assert not [p for p in st.check() if p.startswith("c:")]


def test_check_reports_a_field_that_disagrees_with_the_folder(tmp_path):
    root = node(tmp_path)
    _item(root, "active/p")
    _item(root, "active/q")
    _legacy_child(root, "active", "p", "c", parent="q")
    problems = FsWorkStore.open(root).check()
    assert "c: parent field 'q' disagrees with the folder it sits in ('p')" in problems


# ── Task 2: which descendants are open ───────────────────────────────────────

def _claim_folder(root: Path, slug: str) -> Path:
    """The folder an interrupted claim leaves in `.claiming/`."""
    return root / "docs" / "work" / ".claiming" / f"{slug}-{'a' * 32}"


def test_open_descendants_are_the_open_children_with_their_own_status(tmp_path):
    root = node(tmp_path)
    _item(root, "active/p")
    for status in ("backlog", "active", "review"):
        _item(root, f"{status}/c-{status}", parent="p")
    _item(root, "completed/c-completed", parent="p", resolution="done")
    _item(root, "discarded/c-discarded", parent="p", resolution="wontfix")
    st = FsWorkStore.open(root)
    assert sorted(st.open_descendants("p")) == ["c-active", "c-backlog", "c-review"]
    assert len(st.independent_descendants("p")) == 5


def test_open_descendants_cover_the_whole_subtree(tmp_path):
    root = node(tmp_path)
    _item(root, "active/p")
    _item(root, "completed/c", parent="p", resolution="done")
    _item(root, "active/g", parent="c")
    assert FsWorkStore.open(root).open_descendants("p") == ["g"]


def test_a_legacy_child_neither_blocks_nor_hides_what_is_beneath_it(tmp_path):
    root = node(tmp_path)
    _item(root, "active/p")
    _legacy_child(root, "active", "p", "legacy")
    _item(root, "backlog/g", parent="legacy")
    st = FsWorkStore.open(root)
    assert st.open_descendants("p") == ["g"]
    # A resolved grandchild beneath a legacy child is still an independent
    # descendant, which is what `drop` refuses over.
    _item(root, "completed/h", parent="legacy", resolution="done")
    assert sorted(i.slug for i in st.independent_descendants("p")) == ["g", "h"]


def test_a_parent_cycle_does_not_loop(tmp_path):
    root = node(tmp_path)
    _item(root, "active/a", parent="b")
    _item(root, "active/b", parent="a")
    assert FsWorkStore.open(root).open_descendants("a") == ["b"]


def test_an_item_mid_claim_is_counted_as_open(tmp_path):
    root = node(tmp_path)
    _item(root, "active/p")
    claim = _claim_folder(root, "c")
    claim.mkdir(parents=True)
    (claim / "state.yaml").write_text(yaml.safe_dump(
        {"slug": "c", "title": "c", "resolution": None, "parent": "p"}))
    assert FsWorkStore.open(root).open_descendants("p") == ["c"]


def test_items_nested_inside_a_claim_stay_visible(tmp_path):
    """A claimed legacy item carries its nested children into `.claiming/`; a
    field item whose parent is one of those must still be found."""
    root = node(tmp_path)
    _item(root, "active/p")
    claim = _claim_folder(root, "a")
    claim.mkdir(parents=True)
    (claim / "state.yaml").write_text(yaml.safe_dump(
        {"slug": "a", "title": "a", "resolution": None, "parent": "p"}))
    (claim / "b").mkdir()
    (claim / "b" / "state.yaml").write_text(yaml.safe_dump(
        {"slug": "b", "title": "b", "resolution": None}))
    _item(root, "active/f", parent="b")
    st = FsWorkStore.open(root)
    assert sorted(st.open_descendants("p")) == ["a", "f"]


def test_check_does_not_report_a_legacy_child_carried_to_completion(tmp_path):
    root = node(tmp_path)
    _item(root, "completed/p", resolution="done")
    _legacy_child(root, "completed", "p", "c")
    _item(root, "completed/lone")
    problems = FsWorkStore.open(root).check()
    assert not [p for p in problems if p.startswith("c:")]
    # The exemption is narrow: a top-level resolved item with no resolution is
    # still the defect it always was.
    assert any(p.startswith("lone: status 'completed' with missing") for p in problems)


def test_check_still_reports_a_legacy_child_whose_own_resolution_is_wrong(tmp_path):
    root = node(tmp_path)
    _item(root, "active/p")
    _legacy_child(root, "active", "p", "c", resolution="done")
    problems = FsWorkStore.open(root).check()
    assert "c: status 'active' carries a resolution 'done' (only a closed item has one)" in problems


# ── Task 3: refusing to resolve or drop over open descendants ────────────────

def _board_with_child(tmp_path, child_status: str, parent_status: str = "active"):
    root = node(tmp_path)
    _item(root, f"{parent_status}/p")
    resolution = {"completed": "done", "discarded": "wontfix"}.get(child_status)
    _item(root, f"{child_status}/c", parent="p", resolution=resolution)
    _commit(root)
    return root, FsWorkStore.open(root)


def _assert_nothing_moved(root: Path, where: str) -> None:
    assert (root / "docs" / "work" / where / "state.yaml").is_file()


@pytest.mark.parametrize("child_status", ["backlog", "active", "review"])
@pytest.mark.parametrize("resolution", ["done", "wontfix"])
@pytest.mark.parametrize("force", [False, True])
def test_complete_refuses_while_a_child_is_open(tmp_path, child_status, resolution, force):
    root, st = _board_with_child(tmp_path, child_status)
    with pytest.raises(ValueError, match=r"still open: c\b"):
        st.complete("p", resolution, [], force=force)
    _assert_nothing_moved(root, "active/p")


def test_complete_succeeds_once_every_child_is_resolved(tmp_path):
    root, st = _board_with_child(tmp_path, "completed")
    assert st.complete("p", "done", []).status == "completed"


def test_complete_refuses_over_an_open_grandchild(tmp_path):
    root = node(tmp_path)
    _item(root, "active/p")
    _item(root, "completed/c", parent="p", resolution="done")
    _item(root, "active/g", parent="c")
    _commit(root)
    with pytest.raises(ValueError, match=r"still open: g\b"):
        FsWorkStore.open(root).complete("p", "done", [])
    _assert_nothing_moved(root, "active/p")


def test_complete_refuses_over_an_open_field_child_of_a_legacy_child(tmp_path):
    root = node(tmp_path)
    _item(root, "active/p")
    _legacy_child(root, "active", "p", "legacy")
    _item(root, "backlog/g", parent="legacy")
    _commit(root)
    with pytest.raises(ValueError, match=r"still open: g\b"):
        FsWorkStore.open(root).complete("p", "done", [])
    _assert_nothing_moved(root, "active/p")


def test_completing_a_parent_carries_a_legacy_child(tmp_path):
    root = node(tmp_path)
    _item(root, "active/p")
    _legacy_child(root, "active", "p", "c")
    _commit(root)
    st = FsWorkStore.open(root)
    st.complete("p", "done", [])
    assert st.get("c").status == "completed"


@pytest.mark.parametrize("child_status", ["backlog", "completed"])
def test_drop_refuses_while_any_child_names_the_parent(tmp_path, child_status):
    root, st = _board_with_child(tmp_path, child_status, parent_status="backlog")
    with pytest.raises(ValueError, match=r"name it as their parent: c\b"):
        st.drop("p")
    _assert_nothing_moved(root, "backlog/p")


def test_drop_refuses_over_a_resolved_grandchild_beneath_a_legacy_child(tmp_path):
    root = node(tmp_path)
    _item(root, "backlog/p")
    _legacy_child(root, "backlog", "p", "legacy")
    _item(root, "completed/g", parent="legacy", resolution="done")
    _commit(root)
    with pytest.raises(ValueError, match=r"name it as their parent: g\b"):
        FsWorkStore.open(root).drop("p")


def test_drop_still_removes_legacy_children_with_the_parent(tmp_path):
    root = node(tmp_path)
    _item(root, "backlog/p")
    _legacy_child(root, "backlog", "p", "c")
    _commit(root)
    st = FsWorkStore.open(root)
    st.drop("p")
    assert st.get("c") is None


def test_an_item_mid_claim_blocks_complete_and_drop(tmp_path):
    root = node(tmp_path)
    _item(root, "active/p")
    _item(root, "backlog/q")
    _commit(root)
    for parent in ("p", "q"):
        claim = root / "docs/work/.claiming" / f"c-{parent}-{'b' * 32}"
        claim.mkdir(parents=True)
        (claim / "state.yaml").write_text(yaml.safe_dump(
            {"slug": f"c-{parent}", "title": "c", "resolution": None, "parent": parent}))
    st = FsWorkStore.open(root)
    with pytest.raises(ValueError, match="still open: c-p"):
        st.complete("p", "done", [])
    with pytest.raises(ValueError, match="name it as their parent: c-q"):
        st.drop("q")


def test_cli_complete_force_is_refused_and_names_the_child(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root, _ = _board_with_child(tmp_path, "backlog")
    monkeypatch.chdir(root)
    code = main(["work", "complete", "p", "--resolution", "done", "--confirm", "--force"])
    assert code == 1
    assert "still open: c" in capsys.readouterr().err
    _assert_nothing_moved(root, "active/p")


# ── Task 6: every new child starts in backlog and records its parent ─────────

def _parent_in(st: FsWorkStore, status: str) -> str:
    p = st.create("Parent", created="2026-01-01").slug
    if status in ("active", "review"):
        st.start(p, owner="x")
    if status == "review":
        st.submit(p)
    assert st.get(p).status == status
    return p


@pytest.mark.parametrize("parent_status", ["backlog", "active", "review"])
def test_a_new_child_starts_in_backlog_and_records_its_parent(tmp_path, parent_status):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    p = _parent_in(st, parent_status)
    c = st.create("Child", created="2026-01-02", parent=p)
    assert st.path(c.slug) == root / "docs/work/backlog" / c.slug
    state = yaml.safe_load((st.path(c.slug) / "state.yaml").read_text())
    assert state["parent"] == p
    got = st.get(c.slug)
    assert (got.status, got.parent) == ("backlog", p)


@pytest.mark.parametrize("resolution", ["done", "wontfix"])
def test_a_child_cannot_be_created_under_a_resolved_item(tmp_path, resolution):
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    p = _parent_in(st, "active")
    st.complete(p, resolution, [])
    before = sorted((root / "docs/work/backlog").iterdir())
    with pytest.raises(ValueError, match="resolved"):
        st.create("Child", created="2026-01-02", parent=p)
    assert sorted((root / "docs/work/backlog").iterdir()) == before


def test_a_child_cannot_be_created_under_an_item_with_a_resolved_ancestor(tmp_path):
    root = node(tmp_path)
    _item(root, "discarded/g", resolution="wontfix")
    _item(root, "active/p", parent="g")
    _commit(root)
    with pytest.raises(ValueError, match="its ancestor g is"):
        FsWorkStore.open(root).create("Child", created="2026-01-02", parent="p")


def test_a_child_keeps_its_parent_through_its_own_transitions(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    p = _parent_in(st, "active")
    c = st.create("Child", created="2026-01-02", parent=p).slug
    for move in (lambda: st.start(c, owner="x"), lambda: st.submit(c),
                 lambda: st.rework(c), lambda: st.complete(c, "done", [])):
        move()
        assert st.get(c).parent == p
    assert st.get(c).status == "completed"


def test_starting_a_parent_leaves_its_child_in_backlog(tmp_path):
    st = FsWorkStore.open(node(tmp_path))
    p = st.create("Parent", created="2026-01-01").slug
    c = st.create("Child", created="2026-01-02", parent=p).slug
    st.start(p, owner="x")
    assert (st.get(c).status, st.get(c).parent) == ("backlog", p)
    st.start(c, owner="y")                       # and its own start still works
    assert st.get(c).status == "active"


def test_a_legacy_child_still_rides_its_parents_start(tmp_path):
    root = node(tmp_path)
    _item(root, "backlog/p")
    _legacy_child(root, "backlog", "p", "c")
    _commit(root)
    st = FsWorkStore.open(root)
    st.start("p", owner="x")
    assert (st.get("c").status, st.get("c").parent) == ("active", "p")
    assert (root / "docs/work/active/p/c/state.yaml").is_file()


def test_stage_gates_for_planning_pass_for_a_child_of_an_active_parent(
        tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    root = node(tmp_path)
    monkeypatch.chdir(root)
    st = FsWorkStore.open(root)
    p = _parent_in(st, "active")
    assert main(["work", "new", "Child", "--parent", p]) == 0
    c = capsys.readouterr().out.strip().splitlines()[-1].strip()
    folder = st.path(c)
    (folder / "intake.md").write_text("# Child\n\nraw\n")
    assert main(["work", "stage", "gate", "request", c]) == 0
    (folder / "initial-request.md").write_text("# Child\n\n## Request\n\ndo it\n")
    assert main(["work", "stage", "gate", "spec", c]) == 0
    (folder / "spec.md").write_text("# Spec\n")
    assert main(["work", "stage", "gate", "plan", c]) == 0
    assert "is not legal for an item in" not in capsys.readouterr().err

