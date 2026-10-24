"""A part in another project, files backend (TCW-114 Design 3.1, 3.2; AC 6;
plan Step 13): the part is made in its own project with `tcw -C`, naming its
epic by full identifier, and the epic's project is not written."""

from __future__ import annotations

import re

import pytest

from tests.objectcli import item, project, tcw  # noqa: F401
from tests.projectfiles import write_manifest
from tests.statefiles import ITEM_STATE, read_state

E, O = "2026-10-01-e", "2026-10-01-o"


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file() and ".git" not in p.parts}


@pytest.fixture
def planning_app(tmp_path):
    planning = project(tmp_path, "planning", work={})
    app = project(tmp_path, "app", work={})
    item(planning, E, "Epic")
    item(planning, O, "Other")
    write_manifest(planning, {"app": "../app"})
    write_manifest(app, {"planning": "../planning"})
    return planning, app


def test_a_part_is_made_in_its_own_project_naming_its_epic(tcw, planning_app):
    planning, app = planning_app
    before = snapshot(planning)
    result = tcw(["-C", "../app", "work", "new", "Add export", "--parent",
                  f"planning.work/{E}", "--blocked-by", f"planning.work/{O}",
                  "--priority", "high"], planning)
    assert result.code == 0, result.err
    assert re.fullmatch(r"app\.work/\d{4}-\d{2}-\d{2}-add-export\n", result.out)
    folder = result.out.strip().split("/", 1)[1]
    data = read_state(app / "docs" / "work" / folder / ITEM_STATE)
    assert data["parent"] == f"planning.work/{E}"
    assert data["blocked-by"] == [f"planning.work/{O}"]
    assert data["priority"] == "high"
    assert snapshot(planning) == before


def test_nest_with_an_epic_elsewhere_makes_the_folder_at_the_top(tcw, planning_app):
    planning, app = planning_app
    before = snapshot(planning)
    result = tcw(["-C", "../app", "work", "new", "Second part", "--parent",
                  f"planning.work/{E}", "--nest"], planning)
    assert result.code == 0, result.err
    assert "not nested:" in result.err
    folder = result.out.strip().split("/", 1)[1]
    assert "/" not in folder
    assert (app / "docs" / "work" / folder / ITEM_STATE).is_file()
    assert snapshot(planning) == before
