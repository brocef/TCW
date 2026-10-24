"""`tcw://` links in Markdown are object and folder addresses (TCW-110
Design 2, 6; AC 3, 13, 13a): `app` and `core` in two repositories side by
side, `core` named as a parent of `app` passing nothing (`inherit: none`),
with no `extends`."""

from __future__ import annotations

import io
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from tcw.cli import main
from tcw.store.fs import init
from tests.inherit import entry
from tests.projectfiles import connect_projects
from tests.work.projects import make_project, write_item


@dataclass
class Result:
    code: int
    out: str
    err: str


@pytest.fixture
def tcw(monkeypatch, capsys):
    def run(argv, cwd):
        monkeypatch.chdir(cwd)
        monkeypatch.setattr(sys, "stdin", io.StringIO(""))
        try:
            code = main(argv)
        except SystemExit as stop:
            code = stop.code if isinstance(stop.code, int) else 1
        captured = capsys.readouterr()
        return Result(code, captured.out, captured.err)
    return run


@pytest.fixture
def app(tmp_path) -> Path:
    app = make_project(tmp_path, "app", config={})
    core = make_project(tmp_path, "core", config={})
    for root in (app, core):
        init(["taxonomy", "capabilities"], root)
    entry(app, "capabilities", "cli/x", id="cap-x", Status="Supported")
    entry(core, "taxonomy", "term")
    write_item(app, "2026-10-01-thing", {"title": "Thing", "stage": "request"})
    connect_projects(app, "parent", "core", inherit="none")
    return app


def _link(app: Path, target: str) -> None:
    (app / "docs" / "capabilities" / "cli" / "x" / "description.md").write_text(
        f"See [t]({target}).\n")


def _line(out: str, target: str) -> str:
    [line] = [line for line in out.splitlines() if target in line]
    return line


@pytest.mark.parametrize("target", ["tcw://C/cli/x", "tcw://W/2026-10-01-thing",
                                    "tcw://core/T/term"])
def test_ac3_a_3x_link_is_an_error_naming_tcw_migrate(tcw, app, target):
    _link(app, target)
    checked = tcw(["validate"], app)
    assert checked.code == 1
    line = _line(checked.out, target)
    assert line.startswith("error: ")
    assert "TCW 3.x reference" in line and "tcw migrate" in line


@pytest.mark.parametrize("target", ["tcw://app.capabilities/cli/x",
                                    "tcw://app.work/2026-10-01-thing",
                                    "tcw://core.taxonomy/term"])
def test_a_link_to_an_object_that_is_there_passes(tcw, app, target):
    _link(app, target)
    checked = tcw(["validate"], app)
    assert checked.code == 0, checked.out


def test_ac13_a_link_into_a_project_not_inherited_from_is_checked(tcw, app):
    _link(app, "tcw://core.taxonomy/missing")
    checked = tcw(["validate"], app)
    assert checked.code == 1
    assert _line(checked.out, "tcw://core.taxonomy/missing").startswith("error: ")


def test_ac13_a_link_into_a_project_not_on_this_machine_is_unresolved(tcw, app):
    _link(app, "tcw://core.taxonomy/term")
    shutil.rmtree(app.parent / "core")
    checked = tcw(["validate"], app)
    assert checked.code == 0, checked.out
    assert _line(checked.out, "tcw://core.taxonomy/term").startswith("unresolved: ")


def test_ac13a_an_id_nothing_knows_is_an_error_at_the_link(tcw, app):
    _link(app, "tcw://cor.taxonomy/term")
    checked = tcw(["validate"], app)
    assert checked.code == 1
    line = _line(checked.out, "tcw://cor.taxonomy/term")
    assert line.startswith("error: docs/capabilities/cli/x/description.md")
    assert "no project with ID 'cor'" in line and "check the spelling" in line


def test_ac13a_two_folders_declaring_one_id_name_both_at_the_link(tcw, app, tmp_path):
    one = make_project(tmp_path, "lib")
    two = make_project(tmp_path, "lib", name="lib-copy")
    _link(app, "tcw://lib.taxonomy/term")
    checked = tcw(["validate"], app)
    assert checked.code == 1
    line = _line(checked.out, "tcw://lib.taxonomy/term")
    assert str(one.resolve()) in line and str(two.resolve()) in line


@pytest.mark.parametrize("target", ["tcw://core.path/docs", "tcw://core.path/no/such/folder"])
def test_a_folder_address_is_checked_for_its_project_not_its_folder(tcw, app, target):
    """Design 6.4."""
    _link(app, target)
    assert tcw(["validate"], app).code == 0
    _link(app, target.replace("core", "cor", 1))
    checked = tcw(["validate"], app)
    assert checked.code == 1
    assert "check the spelling" in checked.out
