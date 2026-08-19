"""Transition auto-commit: the plumbing, the policy keys, and the scoping.

Auto-commit is the largest behavior change in the lifecycle epic — it alters what
every `tcw work` command does to the repository, including from `tcw serve`. The
tests that matter most here are the ones that prove what it does *not* do: sweep
in unrelated edits, or report success when the repository refused the write.
"""
import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.store.fs import (
    FsWorkStore, git_commit_result, git_current_branch, init,
)


def node(tmp_path: Path, name: str = "repo") -> Path:
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["work"], root, name.lower())
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "init"], check=True)
    return root


def log_count(root: Path) -> int:
    r = subprocess.run(["git", "-C", str(root), "rev-list", "--count", "HEAD"],
                       capture_output=True, text=True, check=True)
    return int(r.stdout.strip())


def porcelain(root: Path) -> str:
    return subprocess.run(["git", "-C", str(root), "status", "--porcelain"],
                          capture_output=True, text=True, check=True).stdout


def set_config(root: Path, **work_keys) -> None:
    cfg_path = root / "tcw-config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text()) or {}
    cfg.setdefault("work", {}).update(work_keys)
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))


# ── git_commit_result: three outcomes, never collapsed ───────────────────────

def test_commit_result_returns_none_outside_a_repository(tmp_path):
    """A `tmp_path` store or a node whose repo was removed. Committing was never
    possible, so it is not a failure."""
    plain = tmp_path / "not-a-repo"
    plain.mkdir()
    (plain / "f.txt").write_text("x")
    assert git_commit_result(plain, "msg", "f.txt") is None


def test_commit_result_returns_none_when_the_pathspec_is_clean(tmp_path):
    root = node(tmp_path)
    assert git_commit_result(root, "msg", "docs/work") is None
    assert log_count(root) == 1                        # no empty commit


def test_commit_result_returns_none_when_the_path_is_unknown_to_git(tmp_path):
    """The already-committed-move case. `git commit` reports this as
    'pathspec ... did not match', a *different* sentence from 'nothing to
    commit' — which is exactly why the check is porcelain, not stderr matching."""
    root = node(tmp_path)
    assert git_commit_result(root, "msg", "docs/work/backlog/gone") is None
    assert log_count(root) == 1


def test_commit_result_commits_and_returns_none_on_success(tmp_path):
    root = node(tmp_path)
    new = root / "docs/work/backlog/new.txt"
    new.write_text("x")
    subprocess.run(["git", "-C", str(root), "add", "--", str(new)], check=True)
    assert git_commit_result(root, "msg", "docs/work") is None
    assert log_count(root) == 2
    assert porcelain(root) == ""


def test_commit_result_ignores_a_pathspec_holding_only_untracked_files(tmp_path):
    """A scoped `git commit -- <paths>` commits tracked content only, so this has
    nothing to commit. Porcelain reports `??` lines, which would mislead the
    precheck into calling `git commit` — which fails benignly and would then be
    reported as a real error. Callers wanting untracked content committed stage
    it first, as `git_mv` does."""
    root = node(tmp_path)
    (root / "docs/work/backlog/untracked.txt").write_text("x")
    assert git_commit_result(root, "msg", "docs/work") is None
    assert log_count(root) == 1
    assert "docs/work/backlog/untracked.txt" in porcelain(root)


def test_commit_result_reports_a_real_failure(tmp_path):
    """A held `index.lock` stands in for every genuine refusal — permissions, a
    failing pre-commit hook, a corrupt repo. This must NOT be swallowed
    alongside the two benign cases: reporting success when the repository
    refused the write is the one outcome worse than failing."""
    root = node(tmp_path)
    new = root / "docs/work/backlog/new.txt"
    new.write_text("x")
    subprocess.run(["git", "-C", str(root), "add", "--", str(new)], check=True)
    (root / ".git" / "index.lock").write_text("")      # simulate a concurrent git
    try:
        err = git_commit_result(root, "msg", "docs/work")
    finally:
        (root / ".git" / "index.lock").unlink()
    assert err is not None and err != ""
    assert log_count(root) == 1                        # and it really did not commit


