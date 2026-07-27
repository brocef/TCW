"""Transition auto-commit: the plumbing, the policy keys, and the scoping.

Auto-commit is the largest behavior change in the lifecycle epic — it alters what
every `tcw work` command does to the repository, including from `tcw serve`. The
tests that matter most here are the ones that prove what it does *not* do: sweep
in unrelated edits, or report success when the repository refused the write.
"""
import subprocess
from pathlib import Path

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
