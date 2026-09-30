"""`complete --already-integrated` checks that the branch really reached this
checkout, and `--branch` names one TCW did not create (spec:
2026-09-29-let-complete-already-integrated-check-a-branch-worked-in-a-worktree-tcw-did-not-create)."""

import subprocess
from pathlib import Path

import pytest

from tcw.cli import main
from tcw.store.fs import FsWorkStore

from test_work_autocommit import make_item, node


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

def test_a_merged_hand_made_branch_completes_and_is_kept(hand_made, capsys):
    root, slug, branch, _ = hand_made
    git(root, "merge", "-q", "--no-edit", branch)
    assert complete("--branch", branch, slug=slug) == 0, capsys.readouterr().err
    assert status(root, slug) == "completed"
    assert branch_exists(root, branch)                        # never TCW's to delete


def test_an_unmerged_hand_made_branch_is_refused(hand_made, capsys):
    root, slug, branch, _ = hand_made
    assert complete("--branch", branch, slug=slug) == 1
    assert branch in capsys.readouterr().err
    assert status(root, slug) == "active"


def test_branch_without_already_integrated_is_a_usage_error(hand_made, capsys):
    root, slug, branch, _ = hand_made
    assert main(["work", "complete", slug, "--resolution", "done", "--confirm",
                 "--branch", branch]) == 2
    assert "--already-integrated" in capsys.readouterr().err


def test_a_branch_that_does_not_exist_is_refused(hand_made, capsys):
    root, slug, _, _ = hand_made
    assert complete("--branch", "nosuch", slug=slug) == 1
    assert "nosuch" in capsys.readouterr().err
    assert status(root, slug) == "active"


def test_a_branch_other_than_the_recorded_one_is_refused(tcw_worktree, capsys):
    root, slug, branch = tcw_worktree
    git(root, "merge", "-q", "--no-edit", branch)
    git(root, "branch", "other")
    assert complete("--branch", "other", slug=slug) == 1
    err = capsys.readouterr().err
    assert "other" in err and branch in err, err
    assert status(root, slug) == "active"


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

def test_a_checkout_on_the_branch_itself_is_refused(hand_made, monkeypatch, capsys):
    """Checked against itself, any branch is "merged"."""
    root, slug, branch, wt = hand_made
    git(wt, "checkout", "-q", "--detach")                    # free the branch
    git(root, "checkout", "-q", branch)
    assert complete("--branch", branch, slug=slug) == 1
    assert "checked out" in capsys.readouterr().err
    assert status(root, slug) == "active"


# ── review follow-ups ────────────────────────────────────────────────────────

def test_a_detached_head_at_the_branch_tip_is_refused(hand_made, monkeypatch, capsys):
    """Inside a hand-made worktree parked at the branch's tip, the tip is
    trivially an ancestor of HEAD — and the completion would land on no branch."""
    root, slug, branch, wt = hand_made
    git(wt, "checkout", "-q", "--detach")
    monkeypatch.chdir(wt)
    assert complete("--branch", branch, slug=slug) == 1
    assert "detached" in capsys.readouterr().err
    assert status(root, slug) == "active"


def test_a_tag_named_like_the_branch_does_not_hide_it(hand_made, capsys):
    root, slug, branch, wt = hand_made
    git(wt, "checkout", "-q", "--detach")
    git(root, "tag", branch, branch)
    git(root, "checkout", "-q", branch)
    assert complete("--branch", branch, slug=slug) == 1
    assert "checked out" in capsys.readouterr().err


def test_a_conflicting_branch_says_how_to_get_out(tcw_worktree, capsys):
    """Squashed, then trunk edited the same lines: merging conflicts. The way
    out when the work did land is deleting the branch, and the refusal says so."""
    root, slug, branch = tcw_worktree
    git(root, "merge", "-q", "--squash", branch)
    git(root, "commit", "-qm", "squash")
    (root / "only-on-the-branch.txt").write_text("changed on trunk")
    git(root, "commit", "-qam", "trunk edit")
    assert complete(slug=slug) == 1
    err = capsys.readouterr().err
    assert "would still change files" in err and f"delete {branch}" in err, err
    assert branch_exists(root, branch)


def test_branch_on_a_discard_is_a_usage_error(hand_made, capsys):
    root, slug, branch, _ = hand_made
    assert main(["work", "complete", slug, "--resolution", "wontfix", "--confirm",
                 "--already-integrated", "--branch", branch]) == 2
    assert status(root, slug) == "active"


def test_already_integrated_on_a_discard_without_a_worktree_is_still_refused(
        hand_made, capsys):
    root, slug, _, _ = hand_made
    assert main(["work", "complete", slug, "--resolution", "wontfix", "--confirm",
                 "--already-integrated"]) == 1
    assert status(root, slug) == "active"


def test_naming_the_recorded_branch_gets_the_recorded_branchs_advice(tcw_worktree, capsys):
    """`--branch` equal to the recorded branch is the recorded branch: the way out
    is deleting it, not "an item without a worktree"."""
    root, slug, branch = tcw_worktree
    assert complete("--branch", branch, slug=slug) == 1
    err = capsys.readouterr().err
    assert f"delete {branch}" in err and "without a worktree" not in err, err
