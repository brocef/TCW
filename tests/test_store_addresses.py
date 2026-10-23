"""Where a store lives (TCW-110 Design 7): a plain location in the shared
file is relative to the project, or a `tcw://` folder address; each fixture
is a set of git repositories side by side under `tmp_path`."""

from __future__ import annotations

import io
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from tcw.cli import main
from tcw.store.fs import init
from tests.projectfiles import config_file, write_config_file
from tests.work.projects import git, make_project

RELATIVE = "must be a path relative to the project"


@dataclass
class Result:
    code: int
    out: str
    err: str


@pytest.fixture
def tcw(monkeypatch, capsys):
    def run(argv, cwd):
        monkeypatch.chdir(cwd)
        monkeypatch.setattr(sys, "stdin", io.StringIO(""))
        try:
            code = main(argv)
        except SystemExit as stop:
            code = stop.code if isinstance(stop.code, int) else 1
        captured = capsys.readouterr()
        return Result(code, captured.out, captured.err)
    return run


def set_location(root: Path, component: str, value: str) -> None:
    path = config_file(root)
    document = yaml.safe_load(path.read_text())
    section = document.get(component)
    document[component] = {**(section if isinstance(section, dict) else {}), "path": value}
    write_config_file(path, yaml.safe_dump(document, sort_keys=False))


def _says_relative(text: str, key: str) -> None:
    assert f"{key}: {RELATIVE}" in text or f"{key} {RELATIVE}" in text, text
    assert "tcw://" in text and ".tcw/tcw-manifest.local.yaml" in text


# -- AC 24: a plain location is relative (Design 7.1) -----------------------------------


@pytest.mark.parametrize("component", ["work", "taxonomy", "capabilities"])
@pytest.mark.parametrize("value", ["/tmp/x", "~/x"])
def test_ac24_an_absolute_or_home_location_stops_every_command(tcw, tmp_path, component,
                                                               value):
    app = make_project(tmp_path, "app", config={})
    init(["taxonomy", "capabilities"], app)
    set_location(app, component, value)
    listed = tcw(["work", "list"], app)
    assert listed.code == 1
    _says_relative(listed.err, f"{component}.path")
    checked = tcw(["validate"], app)
    assert checked.code == 1
    [line] = [line for line in checked.out.splitlines() if f"{component}.path" in line]
    assert line.startswith("error: ")
    _says_relative(line, f"{component}.path")


@pytest.mark.parametrize("flag, key", [("--work-path", "work.path"),
                                       ("--taxonomy-path", "taxonomy.path")])
@pytest.mark.parametrize("value", ["/abs/store", "~/store"])
def test_ac24_init_refuses_an_absolute_or_home_location_and_writes_nothing(
        tcw, tmp_path, flag, key, value):
    root = tmp_path / "fresh"
    root.mkdir()
    git(root, "init", "-q")
    component = key.split(".")[0]
    found = tcw(["init", "--id", "fresh", flag, value, component], root)
    assert found.code == 2
    _says_relative(found.err, key)
    assert sorted(p.name for p in root.iterdir()) == [".git"]
