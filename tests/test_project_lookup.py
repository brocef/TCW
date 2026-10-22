"""Finding a project's folder from its ID (TCW-107 Design 2), at the library
level: `FsProjectRegistry.project_folder` called directly, and the graph walk
that uses the same lookup for every `projects:` entry that holds only an ID.

The commands built on it are tested in `tests/test_manifest_cli.py`, and the
git worktree rules in `tests/test_manifest_worktree.py`.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from tcw import exit as codes
from tcw.errors import ProjectGraphError, Unreachable, UnknownProject
from tcw.store import project as project_module
from tcw.store.project import FsProjectRegistry
from tests.projectfiles import write_config, write_config_file, write_manifest


def proj(root: Path, project_id: str, **relations) -> Path:
    """A 4.0 project at `root` declaring `project_id`; each relation is a
    list of IDs written under `projects:` with no location."""
    data: dict = {"id": project_id}
    if relations:
        data["projects"] = {name: {i: None for i in ids}
                            for name, ids in relations.items()}
    write_config(root, yaml.safe_dump(data, sort_keys=False))
    return root.resolve()


def lookup(active: Path, project_id: str, named_by: Path | None = None) -> Path:
    registry = FsProjectRegistry.open(active)
    return registry.project_folder(project_id, (named_by or active).resolve())


def texts(registry) -> str:
    return "\n".join(f"{f.where}: {f.message}" for f in registry.check())


@pytest.fixture
def reads(monkeypatch):
    """Counts of every file the registry reads and every folder it lists."""
    counted = {"read": [], "list": []}
    real_read, real_list = project_module._read_text, project_module._list_folder

    def read(path):
        counted["read"].append(Path(path))
        return real_read(path)

    def listing(path):
        counted["list"].append(Path(path))
        return real_list(path)

    monkeypatch.setattr(project_module, "_read_text", read)
    monkeypatch.setattr(project_module, "_list_folder", listing)
    return counted


# ---------------------------------------------------------------------------
# AC 24: the function, for any ID


def test_a_project_next_to_the_naming_one_is_found(tmp_path):
    app = proj(tmp_path / "app", "app")
    lib = proj(tmp_path / "lib", "lib")
    assert lookup(app, "lib") == lib


def test_a_project_only_the_manifest_lists_is_found(tmp_path):
    app = proj(tmp_path / "app", "app")
    lib = proj(tmp_path / "x" / "lib", "lib")
    write_manifest(app, {"lib": "../x/lib"})
    assert lookup(app, "lib") == lib


def test_its_own_id_is_its_own_folder(tmp_path):
    app = proj(tmp_path / "app", "app")
    assert lookup(app, "app") == app


def test_an_entry_whose_folder_is_absent_is_not_on_this_machine(tmp_path):
    app = proj(tmp_path / "app", "app")
    proj(tmp_path / "lib", "lib")         # never second-guessed by the search
    manifest = write_manifest(app, {"lib": {"path": "../gone",
                                            "repository": "https://h/lib.git#main"}})
    with pytest.raises(Unreachable) as raised:
        lookup(app, "lib")
    message = str(raised.value)
    assert message == (f"project 'lib' is not on this machine: {manifest} places it "
                       f"at ../gone, from https://h/lib.git#main; fetch it with "
                       f"'tcw project provision lib'")
    assert raised.value.code == codes.UNREACHABLE
    # TCW-114's handoff: the deciding entry's repository as an attribute.
    assert raised.value.project == "lib"
    assert raised.value.repository == "https://h/lib.git#main"


def test_an_entry_without_a_repository_names_no_command(tmp_path):
    app = proj(tmp_path / "app", "app")
    manifest = write_manifest(app, {"lib": "../gone"})
    with pytest.raises(Unreachable) as raised:
        lookup(app, "lib")
    assert str(raised.value) == (f"project 'lib' is not on this machine: {manifest} "
                                 f"places it at ../gone")
    assert raised.value.repository is None


def test_an_id_nothing_names_or_holds_is_unknown(tmp_path):
    app = proj(tmp_path / "app", "app")
    with pytest.raises(UnknownProject) as raised:
        lookup(app, "nope")
    assert raised.value.code == codes.ERROR == 1
    assert "check the spelling" in str(raised.value)
    assert isinstance(raised.value, ProjectGraphError)


def test_an_id_the_naming_project_names_and_nothing_holds_is_not_here(tmp_path):
    app = proj(tmp_path / "app", "app", upstream=["lib"])
    with pytest.raises(Unreachable) as raised:
        lookup(app, "lib")
    assert str(raised.value) == (
        f"project 'lib' is not on this machine: no manifest lists it, and no folder "
        f"next to {app} or enclosing it declares it; add it to "
        f".tcw/tcw-manifest.yaml or .tcw/tcw-manifest.local.yaml")


def test_two_folders_next_to_it_are_a_graph_problem_naming_both(tmp_path):
    app = proj(tmp_path / "app", "app")
    one = proj(tmp_path / "lib", "lib")
    two = proj(tmp_path / "lib-copy", "lib")
    registry = FsProjectRegistry.open(app)
    with pytest.raises(ProjectGraphError) as raised:
        registry.project_folder("lib", app)
    assert not isinstance(raised.value, UnknownProject)
    for named in (str(one), str(two), ".tcw/tcw-manifest.local.yaml",
                  ".tcw/tcw-manifest.yaml"):
        assert named in str(raised.value)
    assert str(one) in texts(registry) and str(two) in texts(registry)


def test_a_later_call_finding_another_folder_is_the_duplicate_id(tmp_path):
    """Design 2.9: the graph found `core` at one folder; a call from `lib`,
    whose manifest places `core` at a second folder, is a graph problem."""
    app = proj(tmp_path / "app", "app", children=["lib"], upstream=["core"])
    lib = proj(tmp_path / "app" / "lib", "lib", parent=["app"])
    first = proj(tmp_path / "core1", "core")
    second = proj(tmp_path / "core2", "core")
    write_manifest(app, {"lib": "lib", "core": "../core1"})
    write_manifest(lib, {"core": "../../core2"})
    registry = FsProjectRegistry.open(app)
    assert registry.check() == []
    assert Path(registry.get("core").locator) == first
    with pytest.raises(ProjectGraphError) as raised:
        registry.project_folder("core", lib)
    assert str(first) in str(raised.value) and str(second) in str(raised.value)
    assert str(second) in texts(registry)


def test_a_second_identical_call_reads_nothing(tmp_path, reads):
    app = proj(tmp_path / "app", "app")
    lib = proj(tmp_path / "lib", "lib")
    registry = FsProjectRegistry.open(app)
    assert registry.project_folder("lib", app) == lib
    before = (len(reads["read"]), len(reads["list"]))
    assert before[0] > 0 and before[1] > 0, "the counters see the first call"
    assert registry.project_folder("lib", app) == lib
    assert (len(reads["read"]), len(reads["list"])) == before


def test_a_folder_the_registry_has_not_found_is_a_programming_error(tmp_path):
    app = proj(tmp_path / "app", "app")
    stranger = proj(tmp_path / "far" / "away", "away")
    with pytest.raises(ValueError):
        FsProjectRegistry.open(app).project_folder("lib", stranger)


def test_a_folder_an_earlier_call_returned_may_name_another(tmp_path):
    """`named_by` may be a folder an earlier call returned; the registry reads
    its configuration to learn its family (Design 2.12)."""
    app = proj(tmp_path / "app", "app")
    lib = proj(tmp_path / "x" / "lib", "lib")
    core = proj(tmp_path / "y" / "core", "core")
    write_manifest(app, {"lib": "../x/lib"})
    write_manifest(lib, {"core": "../../y/core"})
    registry = FsProjectRegistry.open(app)
    assert registry.project_folder("lib", app) == lib
    assert registry.project_folder("core", lib) == core


def test_the_ordering_of_except_clauses_matters_for_the_two_graph_errors(tmp_path):
    """`UnknownProject` is a `ProjectGraphError`, so a caller handling both
    must catch `UnknownProject` first, or a misspelt ID is reported as a
    broken graph. The two outcomes, from real calls, routed both ways."""
    app = proj(tmp_path / "app", "app")
    proj(tmp_path / "lib", "lib")
    proj(tmp_path / "lib-copy", "lib")

    def unknown_first(call):
        try:
            call()
        except UnknownProject:
            return "misspelt"
        except ProjectGraphError:
            return "graph"

    def graph_first(call):
        try:
            call()
        except ProjectGraphError:
            return "graph"
        except UnknownProject:         # never reached: the subclass is caught above
            return "misspelt"

    registry = FsProjectRegistry.open(app)
    nope = lambda: registry.project_folder("nope", app)       # noqa: E731
    two = lambda: registry.project_folder("lib", app)         # noqa: E731
    assert (unknown_first(nope), unknown_first(two)) == ("misspelt", "graph")
    assert graph_first(nope) == "graph", "the wrong order misroutes a misspelt ID"


# ---------------------------------------------------------------------------
# Design 2.3: the deciding entry's folder


@pytest.mark.parametrize("contents", ["absent", "empty", ".git file", ".git folder"])
def test_an_absent_or_empty_entry_folder_is_not_on_this_machine(tmp_path, contents):
    app = proj(tmp_path / "app", "app")
    folder = tmp_path / "lib"
    if contents != "absent":
        folder.mkdir()
    if contents == ".git file":
        (folder / ".git").write_text("gitdir: ../somewhere\n")
    if contents == ".git folder":
        (folder / ".git").mkdir()
    write_manifest(app, {"lib": "../lib"})
    with pytest.raises(Unreachable):
        lookup(app, "lib")


def test_an_entry_folder_holding_only_git_says_so(tmp_path):
    """TCW-115's handoff: the fetch command refuses a folder holding only
    `.git`, so the message says to finish or remove it first."""
    app = proj(tmp_path / "app", "app")
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / ".git").mkdir()
    write_manifest(app, {"lib": {"path": "../lib", "repository": "https://h/l.git"}})
    with pytest.raises(Unreachable) as raised:
        lookup(app, "lib")
    message = str(raised.value)
    assert "../lib holds only .git; finish or remove it with git" in message
    assert message.index("holds only .git") < message.index("tcw project provision")


@pytest.mark.parametrize("name", ["README.md", ".DS_Store"])
def test_an_entry_folder_with_contents_and_no_project_is_a_graph_problem(tmp_path, name):
    app = proj(tmp_path / "app", "app")
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / name).write_text("x\n")
    manifest = write_manifest(app, {"lib": "../lib"})
    with pytest.raises(ProjectGraphError) as raised:
        lookup(app, "lib")
    assert str(manifest) in str(raised.value)
    assert str((tmp_path / "lib").resolve()) in str(raised.value)


def test_an_entry_folder_that_cannot_be_listed_is_a_graph_problem(tmp_path):
    app = proj(tmp_path / "app", "app")
    folder = tmp_path / "lib"
    (folder / "inner").mkdir(parents=True)
    write_manifest(app, {"lib": "../lib"})
    folder.chmod(0)
    try:
        if os.access(folder, os.R_OK):
            pytest.skip("this test runs with permission to read the folder anyway")
        with pytest.raises(ProjectGraphError):
            lookup(app, "lib")
    finally:
        folder.chmod(0o755)


def test_an_entry_folder_declaring_another_id_names_both(tmp_path):
    app = proj(tmp_path / "app", "app")
    proj(tmp_path / "lib", "other")
    write_manifest(app, {"lib": "../lib"})
    with pytest.raises(ProjectGraphError) as raised:
        lookup(app, "lib")
    assert "'lib'" in str(raised.value) and "'other'" in str(raised.value)


def test_an_entry_folder_holding_a_3x_project_or_a_newer_version(tmp_path):
    from tcw.project_files import LEGACY_PROJECT
    app = proj(tmp_path / "app", "app")
    (tmp_path / "old").mkdir()
    (tmp_path / "old" / "tcw-config.yaml").write_text("id: old\n")
    write_config(tmp_path / "new", "tcw-version: 99.0.0\nid: new\n")
    write_manifest(app, {"old": "../old", "new": "../new"})
    registry = FsProjectRegistry.open(app)
    with pytest.raises(ProjectGraphError) as raised:
        registry.project_folder("old", app)
    assert LEGACY_PROJECT in str(raised.value)
    with pytest.raises(ProjectGraphError) as raised:
        registry.project_folder("new", app)
    assert "upgrade TCW" in str(raised.value)


def test_a_manifest_with_a_problem_is_not_used_and_the_lookup_fails(tmp_path):
    app = proj(tmp_path / "app", "app")
    proj(tmp_path / "lib", "lib")
    manifest = write_manifest(app, "projects: {lib: /abs/lib}\n")
    registry = FsProjectRegistry.open(app)
    assert str(manifest) in texts(registry)          # reported with nothing looked up
    with pytest.raises(ProjectGraphError) as raised:
        registry.project_folder("lib", app)
    assert str(manifest) in str(raised.value)


def test_the_personal_manifest_decides_before_the_shared_one(tmp_path, monkeypatch):
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG")
    app = proj(tmp_path / "app", "app")
    shared = proj(tmp_path / "lib", "lib")
    mine = proj(tmp_path / "mine" / "lib", "lib")
    write_manifest(app, {"lib": "../lib"})
    write_manifest(app, {"lib": str(mine)}, local=True)
    assert lookup(app, "lib") == mine
    monkeypatch.setenv("TCW_NO_PERSONAL_CONFIG", "1")
    assert lookup(app, "lib") == shared


def test_entries_never_merge(tmp_path, monkeypatch):
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG")
    app = proj(tmp_path / "app", "app")
    write_manifest(app, {"lib": {"path": "../gone", "repository": "https://h/l.git"}})
    write_manifest(app, {"lib": "../gone2"}, local=True)
    with pytest.raises(Unreachable) as raised:
        lookup(app, "lib")
    assert "../gone2" in str(raised.value)
    assert "https://h/l.git" not in str(raised.value)
    assert raised.value.repository is None


def test_the_variable_decides_over_every_manifest(tmp_path, monkeypatch):
    app = proj(tmp_path / "app", "app")
    proj(tmp_path / "lib", "lib")
    elsewhere = proj(tmp_path / "v" / "lib", "lib")
    write_manifest(app, {"lib": "../lib"})
    monkeypatch.setenv("TCW_PROJECT_LIB", str(elsewhere))
    assert lookup(app, "lib") == elsewhere


# ---------------------------------------------------------------------------
# Design 2.2: the walk over the family's manifests, and its end


def test_a_children_cycle_ends_the_walk_and_is_reported(tmp_path):
    p = proj(tmp_path / "p", "p", parent=["q"], children=["q"])
    proj(tmp_path / "q", "q", parent=["p"], children=["p"])
    registry = FsProjectRegistry.open(p)
    with pytest.raises(UnknownProject):
        registry.project_folder("z", p)
    assert "cycle in projects" in texts(registry)


def test_a_parent_cycle_ends_the_walk(tmp_path):
    r = proj(tmp_path / "r", "r", parent=["p"])
    proj(tmp_path / "p", "p", parent=["q"], children=["r"])
    proj(tmp_path / "q", "q", parent=["p"], children=["p"])
    registry = FsProjectRegistry.open(r)
    with pytest.raises(UnknownProject):
        registry.project_folder("z", r)
    assert registry.check()


def test_an_id_only_reciprocal_pair_is_not_said_to_point_elsewhere(tmp_path):
    app = proj(tmp_path / "app", "app", children=["lib"])
    proj(tmp_path / "lib", "lib", parent=["app"])
    registry = FsProjectRegistry.open(app)
    assert registry.check() == []
    assert "does not point back" not in texts(registry)


def test_an_id_only_upstream_reading_a_parent_claim_is_not_said_to_point_elsewhere(tmp_path):
    app = proj(tmp_path / "app", "app", upstream=["lib"])
    proj(tmp_path / "lib", "lib", parent=["app"])
    registry = FsProjectRegistry.open(app)
    assert "does not point back" not in texts(registry)
    assert any("read as an upstream project" in w for w in registry.warnings())


def test_an_ancestors_manifest_places_a_project(tmp_path):
    """AC 5, at the library level."""
    shared = proj(tmp_path / "shared", "shared", children=["desktop"])
    desktop = proj(tmp_path / "shared" / "desktop", "desktop", parent=["shared"],
                   upstream=["core"])
    core = proj(tmp_path / "x" / "core", "core")
    write_manifest(shared, {"desktop": "desktop", "core": "../x/core"})
    registry = FsProjectRegistry.open(desktop)
    assert registry.check() == []
    assert Path(registry.get("shared").locator) == shared
    assert registry.found("shared") == {"by": "search"}
    assert Path(registry.get("core").locator) == core
    assert registry.found("core") == {"by": "manifest",
                                      "file": str(shared / ".tcw/tcw-manifest.yaml")}
    assert registry.found("desktop") is None


def test_an_upstreams_manifest_is_not_read(tmp_path):
    """AC 5a."""
    app = proj(tmp_path / "app", "app", upstream=["lib", "y"])
    lib = proj(tmp_path / "lib", "lib")
    proj(tmp_path / "x" / "y", "y")
    write_manifest(lib, {"y": "../x/y"})
    registry = FsProjectRegistry.open(app)
    assert registry.get("lib") is not None
    assert registry.get("y") is None
    assert [u.id for u in registry.unreachable()] == ["y"]


def test_a_descendants_manifest_and_the_own_one_first(tmp_path):
    """AC 6."""
    docs = proj(tmp_path / "docs", "docs", children=["shared"], upstream=["core"])
    shared = proj(tmp_path / "docs" / "shared", "shared", parent=["docs"])
    core = proj(tmp_path / "x" / "core", "core")
    write_manifest(docs, {"shared": "shared"})
    write_manifest(shared, {"core": "../../x/core"})
    registry = FsProjectRegistry.open(docs)
    assert registry.check() == []
    assert Path(registry.get("core").locator) == core
    assert registry.found("core")["file"] == str(shared / ".tcw/tcw-manifest.yaml")
    copy = proj(tmp_path / "y" / "core", "core")
    write_manifest(docs, {"core": "../y/core"})
    registry = FsProjectRegistry.open(docs)
    assert Path(registry.get("core").locator) == copy


def test_next_to_and_enclosing(tmp_path):
    """AC 9."""
    app = proj(tmp_path / "app", "app", children=["shared"])
    shared = proj(tmp_path / "app" / "packages" / "shared", "shared", parent=["app"],
                  upstream=["other"])
    proj(tmp_path / "app" / "other", "other")
    write_manifest(app, {"shared": "packages/shared"})
    registry = FsProjectRegistry.open(shared)
    assert registry.check() == []
    assert Path(registry.get("app").locator) == app
    assert registry.found("app") == {"by": "search"}
    assert registry.get("other") is None          # next to an enclosing folder
    pkg = proj(tmp_path / "app" / "a" / "b" / "pkg", "pkg", parent=["app"])
    write_config(app, yaml.safe_dump({"id": "app", "projects": {
        "children": {"shared": None, "pkg": None}}}))
    write_manifest(app, {"pkg": "a/b/pkg"})
    registry = FsProjectRegistry.open(pkg)
    assert Path(registry.get("app").locator) == app


def test_never_downwards(tmp_path):
    """AC 10."""
    app = proj(tmp_path / "app", "app", children=["shared"])
    shared = proj(tmp_path / "app" / "packages" / "shared", "shared", parent=["app"],
                  upstream=["dep"])
    proj(tmp_path / "app" / "node_modules" / "dep", "dep")
    registry = FsProjectRegistry.open(app)
    assert registry.get("shared") is None
    write_config(app, yaml.safe_dump({"id": "app", "projects": {
        "children": {"shared": None}, "upstream": {"dep": None}}}))
    write_manifest(app, {"shared": "packages/shared"})
    for active in (app, shared):
        assert FsProjectRegistry.open(active).get("dep") is None


def test_two_matches_and_an_entry_settles_them(tmp_path):
    """AC 11, at the library level: beside, and beside plus enclosing."""
    app = proj(tmp_path / "app", "app", upstream=["lib"])
    proj(tmp_path / "lib", "lib")
    proj(tmp_path / "lib-copy", "lib")
    assert ".tcw/tcw-manifest.local.yaml" in texts(FsProjectRegistry.open(app))
    write_manifest(app, {"lib": "../lib"})
    registry = FsProjectRegistry.open(app)
    assert registry.check() == []
    outer = proj(tmp_path / "o" / "lib", "lib")
    inner = proj(tmp_path / "o" / "lib" / "app", "app", upstream=["lib"])
    beside = proj(tmp_path / "o" / "lib" / "lib2", "lib")
    problems = texts(FsProjectRegistry.open(inner))
    assert str(outer) in problems and str(beside) in problems


def test_one_folder_per_id_in_the_walk(tmp_path):
    """AC 12."""
    app = proj(tmp_path / "app", "app", children=["lib"], upstream=["core"])
    lib = proj(tmp_path / "app" / "lib", "lib", parent=["app"], upstream=["core"])
    one = proj(tmp_path / "c1", "core")
    two = proj(tmp_path / "c2", "core")
    write_manifest(app, {"lib": "lib", "core": "../c1"})
    write_manifest(lib, {"core": "../../c2"})
    problems = texts(FsProjectRegistry.open(app))
    assert "duplicate project id 'core'" in problems
    assert str(one) in problems and str(two) in problems


def test_unreadable_candidates_are_not_matches(tmp_path):
    """AC 13."""
    from tcw.project_files import LEGACY_PROJECT
    app = proj(tmp_path / "app", "app", upstream=["lib"])
    lib = proj(tmp_path / "lib", "lib")
    write_config_file(tmp_path / "broken" / ".tcw" / "tcw-config.yaml", "id: [x\n")
    locked = tmp_path / "locked"
    write_config(locked, "id: lib\n")
    locked.chmod(0)
    try:
        registry = FsProjectRegistry.open(app)
        if not os.access(locked, os.R_OK):
            assert registry.check() == []
            assert Path(registry.get("lib").locator) == lib
    finally:
        locked.chmod(0o755)
    import shutil
    shutil.rmtree(locked)
    write_config(tmp_path / "newer", "tcw-version: 99.0.0\nid: lib\n")
    problems = texts(FsProjectRegistry.open(app))
    assert str((tmp_path / "newer").resolve()) in problems and "upgrade TCW" in problems
    shutil.rmtree(tmp_path / "newer")
    (tmp_path / "older").mkdir()
    (tmp_path / "older" / "tcw-config.yaml").write_text("id: lib\n")
    problems = texts(FsProjectRegistry.open(app))
    assert LEGACY_PROJECT in problems


def test_a_tcw_folder_next_to_the_root_is_never_a_candidate(tmp_path):
    """Design 2.4: from `shared/desktop`, `shared/.tcw/` holds a
    `tcw-config.yaml` with no `.tcw/` of its own; it is not a 3.x project."""
    shared = proj(tmp_path / "shared", "shared", children=["desktop"])
    desktop = proj(tmp_path / "shared" / "desktop", "desktop", parent=["shared"])
    write_manifest(shared, {"desktop": "desktop"})
    registry = FsProjectRegistry.open(desktop)
    assert str(shared / ".tcw") not in texts(registry)
    assert registry.check() == []


def test_one_answer_whichever_project_runs(tmp_path):
    """AC 25."""
    app = proj(tmp_path / "app", "app", children=["a"])
    a = proj(tmp_path / "app" / "packages" / "a", "a", parent=["app"], children=["k"])
    k = proj(tmp_path / "app" / "plugins" / "k", "k", parent=["a"])
    write_manifest(app, {"a": "packages/a", "k": "plugins/k"})
    in_a = FsProjectRegistry.open(a)
    assert in_a.check() == [] and in_a.unreachable() == []
    assert Path(in_a.get("k").locator) == k
    assert in_a.found("k")["file"] == str(app / ".tcw/tcw-manifest.yaml")
    assert Path(FsProjectRegistry.open(app).get("k").locator) == k


def test_the_walk_visits_the_parent_before_the_children(tmp_path):
    """Design 2.11 (a): the parent's manifest is there for a child's lookup."""
    app = proj(tmp_path / "app", "app", children=["a"])
    a = proj(tmp_path / "app" / "packages" / "a", "a", parent=["app"],
             children=["k"])
    proj(tmp_path / "app" / "plugins" / "k", "k", parent=["a"])
    write_manifest(app, {"a": "packages/a", "k": "plugins/k"})
    registry = FsProjectRegistry.open(a)
    # Children first, `k` was looked up before `app` had been found, and so
    # without `app`'s manifest.
    assert [p.id for p in registry.projects()] == ["a", "app", "k"]



def test_the_search_never_reads_inside_a_protected_folder_next_to_it(
        tmp_path, monkeypatch, reads):
    """macOS asks a person's permission before a program reads inside
    Desktop, Documents or Downloads. For a project kept directly in the home
    folder those are folders next to it, so the search does not test them
    (implement-stage decision, TCW-107 round 1). A folder of another name is
    still tested."""
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(project_module, "_ON_MACOS", True)
    app = proj(home / "proj", "app")
    for name in ("Desktop", "Documents", "Downloads"):
        proj(home / name, "lib")
    with pytest.raises(UnknownProject):
        lookup(app, "lib")
    touched = [p for p in reads["read"] + reads["list"]
               if any(part in ("Desktop", "Documents", "Downloads") for part in p.parts)]
    assert touched == []
    other = proj(home / "Projects", "lib")
    assert lookup(app, "lib") == other


def test_the_note_for_a_project_not_here_is_design_6_2s_message(tmp_path):
    from tcw.store.fs import unreachable_project_note
    app = proj(tmp_path / "app", "app", upstream=["lib"])
    manifest = write_manifest(app, {"lib": {"path": "../gone",
                                            "repository": "https://h/lib.git"}})
    note = unreachable_project_note(FsProjectRegistry.open(app), "lib")
    assert note == (f"project 'lib' is not on this machine: {manifest} places it at "
                    f"../gone, from https://h/lib.git; fetch it with "
                    f"'tcw project provision lib'")
    assert "tcw provision`" not in note


# ---------------------------------------------------------------------------
# Design 2.13: one registry per command


@pytest.fixture
def command():
    """One command's span, as `tcw.cli._dispatch` makes it."""
    from tcw import config as layered
    layered.begin_command()
    yield
    layered.end_command()


