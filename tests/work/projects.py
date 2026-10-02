"""Fixture projects for the 3.0 work tests.

`make_project` builds one project: a git repository with a `tcw-config.yaml`
and an empty work folder. Every configuration key the code under test branches
on is passed explicitly by the test, through `config`.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

WORK_PATH = Path("docs") / "work"


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True, text=True,
                          stdin=subprocess.DEVNULL).stdout


def make_project(tmp_path: Path, project_id: str, *, config: dict | None = None,
                 name: str | None = None) -> Path:
    """A project at `tmp_path/<name or id>` with `work:` set to `config`."""
    root = tmp_path / (name or project_id)
    root.mkdir(parents=True)
    git(root, "init", "-q")
    git(root, "config", "user.email", "t@t")
    git(root, "config", "user.name", "t")
    document = {"id": project_id}
    if config is not None:
        document["work"] = config
    (root / "tcw-config.yaml").write_text(yaml.safe_dump(document, sort_keys=False))
    (root / WORK_PATH).mkdir(parents=True)
    (root / WORK_PATH / ".gitkeep").write_text("")
    return root


def connect(a: Path, b: Path, relation: str) -> None:
    """Declare `b` in `a`'s connected-projects under `relation` (parent or
    children), by a path relative to `a`."""
    import os
    path = a / "tcw-config.yaml"
    document = yaml.safe_load(path.read_text())
    b_id = yaml.safe_load((b / "tcw-config.yaml").read_text())["id"]
    section = document.setdefault("connected-projects", {}).setdefault(relation, {})
    section[b_id] = os.path.relpath(b, a)
    path.write_text(yaml.safe_dump(document, sort_keys=False))


def commit_all(root: Path, message: str = "fixture") -> None:
    git(root, "add", "-A")
    git(root, "commit", "-qm", message, "--allow-empty")


def write_item(root: Path, folder: str, data: "dict | str") -> Path:
    """A hand-written item folder in the project's work path."""
    path = root / WORK_PATH / folder
    path.mkdir(parents=True, exist_ok=True)
    text = data if isinstance(data, str) else yaml.safe_dump(data, sort_keys=False)
    (path / "item.yaml").write_text(text)
    return path
