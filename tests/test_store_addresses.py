"""Where a store lives (TCW-110 Design 7): a plain location in the shared
file is relative to the project, or a `tcw://` folder address; each fixture
is a set of git repositories side by side under `tmp_path`."""

from __future__ import annotations

import io
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from tcw.cli import main
from tcw.store.fs import init
from tests.projectfiles import config_file, write_config_file
from tests.work.projects import git, make_project

RELATIVE = "must be a path relative to the project"


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


def set_location(root: Path, component: str, value: str) -> None:
    path = config_file(root)
    document = yaml.safe_load(path.read_text())
    section = document.get(component)
    document[component] = {**(section if isinstance(section, dict) else {}), "path": value}
    write_config_file(path, yaml.safe_dump(document, sort_keys=False))


def _says_relative(text: str, key: str) -> None:
    assert f"{key}: {RELATIVE}" in text or f"{key} {RELATIVE}" in text, text
    assert "tcw://" in text and ".tcw/tcw-manifest.local.yaml" in text


# -- AC 24: a plain location is relative (Design 7.1) -----------------------------------


@pytest.mark.parametrize("component", ["work", "taxonomy", "capabilities"])
@pytest.mark.parametrize("value", ["/tmp/x", "~/x"])
def test_ac24_an_absolute_or_home_location_stops_every_command(tcw, tmp_path, component,
                                                               value):
    app = make_project(tmp_path, "app", config={})
    init(["taxonomy", "capabilities"], app)
    set_location(app, component, value)
    listed = tcw(["work", "list"], app)
    assert listed.code == 1
    _says_relative(listed.err, f"{component}.path")
    checked = tcw(["validate"], app)
    assert checked.code == 1
    [line] = [line for line in checked.out.splitlines() if f"{component}.path" in line]
    assert line.startswith("error: ")
    _says_relative(line, f"{component}.path")


@pytest.mark.parametrize("flag, key", [("--work-path", "work.path"),
                                       ("--taxonomy-path", "taxonomy.path"),
                                       ("--capabilities-path", "capabilities.path")])
@pytest.mark.parametrize("value", ["/abs/store", "~/store"])
def test_ac24_init_refuses_an_absolute_or_home_location_and_writes_nothing(
        tcw, tmp_path, flag, key, value):
    """`init` refuses a tcw:// value for these options, so its message does
    not offer one, as the message for a location read from the file does."""
    root = tmp_path / "fresh"
    root.mkdir()
    git(root, "init", "-q")
    component = key.split(".")[0]
    found = tcw(["project", "new", "--id", "fresh", flag, value, component], root)
    assert found.code == 2
    assert f"{key} {RELATIVE}" in found.err, found.err
    assert "tcw://" not in found.err and ".tcw/tcw-manifest.local.yaml" in found.err
    assert sorted(p.name for p in root.iterdir()) == [".git"]


# -- folder addresses as store locations (Design 7.2, 7.3; AC 14, 15, 17) --------------


def _project(tmp_path: Path, project_id: str) -> Path:
    return make_project(tmp_path, project_id, config={})


def test_ac14_a_work_store_in_a_workspace_folder(tcw, tmp_path):
    workspace = _project(tmp_path, "workspace")
    (workspace / "docs" / "app" / "work").mkdir(parents=True)
    app = _project(tmp_path, "app")
    set_location(app, "work", "tcw://workspace.path/docs/app/work")
    made = tcw(["work", "new", "Add login"], app)
    assert made.code == 0, made.err
    full_id = made.out.strip().splitlines()[-1]
    assert full_id.startswith("app.work/")
    folder = full_id.split("/", 1)[1]
    store = (workspace / "docs" / "app" / "work").resolve()
    assert (store / folder).is_dir()
    shown = tcw(["work", "path", folder], app)
    assert Path(shown.out.strip()).resolve() == store / folder
    checked = tcw(["validate"], app)
    assert checked.code == 0, checked.out + checked.err


def test_ac14_a_folder_part_dot_dot_is_refused(tcw, tmp_path):
    _project(tmp_path, "workspace")
    app = _project(tmp_path, "app")
    set_location(app, "work", "tcw://workspace.work.path/../app")
    for argv in (["work", "list"], ["validate"]):
        found = tcw(argv, app)
        assert found.code == 1, found
        assert "'..'" in found.out + found.err


def test_ac15_a_store_inside_another_projects_store(tcw, tmp_path):
    workspace = _project(tmp_path, "workspace")
    (workspace / "docs" / "work" / "app").mkdir(parents=True)
    app = _project(tmp_path, "app")
    set_location(app, "work", "tcw://workspace.work.path/app")
    from tcw.store.fs import WorkLocation
    assert WorkLocation.open(app).root == (workspace / "docs" / "work" / "app").resolve()


