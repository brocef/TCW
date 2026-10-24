"""Parent links as a person meets them on the command line (TCW-108 AC 2-4,
6, 9, 13, 15, 21, 23, 31 and 36), each test running `tcw` from a folder it
builds, as `tests/test_project_files_cli.py` does.

The registry's answers for the same layouts are `tests/test_parent_links.py`."""

from __future__ import annotations

import json
import subprocess
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


# -- AC 5, 6, 24: children listed in the personal file (Design 2) ------------------------


def personal_children(root: Path, children) -> None:
    from tests.projectfiles import write_local_config
    write_local_config(root, yaml.safe_dump({"children": children}))


@pytest.fixture
def five(tmp_path):
    """AC 5: `ws` lists `a`; its personal file lists `b, a`."""
    ws = proj(tmp_path / "ws", "ws", children=["a"])
    personal_children(ws, ["b", "a"])
    proj(tmp_path / "a", "a", parents=["ws"])
    proj(tmp_path / "b", "b", parents=["ws"])
    return ws


def test_ac5_the_personal_children_follow_the_committed_ones(five, tmp_path):
    env = personal_env(tmp_path)
    assert tcw(five, "projects", "list", env=env).out.split() == ["ws", "a", "b"]
    assert tcw(five, "projects", "list").out.split() == ["ws", "a"]
    assert tcw(five, "validate", env=env).code == 0


def test_ac5_children_in_the_user_wide_file_is_refused(tmp_path):
    ws = proj(tmp_path / "ws", "ws")
    proj(tmp_path / "b", "b", parents=["ws"])
    env = personal_env(tmp_path)
    user = tmp_path / "xdg" / "tcw" / "config.yaml"
    write_config_file(user, "children: [b]\n")
    ran, lines = findings(ws, env)
    assert ran.code == 1, ran
    assert any(str(user) in line and "children may be listed only in this project's "
               "own files" in line for line in lines), lines


@pytest.mark.parametrize("where", ["committed", "personal"])
def test_ac5_a_child_listed_twice(tmp_path, where):
    ws = proj(tmp_path / "ws", "ws", children=["a", "a"] if where == "committed" else None)
    if where == "personal":
        personal_children(ws, ["a", "a"])
    proj(tmp_path / "a", "a", parents=["ws"])
    ran, lines = findings(ws, personal_env(tmp_path))
    assert ran.code == 1, ran
    assert any("'a' is listed twice" in line for line in lines), lines


def test_ac5_null_children_in_the_personal_file(tmp_path):
    from tests.projectfiles import write_local_config
    ws = proj(tmp_path / "ws", "ws")
    write_local_config(ws, "children:\n")
    ran, lines = findings(ws, personal_env(tmp_path))
    assert ran.code == 1, ran
    assert any("null has no meaning in a personal file" in line for line in lines), lines


def test_ac6_a_personal_child_must_name_its_parent(tmp_path):
    ws = proj(tmp_path / "ws", "ws")
    personal_children(ws, ["a"])
    proj(tmp_path / "a", "a")
    env = personal_env(tmp_path)
    ran, lines = findings(ws, env)
    assert ran.code == 1, ran
    assert any("'a' is listed as a child of 'ws' but does not name 'ws' among its "
               "parents" in line for line in lines), lines
    assert tcw(ws, "projects", "list", env=env).code == 1


def test_ac24_a_worktree_uses_the_main_checkouts_personal_children(tmp_path):
    ws = link(make_project(tmp_path, "ws"), children=["a"])
    proj(tmp_path / "a", "a", parents=["ws"])
    commit_all(ws)
    worktree = tmp_path / "trees" / "ws"
    git(ws, "worktree", "add", "-q", str(worktree), "-b", "side")
    personal_children(ws, ["b"])
    b = proj(tmp_path / "b", "b", parents=["ws"])
    write_manifest(ws, {"b": "../b"}, local=True)
    write_manifest(worktree, {"a": "../../a", "b": "../../b"}, local=True)
    ran = tcw(worktree, "projects", "list", env=personal_env(tmp_path))
    assert ran.code == 0, ran
    assert ran.out.split() == ["ws", "a", "b"], ran
    assert b.is_dir()


