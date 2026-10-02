"""`tcw capabilities drift` on the 3.0 work store (TCW-70 Design 10.3; the
library half of AC 16)."""

from tcw.capabilities.cli import _completed_but_missing
from tests.work.projects import make_project, write_item


def project(tmp_path):
    p = make_project(tmp_path, "p")
    (p / "docs" / "capabilities").mkdir(parents=True)
    return p


def test_a_completed_item_declaring_an_absent_capability_drifts(tmp_path):
    p = project(tmp_path)
    folder = write_item(p, "2026-10-01-a", {"title": "a", "stage": "completed"})
    (folder / "capabilities.yaml").write_text("new: [x/y]\n")
    [line] = _completed_but_missing(p, None)
    assert "x/y" in line and "2026-10-01-a" in line


def test_no_declaration_no_drift(tmp_path):
    p = project(tmp_path)
    write_item(p, "2026-10-01-a", {"title": "a", "stage": "completed"})
    assert _completed_but_missing(p, None) == []


def test_an_unfinished_item_is_not_drift(tmp_path):
    p = project(tmp_path)
    folder = write_item(p, "2026-10-01-a", {"title": "a", "stage": "implement"})
    (folder / "capabilities.yaml").write_text("new: [x/y]\n")
    assert _completed_but_missing(p, None) == []


def test_an_unreadable_item_is_named_and_the_rest_still_checked(tmp_path):
    p = project(tmp_path)
    folder = write_item(p, "2026-10-01-a", {"title": "a", "stage": "completed"})
    (folder / "capabilities.yaml").write_text("new: [x/y]\n")
    write_item(p, "2026-10-01-bad", "title: [x\n")
    lines = _completed_but_missing(p, None)
    assert any("x/y" in l for l in lines)
    assert any("2026-10-01-bad/item.yaml" in l for l in lines)
