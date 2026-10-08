"""TCW never changes git state (TCW-70 AC 12, the behavior).

Each command runs between two snapshots of both repositories: `HEAD`, every
ref, the index, and what is staged. A delegation leaves the target's work
store with uncommitted files, which the next write into it rightly refuses, so
the test commits between commands itself, outside the snapshots.
"""

import io
import sys
from datetime import date

import pytest
import yaml

from tcw.cli import main
from tests.work.projects import commit_all, connect, git, make_project, write_item

TODAY = date.today().isoformat()


def snapshot(root):
    return (git(root, "rev-parse", "HEAD"),
            git(root, "for-each-ref"),
            git(root, "ls-files", "--stage"),
            git(root, "diff", "--cached", "--name-only"))


def tcw(monkeypatch, capsys, cwd, *argv, stdin=""):
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))
    try:
        code = main(["work", *argv])
    except SystemExit as stop:
        code = stop.code
    captured = capsys.readouterr()
    assert code == 0, f"tcw work {' '.join(argv)}: {captured.err}"


@pytest.fixture
def pq(tmp_path):
    p = make_project(tmp_path, "p", config={"tags": ["ui"]})
    q = make_project(tmp_path, "q")
    connect(p, q, "children")
    connect(q, p, "parent")
    write_item(q, "2026-10-01-x", {"title": "x", "stage": "request"})
    for root in (p, q):
        commit_all(root)
    return p, q


COMMANDS = [
    ("new", "A thing"),
    ("edit", f"{TODAY}-a-thing", "--priority", "high"),
    ("comment", f"{TODAY}-a-thing"),
    ("advance", f"{TODAY}-a-thing", "--to", "plan", "--force", "--reason", "r"),
    ("rename", f"{TODAY}-a-thing", "another-thing"),
    ("edit", f"{TODAY}-another-thing", "--blocks", "q/2026-10-01-x"),
    ("new", "Delegated", "--project", "q"),
    ("discard", f"{TODAY}-another-thing", "--reason", "done with it"),
    ("tags", "add", "x"),
    ("tags", "rm", "x"),
]


def test_no_command_changes_git_state(pq, monkeypatch, capsys):
    p, q = pq
    for argv in COMMANDS:
        before = [snapshot(root) for root in (p, q)]
        tcw(monkeypatch, capsys, p, *argv, stdin="text\n")
        assert [snapshot(root) for root in (p, q)] == before, argv
        for root in (p, q):
            commit_all(root, " ".join(argv))


def test_tags_outside_git(tmp_path, monkeypatch, capsys):
    p = make_project(tmp_path, "p", config={"tags": ["ui"]})
    import shutil
    shutil.rmtree(p / ".git")
    tcw(monkeypatch, capsys, p, "tags", "add", "x")
    assert "x" in yaml.safe_load((p / "tcw-config.yaml").read_text())["work"]["tags"]
    tcw(monkeypatch, capsys, p, "tags", "rm", "x")
    assert "x" not in yaml.safe_load((p / "tcw-config.yaml").read_text())["work"]["tags"]
