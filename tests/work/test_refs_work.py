"""`tcw://` work addresses (TCW-70 Design 12.1, TCW-110 Design 2, 6; the
library half of AC 17)."""

import shutil

import pytest

from tcw.locate import ERROR, MISSING, UNRESOLVED
from tcw.refs import resolve_address
from tests.work.projects import connect, make_project, write_item


@pytest.mark.parametrize("stage", ["request", "completed", "discarded"])
def test_an_item_at_any_stage_resolves(tmp_path, stage):
    p = make_project(tmp_path, "p")
    write_item(p, "2026-10-01-a", {"title": "a", "stage": stage})
    result = resolve_address(p, "tcw://p.work/2026-10-01-a")
    assert (result.ok, result.namespace, result.key, result.project) == \
        (True, "work", "2026-10-01-a", "")


def test_a_missing_item_fails(tmp_path):
    p = make_project(tmp_path, "p")
    result = resolve_address(p, "tcw://p.work/2026-10-01-nothing")
    assert (result.ok, result.outcome) == (False, MISSING)
    assert "p.work/2026-10-01-nothing" in result.reason


def test_another_projects_item_names_its_owner(tmp_path):
    p = make_project(tmp_path, "p")
    q = make_project(tmp_path, "q")
    connect(p, q, "children")
    connect(q, p, "parent")
    write_item(q, "2026-10-01-x", {"title": "x", "stage": "spec"})
    result = resolve_address(p, "tcw://q.work/2026-10-01-x")
    assert (result.ok, result.key, result.project) == (True, "q.work/2026-10-01-x", "q")
    assert not resolve_address(p, "tcw://q.work/2026-10-01-nothing").ok


def test_an_absent_project_is_unresolved_and_an_unknown_one_an_error(tmp_path):
    p = make_project(tmp_path, "p")
    q = make_project(tmp_path, "q")
    connect(p, q, "children")
    shutil.rmtree(q)
    assert resolve_address(p, "tcw://q.work/2026-10-01-x").outcome == UNRESOLVED
    assert resolve_address(p, "tcw://nobody.work/2026-10-01-x").outcome == ERROR


# -- through `tcw validate` (AC 17) ---------------------------------------------------

def test_a_link_in_a_capability_description(tmp_path, capsys, monkeypatch):
    from tcw.cli import main
    p = make_project(tmp_path, "p")
    write_item(p, "2026-10-01-a", {"title": "a", "stage": "discarded"})
    cap = p / "docs" / "capabilities" / "area" / "do-a-thing"
    cap.mkdir(parents=True)
    description = cap / "description.md"
    monkeypatch.chdir(p)

    description.write_text("See [the work](tcw://p.work/2026-10-01-a).\n")
    code = main(["validate"])
    text = "".join(capsys.readouterr())
    assert "tcw://p.work/2026-10-01-a" not in text, text

    description.write_text("See [the work](tcw://p.work/2026-10-01-nothing).\n")
    code = main(["validate"])
    text = "".join(capsys.readouterr())
    assert code == 1 and "tcw://p.work/2026-10-01-nothing" in text
