"""Taxonomy and capabilities commands, and `tcw init`, write files and touch
nothing in git (TCW-73 Design 8.1, 8.2, 8.5; AC 17).

Inside a repository the commit, the refs and the index are the same before
and after every write; outside one, the same commands succeed.
"""

import subprocess
from pathlib import Path

import pytest

from tcw.cli import main
from tcw.store.fs import FsCapabilitiesStore, FsTaxonomyStore

WRITES = [
    ["taxonomy", "add", "Payment"],
    ["taxonomy", "add", "Refund", "--parent", "payment"],
    ["taxonomy", "rm", "payment/refund"],
    ["capabilities", "add", "billing/refund", "--status", "Missing"],
    ["capabilities", "set", "billing/refund", "--status", "Supported"],
    ["capabilities", "rm", "billing/refund"],
    ["taxonomy", "rm", "payment"],
]


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True, text=True).stdout


def git_state(root: Path) -> tuple[str, str, str, str]:
    return (git(root, "rev-parse", "HEAD"), git(root, "for-each-ref"),
            git(root, "diff", "--cached", "--name-status"),
            git(root, "ls-files", "--stage"))


def run(root: Path, monkeypatch, argv) -> int:
    monkeypatch.chdir(root)
    try:
        return main(argv)
    except SystemExit as stop:
        return stop.code


@pytest.fixture
def repository(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "t@t")
    git(root, "config", "user.name", "t")
    (root / "README.md").write_text("x\n")
    git(root, "add", "README.md")
    git(root, "commit", "-qm", "start")
    return root


def test_init_and_every_write_leave_git_alone(repository, monkeypatch, capsys):
    before = git_state(repository)
    assert run(repository, monkeypatch,
               ["init", "--id", "repo", "taxonomy", "capabilities"]) == 0
    assert git_state(repository) == before
    for argv in WRITES:
        assert run(repository, monkeypatch, argv) == 0, (argv, capsys.readouterr().err)
        assert git_state(repository) == before, argv


def test_the_same_commands_work_outside_a_repository(tmp_path, monkeypatch, capsys):
    root = tmp_path / "plain"
    root.mkdir()
    assert run(root, monkeypatch, ["init", "--id", "plain", "taxonomy", "capabilities"]) == 0
    for argv in WRITES:
        assert run(root, monkeypatch, argv) == 0, (argv, capsys.readouterr().err)
    assert not (root / ".git").exists()


def test_rm_removes_a_term_git_never_saw(repository, monkeypatch, capsys):
    assert run(repository, monkeypatch, ["init", "--id", "repo", "taxonomy"]) == 0
    assert run(repository, monkeypatch, ["taxonomy", "add", "Loose"]) == 0
    (repository / "docs" / "taxonomy" / "loose" / ".DS_Store").write_text("")
    (repository / "docs" / "taxonomy" / "loose" / "notes.md").write_text("mine\n")
    assert run(repository, monkeypatch, ["taxonomy", "rm", "loose"]) == 0
    assert not (repository / "docs" / "taxonomy" / "loose").exists()


def test_a_nested_term_still_refuses_the_removal(repository, monkeypatch, capsys):
    assert run(repository, monkeypatch, ["init", "--id", "repo", "taxonomy"]) == 0
    store = FsTaxonomyStore.open(repository)
    store.add("Admin")
    store.add("Permission", parent="admin")
    assert run(repository, monkeypatch, ["taxonomy", "rm", "admin"]) == 3
    assert "admin/permission" in capsys.readouterr().err
    assert (repository / "docs" / "taxonomy" / "admin" / "permission").is_dir()


def test_the_store_records_what_it_changed(repository):
    from tcw.store.fs import init
    init(["taxonomy", "capabilities"], repository, "repo")
    store = FsCapabilitiesStore.open(repository)
    store.add("billing/refund", status="Missing")
    root = store.root
    assert store.changed == [("wrote", root / "billing" / "refund" / "meta.yaml"),
                             ("wrote", root / "billing" / "refund" / "description.md")]
    store.changed.clear()
    store.remove("billing/refund")
    assert sorted(store.changed) == [
        ("removed", root / "billing" / "refund" / "description.md"),
        ("removed", root / "billing" / "refund" / "meta.yaml")]
