"""`tcw project list` (TCW-73 Design 2; AC 7's last part).

One project ID per line, this project first, then its parents and its
children, present or not; `--json` says which is which.
"""

import json
import os

import pytest
import yaml

from tcw.cli import main
from tests.work.projects import make_project
from tests.projectfiles import config_file, write_config_file, write_manifest


def declare(root, relation, project_id, target):
    """Name `project_id` in `root`'s configuration — as a parent passing every
    axis (`relation` "parent"), a parent passing none ("upstream", what a 3.x
    upstream became) or a child ("children") — and say in `root`'s manifest
    that it is at `target`."""
    path = config_file(root)
    document = yaml.safe_load(path.read_text())
    if relation == "children":
        document.setdefault("children", []).append(project_id)
    else:
        document.setdefault("parents", []).append(
            project_id if relation == "parent" else {"id": project_id, "inherit": "none"})
    write_config_file(path, yaml.safe_dump(document, sort_keys=False))
    write_manifest(root, {project_id: os.path.relpath(target, root)})


@pytest.fixture
def graph(tmp_path, request):
    """`fx` under parent `top`, with children `c1` and `c2`, an absent child
    `gone`, and a parent `up` passing no axis (a 3.x upstream)."""
    link = declare
    top = make_project(tmp_path, "top")
    fx = make_project(tmp_path, "fx")
    c1 = make_project(tmp_path, "c1")
    c2 = make_project(tmp_path, "c2")
    up = make_project(tmp_path, "up")
    link(top, "children", "fx", fx)
    link(fx, "parent", "top", top)
    for child in (c1, c2):
        link(fx, "children", child.name, child)
        link(child, "parent", "fx", fx)
    link(fx, "children", "gone", tmp_path / "gone")
    link(fx, "upstream", "up", up)
    return fx


def run(monkeypatch, capsys, cwd, *argv):
    monkeypatch.chdir(cwd)
    try:
        code = main(list(argv))
    except SystemExit as stop:
        code = stop.code
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_one_id_per_line_current_first(graph, monkeypatch, capsys):
    code, out, err = run(monkeypatch, capsys, graph, "project", "list")
    assert code == 0, err
    # TCW-108 Design 8.1: the parents in listing order, then the children;
    # the 3.x upstream is a parent.
    assert out.splitlines() == ["fx", "top", "up", "c1", "c2", "gone"]


def test_json_says_relation_and_presence(graph, monkeypatch, capsys):
    code, out, _ = run(monkeypatch, capsys, graph, "project", "list", "--json")
    data = json.loads(out)
    assert data["schema"] == 2
    rows = {p["id"]: p for p in data["projects"]}
    assert [p["id"] for p in data["projects"]] == ["fx", "top", "up", "c1", "c2", "gone"]
    assert rows["fx"]["relation"] == "current" and rows["top"]["relation"] == "parent"
    assert rows["c1"]["relation"] == "child" and rows["up"]["relation"] == "parent"
    assert rows["gone"]["present"] is False and rows["gone"]["path"] is None
    assert rows["c1"]["present"] is True and rows["c1"]["path"].endswith("c1")


def test_a_lone_project_lists_itself(tmp_path, monkeypatch, capsys):
    root = make_project(tmp_path, "solo")
    assert run(monkeypatch, capsys, root, "project", "list")[:2] == (0, "solo\n")


def test_outside_a_project(tmp_path, monkeypatch, capsys):
    code, out, err = run(monkeypatch, capsys, tmp_path, "project", "list")
    assert (code, out) == (1, "")
    assert err.startswith("tcw project list: no TCW project here")


def test_work_nodes_is_gone(graph, monkeypatch, capsys):
    assert run(monkeypatch, capsys, graph, "work", "nodes")[0] == 2


# -- the `projects:` key (Design 9.3; AC 7) -------------------------------------------


def _add_2x_key(root):
    """Give `root`'s configuration the 2.x `connected-projects` key."""
    path = config_file(root)
    document = yaml.safe_load(path.read_text())
    document["connected-projects"] = {"children": {"zz": None}}
    write_config_file(path, yaml.safe_dump(document, sort_keys=False))


