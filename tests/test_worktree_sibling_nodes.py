"""In a linked worktree of a repository holding several nodes, every node of that
repository resolves to its worktree copy, not only the one the command ran from
(spec: 2026-09-15-resolve-sibling-nodes-to-their-worktree-copies; GitHub #39)."""

import subprocess
import sys
from pathlib import Path

import pytest


def git(path: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True)


def repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q")
    git(path, "config", "user.email", "t@t")
    git(path, "config", "user.name", "t")
    return path


def config(path: Path, pid: str, *, parent: dict | None = None,
           children: dict | None = None) -> None:
    path.mkdir(parents=True, exist_ok=True)
    text = f"id: {pid}\n"
    if parent or children:
        text += "connected-projects:\n"
        for key, links in (("parent", parent), ("children", children)):
            if links:
                text += f"  {key}:\n" + "".join(f"    {k}: {v}\n" for k, v in links.items())
    (path / "tcw-config.yaml").write_text(text)


def validate(cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "tcw.cli", "validate"], cwd=cwd,
                          capture_output=True, text=True, timeout=60)


@pytest.fixture
def workspace(tmp_path) -> Path:
    """The issue's layout: an outer node whose child is the root of an inner
    repository holding two more nodes."""
    ws = repo(tmp_path / "workspace")
    config(ws, "workspace", children={"app-repo": "app"})
    app = repo(ws / "app")
    config(app, "app-repo", parent={"workspace": ".."},
           children={"pkg-a": "pkg-a", "pkg-b": "pkg-b"})
    config(app / "pkg-a", "pkg-a", parent={"app-repo": ".."})
    config(app / "pkg-b", "pkg-b", parent={"app-repo": ".."})
    git(app, "add", "-A")
    git(app, "commit", "-qm", "nodes")
    return ws


@pytest.mark.parametrize("node", ["pkg-a", "pkg-b", "."])
def test_every_node_of_a_linked_worktree_resolves_there(workspace, node):
    git(workspace / "app", "worktree", "add", "-q", "../app-wt", "-b", "feature")
    done = validate(workspace / "app-wt" / node)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "duplicate project id" not in done.stdout + done.stderr


def test_a_worktree_inside_its_own_primary_checkout(workspace):
    """TCW's own layout: `.worktrees/<slug>` under the primary checkout."""
    git(workspace / "app", "worktree", "add", "-q", ".worktrees/feature", "-b", "feature")
    done = validate(workspace / "app" / ".worktrees" / "feature" / "pkg-a")
    assert done.returncode == 0, done.stdout + done.stderr


def test_a_node_only_the_primary_checkout_has_still_resolves_there(workspace):
    app = workspace / "app"
    git(app, "worktree", "add", "-q", "../app-wt", "-b", "feature")
    # Added on the primary checkout's branch after the worktree was made.
    config(app / "pkg-c", "pkg-c", parent={"app-repo": ".."})
    wt_cfg = workspace / "app-wt" / "tcw-config.yaml"
    wt_cfg.write_text(wt_cfg.read_text().replace(
        "    pkg-b: pkg-b\n", "    pkg-b: pkg-b\n    pkg-c: ../app/pkg-c\n"))
    done = validate(workspace / "app-wt" / "pkg-a")
    assert "duplicate project id" not in done.stdout + done.stderr, done.stdout


def test_one_id_in_two_repositories_is_still_a_duplicate(workspace):
    other = repo(workspace / "other")
    config(other, "pkg-b", parent={"workspace": ".."})
    ws_cfg = workspace / "tcw-config.yaml"
    ws_cfg.write_text(ws_cfg.read_text() + "    pkg-b-again: other\n")
    git(workspace / "app", "worktree", "add", "-q", "../app-wt", "-b", "feature")
    done = validate(workspace / "app-wt" / "pkg-a")
    assert done.returncode == 1 and "duplicate project id 'pkg-b'" in done.stdout + done.stderr, \
        done.stdout + done.stderr