def test_commit_result_scopes_to_its_pathspec(tmp_path):
    """The property the whole design rests on: an unrelated dirty file is left
    dirty. `git commit -- <paths>` takes working-tree state, so a broad pathspec
    would quietly sweep it in."""
    root = node(tmp_path)
    mine = root / "docs/work/backlog/mine.txt"
    unrelated = root / "unrelated.txt"
    for f in (mine, unrelated):
        f.write_text("tracked")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "add both"], check=True)
    mine.write_text("changed")
    unrelated.write_text("dirty")

    assert git_commit_result(root, "msg", "docs/work") is None
    assert "unrelated.txt" in porcelain(root)          # left dirty
    assert "mine.txt" not in porcelain(root)           # committed


# ── git_current_branch ───────────────────────────────────────────────────────

def test_current_branch_reads_head(tmp_path):
    assert git_current_branch(node(tmp_path)) == "main"


def test_current_branch_is_none_outside_a_repository(tmp_path):
    plain = tmp_path / "not-a-repo"
    plain.mkdir()
    assert git_current_branch(plain) is None


def test_current_branch_is_none_on_a_detached_head(tmp_path):
    root = node(tmp_path)
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
    subprocess.run(["git", "-C", str(root), "checkout", "-q", head], check=True)
    assert git_current_branch(root) is None


# ── the policy keys ──────────────────────────────────────────────────────────

def test_auto_commit_defaults_to_true(tmp_path):
    assert FsWorkStore.open(node(tmp_path)).auto_commit_transitions() is True


def test_auto_commit_reads_an_explicit_false(tmp_path):
    root = node(tmp_path)
    set_config(root, **{"auto-commit-transitions": False})
    assert FsWorkStore.open(root).auto_commit_transitions() is False


def test_a_non_boolean_auto_commit_reads_as_the_default(tmp_path):
    """A typo silently disabling the commit is worse than a typo being ignored:
    nothing would look wrong until someone found the repo full of uncommitted
    moves."""
    root = node(tmp_path)
    set_config(root, **{"auto-commit-transitions": "no"})
    assert FsWorkStore.open(root).auto_commit_transitions() is True


def test_policy_keys_tolerate_a_work_section_that_is_not_a_mapping(tmp_path):
    root = node(tmp_path)
    cfg_path = root / "tcw-config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text()) or {}
    cfg["work"] = ["hand-edited", "to", "a", "list"]
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))
    st = FsWorkStore.open(root)
    assert st.auto_commit_transitions() is True
    assert st.trunk_branch() is None


def test_trunk_branch_is_none_unless_set(tmp_path):
    assert FsWorkStore.open(node(tmp_path)).trunk_branch() is None


def test_trunk_branch_reads_and_strips(tmp_path):
    root = node(tmp_path)
    set_config(root, **{"trunk-branch": "  main  "})
    assert FsWorkStore.open(root).trunk_branch() == "main"


def test_a_blank_trunk_branch_reads_as_unset(tmp_path):
    root = node(tmp_path)
    set_config(root, **{"trunk-branch": "   "})
    assert FsWorkStore.open(root).trunk_branch() is None


def test_policy_keys_do_not_disturb_the_tag_registry(tmp_path):
    """Both live under `work:`; adding one must not read as replacing the other."""
    root = node(tmp_path)
    st = FsWorkStore.open(root)
    st.register_tags(["bug", "cli"])
    set_config(root, **{"auto-commit-transitions": False, "trunk-branch": "main"})
    st = FsWorkStore.open(root)
    assert st.registered_tags() == ["bug", "cli"]
    assert st.auto_commit_transitions() is False
    assert st.trunk_branch() == "main"


# ── the behavior: every transition commits its own move ──────────────────────

def committed(root: Path) -> FsWorkStore:
    """A store on a node whose scaffolding is already committed."""
    return FsWorkStore.open(root)


def make_item(root: Path, title: str = "Task") -> str:
    """Create an item and commit it, so transitions start from a clean tree."""
    st = FsWorkStore.open(root)
    item = st.create(title, created="2026-01-01")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", f"add {item.slug}"],
                   check=True)
    return item.slug


