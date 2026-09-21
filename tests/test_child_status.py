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