def test_choice6_config_show_gives_each_childs_file(five, tmp_path):
    ran = tcw(five, "config", "show", "--origin", env=personal_env(tmp_path))
    assert ran.code == 0, ran
    lines = [line.strip() for line in ran.out.splitlines()]
    at = lines.index("children:")
    assert lines[at + 1:at + 3] == ["- a  # project",
                                    "- b  # local: .tcw/tcw-config.local.yaml"], ran.out


def test_ac32_personal_children_do_not_change_a_gate(tmp_path):
    from tcw.store.fs import init
    from tests.test_capabilities_rm import write_cap
    ws = make_project(tmp_path, "ws")
    b = link(make_project(tmp_path, "b"), parents=["ws"])
    init(["capabilities"], ws)
    init(["capabilities"], b)
    write_cap(b, "x", id="cap-x00001", Status="Supported")
    personal_children(ws, ["b"])
    folder = write_item(ws, "2026-10-01-a", {"title": "a", "stage": "implement"})
    (folder / "implement").mkdir()
    (folder / "implement" / "round-1.md").write_text("Done.\n")
    (folder / "capabilities.yaml").write_text("changed: [b.capabilities/x]\n")
    for root in (ws, b):
        commit_all(root)
    argv = ("work", "advance", "2026-10-01-a", "--dry-run")
    with_personal = tcw(ws, *argv, env=personal_env(tmp_path))
    without = tcw(ws, *argv)
    assert (with_personal.code, with_personal.err) == (without.code, without.err), \
        (with_personal, without)


# -- AC 18, 20, 26: what a missing project stops (Design 6) ------------------------------


def unresolved(lines):
    return [line for line in lines if line.startswith("unresolved:")]


def test_ac18_a_missing_parent_that_passes_nothing(tmp_path):
    app = link(make_project(tmp_path, "app"),
               parents=[{"id": "ws", "inherit": "none"}, "core"])
    proj(tmp_path / "core", "core")
    assert tcw(app, "work", "list").code == 0
    ran, lines = findings(app)
    assert ran.code == 0, ran
    [finding] = unresolved(lines)
    assert "'ws'" in finding and "could not check what it passes down to 'app'" in finding


def test_ac20_a_missing_grandparent_is_one_finding(tmp_path):
    app = link(make_project(tmp_path, "app"), parents=["lib"])
    proj(tmp_path / "lib", "lib", parents=["core"])
    ran, lines = findings(app)
    assert ran.code == 0, ran
    [finding] = unresolved(lines)
    assert "'core'" in finding, lines


def test_ac26_a_planning_workspace_in_two_repositories(tmp_path):
    from tcw.store.project import FsProjectRegistry
    a = link(make_project(tmp_path, "ws", name="repo-a"), children=["app"])
    b = link(make_project(tmp_path / "repo-a", "app", name="repo-b"),
             parents=[{"id": "ws", "inherit": "none"}])
    (a / ".gitignore").write_text("/repo-b/\n")
    # The search never looks downwards, so `ws`'s manifest places `app`; `app`
    # finds `ws` enclosing it.
    write_manifest(a, {"app": "repo-b"})
    commit_all(a)
    commit_all(b)
    assert rows(a)["app"]["present"] is True
    alone = tmp_path / "elsewhere" / "repo-b"
    alone.parent.mkdir()
    subprocess.run(["git", "clone", "-q", str(b), str(alone)], check=True,
                   capture_output=True)
    ran, lines = findings(alone)
    assert ran.code == 0, ran
    [finding] = unresolved(lines)
    assert "'ws'" in finding, lines
    assert [p.id for p in FsProjectRegistry.open(alone).sources("config")] == ["app"]
    assert tcw(alone, "work", "list").code == 0


# -- AC 19 and Design 3.6: `extends` held to the parent links ---------------------------


def extends(root: Path, axis: str, *ids: str) -> None:
    path = config_file(root)
    document = yaml.safe_load(path.read_text())
    document.setdefault(axis, {})["extends"] = list(ids)
    write_config_file(path, yaml.safe_dump(document, sort_keys=False))