@pytest.mark.parametrize("drive,expected", [
    (lambda st, s: st.start(s), "active"),
    (lambda st, s: (st.start(s), st.submit(s))[-1], "review"),
    (lambda st, s: (st.start(s), st.submit(s), st.rework(s))[-1], "active"),
    (lambda st, s: (st.start(s), st.complete(s, "done", []))[-1], "completed"),
    (lambda st, s: (st.start(s), st.complete(s, "wontfix", []))[-1], "discarded"),
])
def test_every_transition_commits_its_own_move(tmp_path, drive, expected):
    root = node(tmp_path)
    slug = make_item(root)
    before = log_count(root)
    st = committed(root)

    assert drive(st, slug).status == expected
    assert log_count(root) > before
    assert porcelain(root) == ""                       # nothing left staged or dirty


def test_a_transition_commit_names_the_item_and_its_destination(tmp_path):
    root = node(tmp_path)
    slug = make_item(root)
    committed(root).start(slug)
    msg = subprocess.run(["git", "-C", str(root), "log", "-1", "--pretty=%s"],
                         capture_output=True, text=True, check=True).stdout.strip()
    assert slug in msg and "active" in msg


def test_a_transition_commit_does_not_sweep_in_an_unrelated_item(tmp_path):
    """The property the scoping exists for, and the one test that fails if the
    pathspec is widened back to `docs/work`. Every other test in this file passes
    with a broad pathspec."""
    root = node(tmp_path)
    mine = make_item(root, "Mine")
    other = make_item(root, "Other")
    st = committed(root)

    other_doc = st.path(other) / "spec.md"
    other_doc.write_text("# Uncommitted work in progress\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "--", str(other_doc)], check=True)

    st.start(mine)

    dirty = porcelain(root)
    assert "spec.md" in dirty                          # still staged, not swept in
    assert mine in subprocess.run(
        ["git", "-C", str(root), "log", "-1", "--pretty=%s"],
        capture_output=True, text=True, check=True).stdout


def test_auto_commit_off_leaves_the_move_staged(tmp_path):
    """The escape hatch reproduces today's behavior exactly."""
    root = node(tmp_path)
    slug = make_item(root)
    set_config(root, **{"auto-commit-transitions": False})
    before = log_count(root)

    assert FsWorkStore.open(root).start(slug).status == "active"
    assert log_count(root) == before
    assert porcelain(root) != ""                       # staged, awaiting the caller


def test_a_second_transition_attempt_creates_no_empty_commit(tmp_path):
    """The already-committed case: the source folder is gone and git does not
    know it, which `git commit` reports as a pathspec error rather than as
    'nothing to commit'. Neither is a failure."""
    root = node(tmp_path)
    slug = make_item(root)
    st = committed(root)
    st.start(slug)
    after_first = log_count(root)

    src = root / "docs/work/backlog" / slug
    dst = root / "docs/work/active" / slug
    from tcw.store.fs import git_commit_result
    assert git_commit_result(root, "again", str(src.relative_to(root)),
                             str(dst.relative_to(root))) is None
    assert log_count(root) == after_first


def test_a_write_outside_a_repository_is_refused_before_it_writes(tmp_path):
    """This test used to pin the opposite, and the reversal is deliberate.

    It read: "worth pinning so nobody 'fixes' it" — a non-git node died at item
    *creation* with a raw `CalledProcessError` out of `git_stage`, after the
    item folder and its `state.yaml` had already landed. That traceback, and the
    half-item it left behind, is what
    `2026-07-30-fix-non-git-write-paths-work-new-and-init-fail-outside-a-git-repository`
    was filed to fix. The git-required contract is unchanged; only the shape of
    the refusal is.

    What still holds from the original: the not-a-repo branch in
    `git_commit_result` is defensive depth for a store handed a path whose repo
    vanished mid-run, not support for a non-git node, and it is tested directly
    at the function level above. `tcw init` refuses outside a repo for exactly
    this reason, and now says so in the same words."""
    root = tmp_path / "plain"
    root.mkdir()
    init(["work"], root, "plain")
    st = FsWorkStore.open(root)
    with pytest.raises(ValueError, match="not inside a git repository"):
        st.create("Task", created="2026-01-01")
    assert not any((root / "docs" / "work" / "backlog").glob("2026-*"))


def test_a_refused_commit_reports_but_leaves_the_item_moved(tmp_path):
    """The distinction TransitionCommitError exists for: the move succeeded and
    must not be retried; only the commit is missing."""
    from tcw.store.base import TransitionCommitError

    root = node(tmp_path)
    slug = make_item(root)
    st = committed(root)
    # A rejecting pre-commit hook, not a held `index.lock`: the lock blocks
    # `git mv` too, so the move would never happen and the case under test —
    # move succeeded, commit refused — could not arise.
    hook = root / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 1\n")
    hook.chmod(0o755)

    with pytest.raises(TransitionCommitError) as excinfo:
        st.start(slug)

    assert "moved to active" in str(excinfo.value)
    assert FsWorkStore.open(root).get(slug).status == "active"   # it really moved


# ── trunk-branch ─────────────────────────────────────────────────────────────

def test_no_trunk_warning_when_the_branch_matches(tmp_path, capsys):
    root = node(tmp_path)
    slug = make_item(root)
    set_config(root, **{"trunk-branch": "main"})
    capsys.readouterr()
    committed(root).start(slug)
    assert "trunk-branch" not in capsys.readouterr().err


def test_trunk_warning_on_a_mismatch_but_the_commit_still_lands(tmp_path, capsys):
    root = node(tmp_path)
    slug = make_item(root)
    set_config(root, **{"trunk-branch": "main"})
    subprocess.run(["git", "-C", str(root), "checkout", "-qb", "feature"], check=True)
    before = log_count(root)
    capsys.readouterr()

    committed(root).start(slug)

    err = capsys.readouterr().err
    assert "feature" in err and "main" in err
    assert log_count(root) == before + 1              # warned, committed anyway
    assert git_current_branch(root) == "feature"      # and never checked anything out


def test_no_trunk_warning_on_the_items_own_work_branch(tmp_path, capsys):
    """A `--worktree` item is supposed to be on `work/<slug>`; warning there
    would fire constantly on the one workflow behaving correctly."""
    root = node(tmp_path)
    slug = make_item(root)
    set_config(root, **{"trunk-branch": "main"})
    st = FsWorkStore.open(root)
    st.set_field(slug, "branch", f"work/{slug}")
    subprocess.run(["git", "-C", str(root), "checkout", "-qb", f"work/{slug}"], check=True)
    capsys.readouterr()

    FsWorkStore.open(root).start(slug)
    assert "trunk-branch" not in capsys.readouterr().err


def test_no_trunk_warning_when_unset(tmp_path, capsys):
    root = node(tmp_path)
    slug = make_item(root)
    subprocess.run(["git", "-C", str(root), "checkout", "-qb", "anything"], check=True)
    capsys.readouterr()
    committed(root).start(slug)
    assert "trunk-branch" not in capsys.readouterr().err


# ── --worktree, which must commit regardless of the setting ──────────────────

def branch_has_item(root: Path, branch: str, slug: str) -> bool:
    """Whether the item's folder exists under `active/` on `branch`."""
    r = subprocess.run(
        ["git", "-C", str(root), "ls-tree", "-r", "--name-only", branch,
         f"docs/work/active/{slug}/"],
        capture_output=True, text=True, check=True)
    return bool(r.stdout.strip())


def test_worktree_start_puts_the_status_move_on_the_branch(tmp_path, monkeypatch, capsys):
    """The ordering the worktree flow depends on: the branch is created from
    HEAD, so the move must be committed before `add_worktree` runs."""
    from tcw.cli import main
    root = node(tmp_path)
    slug = make_item(root)
    monkeypatch.chdir(root)

    assert main(["work", "start", slug, "--worktree"]) == 0
    capsys.readouterr()

    assert FsWorkStore.open(root).get(slug).status == "active"
    assert branch_has_item(root, f"work/{slug}", slug)
    assert porcelain(root) == ""                       # nothing left behind


def test_worktree_start_commits_even_with_auto_commit_off(tmp_path, monkeypatch, capsys):
    """The documented exception. With the setting off and no commit here, the
    branch would be created without the item's own status move on it —
    a worktree whose item is not in it."""
    from tcw.cli import main
    root = node(tmp_path)
    slug = make_item(root)
    set_config(root, **{"auto-commit-transitions": False})
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "config"], check=True)
    monkeypatch.chdir(root)

    assert main(["work", "start", slug, "--worktree"]) == 0
    capsys.readouterr()

    assert branch_has_item(root, f"work/{slug}", slug)
    assert porcelain(root) == ""