REFUSED = ("'connected-projects' is not a TCW 4.0 key: name parents under "
           "'parents:' and children under 'children:', by ID, and say where "
           "projects are in .tcw/tcw-manifest.yaml")


def test_the_graph_under_projects_validates(graph, monkeypatch, capsys):
    code, out, err = run(monkeypatch, capsys, graph, "validate")
    assert not [line for line in out.splitlines() if line.startswith("error: ")], out
    assert code == 0, (out, err)


def test_the_2x_key_is_an_error_naming_the_guide(graph, monkeypatch, capsys):
    """TCW-108 Design 3.5: the message names `parents:`, `children:` and the
    manifest rather than the 3.x key it was renamed to."""
    _add_2x_key(graph)
    code, out, err = run(monkeypatch, capsys, graph, "validate")
    assert code == 1
    assert REFUSED in out + err


# -- review fix R1: every command refuses the 2.x key ------------------------------


@pytest.mark.parametrize("argv", [
    ("project", "list"),
    ("project", "provision"),
    ("work", "list"),
    ("work", "new", "x"),
    ("taxonomy", "list"),
])
def test_every_command_refuses_the_2x_key(graph, monkeypatch, capsys, argv):
    _add_2x_key(graph)
    code, out, err = run(monkeypatch, capsys, graph, *argv)
    assert (code, out) == (1, ""), (out, err)
    assert err.count("\n") == 1, err
    assert err.startswith(f"tcw {' '.join(argv[:2])}"), err
    assert REFUSED in err





def test_work_list_refuses_the_2x_key_in_a_child(graph, monkeypatch, capsys):
    """Pre-freeze clean-up, C9: `open_backend` checks the project graph, as
    `taxonomy list` does."""
    child = graph.parent / "c1"
    _add_2x_key(child)
    code, out, err = run(monkeypatch, capsys, graph, "work", "list")
    assert (code, out) == (1, ""), err
    assert "c1" in err and REFUSED in err


def test_work_list_runs_with_a_declared_child_that_is_not_here(graph, monkeypatch,
                                                              capsys):
    """`gone` is declared but absent: not a problem with the graph."""
    code, _, err = run(monkeypatch, capsys, graph, "work", "list")
    assert code == 0, err


def test_the_2x_key_refusal_names_the_file_from_a_sub_folder(graph, monkeypatch,
                                                             capsys):
    """Pre-freeze clean-up, C8: run from `fx/docs`, the file is
    `../.tcw/tcw-config.yaml`."""
    _add_2x_key(graph)
    code, out, err = run(monkeypatch, capsys, graph / "docs", "taxonomy", "list")
    assert (code, out) == (1, ""), err
    assert f": ../.tcw/tcw-config.yaml: {REFUSED}" in err, err


def test_an_upstreams_own_2x_key_is_not_its_readers_problem(graph, monkeypatch, capsys):
    up = graph.parent / "up"
    path = config_file(up)
    document = yaml.safe_load(path.read_text())
    document["connected-projects"] = {"children": {"zz": "../zz"}}
    write_config_file(path, yaml.safe_dump(document, sort_keys=False))
    code, out, err = run(monkeypatch, capsys, graph, "project", "list")
    assert code == 0, err


def test_projects_list_reports_a_registry_problem(graph, monkeypatch, capsys):
    """An invalid child ID is an error, not a project left off the list."""
    path = config_file(graph)
    document = yaml.safe_load(path.read_text())
    document["children"].append("Bad ID")
    write_config_file(path, yaml.safe_dump(document, sort_keys=False))
    code, out, err = run(monkeypatch, capsys, graph, "project", "list")
    assert (code, out) == (1, ""), (out, err)
    index = document["children"].index("Bad ID")
    assert err.startswith("tcw project list: "), err
    assert f"fx/.tcw/tcw-config.yaml: children[{index}]: project ID must match" in err, err
