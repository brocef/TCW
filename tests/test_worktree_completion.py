"""`tcw work complete` judges a `--worktree` item from its branch's copy.

`complete` runs in the primary checkout, but a `--worktree` item's lifecycle
moves are committed on its branch, so the primary copy stays as `start` left it
until the merge-back. Everything here is about the judgments `complete` makes
*before* that merge — and about the guard that keeps them honest, since the merge
carries only committed content.
"""

import subprocess
from pathlib import Path

import yaml

from tcw.store.fs import FsWorkStore, init


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args],
                          capture_output=True, text=True)


def repo(tmp_path: Path, name: str = "repo", sub: str = ".") -> Path:
    """A committed TCW work node in its own git repository.

    `sub` puts the node in a subdirectory of the repository — the nested layout
    where the worktree's copy of the node is NOT at the worktree's top.
    """
    top = tmp_path / name
    node = top if sub == "." else top / sub
    node.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "--initial-branch=main", str(top)], check=True)
    _git(top, "config", "user.email", "t@t")
    _git(top, "config", "user.name", "t")
    init(["work"], node, project_id=name if sub == "." else Path(sub).name)
    commit_all(top, "seed")
    return node


def commit_all(root: Path, message: str = "work") -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", message)


def head(root: Path) -> str:
    return _git(root, "rev-parse", "HEAD").stdout.strip()


def new_item(root, monkeypatch, capsys, title: str = "Ship") -> str:
    from tcw.cli import main
    monkeypatch.chdir(root)
    assert main(["work", "new", title]) == 0
    slug = capsys.readouterr().out.strip().splitlines()[-1].strip()
    commit_all(_top(root), f"add {title}")
    return slug


def _top(node: Path) -> Path:
    return Path(_git(node, "rev-parse", "--show-toplevel").stdout.strip())


def start_worktree(root, slug, monkeypatch, capsys, *, force: bool = False) -> Path:
    """Start the item in a worktree and return this node's directory inside it."""
    from tcw.cli import main
    monkeypatch.chdir(root)
    argv = ["work", "start", slug, "--worktree"] + (["--force"] if force else [])
    assert main(argv) == 0
    capsys.readouterr()
    top = _top(root)
    return root / ".worktrees" / slug / root.resolve().relative_to(top.resolve())


def run_in(path: Path, monkeypatch, capsys, *argv: str) -> tuple[int, str, str]:
    from tcw.cli import main
    monkeypatch.chdir(path)
    code = main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def branch_commit(worktree_node: Path, name: str = "branch-work.txt") -> str:
    """Commit something on the branch, and return that commit.

    Every refusal test needs one: `start --worktree` cuts the branch from `HEAD`,
    so until the branch commits something of its own, "the branch reached the
    primary checkout" is true before any merge and the refusal assertion below
    would prove nothing.
    """
    top = _top(worktree_node)
    (top / name).write_text("x\n", encoding="utf-8")
    commit_all(top, "branch work")
    return head(top)


def refused_before_merge(root: Path, worktree_node: Path, slug: str, tip: str) -> None:
    """The item, its branch and its worktree are exactly as they were."""
    assert FsWorkStore.open(root).get(slug).status == "active"
    assert worktree_node.is_dir()
    merged = _git(root, "merge-base", "--is-ancestor", tip, "HEAD")
    assert merged.returncode != 0, "the work branch was merged despite the refusal"


# ── the skipped-verify warning ───────────────────────────────────────────────

WARNING = "directly from active"


def test_no_false_warning_when_the_branch_submitted_the_item(
        tmp_path, monkeypatch, capsys):
    """Criterion 1. The item was submitted in the worktree, so the verify stage
    was not skipped — but the primary checkout's copy still reads `active`."""
    root = repo(tmp_path)
    slug = new_item(root, monkeypatch, capsys)
    wt = start_worktree(root, slug, monkeypatch, capsys)
    branch_commit(wt)
    assert run_in(wt, monkeypatch, capsys, "work", "submit", slug)[0] == 0
    assert FsWorkStore.open(root).get(slug).status == "active"   # the stale copy
    assert FsWorkStore.open(wt).get(slug).status == "review"     # the branch copy

    code, _out, err = run_in(root, monkeypatch, capsys, "work", "complete", slug,
                             "--resolution", "done", "--confirm")
    assert code == 0 and WARNING not in err
    assert FsWorkStore.open(root).get(slug).status == "completed"


def test_warning_still_fires_when_nothing_submitted_the_item(
        tmp_path, monkeypatch, capsys):
    """Criterion 2. A non-discriminating regression guard: both copies read
    `active` here, so no single-copy mutation changes the result. What it guards
    is the warning being dropped or inverted altogether."""
    root = repo(tmp_path)
    slug = new_item(root, monkeypatch, capsys)
    wt = start_worktree(root, slug, monkeypatch, capsys)
    branch_commit(wt)

    code, _out, err = run_in(root, monkeypatch, capsys, "work", "complete", slug,
                             "--resolution", "done", "--confirm")
    assert code == 0 and WARNING in err