def tree(tmp_path, name, *, parents=None, children=None, axes=("taxonomy",)):
    from tcw.store.fs import init
    root = make_project(tmp_path, name)
    init(list(axes), root)
    return link(root, parents=parents, children=children)


def test_ac19_an_extended_parent_not_here_stops_with_exit_7(tmp_path):
    app = tree(tmp_path, "app", parents=["core"], axes=("taxonomy", "capabilities"))
    extends(app, "taxonomy", "core")
    from tests.test_capabilities_rm import write_cap
    write_cap(app, "cli", id="cap-cli00001", Status="Supported")
    write_cap(app, "cli/x", id="cap-x000001", Status="Supported")
    (app / "docs" / "capabilities" / "cli" / "x" / "description.md").write_text(
        "See [this](tcw://app.capabilities/cli).\n")
    listed = tcw(app, "taxonomy", "list")
    assert listed.code == 7, listed
    assert "'app' inherits its taxonomy from project 'core', which is not on this " \
        "machine:" in listed.err
    ran, lines = findings(app)
    assert ran.code == 0, ran
    assert not [line for line in lines if line.startswith("error:")], lines
    [finding] = unresolved(lines)
    assert "'core'" in finding
    assert "could not check what it passes down to 'app'" in finding
    # TCW-109 Design 3.5, 3.6: the parent passes `config` too, and `app` sets
    # no `work.tags`, so the configuration's suffix follows the taxonomy's.
    assert finding.endswith("; could not check the taxonomy inherited from it; could "
                            "not check the configuration inherited from it"), finding


@pytest.mark.parametrize("axis", ["taxonomy", "capabilities"])
@pytest.mark.parametrize("shape", ["outside", "behind-none", "descendant"])
def test_ac19_an_extends_the_links_do_not_pass_is_refused(tmp_path, axis, shape):
    if shape == "descendant":
        app = tree(tmp_path, "ws", children=["kid"], axes=(axis,))
        tree(tmp_path, "kid", parents=["ws"], axes=(axis,))
        named = "kid"
    else:
        app = tree(tmp_path, "app", axes=(axis,),
                   parents=[{"id": "core", "inherit": "none"}] if shape == "behind-none"
                   else None)
        tree(tmp_path, "core" if shape == "behind-none" else "other", axes=(axis,))
        named = "core" if shape == "behind-none" else "other"
    extends(app, axis, named)
    project = app.name
    words = f"'{named}' is in {axis}.extends, but '{project}' does not inherit its {axis} " \
            f"from it: name it under 'parents:'"
    listed = tcw(app, axis, "list")
    assert listed.code == 1 and words in listed.err, listed
    ran, lines = findings(app)
    assert ran.code == 1 and any(line.startswith("error:") and words in line
                                 for line in lines), lines
    extends(app, axis)
    before = config_file(app).read_bytes()
    added = tcw(app, axis, "extends", "add", named)
    assert added.code == 2 and words in added.err, added
    assert config_file(app).read_bytes() == before


@pytest.mark.parametrize("state", ["missing", "unreadable"])
def test_ac19_when_what_lies_above_is_unknown(tmp_path, state):
    app = tree(tmp_path, "app", parents=["lib"])
    if state == "unreadable":
        proj(tmp_path / "lib", "lib", parents="top")
    extends(app, "taxonomy", "core")
    listed = tcw(app, "taxonomy", "list")
    assert listed.code == 7, listed
    lead = ("from project 'lib', which is not on this machine:" if state == "missing"
            else "through project 'lib', whose parents could not be read:")
    assert f"'app' inherits its taxonomy {lead}" in listed.err, listed
    ran, lines = findings(app)
    assert ran.code == 0, ran
    assert not [line for line in lines if line.startswith("error:")], lines
    [finding] = unresolved(lines)
    assert "'lib'" in finding
    first = ("could not check what it passes down to 'app'" if state == "missing"
             else "could not check what 'lib' passes down to 'app'")
    assert first in finding
    # TCW-109 Design 3.5, 3.6: the parent passes `config` too, and `app` sets
    # no `work.tags`, so the configuration's suffix follows the taxonomy's.
    assert finding.endswith("; could not check the taxonomy inherited from it; could "
                            "not check the configuration inherited from it"), finding
    extends(app, "taxonomy")
    before = config_file(app).read_bytes()
    added = tcw(app, "taxonomy", "extends", "add", "core")
    assert added.code == 7, added
    assert config_file(app).read_bytes() == before