def test_worktree_start_is_one_commit_and_excludes_another_staged_item(
        tmp_path, monkeypatch, capsys):
    """The default in-repository layout keeps its single worktree commit — and
    that commit is still scoped to the started item, not to the whole store."""
    from tcw.cli import main
    root = node(tmp_path)
    slug = make_item(root)
    other = FsWorkStore.open(root).create("Other", created="2026-01-02").slug
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    before = log_count(root)
    monkeypatch.chdir(root)

    assert main(["work", "start", slug, "--worktree"]) == 0
    capsys.readouterr()

    assert log_count(root) == before + 2               # store move + worktree setup
    files = subprocess.run(["git", "-C", str(root), "show", "--name-only", "--format="],
                           capture_output=True, text=True, check=True).stdout
    assert ".gitignore" in files                       # same commit, not a second one
    assert f"docs/work/active/{slug}/state.yaml" in files
    assert other not in files
    assert other in porcelain(root)                    # still staged, uncommitted


def test_worktree_start_creates_no_empty_commit(tmp_path, monkeypatch, capsys):
    """The store commits the move and `_start` commits `.gitignore` plus the
    worktree fields. Two commits, and neither is empty."""
    from tcw.cli import main
    root = node(tmp_path)
    slug = make_item(root)
    before = log_count(root)
    monkeypatch.chdir(root)

    assert main(["work", "start", slug, "--worktree"]) == 0
    capsys.readouterr()

    assert log_count(root) == before + 2
    for i in range(2):                                 # neither commit is empty
        stat = subprocess.run(
            ["git", "-C", str(root), "show", "--stat", "--pretty=format:", f"HEAD~{i}"],
            capture_output=True, text=True, check=True)
        assert stat.stdout.strip()