def test_warning_fires_when_the_branch_reworked_the_item_back(
        tmp_path, monkeypatch, capsys):
    """Criterion 3. Submitted then sent back on the branch: the latest branch
    status is `active` again, so the warning is true. Also a non-discriminating
    guard — both copies read `active` by the end."""
    root = repo(tmp_path)
    slug = new_item(root, monkeypatch, capsys)
    wt = start_worktree(root, slug, monkeypatch, capsys)
    branch_commit(wt)
    assert run_in(wt, monkeypatch, capsys, "work", "submit", slug)[0] == 0
    assert run_in(wt, monkeypatch, capsys, "work", "rework", slug)[0] == 0
    assert FsWorkStore.open(wt).get(slug).status == "active"

    code, _out, err = run_in(root, monkeypatch, capsys, "work", "complete", slug,
                             "--resolution", "done", "--confirm")
    assert code == 0 and WARNING in err


def test_no_false_warning_when_submit_ran_in_the_primary_checkout(
        tmp_path, monkeypatch, capsys):
    """Criterion 16. The mirror image: `submit` from the primary checkout while
    the code work sits on the branch leaves the PRIMARY at `review` and the
    branch copy at `active`. Judging the warning from the branch copy alone would
    reproduce this very bug in the other direction."""
    root = repo(tmp_path)
    slug = new_item(root, monkeypatch, capsys)
    wt = start_worktree(root, slug, monkeypatch, capsys)
    branch_commit(wt)
    assert run_in(root, monkeypatch, capsys, "work", "submit", slug)[0] == 0
    assert FsWorkStore.open(root).get(slug).status == "review"
    assert FsWorkStore.open(wt).get(slug).status == "active"

    code, _out, err = run_in(root, monkeypatch, capsys, "work", "complete", slug,
                             "--resolution", "done", "--confirm")
    assert code == 0 and WARNING not in err


# ── blockers ─────────────────────────────────────────────────────────────────


def test_a_blocker_the_branch_removed_no_longer_refuses(
        tmp_path, monkeypatch, capsys):
    """Criterion 4. The work resolved its own blocker on the branch; the primary
    checkout's copy still lists it."""
    root = repo(tmp_path)
    blocker = new_item(root, monkeypatch, capsys, "Blocker")
    slug = new_item(root, monkeypatch, capsys, "Blocked")
    FsWorkStore.open(root).add_blocker(slug, blocker)
    commit_all(_top(root), "block it")
    # `--force`: the store refuses to start a blocked item at all.
    wt = start_worktree(root, slug, monkeypatch, capsys, force=True)
    FsWorkStore.open(wt).remove_blocker(slug, blocker)
    commit_all(_top(wt), "unblock on the branch")

    code, _out, err = run_in(root, monkeypatch, capsys, "work", "complete", slug,
                             "--resolution", "done", "--confirm")
    assert code == 0, err
    assert FsWorkStore.open(root).get(slug).status == "completed"


def test_a_blocker_the_branch_added_refuses_before_the_merge(
        tmp_path, monkeypatch, capsys):
    """Criterion 5. Added on the branch, so the primary copy cannot see it — and
    the refusal has to land before anything is merged."""
    root = repo(tmp_path)
    blocker = new_item(root, monkeypatch, capsys, "Blocker")
    slug = new_item(root, monkeypatch, capsys, "Blocked")
    wt = start_worktree(root, slug, monkeypatch, capsys)
    FsWorkStore.open(wt).add_blocker(slug, blocker)
    commit_all(_top(wt), "block on the branch")
    tip = head(_top(wt))

    code, _out, err = run_in(root, monkeypatch, capsys, "work", "complete", slug,
                             "--resolution", "done", "--confirm")
    assert code == 1 and "blocked by" in err
    refused_before_merge(root, wt, slug, tip)


# ── reading the branch copy at all ───────────────────────────────────────────


def test_a_nested_node_reads_its_own_copy_inside_the_worktree(
        tmp_path, monkeypatch, capsys):
    """Criterion 9. `git worktree add` checks out the whole repository, so a node
    at `apps/server` has its copy at `<worktree top>/apps/server`, not at the
    worktree top."""
    root = repo(tmp_path, sub="apps/server")
    slug = new_item(root, monkeypatch, capsys)
    wt = start_worktree(root, slug, monkeypatch, capsys)
    assert wt != root / ".worktrees" / slug            # the nesting is real
    branch_commit(wt)
    assert run_in(wt, monkeypatch, capsys, "work", "submit", slug)[0] == 0

    code, _out, err = run_in(root, monkeypatch, capsys, "work", "complete", slug,
                             "--resolution", "done", "--confirm")
    assert code == 0 and WARNING not in err and "could not read" not in err


def test_a_missing_worktree_falls_back_to_the_primary_copy(
        tmp_path, monkeypatch, capsys):
    """Criterion 13. The worktree was removed by hand; the branch survives. That
    is a recovery path, so `complete` says which copy it judged and carries on."""
    root = repo(tmp_path)
    slug = new_item(root, monkeypatch, capsys)
    wt = start_worktree(root, slug, monkeypatch, capsys)
    branch_commit(wt)
    _git(root, "worktree", "remove", "--force", str(root / ".worktrees" / slug))

    code, _out, err = run_in(root, monkeypatch, capsys, "work", "complete", slug,
                             "--resolution", "done", "--confirm")
    assert code == 0
    assert "could not read" in err
    assert "judging it from the primary checkout's copy" in err
    assert FsWorkStore.open(root).get(slug).status == "completed"