def test_ac9_a_siblings_extends_is_read_from_its_own_load_order(tmp_path):
    from tcw.store.project import FsProjectRegistry
    tree(tmp_path, "ws", children=["a", "b"])
    a = tree(tmp_path, "a", parents=["ws"])
    b = tree(tmp_path, "b", parents=["ws", "bp"])
    tree(tmp_path, "bp")
    extends(b, "taxonomy", "bp")
    added = tcw(b, "taxonomy", "add", "t")
    assert added.code == 0, added
    shown = tcw(a, "taxonomy", "show", "b.taxonomy/t")
    assert shown.code == 0 and "full-id: b.taxonomy/t" in shown.out, shown
    assert FsProjectRegistry.open(a).get("bp") is None


# -- Design 8.2: `tcw projects list --json` ---------------------------------------------


def listing(cwd: Path, env: dict | None = None) -> dict:
    ran = tcw(cwd, "projects", "list", "--json", env=env)
    assert ran.code == 0, ran
    return json.loads(ran.out)


@pytest.mark.parametrize("entry, inherit", [
    ("core", ["taxonomy", "capabilities", "config"]),
    ({"id": "core"}, ["taxonomy", "capabilities", "config"]),
    ({"id": "core", "inherit": "all"}, ["taxonomy", "capabilities", "config"]),
    ({"id": "core", "inherit": "none"}, []),
    ({"id": "core", "inherit": ["config", "taxonomy"]}, ["taxonomy", "config"]),
    ({"id": "core", "inherit": ["taxonomy", "capabilities", "config"]},
     ["taxonomy", "capabilities", "config"]),
])
def test_ac1_each_parent_row_says_what_it_passes(tmp_path, entry, inherit):
    app = proj(tmp_path / "app", "app", parents=[entry])
    proj(tmp_path / "core", "core")
    row = rows(app)["core"]
    assert (row["relation"], row["inherit"]) == ("parent", inherit)
    assert "personal" not in row


def test_ac5_each_child_row_says_whether_it_is_personal(five, tmp_path):
    found = {row["id"]: row for row in listing(five, personal_env(tmp_path))["projects"]}
    assert (found["a"]["personal"], found["b"]["personal"]) == (False, True)
    assert "inherit" not in found["a"] and "personal" not in found["ws"]


def test_ac23_exactly_five_top_level_keys(tmp_path):
    gg = proj(tmp_path / "gg", "gg", parents=["cc", "ff"], children=["xx", "yy"])
    for name in ("cc", "ff"):
        proj(tmp_path / name, name)
    for name in ("xx", "yy"):
        proj(tmp_path / name, name, parents=["gg"])
    document = listing(gg)
    assert list(document) == ["schema", "projects", "load-order", "load-order-complete",
                              "load-order-warning"]
    assert document["schema"] == 2
    assert document["load-order"] == ["cc", "ff", "gg"]
    assert (document["load-order-complete"], document["load-order-warning"]) == (True, None)


def test_ac12_c3_gives_no_warning(tmp_path):
    zz = proj(tmp_path / "zz", "zz", parents=["xx", "yy"])
    proj(tmp_path / "xx", "xx", parents=["bb"])
    proj(tmp_path / "yy", "yy", parents=["aa", "bb"])
    proj(tmp_path / "aa", "aa")
    proj(tmp_path / "bb", "bb")
    document = listing(zz)
    assert document["load-order"] == ["aa", "bb", "xx", "yy", "zz"]
    assert document["load-order-warning"] is None
    ran, lines = findings(zz)
    assert ran.code == 0 and not [line for line in lines if "load order" in line], lines


