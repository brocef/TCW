"""Only the owning project changes anything, at the CLI (TCW-114 AC 1, AC 2,
and AC 3's first half; plan Step 3). Every fixture is two or more git
repositories side by side, each a 4.0 project with all three stores."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tests.objectcli import item, obj, project, tcw  # noqa: F401
from tests.projectfiles import connect_projects, write_manifest
from tests.statefiles import ITEM_STATE, write_state_data

C = "2026-10-01-c"


def snapshot(root: Path) -> dict[str, bytes]:
    """Every file under `root`, by path, with its bytes."""
    return {str(p.relative_to(root)): p.read_bytes()
            for p in sorted(Path(root).rglob("*")) if p.is_file()}


def assert_refused_naming(result, owner: str, folder: Path | None) -> None:
    """Exit 3, Design 1.3's shape, and where to go: the owner's folder with
    `tcw -C`, or nothing when `folder` is None."""
    assert result.code == 3, result.err
    assert f"belongs to project '{owner}'" in result.err
    assert "run the command in that project" not in result.err
    assert "change it in" not in result.err
    if folder is not None:
        assert f"tcw -C {folder.resolve()}" in result.err


@pytest.fixture
def app_core(tmp_path):
    """`app` and `core` side by side, `core` holding a files-backend item."""
    app = project(tmp_path, "app", work={})
    core = project(tmp_path, "core", work={})
    item(core, C)
    return app, core


def _fail_if_opened(monkeypatch):
    import tcw.work.open

    def fail(*_, **__):
        raise AssertionError("a backend of core was opened")
    monkeypatch.setattr(tcw.work.open, "open_project", fail)


WORK_WRITES = [
    (["work", "edit", f"core.work/{C}", "--priority", "high"], ""),
    (["work", "advance", f"core.work/{C}"], ""),
    (["work", "discard", f"core.work/{C}", "--reason", "x"], ""),
    (["work", "comment", f"core.work/{C}"], "a comment\n"),
    (["work", "rename", f"core.work/{C}", "other"], ""),
    pytest.param(["work", "move", f"core.work/{C}", "--top"], "", marks=pytest.mark.xfail(
        strict=True, reason="tcw work move arrives in Step 18")),
]


# -- AC 1 ----------------------------------------------------------------------------


@pytest.mark.parametrize("argv,stdin", WORK_WRITES, ids=lambda a: a[1] if
                         isinstance(a, list) else None)
def test_a_work_write_to_another_project_is_refused(tcw, app_core, argv, stdin,
                                                    monkeypatch):
    app, core = app_core
    before = snapshot(core)
    _fail_if_opened(monkeypatch)
    assert_refused_naming(tcw(argv, app, stdin), "core", core)
    assert snapshot(core) == before


@pytest.mark.parametrize("argv,stdin", WORK_WRITES, ids=lambda a: a[1] if
                         isinstance(a, list) else None)
def test_a_work_write_to_a_project_not_on_this_machine(tcw, app_core, argv, stdin,
                                                       monkeypatch):
    app, core = app_core
    shutil.rmtree(core)
    write_manifest(app, {"core": {"path": "../core",
                                  "repository": "https://example.invalid/core.git"}})
    _fail_if_opened(monkeypatch)
    result = tcw(argv, app, stdin)
    assert_refused_naming(result, "core", None)
    assert "project 'core' is not on this machine (https://example.invalid/core.git)" \
        in result.err


def test_a_work_write_naming_a_project_nothing_names(tcw, app_core, monkeypatch):
    app, core = app_core
    shutil.rmtree(core)
    _fail_if_opened(monkeypatch)
    result = tcw(["work", "edit", f"core.work/{C}", "--priority", "high"], app)
    assert_refused_naming(result, "core", None)
    assert "project 'core' is not on this machine" in result.err


def test_a_work_write_naming_a_project_two_folders_declare(tcw, tmp_path, monkeypatch):
    """Locating never changes the exit: a graph problem is still exit 3."""
    app = project(tmp_path, "app", work={})
    for name in ("core-a", "core-b"):
        item(project(tmp_path, "core", work={}, name=name), C)
    _fail_if_opened(monkeypatch)
    result = tcw(["work", "edit", f"core.work/{C}", "--priority", "high"], app)
    assert_refused_naming(result, "core", None)
    assert "project 'core' cannot be located: " in result.err
    assert "not on this machine" not in result.err


def test_a_ticket_key_in_another_projects_identifier_is_refused_first(tcw, app_core,
                                                                    monkeypatch):
    app, core = app_core
    _fail_if_opened(monkeypatch)
    assert_refused_naming(tcw(["work", "comment", "core.work/CORE-1"], app, "x\n"),
                          "core", core)


def test_the_active_projects_own_item_is_still_written(tcw, app_core):
    app, _ = app_core
    item(app, "2026-10-01-a")
    assert tcw(["work", "edit", "app.work/2026-10-01-a", "--priority", "high"],
               app).code == 0
    assert tcw(["work", "edit", "2026-10-01-a", "--priority", "low"], app).code == 0


# -- AC 2 ----------------------------------------------------------------------------


@pytest.fixture
def family(tmp_path):
    """`app` with parent `core` passing taxonomy and capabilities, `core`
    holding term `t` and capability `cli/x`, and `other` beside them naming
    no parent."""
    app = project(tmp_path, "app", work={})
    core = project(tmp_path, "core", work={})
    other = project(tmp_path, "other", work={})
    connect_projects(app, "parent", "core", inherit=["taxonomy", "capabilities"])
    write_manifest(app, {"core": "../core"})
    write_manifest(other, {"core": "../core"})
    obj(core, "taxonomy", "t", name="T", kind="Vocabulary")
    obj(core, "capabilities", "cli/x", name="X", Status="Missing")
    return app, core, other


TREE_WRITES = [
    pytest.param(["taxonomy", "rm", "core.taxonomy/t"], id="taxonomy-rm"),
    pytest.param(["taxonomy", "rename", "core.taxonomy/t", "u"], id="taxonomy-rename",
                 marks=pytest.mark.xfail(strict=True, reason="arrives in Step 19")),
    pytest.param(["capabilities", "rm", "core.capabilities/cli/x"], id="capabilities-rm"),
    pytest.param(["capabilities", "move", "core.capabilities/cli/x", "--top"],
                 id="capabilities-move",
                 marks=pytest.mark.xfail(strict=True, reason="arrives in Step 19")),
]


@pytest.mark.parametrize("argv", TREE_WRITES)
def test_a_tree_write_to_another_project_is_refused(tcw, family, argv):
    app, core, _ = family
    before = snapshot(core)
    assert_refused_naming(tcw(argv, app), "core", core)
    assert snapshot(core) == before


def test_rm_says_the_one_shape(tcw, family):
    app, core, _ = family
    result = tcw(["capabilities", "rm", "core.capabilities/cli/x"], app)
    assert "core.capabilities/cli/x belongs to project 'core'; run the command " \
           "there: tcw -C" in result.err
    assert "cannot remove" not in result.err


@pytest.mark.parametrize("argv", [["capabilities", "rm", "core.capabilities/cli/x"],
                                  ["taxonomy", "rm", "core.taxonomy/t"]])
def test_rm_of_a_project_not_on_this_machine_is_still_refused(tcw, family, argv):
    """Before this item these exited 4 or 5 from the lookup (review M4)."""
    app, core, _ = family
    shutil.rmtree(core)
    result = tcw(argv, app)
    assert_refused_naming(result, "core", None)
    assert "is not on this machine" in result.err


def test_overriding_an_inherited_capability_is_allowed(tcw, family):
    app, core, _ = family
    before = snapshot(core)
    result = tcw(["capabilities", "set", "core.capabilities/cli/x", "--status",
                  "Supported"], app)
    assert result.code == 0, result.err
    assert (app / "docs" / "capabilities" / "cli" / "x" / "tcw-capability.yaml").is_file()
    assert snapshot(core) == before


def test_set_in_a_project_that_does_not_inherit_it(tcw, family):
    _, core, other = family
    result = tcw(["capabilities", "set", "core.capabilities/cli/x", "--status",
                  "Supported"], other)
    assert_refused_naming(result, "core", core)
    assert ("belongs to project 'core', and 'other' does not inherit it, so it cannot "
            "be overridden here; run the command there: tcw -C") in result.err


def test_set_with_the_owner_gone(tcw, family):
    """In `app`, `core` is a source, so deciding that the write is an
    override needs `core`'s content (exit 7); in `other`, `core` is no
    source and is refused before anything is read (TCW-112's order)."""
    app, core, other = family
    shutil.rmtree(core)
    argv = ["capabilities", "set", "core.capabilities/cli/x", "--status", "Supported"]
    assert tcw(argv, app).code == 7
    result = tcw(argv, other)
    assert_refused_naming(result, "core", None)
    assert "is not on this machine" in result.err


# -- AC 3, the first half --------------------------------------------------------------


@pytest.fixture
def workspace(tmp_path):
    """`workspace` and `app` side by side, `app`'s work store inside the
    workspace's repository, holding item `<a>`."""
    ws = project(tmp_path, "workspace", work={})
    app = project(tmp_path, "app", work={"path": "tcw://workspace.path/docs/app/work"})
    shutil.rmtree(app / "docs" / "work")
    folder = ws / "docs" / "app" / "work" / "2026-10-01-a"
    folder.mkdir(parents=True)
    write_state_data(folder / ITEM_STATE, {"title": "A", "stage": "request"})
    return ws, app


@pytest.mark.parametrize("argv,stdin", [
    (["work", "comment", "app.work/2026-10-01-a"], "hi\n"),
    (["work", "edit", "app.work/2026-10-01-a", "--priority", "low"], ""),
    (["work", "advance", "app.work/2026-10-01-a"], ""),
])
def test_a_workspace_cannot_change_the_items_it_holds(tcw, workspace, argv, stdin):
    ws, app = workspace
    before = snapshot(ws / "docs" / "app" / "work")
    assert_refused_naming(tcw(argv, ws, stdin), "app", app)
    assert snapshot(ws / "docs" / "app" / "work") == before
