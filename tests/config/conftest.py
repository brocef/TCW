"""Fixtures for the personal-configuration tests (TCW-72).

`personal` switches the personal layers back on for one test (the suite-wide
fixture switches them off) and gives the paths of both personal files, with
`XDG_CONFIG_HOME` and `HOME` inside the test's own folder.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml
from tests.projectfiles import write_config, write_config_file


@dataclass
class Personal:
    root: Path        # the acting project
    xdg: Path         # $XDG_CONFIG_HOME
    home: Path        # $HOME

    @property
    def user_file(self) -> Path:
        return self.xdg / "tcw" / "config.yaml"

    @property
    def local_file(self) -> Path:
        return self.root / ".tcw/tcw-config.local.yaml"

    @property
    def project_file(self) -> Path:
        return self.root / ".tcw/tcw-config.yaml"

    def project(self, mapping: dict) -> None:
        write_config_file(self.project_file, yaml.safe_dump({"id": "p", **mapping},
                                                     sort_keys=False))

    def user(self, mapping) -> None:
        self.user_file.parent.mkdir(parents=True, exist_ok=True)
        write_config_file(self.user_file, mapping if isinstance(mapping, str)
                                  else yaml.safe_dump(mapping, sort_keys=False))

    def local(self, mapping) -> None:
        write_config_file(self.local_file, mapping if isinstance(mapping, str)
                                   else yaml.safe_dump(mapping, sort_keys=False))


@pytest.fixture
def personal(tmp_path, monkeypatch) -> Personal:
    root = tmp_path / "p"
    root.mkdir()
    write_config(root, "id: p\n")
    xdg, home = tmp_path / "xdg", tmp_path / "home"
    home.mkdir()
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    monkeypatch.setenv("HOME", str(home))
    return Personal(root, xdg, home)


def problem_lines(config) -> list[str]:
    return [str(p) for p in config.problems]


SOURCE = str(Path(__file__).resolve().parents[2])


@dataclass
class Ran:
    code: int
    out: str
    err: str


def tcw(cwd: Path, *argv: str, stdin: str = "") -> Ran:
    """`tcw` as a shell runs it, with this checkout's code and the test's
    environment (personal files as the test set them)."""
    import os
    import subprocess
    import sys
    env = {**os.environ, "PYTHONPATH": SOURCE}
    done = subprocess.run([sys.executable, "-m", "tcw.cli", *argv], cwd=cwd, env=env,
                          input=stdin, capture_output=True, text=True, timeout=60)
    return Ran(done.returncode, done.stdout, done.stderr)