def test_ac27_each_candidate_is_read_once_by_the_registry(tmp_path, monkeypatch, reads):
    from tcw.cli import main
    app = proj(tmp_path / "app", "app", children=["shared"])
    shared = proj(tmp_path / "app" / "packages" / "shared", "shared", parent=["app"])
    proj(tmp_path / "app" / "packages" / "neighbour", "neighbour")
    write_manifest(app, {"shared": "packages/shared"})
    opened: dict[Path, list] = {}
    real_open = FsProjectRegistry.open.__func__

    def counting_open(cls, root):
        registry = real_open(cls, root)
        opened.setdefault(Path(root).resolve(), []).append(registry)
        return registry

    monkeypatch.setattr(FsProjectRegistry, "open", classmethod(counting_open))
    monkeypatch.chdir(shared)
    assert main(["validate"]) == 0
    assert reads["list"].count(shared.parent) == 1
    for folder in (shared.parent / "neighbour", shared.parent, app, app.parent):
        for name in (".tcw/tcw-config.yaml", "tcw-config.yaml"):
            assert reads["read"].count(folder / name) <= 1, (folder, name)
    assert len(opened[shared]) >= 2, "the command opens the registry more than once"
    assert all(r is opened[shared][0] for r in opened[shared])


def test_a_write_drops_the_registry_within_the_command(tmp_path, command):
    from tcw.store.fs import _atomic_write_all, write_sentinel
    root = tmp_path / "p"
    write_config(root, "projects:\n  upstream:\n    lib:\n")
    first = FsProjectRegistry.open(root)
    assert FsProjectRegistry.open(root) is first
    assert write_sentinel(root, "fresh")
    second = FsProjectRegistry.open(root)
    assert second is not first and second.current.id == "fresh"
    assert second.declared_upstream_ids() == ["lib"]
    _atomic_write_all([(root / ".tcw" / "tcw-manifest.yaml",
                        "tcw-version: 4.0.0\nprojects: {lib: ../lib}\n")])
    third = FsProjectRegistry.open(root)
    assert third is not second
    assert third.unreachable_project("lib").decided_by == root.resolve() / ".tcw/tcw-manifest.yaml"


