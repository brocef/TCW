"""`tcw migrate` as a command: its form, which project it runs in, and the
checks it is spared (TCW-116 Design 1.1, 1.2, 1.5, 8.1; criteria 1-3).

Every run is in-process (`tests/objectcli.py`'s `tcw`), so a test can patch
what a run calls; standard output is checked empty in every case.
"""

from __future__ import annotations

from pathlib import Path

from tcw.errors import NO_PROJECT
from tcw.project_files import legacy_message
from tests.objectcli import tcw  # noqa: F401  (a fixture)
from tests.projectfiles import write_config


def _three_x(root: Path, text: str = "id: app\n") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "tcw-config.yaml").write_text(text, encoding="utf-8")
    return root


def test_help_shows_the_two_flags_and_no_argument(tcw, tmp_path):
    done = tcw(["migrate", "--help"], tmp_path)
    assert done.code == 0
    usage = done.out.split("\n\n")[0]
    assert "[--dry-run]" in usage and "[--no-jira]" in usage
    assert usage.split("migrate", 1)[1].split() == ["[-h]", "[--dry-run]", "[--no-jira]"]


def test_an_argument_is_a_usage_error(tcw, tmp_path):
    done = tcw(["migrate", "x"], _three_x(tmp_path / "app"))
    assert done.code == 2
    assert done.out == ""


def test_outside_any_project_it_exits_1_with_the_common_message(tcw, tmp_path):
    done = tcw(["migrate", "--dry-run"], tmp_path)
    assert done.code == 1
    assert NO_PROJECT in done.err
    assert done.out == ""


def test_a_3x_project_is_not_refused_while_other_commands_are(tcw, tmp_path):
    app = _three_x(tmp_path / "app")
    done = tcw(["migrate", "--dry-run"], app)
    assert done.code == 0, done.err
    assert done.out == ""
    assert legacy_message(app.resolve()) not in done.err
    refused = tcw(["work", "list"], app)
    assert refused.code == 1
    assert legacy_message(app.resolve()) in refused.err


def test_dash_c_into_a_3x_project_runs_as_if_started_there(tcw, tmp_path):
    app = _three_x(tmp_path / "app")
    here = tmp_path / "here"
    write_config(here, "id: here\n")
    direct = tcw(["migrate", "--dry-run"], app)
    through = tcw(["-C", str(app), "migrate", "--dry-run"], here)
    assert (through.code, through.err, through.out) == (direct.code, direct.err, direct.out)


def test_a_configuration_problem_does_not_refuse_it(tcw, tmp_path):
    app = tmp_path / "app"
    write_config(app, "id: app\nwork:\n  no_such_key: 1\n")
    assert tcw(["work", "list"], app).code == 1
    done = tcw(["migrate", "--dry-run"], app)
    assert done.code == 0, done.err
    assert done.out == ""
