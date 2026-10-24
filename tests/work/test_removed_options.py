"""`tcw work new --project` and `tcw work edit --blocks` are refused, naming
the command to run instead (TCW-114 Design 2.1, 2.2; AC 5, AC 22's CLI half;
plan Step 7)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

import pytest

from tests.objectcli import item, project, tcw  # noqa: F401
from tests.projectfiles import write_manifest

A, B = "2026-10-01-a", "2026-10-01-b"


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file()}


@pytest.fixture
def app_core(tmp_path):
    app = project(tmp_path, "app", work={})
    core = project(tmp_path, "core", work={})
    write_manifest(app, {"core": "../core"})
    item(app, A)
    item(app, B)
    item(core, B)
    return app, core


def test_new_with_project_is_refused_naming_minus_c(tcw, app_core):
    app, core = app_core
    before = snapshot(app), snapshot(core)
    result = tcw(["work", "new", "x", "--project", "core"], app)
    assert result.code == 2
    assert "work new --project is removed in TCW 4" in result.err
    assert "tcw -C tcw://core.path/ work new x --parent <full id>" in result.err
    assert (snapshot(app), snapshot(core)) == before


def test_new_with_project_does_not_wait_on_an_open_pipe(app_core, tmp_path):
    """Refused before piped input is read: a pipe that never closes does
    not hold it."""
    app, _ = app_core
    env = {k: v for k, v in os.environ.items() if not k.startswith("TCW_")}
    env.update(HOME=str(tmp_path / "home"), XDG_CONFIG_HOME=str(tmp_path / "xdg"),
               TCW_NO_PERSONAL_CONFIG="1")
    held = subprocess.Popen([sys.executable, "-m", "tcw.cli", "work", "new", "x",
                             "--project", "core"], cwd=app, env=env,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    try:
        # Standard input stays open: only the refusal ends the command.
        code = held.wait(timeout=10)
        err = held.stderr.read()
    finally:
        held.stdin.close()
        if held.poll() is None:
            held.kill()
    assert code == 2
    assert "work new --project is removed in TCW 4" in err


def test_edit_with_blocks_in_this_project(tcw, app_core):
    app, _ = app_core
    before = snapshot(app)
    result = tcw(["work", "edit", A, "--blocks", B], app)
    assert result.code == 2
    assert ("work edit --blocks is removed in TCW 4: record it on the blocked item "
            f"instead: tcw work edit {B} --blocked-by {A}") in result.err
    assert "tcw -C" not in result.err
    assert snapshot(app) == before


def test_edit_with_blocks_in_this_project_by_full_identifier(tcw, app_core):
    app, _ = app_core
    result = tcw(["work", "edit", A, "--blocks", f"app.work/{B}"], app)
    assert result.code == 2
    assert "tcw -C" not in result.err


def test_edit_with_blocks_in_another_project(tcw, app_core):
    app, core = app_core
    before = snapshot(app), snapshot(core)
    result = tcw(["work", "edit", A, "--blocks", f"core.work/{B}"], app)
    assert result.code == 2
    assert (f"tcw -C {core.resolve()} work edit core.work/{B} --blocked-by {A}"
            in result.err)
    assert (snapshot(app), snapshot(core)) == before


def test_edit_with_blocks_in_a_project_not_on_this_machine(tcw, app_core):
    app, core = app_core
    shutil.rmtree(core)
    result = tcw(["work", "edit", A, "--blocks", f"core.work/{B}"], app)
    assert result.code == 2
    assert f"tcw -C tcw://core.path/ work edit core.work/{B}" in result.err


@pytest.mark.parametrize("verb,option", [("new", "--project"), ("edit", "--blocks")])
def test_help_does_not_mention_the_removed_options(tcw, app_core, verb, option):
    app, _ = app_core
    result = tcw(["work", verb, "--help"], app)
    assert result.code == 0
    assert option not in result.out


def test_projects_list_has_no_read_only_key(tcw, app_core):
    from tests.projectfiles import connect_projects
    app, _ = app_core
    connect_projects(app, "parent", "core")
    result = tcw(["projects", "list", "--json"], app)
    assert result.code == 0, result.err
    rows = json.loads(result.out)["projects"]
    assert len(rows) == 2
    assert all("read-only" not in row for row in rows)
