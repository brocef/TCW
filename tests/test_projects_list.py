"""`tcw projects list` (TCW-73 Design 2; AC 7's last part).

One project ID per line, this project first, then its parent, children and
upstream projects, present or not; `--json` says which is which.
"""

import json
import os

import pytest
import yaml

from tcw.cli import main
from tests.work.projects import make_project


def declare(root, relation, project_id, target):
    path = root / "tcw-config.yaml"
    document = yaml.safe_load(path.read_text())
    section = document.setdefault("connected-projects", {}).setdefault(relation, {})
    section[project_id] = os.path.relpath(target, root)
    path.write_text(yaml.safe_dump(document, sort_keys=False))


@pytest.fixture
def graph(tmp_path):
    """`fx` under parent `top`, with children `c1` and `c2`, an absent child
    `gone`, and an upstream `up`."""
    top = make_project(tmp_path, "top")
    fx = make_project(tmp_path, "fx")
    c1 = make_project(tmp_path, "c1")
    c2 = make_project(tmp_path, "c2")
    up = make_project(tmp_path, "up")
    declare(top, "children", "fx", fx)
    declare(fx, "parent", "top", top)
    for child in (c1, c2):
        declare(fx, "children", child.name, child)
        declare(child, "parent", "fx", fx)
    declare(fx, "children", "gone", tmp_path / "gone")
    declare(fx, "upstream", "up", up)
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
    code, out, err = run(monkeypatch, capsys, graph, "projects", "list")
    assert code == 0, err
    assert out.splitlines() == ["fx", "top", "c1", "c2", "gone", "up"]


def test_json_says_relation_and_presence(graph, monkeypatch, capsys):
    code, out, _ = run(monkeypatch, capsys, graph, "projects", "list", "--json")
    data = json.loads(out)
    assert data["schema"] == 1
    rows = {p["id"]: p for p in data["projects"]}
    assert [p["id"] for p in data["projects"]] == ["fx", "top", "c1", "c2", "gone", "up"]
    assert rows["fx"]["relation"] == "current" and rows["top"]["relation"] == "parent"
    assert rows["c1"]["relation"] == "child" and rows["up"]["relation"] == "upstream"
    assert rows["gone"]["present"] is False and rows["gone"]["path"] is None
    assert rows["c1"]["present"] is True and rows["c1"]["path"].endswith("c1")


def test_a_lone_project_lists_itself(tmp_path, monkeypatch, capsys):
    root = make_project(tmp_path, "solo")
    assert run(monkeypatch, capsys, root, "projects", "list")[:2] == (0, "solo\n")


def test_outside_a_project(tmp_path, monkeypatch, capsys):
    code, out, err = run(monkeypatch, capsys, tmp_path, "projects", "list")
    assert (code, out) == (1, "")
    assert err.startswith("tcw projects list: no tcw project here")


def test_work_nodes_is_gone(graph, monkeypatch, capsys):
    assert run(monkeypatch, capsys, graph, "work", "nodes")[0] == 2