# ── the web API goes through the same choke point ────────────────────────────

def test_a_transition_through_the_store_used_by_serve_commits(tmp_path):
    """`tcw serve` calls `work.start(...)` on the same FsWorkStore the CLI uses,
    and auto-commit lives in `_effect_transition` rather than in the CLI
    precisely so this path is covered. A CLI-only implementation would leave a
    web transition staged but uncommitted."""
    root = node(tmp_path)
    slug = make_item(root)
    before = log_count(root)

    FsWorkStore.open(root).start(slug)                 # exactly what serve does

    assert log_count(root) == before + 1
    assert porcelain(root) == ""


# ── --already-integrated ─────────────────────────────────────────────────────

def test_already_integrated_skips_the_merge_but_keeps_the_gates(
        tmp_path, monkeypatch, capsys):
    """For a branch merged outside TCW — typically a merged PR. It skips the
    merge-back and nothing else."""
    from tcw.cli import main
    root = node(tmp_path)
    slug = make_item(root)
    monkeypatch.chdir(root)
    assert main(["work", "start", slug, "--worktree"]) == 0
    capsys.readouterr()

    # Stand in for an external merge: the branch exists but was never merged, so
    # TCW's own merge-back would have pulled it in. --already-integrated must not.
    wt = root / ".worktrees" / slug                    # the item's own worktree
    (wt / "only-on-the-branch.txt").write_text("x")
    subprocess.run(["git", "-C", str(wt), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(wt), "commit", "-qm", "branch work"], check=True)

    assert main(["work", "complete", slug, "--resolution", "done", "--confirm",
                 "--already-integrated"]) == 0
    capsys.readouterr()

    assert FsWorkStore.open(root).get(slug).status == "completed"
    assert not (root / "only-on-the-branch.txt").exists()   # the merge was skipped


