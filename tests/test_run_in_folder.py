"""`tcw -C <folder | tcw://<id>[.<namespace>].path/>` (TCW-114 Design 4; AC 8,
AC 9, AC 10, and the `-C` half of AC 3; plan Steps 5 and 6): a command runs
as if `tcw` had been started in the folder chosen, and an address runs as
the project it names."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
import yaml

from tcw.cli import build_parser, main
from tests.objectcli import item, project, tcw  # noqa: F401
from tests.processes import allowed_read_only_git, recorded_processes  # noqa: F401
from tests.projectfiles import config_file, write_config_file, write_local_config
from tests.projectfiles import write_manifest
from tests.statefiles import ITEM_STATE, write_state_data

A = "2026-10-01-a"


def listed(result) -> list[str]:
    assert result.code == 0, result.err
    return result.out.split()


@pytest.fixture
def demo(tmp_path):
    root = project(tmp_path, "demo", work={})
    item(root, A, title="Alpha")
    return root


# -- AC 8: a folder path ----------------------------------------------------------------


def test_a_path_runs_the_command_there(tcw, demo, tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    there = tcw(["work", "list"], demo)
    from_elsewhere = tcw(["-C", str(demo), "work", "list"], empty)
    assert from_elsewhere.code == 0, from_elsewhere.err
    assert from_elsewhere.out == there.out
    assert "demo.work/2026-10-01-a" in there.out or A in there.out


def test_a_relative_path_and_two_of_them(tcw, tmp_path):
    inner = project(tmp_path / "a", "inner", work={}, name="b")
    item(inner, A)
    assert tcw(["-C", "a", "-C", "b", "work", "list"], tmp_path).out == \
        tcw(["work", "list"], inner).out
    assert tcw(["-C", "a/b", "work", "list"], tmp_path).code == 0


def test_a_missing_folder_is_a_usage_error_before_anything_is_read(tcw, tmp_path,
                                                                  monkeypatch):
    import tcw.cli as cli

    def fail(*_, **__):
        raise AssertionError("a project was looked for")
    monkeypatch.setattr(cli, "find_project_root", fail)
    monkeypatch.setattr(cli, "refuse_legacy_project", fail)
    result = tcw(["-C", "missing", "work", "list"], tmp_path)
    assert result.code == 2
    assert "cannot run in missing: no such folder" in result.err


def test_an_uppercase_scheme_is_a_refused_address_not_a_folder(tcw, demo):
    result = tcw(["-C", "TCW://demo.path/", "work", "list"], demo)
    assert result.code == 2
    assert "is not a tcw:// address" in result.err
    assert "no such folder" not in result.err


@pytest.mark.parametrize("argv,code", [
    (["work", "list"], 0),
    (["work", "show", "2026-10-01-zz"], 4),
])
def test_main_gives_the_callers_folder_back(demo, tmp_path, argv, code, monkeypatch):
    monkeypatch.chdir(tmp_path)
    before = os.getcwd()
    assert main(["-C", str(demo), *argv]) == code
    assert os.getcwd() == before


def test_main_gives_the_folder_back_on_a_broken_pipe(demo, tmp_path, monkeypatch):
    import tcw.cli as cli
    monkeypatch.chdir(tmp_path)
    before = os.getcwd()

    def broken(args, command):
        os.chdir(demo)
        raise BrokenPipeError
    monkeypatch.setattr(cli, "_dispatch", broken)
    # `main` points stdout at the null device on a broken pipe; not the
    # suite's own stdout.
    monkeypatch.setattr(cli.os, "dup2", lambda *_: None)
    assert main(["-C", str(demo), "work", "list"]) == 1
    assert os.getcwd() == before


def test_init_in_a_fresh_folder_inside_another_project(tcw, tmp_path):
    """AC 10's last part: relative paths are the chosen folder's."""
    ws = project(tmp_path, "workspace", work={})
    (ws / "fresh").mkdir()
    result = tcw(["-C", "fresh", "project", "new", "--id", "fresh", "--work-path", "board"], ws)
    assert result.code == 0, result.err
    assert (ws / "fresh" / ".tcw" / "tcw-config.yaml").is_file()
    assert (ws / "fresh" / "board").is_dir()
    assert not (ws / "board").exists()


def _three_x(folder: Path) -> Path:
    folder.mkdir()
    (folder / "tcw-config.yaml").write_text("version: 1\n")
    return folder


def test_a_path_reads_nothing_at_a_3x_starting_folder(tcw, demo, tmp_path):
    old = _three_x(tmp_path / "old")
    assert tcw(["work", "list"], old).code == 1
    assert tcw(["-C", str(demo), "work", "list"], old).code == 0


def test_help_lists_minus_c():
    assert "-C <folder or tcw://<id>.path/>" in build_parser().format_help()


# -- AC 9, AC 10: an address -----------------------------------------------------------


@pytest.fixture
def ws_app(tmp_path):
    """`workspace` and `app` side by side, `app`'s work store inside the
    workspace (UC-4), holding `<a>`; `app` placed in the workspace's
    manifest."""
    ws = project(tmp_path, "workspace", work={})
    app = project(tmp_path, "app", work={"path": "tcw://workspace.path/docs/app/work"})
    shutil.rmtree(app / "docs" / "work")
    write_manifest(ws, {"app": "../app"})
    folder = ws / "docs" / "app" / "work" / A
    folder.mkdir(parents=True)
    write_state_data(folder / ITEM_STATE, {"title": "Alpha", "stage": "request"})
    (folder / "request").mkdir()
    (folder / "request" / "request.md").write_text("Do it.\n")
    return ws, app


def test_an_address_runs_as_the_project_it_names(tcw, ws_app):
    ws, app = ws_app
    result = tcw(["-C", "tcw://app.path/", "work", "list"], ws)
    assert result.out == tcw(["work", "list"], app).out
    assert A in result.out


def test_an_object_address_is_refused_naming_the_path_form(tcw, ws_app):
    ws, _ = ws_app
    result = tcw(["-C", "tcw://app.work/x", "work", "list"], ws)
    assert result.code == 2
    assert ".path" in result.err and "names an object, not a folder" in result.err


def test_an_address_of_a_folder_in_another_project(tcw, ws_app):
    ws, _ = ws_app
    result = tcw(["-C", "tcw://app.work.path/", "work", "list"], ws)
    assert result.code == 2
    assert ("tcw://app.work.path/ is a folder of project 'workspace', so the command "
            "would run as 'workspace', not 'app'; give tcw://app.path/ to run as "
            "'app'") in result.err


def test_an_address_of_a_project_not_on_this_machine(tcw, ws_app):
    ws, _ = ws_app
    write_manifest(ws, {"gone": "../gone"})
    result = tcw(["-C", "tcw://gone.path/", "work", "list"], ws)
    assert result.code == 5
    assert "gone" in result.err


def test_an_address_of_an_unknown_project(tcw, ws_app):
    ws, _ = ws_app
    result = tcw(["-C", "tcw://cor.path/", "work", "list"], ws)
    assert result.code == 1
    assert "check the spelling" in result.err


def test_an_address_needs_a_project_to_start_from(tcw, ws_app, tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    result = tcw(["-C", "tcw://app.path/", "work", "list"], empty)
    assert result.code == 1
    assert ("tcw -C tcw://app.path/ needs a TCW project here to find 'app' from; give "
            "the folder's path instead") in result.err


def test_an_address_of_a_folder_in_no_project(tcw, tmp_path):
    lone = project(tmp_path, "lone", work={"path": "../board"})
    (tmp_path / "board").mkdir()
    result = tcw(["-C", "tcw://lone.work.path/", "work", "list"], lone)
    assert result.code == 2
    assert "which is in no TCW project; give tcw://lone.path/ to run as 'lone'" \
        in result.err


def test_an_address_from_a_3x_project_is_refused(tcw, ws_app, tmp_path):
    old = _three_x(tmp_path / "old")
    result = tcw(["-C", "tcw://app.path/", "work", "list"], old)
    assert result.code == 1
    assert "tcw migrate" in result.err


def test_a_resolved_folder_that_is_not_there(tcw, ws_app):
    ws, _ = ws_app
    result = tcw(["-C", "tcw://app.path/nowhere", "work", "list"], ws)
    assert result.code == 2
    assert "cannot run in tcw://app.path/nowhere: no such folder" in result.err


@pytest.mark.parametrize("argv", [
    ["-C", "tcw://app.path/", "work", "list"],
    ["-C", "tcw://app.path/", "work", "show", A],
    ["-C", "tcw://app.work.path/", "work", "list"],
    ["-C", "tcw://cor.path/", "work", "list"],
])
def test_minus_c_starts_only_read_only_git(tcw, ws_app, recorded_processes, argv):
    """The process rule (Design 4.6, plan choice 11): the worktree probe is
    cleared first, so it runs, and is checked, rather than passing by
    accident."""
    ws, _ = ws_app
    from tcw.store import project as registry_module
    registry_module._ANCHOR_CACHE.clear()
    tcw(argv, ws)
    assert recorded_processes, "the worktree probe did not run"
    assert all(allowed_read_only_git(p) for p in recorded_processes), recorded_processes


def test_personal_files_and_checks_are_the_named_projects(tcw, ws_app, tmp_path,
                                                         monkeypatch):
    """AC 10: `app`'s personal file names the user, and `app`'s `pre` check
    runs with `app`'s root; the workspace's do not."""
    ws, app = ws_app
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG")
    write_local_config(app, "user:\n  name: Alice\n")
    write_local_config(ws, "user:\n  name: Bob\n")
    made = tcw(["-C", "tcw://app.path/", "work", "new", "x", "--assign-me"], ws)
    assert made.code == 0, made.err
    full_id = made.out.split()[0]
    shown = tcw(["-C", "tcw://app.path/", "work", "show", full_id, "--json"], ws)
    assert '"Alice"' in shown.out

    seen, wrong = tmp_path / "seen.txt", tmp_path / "wrong.txt"
    _bind_pre(app, f'echo "$TCW_PROJECT_ROOT" > {seen}')
    _bind_pre(ws, f'echo ran > {wrong}')
    advanced = tcw(["-C", "tcw://app.path/", "work", "advance", A], ws)
    assert advanced.code == 0, advanced.err
    assert os.path.realpath(seen.read_text().strip()) == os.path.realpath(app)
    assert not wrong.exists()


def _bind_pre(root: Path, command: str) -> None:
    path = config_file(root)
    document = yaml.safe_load(path.read_text())
    document.setdefault("work", {})["stages"] = {"spec": {"pre": [{"command": command}]}}
    body = {k: v for k, v in document.items() if k != "version"}
    write_config_file(path, yaml.safe_dump(body, sort_keys=False))


def test_a_workspace_changes_an_item_it_holds_through_minus_c(tcw, ws_app):
    """AC 3's second half."""
    ws, _ = ws_app
    comments = ws / "docs" / "app" / "work" / A / "comments"
    before = set(comments.iterdir()) if comments.is_dir() else set()
    result = tcw(["-C", "tcw://app.path/", "work", "comment", f"app.work/{A}"], ws,
                 "a comment\n")
    assert result.code == 0, result.err
    assert len(set(comments.iterdir()) - before) == 1
