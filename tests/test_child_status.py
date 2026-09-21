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