def test_a_write_of_another_file_keeps_the_registry(tmp_path, command):
    from tcw.store.fs import _atomic_write_all
    root = proj(tmp_path / "p", "p")
    first = FsProjectRegistry.open(root)
    _atomic_write_all([(root / "notes.md", "x\n")])
    assert FsProjectRegistry.open(root) is first


def test_outside_a_command_every_open_reads_afresh(tmp_path):
    root = proj(tmp_path / "p", "p")
    assert FsProjectRegistry.open(root) is not FsProjectRegistry.open(root)


def test_a_registry_whose_load_raised_is_not_kept(tmp_path, monkeypatch, command):
    root = proj(tmp_path / "p", "p")
    real = FsProjectRegistry._load_graph
    calls = []

    def once(self):
        calls.append(self)
        if len(calls) == 1:
            raise RuntimeError("load failed")
        return real(self)

    monkeypatch.setattr(FsProjectRegistry, "_load_graph", once)
    with pytest.raises(RuntimeError):
        FsProjectRegistry.open(root)
    kept = FsProjectRegistry.open(root)
    assert kept is calls[1] and FsProjectRegistry.open(root) is kept


def test_an_entry_placing_a_3x_project_says_so(tmp_path):
    from tcw.project_files import LEGACY_PROJECT
    app = proj(tmp_path / "app", "app", upstream=["lib"])
    old = tmp_path / "lib"
    old.mkdir()
    (old / "tcw-config.yaml").write_text("id: lib\n")
    manifest = write_manifest(app, {"lib": "../lib"})
    with pytest.raises(ProjectGraphError) as raised:
        FsProjectRegistry.open(app).project_folder("lib", app)
    assert str(raised.value) == (f"{manifest}: entry for 'lib' in {manifest} places it "
                                 f"at {old.resolve()}, which is {LEGACY_PROJECT}")
