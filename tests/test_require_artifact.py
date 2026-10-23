"""`scripts/require_artifact.py` as a 3.0 `pre` hook (TCW-76 criterion 20).

The script is bound in a fixture project's `plan.pre`, and an item is moved
from spec to plan through `tcw work advance`, in-process. The hook runs the
`tcw` it finds on PATH, so the folder of the running Python, which holds the
`tcw` under test (a virtual environment locally, the installed package in
CI), is put first.
"""

import io
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tcw.cli import main
from tests.work.projects import commit_all, make_project, write_item

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "require_artifact.py"
FOLDER = "2026-10-01-a"
SPEC = Path("docs") / "work" / FOLDER / "spec" / "spec.md"


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", f"{Path(sys.executable).parent}{os.pathsep}"
                               f"{os.environ.get('PATH', '')}")
    hook = f"{shlex.quote(sys.executable)} {shlex.quote(str(SCRIPT))} spec"
    seen = "printf '%s' \"$TCW_SLUG\" > slug-seen.txt"
    root = make_project(tmp_path, "p", config={
        "stages": {"plan": {"pre": [{"command": seen}, {"command": hook}]}}})
    write_item(root, FOLDER, {"title": "a", "stage": "spec"})
    commit_all(root)
    return root


def advance(root, monkeypatch, capsys):
    monkeypatch.chdir(root)
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    try:
        code = main(["work", "advance", FOLDER])
    except SystemExit as stop:
        code = stop.code if isinstance(stop.code, int) else 1
    return code, capsys.readouterr()


def stage(root):
    item = root / "docs" / "work" / FOLDER / "item.yaml"
    return yaml.safe_load(item.read_text())["stage"]


def test_no_spec_refuses_the_move(project, monkeypatch, capsys):
    code, out = advance(project, monkeypatch, capsys)
    assert code == 3, out.err
    assert "has no spec document" in out.err
    assert stage(project) == "spec"


@pytest.mark.parametrize("text", ["", " \n\t\n"], ids=["empty", "white-space"])
def test_an_unwritten_spec_refuses_the_move(text, project, monkeypatch, capsys):
    (project / SPEC).parent.mkdir(parents=True)
    (project / SPEC).write_text(text)
    code, out = advance(project, monkeypatch, capsys)
    assert code == 3, out.err
    assert "has no spec document" in out.err
    assert stage(project) == "spec"


def test_a_written_spec_lets_the_move_through(project, monkeypatch, capsys):
    (project / SPEC).parent.mkdir(parents=True)
    (project / SPEC).write_text("# Spec\n\nSomething.\n")
    code, out = advance(project, monkeypatch, capsys)
    assert code == 0, out.err
    assert stage(project) == "plan"
    assert (project / "slug-seen.txt").read_text() == f"p.work/{FOLDER}"


def run_script(root, env):
    return subprocess.run([sys.executable, str(SCRIPT), "spec"], cwd=root, env=env,
                          capture_output=True, text=True, stdin=subprocess.DEVNULL)


def test_an_unset_slug_fails_closed(project):
    env = {k: v for k, v in os.environ.items() if k != "TCW_SLUG"}
    r = run_script(project, env)
    assert r.returncode == 1
    assert "TCW_SLUG is not set" in r.stderr


def test_an_unknown_slug_fails_closed(project):
    r = run_script(project, {**os.environ, "TCW_SLUG": "p.work/2026-10-01-nothing"})
    assert r.returncode == 1
    assert "tcw work path p.work/2026-10-01-nothing spec failed" in r.stderr


def test_the_script_names_no_2x_interface():
    text = SCRIPT.read_text()
    assert "--json" not in text
    assert "TCW_NODE_ROOT" not in text
