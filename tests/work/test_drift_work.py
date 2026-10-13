"""`tcw capabilities drift` on the 3.0 work store (TCW-70 Design 10.3;
TCW-73 Design 7; AC 16). The Jira case is in
`tests/work/jira/test_jira_drift.py`."""

import ast
from pathlib import Path

import pytest

import tcw
from tcw.capabilities.cli import _completed_work_drift
from tcw.cli import main
from tcw.store.fs import FsCapabilitiesStore, init
from tests.work.projects import connect, make_project, write_item


def project(tmp_path, name="p"):
    p = make_project(tmp_path, name)
    init(["capabilities"], p, name)
    return p


def drift(root, monkeypatch, capsys):
    monkeypatch.chdir(root)
    code = main(["capabilities", "drift"])
    printed = capsys.readouterr()
    return code, printed.out.splitlines(), printed.err


def test_a_completed_item_declaring_an_absent_capability_drifts(tmp_path):
    p = project(tmp_path)
    folder = write_item(p, "2026-10-01-a", {"title": "a", "stage": "completed"})
    (folder / "capabilities.yaml").write_text("new: [x/y]\n")
    [problem] = _completed_work_drift(p)
    assert (problem.kind, problem.where) == ("drift", "x/y")
    assert "2026-10-01-a" in problem.message


def test_no_declaration_no_drift(tmp_path):
    p = project(tmp_path)
    write_item(p, "2026-10-01-a", {"title": "a", "stage": "completed"})
    assert _completed_work_drift(p) == []


def test_an_unfinished_item_is_not_drift(tmp_path):
    p = project(tmp_path)
    folder = write_item(p, "2026-10-01-a", {"title": "a", "stage": "implement"})
    (folder / "capabilities.yaml").write_text("new: [x/y]\n")
    assert _completed_work_drift(p) == []


def test_an_unreadable_item_is_named_and_the_rest_still_checked(tmp_path):
    p = project(tmp_path)
    folder = write_item(p, "2026-10-01-a", {"title": "a", "stage": "completed"})
    (folder / "capabilities.yaml").write_text("new: [x/y]\n")
    write_item(p, "2026-10-01-bad", "title: [x\n")
    problems = _completed_work_drift(p)
    assert any(p.where == "x/y" for p in problems)
    assert any(p.kind == "unchecked" and p.where.endswith("2026-10-01-bad/item.yaml")
               for p in problems)


# -- through `tcw capabilities drift` (AC 16) ------------------------------------------

def test_drift_prints_one_line_and_exits_1(tmp_path, monkeypatch, capsys):
    p = project(tmp_path)
    folder = write_item(p, "2026-10-01-a", {"title": "a", "stage": "completed"})
    (folder / "capabilities.yaml").write_text("new: [x/y]\n")
    code, out, _ = drift(p, monkeypatch, capsys)
    assert code == 1
    [line] = out
    assert line.startswith("drift: x/y: ")


def test_a_later_removal_clears_it(tmp_path, monkeypatch, capsys):
    p = project(tmp_path)
    first = write_item(p, "2026-10-01-a", {"title": "a", "stage": "completed"})
    (first / "capabilities.yaml").write_text("new: [x/y]\n")
    later = write_item(p, "2026-10-02-b", {"title": "b", "stage": "completed"})
    (later / "capabilities.yaml").write_text("removed: [x/y]\n")
    assert drift(p, monkeypatch, capsys)[:2] == (0, [])


def test_an_inherited_capability_never_ruled_on(tmp_path, monkeypatch, capsys):
    base = project(tmp_path, "base")
    FsCapabilitiesStore.open(base).add("auth/login", status="Supported")
    child = project(tmp_path, "child")
    connect(child, base, "upstream")
    FsCapabilitiesStore.open(child).extends_add("base")
    code, out, _ = drift(child, monkeypatch, capsys)
    assert code == 1
    assert out == [line for line in out if line.startswith("unreviewed: base/auth/login: ")]
    assert len(out) == 1


def test_without_a_work_component_only_unreviewed_and_a_note(tmp_path, monkeypatch, capsys):
    root = tmp_path / "plain"
    root.mkdir()
    init(["capabilities"], root, "plain")
    code, out, err = drift(root, monkeypatch, capsys)
    assert (code, out) == (0, [])
    assert "completed-work drift was not checked" in err


def test_no_code_under_capabilities_reads_planning_doc():
    """AC 16, last bullet: the field is retired (Design 8.6), and drift
    follows `<item>/capabilities.yaml` instead. String constants only, so a
    docstring that says so does not count."""
    folder = Path(tcw.__file__).resolve().parent / "capabilities"
    for path in folder.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docstrings = {id(node.body[0].value) for node in ast.walk(tree)
                      if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef))
                      and node.body and isinstance(node.body[0], ast.Expr)}
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                    and id(node) not in docstrings:
                assert "Planning doc" not in node.value, f"{path}:{node.lineno}"
