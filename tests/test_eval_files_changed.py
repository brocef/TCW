"""`files_changed_exactly` measures what the agent changed, not what it committed.

It used to compare the last two commits, so an agent that edited the right file
without committing failed, and a run with no commit at all compared the seeder's
own last commit. It now compares the working tree, plus untracked files git does
not ignore, with the commit the seeder recorded as `seeded_head`.
"""

import json
import subprocess
from pathlib import Path

from evals import grade

EXPECTED = "src/reports.py"


def _git(root, *args) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def _seeded(tmp_path, last_seed_commit_touches: str) -> dict:
    """A seeded repository and the run entry the runner would record for it.

    The seeder's own last commit touches `last_seed_commit_touches`. It is an
    explicit argument because the old check read exactly that commit whenever
    the agent made none, so which file it touches decides whether a test could
    pass against the old check by accident.
    """
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.invalid")
    _git(tmp_path, "config", "user.name", "T")
    (tmp_path / "src").mkdir()
    (tmp_path / EXPECTED).write_text("before\n")
    (tmp_path / "README.md").write_text("demo\n")
    (tmp_path / ".gitignore").write_text("ignored.txt\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "seed")
    with (tmp_path / last_seed_commit_touches).open("a") as f:
        f.write("seeded\n")
    _git(tmp_path, "commit", "-q", "-am", "seed, last step")
    return {"fixture": tmp_path, "seeded_head": _git(tmp_path, "rev-parse", "HEAD")}


def _check(run) -> dict:
    return grade.p_files_changed_exactly(run, paths=[EXPECTED])


def test_an_uncommitted_edit_to_the_expected_file_passes(tmp_path):
    run = _seeded(tmp_path, "README.md")
    (tmp_path / EXPECTED).write_text("after\n")
    verdict = _check(run)
    assert verdict["passed"], verdict["evidence"]


def test_a_committed_edit_to_the_expected_file_passes(tmp_path):
    run = _seeded(tmp_path, "README.md")
    (tmp_path / EXPECTED).write_text("after\n")
    # An ignored file is not a change the agent made to the project.
    (tmp_path / "ignored.txt").write_text("noise\n")
    _git(tmp_path, "commit", "-q", "-am", "fix")
    # A second commit, so "the last commit" and "since the seed" differ.
    _git(tmp_path, "commit", "-q", "--allow-empty", "-m", "later")
    verdict = _check(run)
    assert verdict["passed"], verdict["evidence"]


def test_an_extra_untracked_file_fails(tmp_path):
    run = _seeded(tmp_path, "README.md")
    (tmp_path / EXPECTED).write_text("after\n")
    _git(tmp_path, "commit", "-q", "-am", "fix")
    (tmp_path / "stray.txt").write_text("not asked for\n")
    verdict = _check(run)
    assert not verdict["passed"]
    assert "stray.txt" in verdict["evidence"]


def test_an_unchanged_expected_file_fails(tmp_path):
    run = _seeded(tmp_path, EXPECTED)
    verdict = _check(run)
    assert not verdict["passed"]
    assert "changed []" in verdict["evidence"]


def test_a_run_without_seeded_head_fails_and_says_so(tmp_path):
    run = _seeded(tmp_path, "README.md")
    (tmp_path / EXPECTED).write_text("after\n")
    _git(tmp_path, "commit", "-q", "-am", "fix")
    del run["seeded_head"]
    verdict = _check(run)
    assert not verdict["passed"]
    assert "seeded_head" in verdict["evidence"]


def test_a_seeded_head_git_cannot_resolve_fails_with_git_s_error(tmp_path):
    """A git failure must not read as an empty change list, which would look
    like "the agent changed nothing" and pass a case expecting no changes."""
    run = _seeded(tmp_path, "README.md")
    run["seeded_head"] = "0" * 40
    verdict = grade.p_files_changed_exactly(run, paths=[])
    assert not verdict["passed"]
    assert "git" in verdict["evidence"]
    assert "changed []" not in verdict["evidence"]


def test_a_missing_fixture_folder_fails(tmp_path):
    run = {"fixture": tmp_path / "nowhere", "seeded_head": "0" * 40}
    verdict = grade.p_files_changed_exactly(run, paths=[])
    assert not verdict["passed"]
    assert "changed []" not in verdict["evidence"]


def test_a_rename_counts_the_same_however_the_agent_moved_the_file(tmp_path):
    """git reports a staged or committed rename as the new path only, and a
    plain `mv` as a deletion plus an untracked file. Both are the same edit."""
    run = _seeded(tmp_path, "README.md")
    _git(tmp_path, "mv", EXPECTED, "src/renamed.py")
    verdict = grade.p_files_changed_exactly(
        run, paths=[EXPECTED, "src/renamed.py"])
    assert verdict["passed"], verdict["evidence"]


def test_grading_a_run_directory_carries_seeded_head_to_the_check(tmp_path):
    """The runner writes `seeded_head` to timing.json, and `grade_run` must hand
    it to the predicate, or every graded run fails for want of it."""
    case = next(c for c in json.loads(
        Path(grade.__file__).with_name("evals.json").read_text())["cases"]
        if c["id"] == "B10")
    paths = next(a["args"]["paths"] for a in case["assertions"]
                 if a.get("predicate") == "files_changed_exactly")

    fixture = tmp_path / "fixture"
    fixture.mkdir()
    run = _seeded(fixture, "README.md")
    for rel in paths:
        target = fixture / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("edited by the agent\n")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "timing.json").write_text(json.dumps({
        "case": "B10", "axis": "B", "arm": "with-skill",
        "fixture": str(fixture), "seeded_head": run["seeded_head"]}))

    report = grade.grade_run(run_dir)
    verdict = next(r for r in report["assertions"]
                   if r.get("predicate") == "files_changed_exactly")
    assert verdict["passed"], verdict["evidence"]
