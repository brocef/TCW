"""A worktree whose detached `HEAD` holds commits no ref contains is never torn
down: a completion refuses before anything changes, a discard keeps the worktree
(spec: 2026-09-30-refuse-to-tear-down-a-detached-worktree-whose-commits-are-on-no-branch)."""

import subprocess

import pytest

from tcw.cli import main
from tcw.store.fs import remove_worktree

from test_already_integrated_check import (branch_exists, commit_on, git,  # noqa: F401
                                           status, tcw_worktree)


def complete(slug: str, *extra: str, resolution: str = "done") -> int:
    return main(["work", "complete", slug, "--resolution", resolution, "--confirm",
                 *extra])


def reachable(root, commit: str) -> bool:
    return subprocess.run(["git", "-C", str(root), "cat-file", "-e", f"{commit}^{{commit}}"],
                          capture_output=True).returncode == 0


@pytest.fixture
def detached(tcw_worktree):
    """The item's worktree detached at a commit of its own, on no ref."""
    root, slug, branch = tcw_worktree
    wt = root / ".worktrees" / slug
    git(wt, "switch", "-q", "--detach")
    commit_on(wt, "only-on-a-detached-head.txt")
    return root, slug, branch, wt, git(wt, "rev-parse", "HEAD")


def assert_untouched(root, slug, branch, wt, lost, state="active"):
    assert status(root, slug) == state
    assert branch_exists(root, branch)
    assert wt.is_dir()
    assert git(wt, "rev-parse", "HEAD") == lost


# ── 1, 2: a completion is refused and changes nothing ────────────────────────

@pytest.mark.parametrize("extra", [(), ("--already-integrated",)])
def test_a_completion_is_refused(detached, capsys, extra):
    root, slug, branch, wt, lost = detached
    if extra:                                  # integrated, so only the detached commit blocks
        git(root, "merge", "-q", "--no-edit", branch)
    head = git(root, "rev-parse", "HEAD")
    assert complete(slug, *extra) == 1
    err = capsys.readouterr().err
    assert lost[:7] in err and str(wt) in err, err
    assert "branch" in err, err
    assert_untouched(root, slug, branch, wt, lost)
    assert git(root, "rev-parse", "HEAD") == head            # nothing merged


# ── 3: a discard keeps the worktree ──────────────────────────────────────────

def test_a_discard_keeps_the_worktree(detached, capsys):
    root, slug, branch, wt, lost = detached
    assert complete(slug, resolution="wontfix") == 0
    err = capsys.readouterr().err
    assert lost[:7] in err and str(wt) in err, err
    assert status(root, slug) == "discarded"
    assert wt.is_dir() and git(wt, "rev-parse", "HEAD") == lost


# ── 4: detached, but at a commit a branch holds ──────────────────────────────

def test_detached_at_the_branch_tip_completes_as_before(tcw_worktree, capsys):
    root, slug, branch = tcw_worktree
    wt = root / ".worktrees" / slug
    git(wt, "switch", "-q", "--detach")
    assert complete(slug) == 0, capsys.readouterr().err
    assert status(root, slug) == "completed"
    assert not wt.exists() and not branch_exists(root, branch)


# ── 5: saved on a branch, the completion goes through ────────────────────────

def test_once_saved_on_a_branch_it_completes(detached, capsys):
    root, slug, branch, wt, lost = detached
    git(wt, "branch", "keep")
    assert complete(slug) == 0, capsys.readouterr().err
    assert status(root, slug) == "completed"
    assert branch_exists(root, "keep") and reachable(root, lost)


# ── 6: the teardown itself refuses ───────────────────────────────────────────

def test_remove_worktree_keeps_it(detached):
    root, slug, branch, wt, lost = detached
    warnings = remove_worktree(root, slug, branch)
    assert warnings and lost[:7] in " ".join(warnings), warnings
    assert wt.is_dir() and branch_exists(root, branch)


def test_force_does_not_bypass_it(detached, capsys):
    root, slug, branch, wt, lost = detached
    assert complete(slug, "--force") == 1
    assert lost[:7] in capsys.readouterr().err
    assert_untouched(root, slug, branch, wt, lost)


# ── 7: a plain folder is not mistaken for the worktree ───────────────────────

def test_a_plain_folder_is_not_answered_for_by_the_primary_checkout(tmp_path):
    """`git -C` on a plain folder inside the primary checkout answers for the
    primary checkout; its detached commit must not be reported as the folder's."""
    from test_work_autocommit import node
    from tcw.store.fs import unbranched_commits
    root = node(tmp_path)
    git(root, "switch", "-q", "--detach")
    commit_on(root, "primary-only.txt")
    primary = git(root, "rev-parse", "HEAD")
    plain = root / ".worktrees" / "not-a-worktree"
    plain.mkdir(parents=True)
    answer = unbranched_commits(plain)
    assert isinstance(answer, str), answer          # "could not check", not a list
    assert primary[:7] not in answer
