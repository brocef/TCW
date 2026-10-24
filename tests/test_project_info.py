"""`tcw project info [--json]` (TCW-115 Design 6; AC 12 to 18, and AC 34's
`info`): how the active project is assembled, with what is missing shown
rather than refused."""

from __future__ import annotations

import json
import shutil

import pytest
import yaml

from tests.projectfiles import (config_file, connect_projects, write_config_file,
                                write_local_config, write_manifest)
from tests.test_cli_contract import run, snapshot
from tests.test_project_files_cli import personal_env, tcw
from tests.test_projects_list import ac6
from tests.work.projects import make_project


def info(cwd, *argv, env=None):
    done = tcw(cwd, "project", "info", *argv, env=env)
    assert (done.code, done.err) == (0, ""), done
    return done.out


def ac12(tmp_path):
    """AC 6's `app`, with `ws` a second parent passing nothing and absent,
    and `p` a child only the personal file lists, not on this machine."""
    app = ac6(tmp_path)
    connect_projects(app, "parent", "ws", inherit="none")
    write_local_config(app, "children: [p]\n")
    return app


# -- AC 12: the lines, in order ----------------------------------------------------------

def test_ac12_the_lines_in_order(tmp_path):
    app = ac12(tmp_path)
    out = info(app, env=personal_env(tmp_path)).splitlines()
    root = app.resolve()
    expected = ["id: app", f"path: {root}", "parents:", "  core (inherit: taxonomy)",
                "  ws (inherit: none; not on this machine)", "children:", "  k",
                "  p (personal; not on this machine)", "load order: core, ws, app",
                "load order incomplete: not on this machine: ws", "settings:",
                "  work.backend: filesystem (built-in)", "stores:"]
    assert out[:len(expected)] == expected, out
    rest = out[len(expected):]
    assert [line.split(":")[0] for line in rest[:3]] == [
        "  taxonomy", "  capabilities", "  work"], out
    assert rest[2] == f"  work: {root / 'docs' / 'work'}", out
    assert rest[3] == "overrides:", out
    assert rest[-1].startswith("same path in two unrelated projects: "), out
    assert not any("work.jira" in line for line in out), out


def test_ac12_it_writes_nothing(tmp_path):
    app = ac12(tmp_path)
    env = personal_env(tmp_path)
    before = snapshot(tmp_path)
    info(app, env=env)
    info(app, "--json", env=env)
    assert snapshot(tmp_path) == before


def test_ac34_a_project_alone(tmp_path):
    app = make_project(tmp_path, "solo")
    out = info(app).splitlines()
    assert out[2:5] == ["parents: none", "children: none", "load order: solo"], out


# -- AC 13: settings and where each comes from ---------------------------------------------

def ac13(tmp_path, **app_jira):
    from tests.test_inherited_config import CORE_JIRA, jira_mode, made
    core = made(tmp_path, "core", work={"jira": CORE_JIRA})
    app = made(tmp_path, "app", parents=["core"],
               work=jira_mode(**({"jira": app_jira} if app_jira else {})))
    return core, app


def _setting_line(out: str, key: str) -> str:
    [line] = [l for l in out.splitlines() if l.startswith(f"  {key}: ")]
    return line


def test_ac13_each_setting_with_its_origin(tmp_path):
    core, app = ac13(tmp_path)
    out = info(app)
    assert _setting_line(out, "work.backend") == \
        "  work.backend: jira (app, project .tcw/tcw-config.yaml)", out
    for key in ("work.jira.site", "work.jira.project"):
        assert _setting_line(out, key).endswith(
            f"(core, project {config_file(core)}; inherited)"), out


def test_ac13_a_value_the_project_sets_itself(tmp_path):
    _core, app = ac13(tmp_path, project="APP")
    line = _setting_line(info(app), "work.jira.project")
    assert line == "  work.jira.project: APP (app, project .tcw/tcw-config.yaml)", line


def test_ac13_with_core_absent_both_are_undecided(tmp_path):
    from tcw.config import load_config
    core, app = ac13(tmp_path)
    shutil.rmtree(core)
    message = str(load_config(app).withheld["work.jira"].error())
    out = info(app)
    for key in ("work.jira.site", "work.jira.project"):
        assert _setting_line(out, key) == f"  {key}: undecided: {message}", out


# -- AC 14: the load-order warning -------------------------------------------------------

def test_ac14_the_load_order_warning(tmp_path):
    from tcw.store.project import FsProjectRegistry
    roots = {name: make_project(tmp_path, name) for name in ("aa", "bb", "xx", "yy", "zz")}
    connect_projects(roots["zz"], "parent", "xx", "yy")
    connect_projects(roots["xx"], "parent", "aa", "bb")
    connect_projects(roots["yy"], "parent", "bb", "aa")
    warning = FsProjectRegistry.open(roots["zz"]).load_order().warning
    assert warning
    out = info(roots["zz"]).splitlines()
    assert "load order: aa, bb, xx, yy, zz" in out, out
    assert f"load order warning: {warning}" in out, out
    assert not any(l.startswith("load order warning") for l in info(roots["xx"]).splitlines())


# -- AC 15: overrides and the same-path count ---------------------------------------------

def _caps(tmp_path):
    from tcw.store.fs import init
    from tests.test_capabilities_rm import write_cap
    core = make_project(tmp_path, "core")
    app = make_project(tmp_path, "app")
    for root in (core, app):
        init(["capabilities", "taxonomy"], root)
    connect_projects(app, "parent", "core")
    write_cap(core, "cli/x", Status="Supported")
    write_cap(app, "cli/x", Status="Supported")
    return core, app


