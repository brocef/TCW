"""Parent links as a person meets them on the command line (TCW-108 AC 2-4,
6, 9, 13, 15, 21, 23, 31 and 36), each test running `tcw` from a folder it
builds, as `tests/test_project_files_cli.py` does.

The registry's answers for the same layouts are `tests/test_parent_links.py`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from tests.projectfiles import (config_file, local_config_file, write_config,
                                write_config_file, write_manifest)
from tests.test_project_files_cli import personal_env, tcw
from tests.work.projects import commit_all, git, make_project, write_item

SHARED_KEY = "a shared key; a personal file cannot set it"


def proj(root: Path, project_id: str, parents=None, children=None) -> Path:
    data: dict = {"id": project_id}
    if parents is not None:
        data["parents"] = parents
    if children is not None:
        data["children"] = children
    write_config(root, yaml.safe_dump(data, sort_keys=False))
    return root.resolve()


def link(root: Path, parents=None, children=None) -> Path:
    """Add `parents:` and `children:` to a project `make_project` built."""
    path = config_file(root)
    document = yaml.safe_load(path.read_text())
    if parents is not None:
        document["parents"] = parents
    if children is not None:
        document["children"] = children
    write_config_file(path, yaml.safe_dump(document, sort_keys=False))
    return root


def findings(cwd: Path, env: dict | None = None):
    ran = tcw(cwd, "validate", env=env)
    return ran, [line for line in ran.out.splitlines() if line.strip()]


def rows(cwd: Path) -> dict:
    ran = tcw(cwd, "projects", "list", "--json")
    assert ran.code == 0, ran
    return {row["id"]: row for row in json.loads(ran.out)["projects"]}


# -- AC 2: parent problems in the active project ----------------------------------------


@pytest.mark.parametrize("document, words", [
    ({"parents": "core"}, "must be a list of parents"),
    ({"parents": [5]}, "must be a project ID or a mapping"),
    ({"parents": [{"inherit": "none"}]}, "parents[0].id: is required"),
    ({"parents": [{"id": "Core"}]}, "parents[0].id"),
    ({"parents": [{"id": "core", "path": "../core"}]}, "unknown key 'path'"),
    ({"parents": [{"id": "core", "inherit": "some"}]}, "parents[0].inherit"),
    ({"parents": [{"id": "core", "inherit": ["taxonomy", "taxonomy"]}]},
     "'taxonomy' is listed more than once"),
    ({"parents": [{"id": "core", "inherit": ["work"]}]}, "'work' is not one of"),
    ({"parents": [{"id": "core", "inherit": []}]}, "inherit: none"),
    ({"parents": ["core", "core"]}, "'core' is listed twice"),
    ({"parents": ["core"], "children": ["core"]}, "named both as a parent and as a child"),
    ({"children": ["app"]}, "'app' lists itself as a child"),
])
def test_ac2_parent_problems_in_the_active_project(tmp_path, document, words):
    app = proj(tmp_path / "app", "app")
    proj(tmp_path / "core", "core", parents=["app"] if "children" in document
         and "core" in document["children"] else None)
    path = config_file(app)
    write_config_file(path, yaml.safe_dump({"id": "app", **document}, sort_keys=False))
    listed = tcw(app, "projects", "list")
    assert listed.code == 1, listed
    ran, lines = findings(app)
    assert ran.code == 1, ran
    assert any(line.startswith("error: .tcw/tcw-config.yaml: ") and words in line
               for line in lines), lines


# -- AC 3: parents only in the committed file -------------------------------------------


@pytest.mark.parametrize("where", ["local", "user"])
def test_ac3_parents_only_in_the_committed_file(tmp_path, where):
    app = proj(tmp_path / "app", "app")
    proj(tmp_path / "core", "core")
    env = personal_env(tmp_path)
    if where == "local":
        file = local_config_file(app)
    else:
        file = tmp_path / "xdg" / "tcw" / "config.yaml"
    write_config_file(file, "parents: [core]\n")
    for argv in (("validate",), ("work", "list")):
        ran = tcw(app, *argv, env=env)
        assert ran.code == 1, (argv, ran)
        assert SHARED_KEY in ran.out + ran.err and file.name in ran.out + ran.err, ran


# -- AC 4: a one-sided parent -----------------------------------------------------------


def test_ac4_a_one_sided_parent(tmp_path):
    app = proj(tmp_path / "app", "app", parents=["core"])
    core = proj(tmp_path / "core", "core")
    ran, lines = findings(app)
    assert ran.code == 0 and not [line for line in lines if "core" in line], lines
    assert rows(app)["core"]["present"] is True
    assert tcw(core, "projects", "list").out == "core\n"


# -- AC 6: a listed child must name its parent ------------------------------------------


def test_ac6_a_listed_child_must_name_its_parent(tmp_path):
    ws = proj(tmp_path / "ws", "ws", children=["a"])
    a = proj(tmp_path / "a", "a")
    ran, lines = findings(ws)
    assert ran.code == 1
    assert any("'a' is listed as a child of 'ws' but does not name 'ws' among its "
               "parents" in line for line in lines), lines
    assert tcw(ws, "projects", "list").code == 1
    import shutil
    shutil.rmtree(a)
    ran, lines = findings(ws)
    assert ran.code == 0, ran
    unresolved = [line for line in lines if line.startswith("unresolved:")]
    assert len(unresolved) == 1 and "'a'" in unresolved[0], lines
    assert "could not check that it names 'ws' as a parent" in unresolved[0]
    assert rows(ws)["a"]["present"] is False


# -- AC 9: never a sibling --------------------------------------------------------------


def test_ac9_a_siblings_item_is_read_by_its_full_identifier(tmp_path):
    ws = link(make_project(tmp_path, "ws"), children=["a", "b"])
    a = link(make_project(tmp_path, "a"), parents=["ws"])
    b = link(make_project(tmp_path, "b"), parents=["ws"])
    write_item(b, "2026-10-01-x", {"title": "Theirs", "stage": "inbox"})
    for root in (ws, a, b):
        commit_all(root)
    assert tcw(a, "projects", "list").out.split() == ["a", "ws"]
    shown = tcw(a, "work", "show", "b.work/2026-10-01-x")
    assert shown.code == 0 and "Theirs" in shown.out, shown
    import shutil
    shutil.rmtree(b)
    shown = tcw(a, "work", "show", "b.work/2026-10-01-x")
    assert shown.code == 5, shown
    assert "project 'b' is not on this machine" in shown.err
    assert "no project with ID 'b'" not in shown.err
    ran, lines = findings(a)
    assert not [line for line in lines if "'b'" in line], lines


# -- AC 13's last sentence: the warning only where it can be acted on -------------------


def test_ac13_the_fallback_warning_is_not_printed_by_other_commands(tmp_path):
    zz = link(make_project(tmp_path, "zz"), parents=["xx", "yy"])
    proj(tmp_path / "xx", "xx", parents=["aa", "bb"])
    proj(tmp_path / "yy", "yy", parents=["bb", "aa"])
    proj(tmp_path / "aa", "aa")
    proj(tmp_path / "bb", "bb")
    ran = tcw(zz, "work", "list")
    assert (ran.code, ran.err) == (0, ""), ran


# -- AC 15: loops ------------------------------------------------------------------------


def test_ac15_a_loop_stops_every_command(tmp_path):
    aa = link(make_project(tmp_path, "aa"), parents=["bb"])
    proj(tmp_path / "bb", "bb", parents=["aa"])
    assert tcw(aa, "projects", "list").code == 1
    assert tcw(aa, "work", "list").code == 1
    ran, lines = findings(aa)
    assert ran.code == 1
    assert any("loop in parents: aa -> bb -> aa" in line for line in lines), lines


# -- AC 21: writing into another project, until TCW-114 ----------------------------------


@pytest.fixture
def family(tmp_path):
    """`app: [lib, ws]`; `ws` lists `app` and `sib`; `lib: [top]`, and `top`
    lists `lib`; every project has a work store with nothing uncommitted."""
    app = link(make_project(tmp_path, "app"), parents=["lib", "ws"])
    lib = link(make_project(tmp_path, "lib"), parents=["top"])
    ws = link(make_project(tmp_path, "ws"), children=["app", "sib"])
    top = link(make_project(tmp_path, "top"), children=["lib"])
    sib = link(make_project(tmp_path, "sib"), parents=["ws"])
    roots = {"app": app, "lib": lib, "ws": ws, "top": top, "sib": sib}
    for root in roots.values():
        commit_all(root)
    return roots


def work_files(root: Path) -> list[str]:
    return sorted(p.name for p in (root / "docs" / "work").iterdir())


def test_ac21_writing_into_another_project(family):
    app = family["app"]
    before = work_files(family["lib"])
    ran = tcw(app, "work", "new", "x", "--project", "lib")
    assert ran.code == 3, ran
    assert "read-only" in ran.err and "'lib' does not list 'app'" in ran.err
    assert work_files(family["lib"]) == before
    assert tcw(app, "work", "new", "x", "--project", "ws").code == 0
    assert tcw(app, "work", "new", "x", "--project", "top").code == 3
    before = work_files(family["sib"])
    assert tcw(app, "work", "new", "x", "--project", "sib").code == 3
    assert work_files(family["sib"]) == before
    commit_all(family["ws"])
    assert tcw(family["ws"], "work", "new", "x", "--project", "sib").code == 0


def test_ac21_a_parent_not_here_is_refused_with_no_jira_block(family):
    import shutil
    shutil.rmtree(family["ws"])
    ran = tcw(family["app"], "work", "new", "x", "--project", "ws")
    assert ran.code == 3, ran
    assert "jira" not in ran.err


# -- AC 23: the plain listing -----------------------------------------------------------


def test_ac23_the_plain_listing(tmp_path):
    gg = proj(tmp_path / "gg", "gg", parents=["cc", "ff"], children=["xx", "yy"])
    proj(tmp_path / "cc", "cc")
    proj(tmp_path / "ff", "ff")
    proj(tmp_path / "xx", "xx", parents=["gg"])
    proj(tmp_path / "yy", "yy", parents=["gg"])
    assert tcw(gg, "projects", "list").out.split() == ["gg", "cc", "ff", "xx", "yy"]


# -- AC 31: a problem in a parent's links ----------------------------------------------


def test_ac31_a_problem_in_a_parents_links_does_not_stop_the_reader(tmp_path):
    app = link(make_project(tmp_path, "app"), parents=["lib"])
    lib = proj(tmp_path / "lib", "lib", parents="core")
    assert tcw(app, "projects", "list").code == 0
    assert tcw(app, "work", "list").code == 0
    ran, lines = findings(app)
    assert ran.code == 0, ran
    unresolved = [line for line in lines if line.startswith("unresolved:")]
    assert len(unresolved) == 1 and "'lib'" in unresolved[0], lines
    assert "could not check what 'lib' passes down to 'app'" in unresolved[0]
    assert tcw(lib, "projects", "list").code == 1


def test_ac31_a_loop_above_a_parent_stops_the_reader(tmp_path):
    app = link(make_project(tmp_path, "app"), parents=["lib"])
    proj(tmp_path / "lib", "lib", parents=["top"])
    proj(tmp_path / "top", "top", parents=["lib"])
    assert tcw(app, "work", "list").code == 1


def test_ac31_named_both_in_a_parent_is_not_the_readers_problem(tmp_path):
    app = proj(tmp_path / "app", "app", parents=["lib"])
    proj(tmp_path / "lib", "lib", parents=["top"], children=["top"])
    proj(tmp_path / "top", "top")
    ran, lines = findings(app)
    assert ran.code == 0, ran
    assert not [line for line in lines if "'top'" in line or "'lib'" in line], lines
    ran = tcw(app, "projects", "list", "--json")
    assert ran.code == 0, ran


# -- AC 36: the folder an entry was resolved to ----------------------------------------


def test_ac36_not_on_this_machine_names_the_resolved_folder(tmp_path):
    app = link(make_project(tmp_path, "app"), parents=["lib2"])
    write_manifest(app, {"lib2": "../lib2"})
    commit_all(app)
    folder = str((tmp_path / "lib2").resolve())
    ran, lines = findings(app)
    unresolved = [line for line in lines if line.startswith("unresolved:")]
    assert len(unresolved) == 1 and f"places it at {folder}" in unresolved[0], lines
    shown = tcw(app, "work", "show", "lib2.work/x")
    assert shown.code == 5 and f"places it at {folder}" in shown.err, shown


def test_ac36_in_a_linked_worktree_the_folder_beside_the_main_checkout(tmp_path):
    app = link(make_project(tmp_path, "app"), parents=["lib2"])
    write_manifest(app, {"lib2": "../lib2"})
    commit_all(app)
    worktree = tmp_path / "trees" / "feature"
    git(app, "worktree", "add", "-q", str(worktree), "-b", "feature")
    beside_main = str((tmp_path / "lib2").resolve())
    ran, lines = findings(worktree)
    unresolved = [line for line in lines if line.startswith("unresolved:")]
    assert len(unresolved) == 1 and f"places it at {beside_main}" in unresolved[0], lines
    assert str(tmp_path / "trees" / "lib2") not in unresolved[0]


# -- AC 8 and AC 31: `projects:` and `connected-projects` are refused --------------------

REFUSED = ("is not a TCW 4.0 key: name parents under 'parents:' and children "
           "under 'children:', by ID, and say where projects are in "
           ".tcw/tcw-manifest.yaml")


@pytest.mark.parametrize("key", ["projects", "connected-projects"])
def test_ac8_the_3x_key_is_refused(tmp_path, key):
    proj(tmp_path / "ws", "ws", children=["a"])
    a = tmp_path / "a"
    write_config(a, yaml.safe_dump({"id": "a", key: {"parent": {"ws": None}}}))
    listed = tcw(a, "projects", "list")
    assert listed.code == 1, listed
    ran, lines = findings(a)
    assert ran.code == 1, ran
    assert f"error: .tcw/tcw-config.yaml: '{key}' {REFUSED}" in lines, lines


@pytest.mark.parametrize("key", ["projects", "connected-projects"])
def test_ac31_the_3x_key_in_a_parent_leaves_its_links_unknown(tmp_path, key):
    app = link(make_project(tmp_path, "app"), parents=["lib"])
    lib = tmp_path / "lib"
    write_config(lib, yaml.safe_dump({"id": "lib", key: {"parent": {"core": None}}}))
    proj(tmp_path / "core", "core")
    assert tcw(app, "work", "list").code == 0
    ran, lines = findings(app)
    assert ran.code == 0, ran
    unresolved = [line for line in lines if line.startswith("unresolved:")]
    assert len(unresolved) == 1 and f"'{key}' is not a TCW 4.0 key" in unresolved[0], lines


def test_ac31_the_3x_key_in_a_descendant_is_a_graph_problem(tmp_path):
    ws = proj(tmp_path / "ws", "ws", children=["kid"])
    write_config(tmp_path / "kid", yaml.safe_dump(
        {"id": "kid", "parents": ["ws"], "projects": {"children": {"x": None}}}))
    ran, lines = findings(ws)
    assert ran.code == 1, ran
    assert any(f"'projects' {REFUSED}" in line for line in lines), lines


def test_a_parent_passing_some_axes_is_read_by_every_command(tmp_path):
    """`inherit` inside a `parents:` entry is the link's, not a chain list's
    `inherit: true` (tcw/config.py's list rules)."""
    app = link(make_project(tmp_path, "app"),
               parents=[{"id": "ws", "inherit": "none"},
                        {"id": "core", "inherit": ["taxonomy"]}])
    proj(tmp_path / "ws", "ws")
    proj(tmp_path / "core", "core")
    for argv in (("projects", "list"), ("work", "list"), ("validate",)):
        ran = tcw(app, *argv)
        assert ran.code == 0, (argv, ran)