def test_ac13_the_fallback_warning_in_validate_and_the_listing(tmp_path):
    zz = proj(tmp_path / "zz", "zz", parents=["xx", "yy"])
    proj(tmp_path / "xx", "xx", parents=["aa", "bb"])
    proj(tmp_path / "yy", "yy", parents=["bb", "aa"])
    proj(tmp_path / "aa", "aa")
    proj(tmp_path / "bb", "bb")
    text = ("load order: no order keeps every project's own order of parents (at 'zz': "
            "'aa', 'bb' cannot be placed); using depth-first order aa, bb, xx, yy, zz; "
            "to choose a value yourself, set it in 'zz'")
    document = listing(zz)
    assert document["load-order"] == ["aa", "bb", "xx", "yy", "zz"]
    assert document["load-order-warning"] == text
    ran, lines = findings(zz)
    assert ran.code == 0, ran
    assert lines == [f"warning: .tcw/tcw-config.yaml: {text}"], lines


def test_ac18_and_ac20_the_load_order_is_not_complete(tmp_path):
    app = proj(tmp_path / "app", "app", parents=[{"id": "ws", "inherit": "none"}, "core"])
    proj(tmp_path / "core", "core")
    document = listing(app)
    assert document["load-order"] == ["ws", "core", "app"]
    assert document["load-order-complete"] is False
    lib_app = proj(tmp_path / "two" / "app", "app", parents=["lib"])
    proj(tmp_path / "two" / "lib", "lib", parents=["core"])
    document = listing(lib_app)
    assert document["load-order"] == ["core", "lib", "app"]
    assert document["load-order-complete"] is False


def test_ac6_a_child_not_here_is_not_present(tmp_path):
    ws = proj(tmp_path / "ws", "ws", children=["a"])
    row = rows(ws)["a"]
    assert (row["present"], row["read-only"], row["personal"]) == (False, None, False)


def test_ac21_and_ac33_read_only_rows(family):
    found = rows(family["app"])
    assert (found["lib"]["read-only"], found["ws"]["read-only"]) == (True, False)
    assert "read-only" not in found["app"]
    assert "upstream" not in json.dumps(found)
    found = rows(family["ws"])
    assert (found["app"]["read-only"], found["sib"]["read-only"]) == (False, False)


def test_ac27_a_single_project_pays_nothing(tmp_path, monkeypatch, capsys):
    import builtins
    import pathlib

    from tcw import cli
    alone = make_project(tmp_path / "alone", "solo")
    beside = make_project(tmp_path / "beside", "solo")
    make_project(tmp_path / "beside", "other")
    commit_all(alone)
    commit_all(beside)

    def outputs(root: Path) -> list:
        monkeypatch.chdir(root)
        found = []
        for argv in (["work", "list"], ["projects", "list"], ["validate"],
                     ["projects", "list", "--json"]):
            code = cli.main(argv)
            out, err = capsys.readouterr()
            found.append((code, out.replace(str(root), "<root>"), err))
        return found

    other = (tmp_path / "beside" / "other").resolve()
    opened: list[str] = []
    real_open, real_read = builtins.open, pathlib.Path.read_text

    def watch_open(file, *args, **kwargs):
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    def watch_read(self, *args, **kwargs):
        opened.append(str(self))
        return real_read(self, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", watch_open)
    monkeypatch.setattr(pathlib.Path, "read_text", watch_read)
    beside_out = outputs(tmp_path / "beside" / "solo")
    # The watch sees the project's own configuration read, so it would see
    # the other's.
    own = str((tmp_path / "beside" / "solo" / ".tcw" / "tcw-config.yaml").resolve())
    assert own in {str(Path(p).resolve()) for p in opened}, opened
    assert not [p for p in opened if str(Path(p).resolve()).startswith(str(other))], opened
    assert beside_out == outputs(tmp_path / "alone" / "solo")
    document = json.loads(beside_out[3][1])
    assert [row["id"] for row in document["projects"]] == ["solo"]
    assert document["load-order"] == ["solo"]
    assert (document["load-order-complete"], document["load-order-warning"]) == (True, None)