def test_ac15_an_override_is_listed(tmp_path):
    _core, app = _caps(tmp_path)
    out = info(app).splitlines()
    at = out.index("overrides:")
    assert out[at + 1:at + 4] == ["  taxonomy: none", "  capabilities:",
                                  "    app.capabilities/cli/x overrides core.capabilities/cli/x"], out
    assert out[-1] == "same path in two unrelated projects: taxonomy 0, capabilities 0", out


def test_ac15_two_unrelated_parents_at_one_path_are_counted(tmp_path):
    from tcw.store.fs import FsTaxonomyStore, init
    one, two, app = (make_project(tmp_path, n) for n in ("one", "two", "app"))
    for root in (one, two, app):
        init(["taxonomy"], root)
    connect_projects(app, "parent", "one", "two")
    for root in (one, two):
        FsTaxonomyStore.open(root).add("a")
    out = info(app).splitlines()
    assert out[-1] == "same path in two unrelated projects: taxonomy 1, capabilities 0", out


def test_ac15_with_core_absent_it_could_not_check(tmp_path):
    from tcw.errors import InheritedUnavailable
    from tcw.store.fs import FsCapabilitiesStore
    core, app = _caps(tmp_path)
    shutil.rmtree(core)
    with pytest.raises(InheritedUnavailable) as caught:
        FsCapabilitiesStore.open(app).view_warnings()
    out = info(app).splitlines()
    assert f"  capabilities: could not check: {caught.value}" in out, out
    assert out[-1].endswith("capabilities ?"), out


# -- AC 16: a store not fetched -----------------------------------------------------------

def test_ac16_a_store_not_fetched_reads_its_reason(tmp_path):
    app = make_project(tmp_path, "app")
    document = yaml.safe_load(config_file(app).read_text())
    document["work"] = {"repository": {"url": str(tmp_path / "remote.git")}}
    write_config_file(config_file(app), yaml.safe_dump(document, sort_keys=False))
    shutil.rmtree(app / "docs" / "work")
    reason = run(app, "work", "path")
    assert reason.code != 0 and "tcw project provision" in reason.err, reason
    out = info(app).splitlines()
    [line] = [l for l in out if l.startswith("  work: ")]
    assert "tcw project provision" in line, out
    assert line == f"  work: {reason.err.split(': ', 1)[1].rstrip()}", (line, reason.err)


# -- AC 18: it refuses only what `list` refuses --------------------------------------------

def test_ac18_a_graph_problem(tmp_path):
    app = ac6(tmp_path)
    make_project(tmp_path, "core", name="core-again")
    listed = run(app, "project", "list")
    shown = run(app, "project", "info")
    assert (listed.code, shown.code, shown.out) == (1, 1, ""), (listed, shown)
    assert shown.err.split(": ", 1)[1] == listed.err.split(": ", 1)[1], (listed, shown)


def test_ac18_a_problem_in_its_own_configuration(tmp_path):
    app = make_project(tmp_path, "app", config={"tags": 5})
    shown = run(app, "project", "info")
    assert (shown.code, shown.out) == (1, ""), shown


def test_ac18_info_takes_no_project(tmp_path):
    app = ac6(tmp_path)
    assert run(app, "project", "info", "core").code == 2


def test_outside_a_project(tmp_path):
    done = run(tmp_path, "project", "info")
    assert (done.code, done.out) == (1, "") and "no TCW project here" in done.err, done


# -- AC 17: `--json` ---------------------------------------------------------------------

def test_ac17_the_document(tmp_path):
    app = ac12(tmp_path)
    data = json.loads(info(app, "--json", env=personal_env(tmp_path)))
    assert data["schema"] == 2 and list(data) == ["schema", "project"]
    project = data["project"]
    assert {"id": "ws", "inherit": [], "present": False, "path": None} in project["parents"]
    assert {"id": "p", "personal": True, "present": False, "path": None} in \
        project["children"]
    assert project["load-order-missing"] == ["ws"]
    assert project["load-order-complete"] is False
    assert project["load-order-unreadable"] == [] and project["load-order-warning"] is None
    assert project["settings"] == {"work.backend": {
        "value": "filesystem", "origin": {"layer": "built-in"}, "inherited": False}}
    assert project["stores"]["work"] == {"path": str(app.resolve() / "docs" / "work")}
    assert set(project["stores"]["taxonomy"]) == {"unavailable"}
    assert project["overrides"] == {"taxonomy": [], "capabilities": []}
    assert project["same-path-warnings"] == {"taxonomy": 0, "capabilities": 0}


def test_ac17_an_inherited_setting(tmp_path):
    core, app = ac13(tmp_path)
    site = json.loads(info(app, "--json"))["project"]["settings"]["work.jira.site"]
    assert site["inherited"] is True
    assert site["origin"] == {"project": "core", "layer": "project",
                              "file": str(config_file(core))}
    shutil.rmtree(core)
    settings = json.loads(info(app, "--json"))["project"]["settings"]
    assert list(settings["work.jira.project"]) == ["undecided"]


def test_ac17_an_axis_that_could_not_be_checked(tmp_path):
    core, app = _caps(tmp_path)
    shutil.rmtree(core)
    project = json.loads(info(app, "--json"))["project"]
    assert list(project["overrides"]["capabilities"]) == ["unavailable"]
    assert project["same-path-warnings"]["capabilities"] is None
