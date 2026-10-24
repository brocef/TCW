"""`tcw project path [<id>]` (TCW-115 Design 5; AC 9, 10, 11, and AC 37's
second half): the folder of a project on this machine, as every other command
in this project finds it."""

from __future__ import annotations

import shutil

import pytest

from tests.projectfiles import connect_projects, write_config, write_manifest
from tests.test_cli_contract import run, snapshot
from tests.test_projects_list import ac6
from tests.work.projects import make_project


def path_of(cwd, *argv):
    done = run(cwd, "project", "path", *argv)
    assert (done.code, done.err) == (0, ""), done
    return done.out


# -- AC 9: found ---------------------------------------------------------------------

def test_ac9_each_project_of_the_graph(tmp_path):
    app = ac6(tmp_path).resolve()
    (app / "docs").mkdir(exist_ok=True)
    before = snapshot(tmp_path)
    for cwd in (app, app / "docs"):
        assert path_of(cwd, "core") == f"{tmp_path.resolve() / 'core'}\n"
        assert path_of(cwd, "k") == f"{tmp_path.resolve() / 'x' / 'k'}\n"
        assert path_of(cwd) == f"{app}\n"
        assert path_of(cwd, "app") == f"{app}\n"
    assert snapshot(tmp_path) == before


def test_ac9_a_sibling_named_by_an_ancestor(tmp_path):
    ws = make_project(tmp_path, "ws")
    app2 = make_project(ws, "app2")
    b = make_project(ws, "b")
    connect_projects(ws, "children", "app2", "b")
    write_manifest(ws, {"app2": "app2", "b": "b"})
    for child in (app2, b):
        connect_projects(child, "parent", "ws")
        write_manifest(child, {"ws": ".."})
    assert path_of(app2, "b") == f"{b.resolve()}\n"


# -- AC 10: not found ------------------------------------------------------------------

def test_ac10_not_here_with_a_repository_names_provision(tmp_path):
    app = ac6(tmp_path)
    remote = tmp_path / "remotes" / "k.git"
    write_manifest(app, {"k": {"path": "../x/k", "repository": f"{remote}#main"}})
    shutil.rmtree(tmp_path / "x" / "k")
    done = run(app, "project", "path", "k")
    assert (done.code, done.out) == (5, ""), done
    assert "tcw project provision k" in done.err and str(remote) in done.err, done.err


def test_ac10_not_here_with_no_repository(tmp_path):
    app = ac6(tmp_path)
    shutil.rmtree(tmp_path / "x" / "k")
    done = run(app, "project", "path", "k")
    assert (done.code, done.out) == (5, ""), done
    assert "tcw project provision" not in done.err, done.err


def test_ac10_an_unknown_id(tmp_path):
    app = ac6(tmp_path)
    done = run(app, "project", "path", "nope")
    assert (done.code, done.out) == (1, ""), done
    assert "check the spelling" in done.err, done.err


def test_ac10_an_id_that_is_not_valid_is_a_usage_error(tmp_path):
    app = ac6(tmp_path)
    done = run(app, "project", "path", "Nope")
    assert (done.code, done.out) == (2, ""), done


def test_ac10_two_folders_for_one_id_names_both(tmp_path):
    app = ac6(tmp_path)
    one = make_project(tmp_path, "lib", name="lib-one")
    two = make_project(tmp_path, "lib", name="lib-two")
    done = run(app, "project", "path", "lib")
    assert (done.code, done.out) == (1, ""), done
    assert one.name in done.err and two.name in done.err, done.err


def test_outside_a_project(tmp_path):
    done = run(tmp_path, "project", "path", "core")
    assert (done.code, done.out) == (1, ""), done
    assert "no TCW project here" in done.err, done.err


# -- AC 11: a linked worktree -----------------------------------------------------------

def test_ac11_in_a_linked_worktree(tmp_path):
    from tests.test_manifest_worktree import repository_with_worktree
    app = tmp_path / "app"
    write_config(app, "id: app\n")
    make_project(tmp_path, "lib")
    worktree = repository_with_worktree(app, tmp_path / "trees" / "app-feature")
    assert path_of(worktree) == f"{worktree}\n"
    assert path_of(worktree, "lib") == f"{tmp_path.resolve() / 'lib'}\n"


# -- AC 37, second half: a leftover staging folder is not a second copy -----------------

def test_ac37_a_leftover_staging_folder_is_not_found(tmp_path):
    app = ac6(tmp_path)
    staged = tmp_path / ".tcw-staging-0123abcd"
    staged.mkdir()
    shutil.copytree(tmp_path / "core", staged / "core")
    assert path_of(app, "core") == f"{tmp_path.resolve() / 'core'}\n"


@pytest.mark.parametrize("argv", [("project", "path"), ("project", "path", "core")])
def test_it_writes_nothing(tmp_path, argv):
    app = ac6(tmp_path)
    before = snapshot(tmp_path)
    run(app, *argv)
    assert snapshot(tmp_path) == before