def test_ac15_store_locations_that_loop_stop_every_command(tcw, tmp_path):
    p1 = _project(tmp_path, "p1")
    p2 = _project(tmp_path, "p2")
    set_location(p2, "work", "tcw://p1.work.path/x")
    set_location(p1, "work", "tcw://p2.work.path/y")
    found = tcw(["work", "list"], p2)
    assert found.code == 1
    assert "work.path: store locations loop: p2 work -> p1 work -> p2 work" in found.err


def test_ac15_a_location_naming_its_own_store_is_the_shortest_loop(tcw, tmp_path):
    p2 = _project(tmp_path, "p2")
    set_location(p2, "work", "tcw://p2.work.path/x")
    found = tcw(["work", "list"], p2)
    assert found.code == 1
    assert "store locations loop: p2 work -> p2 work" in found.err


def test_ac17_a_location_in_a_project_not_on_this_machine_exits_5(tcw, tmp_path):
    from tests.projectfiles import write_manifest
    app = _project(tmp_path, "app")
    write_manifest(app, {"gone": "../gone"})
    set_location(app, "work", "tcw://gone.path/w")
    found = tcw(["work", "list"], app)
    assert found.code == 5, found
    assert "gone" in found.err


def test_ac17_a_misspelt_project_exits_1_saying_check_the_spelling(tcw, tmp_path):
    app = _project(tmp_path, "app")
    set_location(app, "work", "tcw://gonne.path/w")
    found = tcw(["work", "list"], app)
    assert found.code == 1
    assert "check the spelling" in found.err


def test_ac17_with_a_repository_declared_the_declaration_answers(tcw, tmp_path,
                                                                 monkeypatch):
    from tests.projectfiles import write_manifest
    from tests.test_store_provisioning import _remote_with_store
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    remote = _remote_with_store(tmp_path)
    app = _project(tmp_path, "app")
    write_manifest(app, {"gone": "../gone"})
    path = config_file(app)
    document = yaml.safe_load(path.read_text())
    document["work"] = {"path": "tcw://gone.path/w",
                        "repository": {"url": str(remote), "path": "docs/work/corelib"}}
    write_config_file(path, yaml.safe_dump(document, sort_keys=False))
    before = tcw(["work", "list"], app)
    assert before.code == 1 and "tcw project provision" in before.err, before
    assert tcw(["project", "provision"], app).code == 0
    after = tcw(["work", "list"], app)
    assert after.code == 0, after.err


def test_an_object_address_is_refused_as_a_location_naming_the_path_form(tcw, tmp_path):
    app = _project(tmp_path, "app")
    set_location(app, "work", "tcw://app.work/x")
    found = tcw(["work", "list"], app)
    assert found.code == 1
    assert "names an object, not a folder" in found.err and ".path/" in found.err


def test_an_address_of_this_projects_own_folder_is_the_plain_path(tmp_path):
    from tcw.store.fs import WorkLocation
    app = _project(tmp_path, "app")
    plain = WorkLocation.open(app).root
    set_location(app, "work", "tcw://app.path/docs/work")
    assert WorkLocation.open(app).root == plain


@pytest.mark.parametrize("component", ["taxonomy", "capabilities"])
def test_a_tree_store_at_a_folder_address(tmp_path, component):
    from tcw.store.fs import STORE_CLASSES
    workspace = _project(tmp_path, "workspace")
    (workspace / "trees" / component).mkdir(parents=True)
    app = _project(tmp_path, "app")
    set_location(app, component, f"tcw://workspace.path/trees/{component}")
    assert STORE_CLASSES[component].open(app).root == \
        (workspace / "trees" / component).resolve()


@pytest.mark.parametrize("component", ["work", "taxonomy", "capabilities"])
def test_validate_reports_a_location_in_an_absent_project_at_its_key(tcw, tmp_path,
                                                                     component):
    from tests.projectfiles import write_manifest
    app = _project(tmp_path, "app")
    init(["taxonomy", "capabilities"], app)
    write_manifest(app, {"gone": "../gone"})
    set_location(app, component, "tcw://gone.path/w")
    checked = tcw(["validate"], app)
    assert checked.code == 0, checked.out + checked.err
    [line] = [line for line in checked.out.splitlines() if f"{component}.path" in line]
    assert line.startswith("unresolved: .tcw/tcw-config.yaml: ") and "'gone'" in line


@pytest.mark.parametrize("component", ["work", "taxonomy", "capabilities"])
@pytest.mark.parametrize("address, words", [
    ("tcw://gonne.path/w", "check the spelling"),
    ("tcw://app.work/x", "names an object, not a folder"),
])
def test_validate_reports_an_unusable_location_as_an_error_at_its_key(
        tcw, tmp_path, component, address, words):
    app = _project(tmp_path, "app")
    init(["taxonomy", "capabilities"], app)
    set_location(app, component, address)
    checked = tcw(["validate"], app)
    assert checked.code == 1
    [line] = [line for line in checked.out.splitlines() if f"{component}.path" in line]
    assert line.startswith("error: .tcw/tcw-config.yaml: ") and words in line