def test_already_integrated_still_refuses_on_an_unreconciled_capability(
        tmp_path, monkeypatch, capsys):
    """"Skips the merge and nothing else" has to be true of the gate that
    actually blocks completions."""
    from tcw.cli import main
    root = node(tmp_path)
    init(["capabilities"], root, "repo")               # the gate no-ops without one
    slug = make_item(root)
    monkeypatch.chdir(root)
    assert main(["work", "start", slug, "--worktree"]) == 0
    capsys.readouterr()

    st = FsWorkStore.open(root)
    (st.path(slug) / "capabilities.yaml").write_text(
        "new:\n  - work/never-built\n", encoding="utf-8")

    assert main(["work", "complete", slug, "--resolution", "done", "--confirm",
                 "--already-integrated"]) == 1
    assert "not reconciled" in capsys.readouterr().err
    assert FsWorkStore.open(root).get(slug).status == "active"


def test_already_integrated_tolerates_a_worktree_removed_externally(
        tmp_path, monkeypatch, capsys):
    """An external flow that merged the PR may well have cleaned up after
    itself. Teardown is best-effort and must stay that way."""
    from tcw.cli import main
    root = node(tmp_path)
    slug = make_item(root)
    monkeypatch.chdir(root)
    assert main(["work", "start", slug, "--worktree"]) == 0
    capsys.readouterr()

    subprocess.run(["git", "-C", str(root), "worktree", "remove", "--force",
                    str(root / ".worktrees" / slug)], check=True)
    subprocess.run(["git", "-C", str(root), "branch", "-D", f"work/{slug}"],
                   capture_output=True, check=True)

    assert main(["work", "complete", slug, "--resolution", "done", "--confirm",
                 "--already-integrated"]) == 0
    capsys.readouterr()
    assert FsWorkStore.open(root).get(slug).status == "completed"


def test_already_integrated_is_rejected_without_a_worktree(tmp_path, monkeypatch, capsys):
    """Accepting it silently would teach the wrong model: the flag skips a
    merge-back only a TCW-created worktree ever performs."""
    from tcw.cli import main
    root = node(tmp_path)
    slug = make_item(root)
    monkeypatch.chdir(root)
    assert main(["work", "start", slug]) == 0
    capsys.readouterr()

    assert main(["work", "complete", slug, "--resolution", "done", "--confirm",
                 "--already-integrated"]) == 1
    assert "--already-integrated" in capsys.readouterr().err
    assert FsWorkStore.open(root).get(slug).status == "active"


# ── a gitignored destination status folder ───────────────────────────────────

def test_a_transition_into_an_ignored_destination_untracks_instead_of_moving(tmp_path):
    """A node that gitignores `completed/` wants resolved work out of the tracked
    tree. `git mv` does not honor `.gitignore` for its destination, so a plain
    ignore would look like it worked while every completion re-added the item.
    """
    root = node(tmp_path)
    # What a node actually does when it adopts the ignore: write it, then drop
    # what git already tracks there (`init`'s `.gitkeep`).
    (root / ".gitignore").write_text("docs/work/completed/\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "rm", "-rq", "--cached",
                    "--", "docs/work/completed"], check=True)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "ignore completed"],
                   check=True)
    slug = make_item(root)
    before = log_count(root)
    st = committed(root)

    st.start(slug)
    assert st.complete(slug, "done", []).status == "completed"

    assert (root / "docs" / "work" / "completed" / slug).is_dir()   # still on disk
    tracked = subprocess.run(
        ["git", "-C", str(root), "ls-files", "docs/work/completed"],
        capture_output=True, text=True, check=True).stdout
    assert tracked == ""                               # but out of the index
    assert porcelain(root) == ""                       # and nothing left dirty
    assert log_count(root) == before + 2               # start + complete committed
