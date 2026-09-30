"""`complete --already-integrated` checks that the branch really reached this
checkout, and `--branch` names one TCW did not create (spec:
2026-09-29-let-complete-already-integrated-check-a-branch-worked-in-a-worktree-tcw-did-not-create)."""

import subprocess
from pathlib import Path

import pytest

from tcw.cli import main
from tcw.store.fs import FsWorkStore

from test_work_autocommit import make_item, node

PENDING = pytest.mark.xfail(strict=True, reason="not implemented yet")


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                          text=True, check=True).stdout.strip()


def branch_exists(root: Path, branch: str) -> bool:
    return subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "--quiet",
                           f"refs/heads/{branch}"], capture_output=True).returncode == 0


def commit_on(checkout: Path, name: str = "only-on-the-branch.txt") -> None:
    (checkout / name).write_text("x")
    git(checkout, "add", "--", name)
    git(checkout, "commit", "-qm", f"add {name}")


def complete(*extra: str, slug: str) -> int:
    return main(["work", "complete", slug, "--resolution", "done", "--confirm",
                 "--already-integrated", *extra])


def status(root: Path, slug: str) -> str:
    return FsWorkStore.open(root).get(slug).status


@pytest.fixture
def tcw_worktree(tmp_path, monkeypatch, capsys):
    """An item started with `--worktree`, with one commit on its branch."""
    root = node(tmp_path)
    slug = make_item(root)
    monkeypatch.chdir(root)
    assert main(["work", "start", slug, "--worktree"]) == 0
    commit_on(root / ".worktrees" / slug)
    capsys.readouterr()
    return root, slug, f"work/{slug}"


@pytest.fixture
def hand_made(tmp_path, monkeypatch, capsys):
    """An item started without a worktree, worked on a branch made by hand."""
    root = node(tmp_path)
    slug = make_item(root)
    monkeypatch.chdir(root)
    assert main(["work", "start", slug]) == 0
    wt = tmp_path / "elsewhere"
    git(root, "worktree", "add", "-q", "-b", "feature/by-hand", str(wt))
    commit_on(wt)
    capsys.readouterr()
    return root, slug, "feature/by-hand", wt


# ── 1-3: a TCW worktree ──────────────────────────────────────────────────────

@PENDING
def test_an_unmerged_branch_is_refused_and_kept(tcw_worktree, capsys):
    root, slug, branch = tcw_worktree
    head = git(root, "rev-parse", "HEAD")
    assert complete(slug=slug) == 1
    err = capsys.readouterr().err
    assert branch in err and head[:7] in err, err
    assert status(root, slug) == "active"
    assert branch_exists(root, branch)
    assert git(root, "rev-parse", "HEAD") == head           # nothing merged or moved


def test_a_merged_branch_completes_and_is_deleted(tcw_worktree, capsys):
    root, slug, branch = tcw_worktree
    git(root, "merge", "-q", "--no-edit", branch)
    assert complete(slug=slug) == 0, capsys.readouterr().err
    assert status(root, slug) == "completed"
    assert not branch_exists(root, branch)


def test_a_squash_merged_branch_completes(tcw_worktree, capsys):
    root, slug, branch = tcw_worktree
    git(root, "merge", "-q", "--squash", branch)
    git(root, "commit", "-qm", "squash")
    assert complete(slug=slug) == 0, capsys.readouterr().err
    assert status(root, slug) == "completed"


# ── 4-6, 9: a branch TCW did not create ──────────────────────────────────────

@PENDING
def test_a_merged_hand_made_branch_completes_and_is_kept(hand_made, capsys):
    root, slug, branch, _ = hand_made
    git(root, "merge", "-q", "--no-edit", branch)
    assert complete("--branch", branch, slug=slug) == 0, capsys.readouterr().err
    assert status(root, slug) == "completed"
    assert branch_exists(root, branch)                        # never TCW's to delete


@PENDING
def test_an_unmerged_hand_made_branch_is_refused(hand_made, capsys):
    root, slug, branch, _ = hand_made
    assert complete("--branch", branch, slug=slug) == 1
    assert branch in capsys.readouterr().err
    assert status(root, slug) == "active"


@PENDING
def test_branch_without_already_integrated_is_a_usage_error(hand_made, capsys):
    root, slug, branch, _ = hand_made
    with pytest.raises(SystemExit) as raised:
        main(["work", "complete", slug, "--resolution", "done", "--confirm",
              "--branch", branch])
    assert raised.value.code == 2
    assert "--already-integrated" in capsys.readouterr().err


@PENDING
def test_a_branch_that_does_not_exist_is_refused(hand_made, capsys):
    root, slug, _, _ = hand_made
    assert complete("--branch", "nosuch", slug=slug) == 1
    assert "nosuch" in capsys.readouterr().err
    assert status(root, slug) == "active"


@PENDING
def test_a_branch_other_than_the_recorded_one_is_refused(tcw_worktree, capsys):
    root, slug, branch = tcw_worktree
    git(root, "merge", "-q", "--no-edit", branch)
    git(root, "branch", "other")
    assert complete("--branch", "other", slug=slug) == 1
    err = capsys.readouterr().err
    assert "other" in err and branch in err, err
    assert status(root, slug) == "active"


@PENDING
def test_no_branch_at_all_is_refused_naming_the_flag(hand_made, capsys):
    root, slug, _, _ = hand_made
    assert complete(slug=slug) == 1
    assert "--branch" in capsys.readouterr().err
    assert status(root, slug) == "active"


# ── 7: a recorded branch already gone ────────────────────────────────────────

def test_a_recorded_branch_deleted_outside_tcw_completes(tcw_worktree, capsys):
    root, slug, branch = tcw_worktree
    git(root, "worktree", "remove", "--force", str(root / ".worktrees" / slug))
    git(root, "branch", "-D", branch)
    assert complete(slug=slug) == 0, capsys.readouterr().err
    assert status(root, slug) == "completed"


# ── 8: not from the branch itself ────────────────────────────────────────────

@PENDING
def test_a_checkout_on_the_branch_itself_is_refused(hand_made, monkeypatch, capsys):
    """Checked against itself, any branch is "merged"."""
    root, slug, branch, wt = hand_made
    git(wt, "checkout", "-q", "--detach")                    # free the branch
    git(root, "checkout", "-q", branch)
    assert complete("--branch", branch, slug=slug) == 1
    assert "checked out" in capsys.readouterr().err
    assert status(root, slug) == "active"
