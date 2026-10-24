"""`tcw work new --project` and `tcw work edit --blocks` are refused, naming
the command to run instead (TCW-114 Design 2.1, 2.2; AC 5, AC 22's CLI half;
plan Step 7)."""

from __future__ import annotations

import json
import os
import shlex
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
    assert (f"tcw -C {core.resolve()} work edit core.work/{B} --blocked-by app.work/{A}"
            in result.err)
    assert (snapshot(app), snapshot(core)) == before


def suggested(err: str) -> list[str]:
    """The command a `--blocks` refusal names, as arguments after `tcw`."""
    import shlex
    command = err.split("record it on the blocked item instead: ", 1)[1]
    words = shlex.split(command.strip())
    assert words[0] == "tcw"
    return words[1:]


@pytest.mark.parametrize("typed", [A, f"app.work/{A}"])
def test_edit_with_blocks_in_another_project_names_this_item_in_full(
        tcw, app_core, typed):
    """However this item was typed, the other project is told its full
    identifier: a folder name there would be one of its own items."""
    app, core = app_core
    result = tcw(["work", "edit", typed, "--blocks", f"core.work/{B}"], app)
    assert result.code == 2
    assert f"--blocked-by app.work/{A}" in result.err


@pytest.mark.parametrize("typed", [A, f"app.work/{A}"])
def test_the_suggested_command_works_in_another_project(tcw, app_core, typed):
    app, core = app_core
    write_manifest(core, {"app": "../app"})
    result = tcw(["work", "edit", typed, "--blocks", f"core.work/{B}"], app)
    assert result.code == 2
    ran = tcw(suggested(result.err), app)
    assert ran.code == 0, ran.err
    state = (core / "docs" / "work" / B / "tcw-work-item.yaml").read_text()
    assert f"app.work/{A}" in state


@pytest.mark.parametrize("target", [B, f"app.work/{B}"])
def test_the_suggested_command_works_in_this_project(tcw, app_core, target):
    app, _ = app_core
    result = tcw(["work", "edit", A, "--blocks", target], app)
    assert result.code == 2
    ran = tcw(suggested(result.err), app)
    assert ran.code == 0, ran.err
    state = (app / "docs" / "work" / B / "tcw-work-item.yaml").read_text()
    assert f"app.work/{A}" in state


def test_edit_with_blocks_by_tracker_key_puts_this_project_before_it(tcw, app_core):
    """A key alone becomes `<this project>.work/<key>`, which the other
    project looks up in this one; no backend is opened to word it."""
    app, _ = app_core
    result = tcw(["work", "edit", "TCW-5", "--blocks", f"core.work/{B}"], app)
    assert result.code == 2
    assert result.err.rstrip().endswith("--blocked-by app.work/TCW-5")


def test_edit_with_blocks_naming_no_item_names_a_placeholder(tcw, app_core):
    """Decided by the implementing agent: text that names no item gives no
    identifier to repeat, so the command says where one goes."""
    app, _ = app_core
    result = tcw(["work", "edit", "Not.An/Item/..", "--blocks", f"core.work/{B}"], app)
    assert result.code == 2
    assert result.err.rstrip().endswith("--blocked-by <full id>")
    advised = result.err.rstrip().rsplit("instead: ", 1)[1]
    shlex.split(advised)                # no quote left open when pasted


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
    result = tcw(["project", "list", "--json"], app)
    assert result.code == 0, result.err
    rows = json.loads(result.out)["projects"]
    assert len(rows) == 2
    assert all("read-only" not in row for row in rows)
