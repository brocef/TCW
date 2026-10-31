"""Running `tcw` in-process over a fixture project with all three stores,
for the TCW-111 tests of object folders, state files and nesting.

`project` makes a git repository scaffolded by the branch's own `init`, with
the work store's configuration passed by the test (`work`), so no axis the
code branches on is defaulted here. `obj` writes one object folder by hand,
its state file through `tests/statefiles.py`.
"""

from __future__ import annotations

import io
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from tcw.cli import main
from tcw.store.fs import init
from tests.projectfiles import config_file, write_config_file
from tests.statefiles import (CAPABILITY_STATE, ITEM_STATE, TAXONOMY_STATE,
                              write_state_data)

STATES = {"taxonomy": TAXONOMY_STATE, "capabilities": CAPABILITY_STATE,
          "work": ITEM_STATE}


@dataclass
class Result:
    code: int
    out: str
    err: str


@pytest.fixture
def tcw(monkeypatch, capsys):
    def run(argv, cwd, stdin=""):
        monkeypatch.chdir(cwd)
        monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))
        try:
            code = main(list(argv))
        except SystemExit as stop:
            code = stop.code if isinstance(stop.code, int) else 1
        captured = capsys.readouterr()
        return Result(code, captured.out, captured.err)
    return run


def project(tmp_path: Path, project_id: str = "demo", *, work: dict,
            name: str | None = None) -> Path:
    """A project with a taxonomy, a capabilities and a work store, its
    `work:` section set to `work`."""
    root = tmp_path / (name or project_id)
    root.mkdir(parents=True)
    for args in (("init", "-q"), ("config", "user.email", "t@t"),
                 ("config", "user.name", "t")):
        subprocess.run(["git", "-C", str(root), *args], check=True,
                       capture_output=True)
    init(["taxonomy", "capabilities", "work"], root, project_id)
    path = config_file(root)
    document = yaml.safe_load(path.read_text())
    document["work"] = work
    write_config_file(path, yaml.safe_dump(document, sort_keys=False))
    return root


def store(root: Path, namespace: str) -> Path:
    return root / "docs" / namespace


def obj(root: Path, namespace: str, id_path: str, **data) -> Path:
    """One object folder by hand: its state file holding `data`, and for a
    term or capability an empty `description.md`."""
    folder = store(root, namespace) / id_path
    folder.mkdir(parents=True, exist_ok=True)
    write_state_data(folder / STATES[namespace], data)
    if namespace != "work":
        (folder / "description.md").write_text("")
    return folder


def item(root: Path, id_path: str, title: str = "x", stage: str = "request",
         **data) -> Path:
    """A files-backend work item by hand."""
    return obj(root, "work", id_path, title=title, stage=stage, **data)


def findings(result: Result) -> list[str]:
    """The finding lines `tcw validate` printed."""
    return [line for line in result.out.splitlines()
            if line.startswith(("error:", "warning:", "unresolved:"))]