def test_init_builds_a_store_at_its_folder_address(tcw, tmp_path):
    """Design 7.5: `tcw project new` finds the folder as the readers do."""
    workspace = _project(tmp_path, "workspace")
    app = _project(tmp_path, "app")
    set_location(app, "taxonomy", "tcw://workspace.path/trees/app")
    made = tcw(["project", "new", "taxonomy"], app)
    assert made.code == 0, made.err
    assert (workspace / "trees" / "app").is_dir()
    assert not (app / "docs" / "taxonomy").exists()


# -- stores never nest or coincide (Design 7.4; AC 15, 16) ---------------------------


def _overlap(out: str) -> list[str]:
    return [line for line in out.splitlines()
            if "same folder as" in line or "lies inside" in line]


def _workspace_and_app(tmp_path: Path) -> tuple[Path, Path]:
    from tests.projectfiles import connect_projects
    workspace = _project(tmp_path, "workspace")
    app = _project(tmp_path, "app")
    connect_projects(app, "parent", "workspace", inherit="none")
    return workspace, app


def test_ac15_a_store_inside_another_projects_store_fails_validate(tcw, tmp_path):
    workspace = _project(tmp_path, "workspace")
    (workspace / "docs" / "work" / "app").mkdir(parents=True)
    app = _project(tmp_path, "app")
    set_location(app, "work", "tcw://workspace.work.path/app")
    checked = tcw(["validate"], app)
    assert checked.code == 1
    [line] = _overlap(checked.out)
    assert "the work store of project 'app'" in line and "lies inside" in line
    assert "the work store of project 'workspace'" in line


def test_ac16_a_plain_path_to_another_projects_store_fails(tcw, tmp_path):
    workspace, app = _workspace_and_app(tmp_path)
    set_location(app, "work", "../workspace/docs/work")
    checked = tcw(["validate"], app)
    assert checked.code == 1
    [line] = _overlap(checked.out)
    assert "is the same folder as" in line
    assert str((workspace / "docs" / "work").resolve()) in line


def test_ac16_a_symlink_does_not_hide_the_same_folder(tcw, tmp_path):
    workspace, app = _workspace_and_app(tmp_path)
    (tmp_path / "link").symlink_to(workspace / "docs" / "work")
    set_location(app, "work", "../link")
    checked = tcw(["validate"], app)
    assert checked.code == 1
    assert len(_overlap(checked.out)) == 1, checked.out


def test_ac16_two_stores_of_one_project_may_not_nest(tcw, tmp_path):
    app = _project(tmp_path, "app")
    init(["capabilities"], app)
    (app / "docs" / "capabilities" / "terms").mkdir()
    set_location(app, "taxonomy", "docs/capabilities/terms")
    checked = tcw(["validate"], app)
    assert checked.code == 1
    [line] = _overlap(checked.out)
    assert "the taxonomy store of project 'app'" in line
    assert "the capabilities store of project 'app'" in line


def test_ac16_a_sibling_of_another_projects_store_is_allowed(tcw, tmp_path):
    workspace, app = _workspace_and_app(tmp_path)
    (workspace / "docs" / "app-work").mkdir()
    set_location(app, "work", "tcw://workspace.path/docs/app-work")
    checked = tcw(["validate"], app)
    assert checked.code == 0, checked.out
    assert _overlap(checked.out) == []


def test_ac16_a_jira_projects_work_store_counts_and_jira_is_not_asked(
        tcw, tmp_path, monkeypatch):
    from tests.work.jira.conftest import jira_config
    workspace, app = _workspace_and_app(tmp_path)
    path = config_file(workspace)
    document = yaml.safe_load(path.read_text())
    document["work"] = jira_config("workspace")
    write_config_file(path, yaml.safe_dump(document, sort_keys=False))
    monkeypatch.setattr("urllib.request.urlopen",
                        lambda *a, **k: pytest.fail("a request was made"))
    set_location(app, "work", "../workspace/docs/work")
    checked = tcw(["validate"], app)
    assert checked.code == 1
    assert len(_overlap(checked.out)) == 1, checked.out


def test_a_worktree_of_this_project_is_not_compared_with_itself(tcw, tmp_path):
    from tests.work.projects import commit_all
    app = _project(tmp_path, "app")
    commit_all(app)
    git(app, "worktree", "add", "-q", str(tmp_path / "app-wt"))
    checked = tcw(["validate"], tmp_path / "app-wt")
    assert checked.code == 0, checked.out + checked.err
    assert _overlap(checked.out) == []
