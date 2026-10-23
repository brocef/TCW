"""Finding the owner of a full identifier (TCW-110 Design 6): two git
repositories side by side, `app` naming `core` under `projects.upstream` by
ID, with no `extends` unless a test adds one."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from tcw.errors import ProjectGraphError, Unreachable, UnknownProject
from tcw.ids import FullId
from tcw.locate import (ERROR, FOUND, MISSING, UNRESOLVED, Locator, outcome_of,
                        three_x_hint)
from tcw.store import project as project_module
from tcw.store.fs import FsCapabilitiesStore, FsTaxonomyStore, init
from tcw.store.project import FsProjectRegistry, begin_command, end_command
from tests.projectfiles import (config_file, connect_projects, write_config_file,
                                write_manifest)
from tests.work.jira.conftest import jira_config
from tests.work.projects import make_project, write_item


def _entry(root: Path, tree: str, path: str, **meta) -> None:
    folder = root / "docs" / tree / path
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "meta.yaml").write_text(yaml.safe_dump(
        {"name": path.rsplit("/", 1)[-1].title(), **meta}))
    (folder / "description.md").write_text("")


@pytest.fixture
def pair(tmp_path):
    app = make_project(tmp_path, "app", config={})
    core = make_project(tmp_path, "core", config={})
    for root in (app, core):
        init(["taxonomy", "capabilities"], root)
    _entry(core, "taxonomy", "term")
    _entry(core, "capabilities", "cli/x", id="cap-x", Status="Supported")
    connect_projects(app, "upstream", "core")
    return app.resolve(), core.resolve()


@pytest.fixture
def command():
    begin_command()
    yield
    end_command()


def test_owner_root_finds_a_named_project(pair):
    app, core = pair
    assert Locator.of(app).owner_root("core", named_by=app) == core


def test_owner_root_of_the_active_project_needs_no_lookup(pair, monkeypatch):
    app, _ = pair
    locator = Locator.of(app)
    monkeypatch.setattr(locator.registry, "project_folder",
                        lambda *a: pytest.fail("looked up"))
    assert locator.owner_root("app", named_by=app) == app


def test_a_named_project_whose_folder_is_gone_is_unreachable(pair):
    app, core = pair
    shutil.rmtree(core)
    with pytest.raises(Unreachable):
        Locator.of(app).owner_root("core", named_by=app)


def test_an_id_nothing_knows_is_unknown(pair):
    app, _ = pair
    with pytest.raises(UnknownProject) as raised:
        Locator.of(app).owner_root("cor", named_by=app)
    assert str(raised.value) == ("no project with ID 'cor' is known or found near "
                                 "this one; check the spelling")


def test_two_folders_declaring_one_id_are_a_graph_problem(pair, tmp_path):
    app, _ = pair
    one = make_project(tmp_path, "lib")
    two = make_project(tmp_path, "lib", name="lib-copy")
    with pytest.raises(ProjectGraphError) as raised:
        Locator.of(app).owner_root("lib", named_by=app)
    assert not isinstance(raised.value, UnknownProject)
    assert str(one.resolve()) in str(raised.value)
    assert str(two.resolve()) in str(raised.value)


@pytest.mark.parametrize("leave", [(), (".git",)])
def test_an_empty_folder_or_one_with_only_git_is_unreachable(pair, leave):
    """TCW-107: a manifest entry's folder that is empty, or holds only `.git`,
    is a project not on this machine."""
    app, core = pair
    write_manifest(app, {"core": "../core"})
    for child in core.iterdir():
        if child.name not in leave:
            shutil.rmtree(child) if child.is_dir() else child.unlink()
    assert outcome_of(_raised(lambda: Locator.of(app).owner_root("core", app))).kind \
        == UNRESOLVED


def test_a_folder_with_contents_and_no_project_is_a_graph_problem(pair):
    """TCW-107: a manifest entry's folder with other contents and no project
    is a problem in the graph, not an absence."""
    app, core = pair
    write_manifest(app, {"core": "../core"})
    shutil.rmtree(core / ".tcw")
    assert outcome_of(_raised(lambda: Locator.of(app).owner_root("core", app))).kind \
        == ERROR


def _raised(call) -> Exception:
    try:
        call()
    except Exception as error:
        return error
    pytest.fail("nothing was raised")


def test_read_finds_the_owners_own_entry(pair):
    app, _ = pair
    found = Locator.of(app).read(FullId("core", "taxonomy", "term"), named_by=app)
    assert found.kind == FOUND
    assert found.value.full_id == FullId("core", "taxonomy", "term")
    missing = Locator.of(app).read(FullId("core", "taxonomy", "missing"), app)
    assert missing.kind == MISSING and "core.taxonomy/missing" in missing.message


def test_read_of_an_absent_owner_is_unresolved(pair):
    app, core = pair
    shutil.rmtree(core)
    assert Locator.of(app).read(FullId("core", "taxonomy", "term"), app).kind == UNRESOLVED


def test_read_of_an_unknown_owner_is_an_error(pair):
    app, _ = pair
    found = Locator.of(app).read(FullId("cor", "taxonomy", "term"), app)
    assert found.kind == ERROR and "check the spelling" in found.message


def test_read_of_the_active_projects_own_entry(pair):
    app, _ = pair
    _entry(app, "capabilities", "web", id="cap-w", Status="Missing")
    found = Locator.of(app).read(FullId("app", "capabilities", "web"), app)
    assert found.kind == FOUND and found.value.status == "Missing"


def test_read_through_extends_is_the_active_projects_view(pair):
    """Design 6.2: with `app` extending `core`, a capability is read as `app`
    sees it, its local override applied; without, as `core` holds it."""
    app, _ = pair
    target = FullId("core", "capabilities", "cli/x")
    assert Locator.of(app).read(target, app).value.status == "Supported"
    FsCapabilitiesStore.open(app).extends_add("core")
    _entry(app, "capabilities", "ov/x", overrides="cap-x", Status="Omitted")
    assert Locator.of(app).read(target, app).value.status == "Omitted"
    FsTaxonomyStore.open(app).extends_add("core")
    term = Locator.of(app).read(FullId("core", "taxonomy", "term"), app)
    assert term.kind == FOUND and term.value.origin == "core"


def test_read_never_reaches_what_the_owner_itself_inherits(pair, tmp_path):
    app, core = pair
    base = make_project(tmp_path, "base", config={})
    init(["taxonomy"], base)
    _entry(base, "taxonomy", "deep")
    connect_projects(core, "upstream", "base")
    FsTaxonomyStore.open(core).extends_add("base")
    assert FsTaxonomyStore.open(core).get("base/deep") is not None
    assert Locator.of(app).read(FullId("core", "taxonomy", "deep"), app).kind == MISSING


def test_read_of_a_work_item_reads_the_owners_backend(pair):
    app, core = pair
    write_item(core, "2026-10-01-thing", {"title": "Thing", "stage": "request"})
    found = Locator.of(app).read(FullId("core", "work", "2026-10-01-thing"), app)
    assert found.kind == FOUND and found.value.title == "Thing"
    assert Locator.of(app).read(FullId("core", "work", "2026-10-01-none"), app).kind \
        == MISSING


def test_a_jira_owner_is_answered_by_its_folders_with_no_request(pair, monkeypatch):
    app, core = pair
    path = config_file(core)
    document = yaml.safe_load(path.read_text())
    document["work"] = jira_config("core")
    write_config_file(path, yaml.safe_dump(document, sort_keys=False))
    (core / "docs" / "work" / "TCW-5-thing").mkdir(parents=True)
    monkeypatch.setattr("urllib.request.urlopen",
                        lambda *a, **k: pytest.fail("a request was made"))
    locator = Locator.of(app)
    assert locator.read(FullId("core", "work", "TCW-5-thing"), app).kind == FOUND
    assert locator.read(FullId("core", "work", "TCW-6-none"), app).kind == MISSING


def test_one_locator_and_one_registry_per_command(pair, command, monkeypatch):
    app, core = pair
    built = []
    real = FsProjectRegistry.__init__

    def counted(self, *args, **kwargs):
        built.append(args)
        real(self, *args, **kwargs)
    monkeypatch.setattr(FsProjectRegistry, "__init__", counted)
    locator = Locator.of(app)
    assert Locator.of(app) is locator
    assert locator.owner_root("core", named_by=app) == core
    with pytest.raises(UnknownProject):
        locator.owner_root("elsewhere", named_by=core)
    assert len(built) == 1
    assert project_module._OPEN is not None


@pytest.mark.parametrize("id_path", ["Cli/x", "local/x", "x"])
def test_the_3x_hint_looks_nothing_up_unless_the_first_part_is_a_project_id(
        pair, monkeypatch, id_path):
    """Design 3.4: the hint is tried only for a multi-part id-path whose first
    part is a valid project ID."""
    app, _ = pair
    locator = Locator.of(app)
    monkeypatch.setattr(locator.registry, "project_folder",
                        lambda *a: pytest.fail("looked up"))
    assert three_x_hint(locator, "capabilities", id_path) == ""


def test_the_3x_hint_for_a_project_that_is_found(pair):
    app, _ = pair
    assert three_x_hint(Locator.of(app), "taxonomy", "core/term") == \
        "; to name an object in project 'core', write core.taxonomy/term"
