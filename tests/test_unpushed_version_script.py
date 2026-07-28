"""The documentation-sync `unpushed-version.sh` gate.

The script decides whether work may be folded into an already-cut version, so a
wrong answer either loses a release's notes or rewrites a tag other people have
fetched. Exercised over real tmp_path git repos with a local bare remote — no
network.
"""
import subprocess
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "skills" / "documentation-sync" / "scripts" / "unpushed-version.sh"
)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def commit(repo: Path, message: str) -> None:
    (repo / "f.txt").write_text(message, encoding="utf-8")
    git(repo, "add", "f.txt")
    git(repo, "commit", "-q", "-m", message)


def run(repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run([str(SCRIPT)], cwd=repo, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    git(r, "config", "user.email", "t@example.com")
    git(r, "config", "user.name", "T")
    commit(r, "A")
    return r


def test_script_is_executable():
    assert SCRIPT.is_file() and SCRIPT.stat().st_mode & 0o111, f"{SCRIPT} not executable"


def test_no_tag_is_not_foldable(repo: Path):
    result = run(repo)
    assert result.returncode == 1
    assert "STATUS: NOT-FOLDABLE" in result.stdout
    assert "nothing has been cut yet" in result.stdout


def test_tag_at_head_has_nothing_to_fold(repo: Path):
    git(repo, "tag", "v1.0.0")
    result = run(repo)
    assert result.returncode == 1
    assert "nothing since it to fold" in result.stdout


def test_unpushed_tag_with_later_commits_is_foldable(repo: Path):
    git(repo, "tag", "v1.0.0")
    commit(repo, "B")
    result = run(repo)
    assert result.returncode == 0, result.stdout
    assert "STATUS: FOLDABLE" in result.stdout
    assert "v1.0.0" in result.stdout
    assert "1 commit(s) after it" in result.stdout


def test_published_tag_is_not_foldable(tmp_path: Path, repo: Path):
    """A tag present on the remote must never be offered for folding."""
    bare = tmp_path / "origin.git"
    git(repo, "init", "-q", "--bare", str(bare))
    git(repo, "remote", "add", "origin", str(bare))
    git(repo, "tag", "v1.0.0")
    git(repo, "push", "-q", "origin", "main", "--tags")
    commit(repo, "B")

    result = run(repo)
    assert result.returncode == 1, result.stdout
    assert "is published" in result.stdout
    assert "cut a new version instead" in result.stdout


def test_unpushed_tag_whose_commit_rode_out_on_a_branch_is_not_foldable(
    tmp_path: Path, repo: Path
):
    """The tag is local-only, but its commit is already on the remote branch —
    the release content is public even though the label is not."""
    bare = tmp_path / "origin.git"
    git(repo, "init", "-q", "--bare", str(bare))
    git(repo, "remote", "add", "origin", str(bare))
    git(repo, "tag", "v1.0.0")
    git(repo, "push", "-q", "origin", "main")  # branch only, no --tags
    commit(repo, "B")

    result = run(repo)
    assert result.returncode == 1, result.stdout
    assert "commit already on a remote branch" in result.stdout


def test_tag_pushed_to_a_non_default_remote_is_not_foldable(
    tmp_path: Path, repo: Path
):
    """Regression: checking only the upstream/origin remote reported FOLDABLE for
    a tag that had been pushed to a second remote — the exact unsafe case."""
    for name in ("origin", "other"):
        git(repo, "init", "-q", "--bare", str(tmp_path / f"{name}.git"))
        git(repo, "remote", "add", name, str(tmp_path / f"{name}.git"))
    git(repo, "tag", "v1.0.0")
    git(repo, "push", "-q", "other", "refs/tags/v1.0.0")  # tag only, non-default remote
    commit(repo, "B")

    result = run(repo)
    assert result.returncode == 1, result.stdout
    assert "tag present on 'other'" in result.stdout


def test_unreachable_remote_reports_unknown(repo: Path, tmp_path: Path):
    """Offline or unreachable remote must not be read as 'unpublished'."""
    git(repo, "remote", "add", "origin", str(tmp_path / "does-not-exist.git"))
    git(repo, "tag", "v1.0.0")
    commit(repo, "B")

    result = run(repo)
    assert result.returncode == 2, result.stdout
    assert "STATUS: UNKNOWN" in result.stdout
    assert "ask the user" in result.stdout


def test_a_published_tag_beats_an_unreachable_remote(tmp_path: Path, repo: Path):
    """One dead remote must not mask a definitive answer from a live one: a tag
    found anywhere is NOT-FOLDABLE (1), not UNKNOWN (2)."""
    git(repo, "remote", "add", "dead", str(tmp_path / "does-not-exist.git"))
    git(repo, "init", "-q", "--bare", str(tmp_path / "live.git"))
    git(repo, "remote", "add", "live", str(tmp_path / "live.git"))
    git(repo, "tag", "v1.0.0")
    git(repo, "push", "-q", "live", "refs/tags/v1.0.0")
    commit(repo, "B")

    result = run(repo)
    assert result.returncode == 1, result.stdout
    assert "tag present on 'live'" in result.stdout


def test_tag_on_another_branch_is_invisible(repo: Path):
    """`git describe` only sees tags reachable from HEAD; a tag on a side branch
    is not 'the last version cut' for this line of work."""
    git(repo, "checkout", "-q", "-b", "side")
    commit(repo, "side work")
    git(repo, "tag", "v1.0.0")
    git(repo, "checkout", "-q", "main")
    commit(repo, "B")

    result = run(repo)
    assert result.returncode == 1, result.stdout
    assert "nothing has been cut yet" in result.stdout


def test_tag_glob_argument_is_honored(repo: Path):
    """Projects that don't prefix tags with `v` pass their own glob."""
    git(repo, "tag", "release-1.0.0")
    commit(repo, "B")

    assert run(repo).returncode == 1  # default 'v*' glob finds nothing

    result = subprocess.run(
        [str(SCRIPT), "release-*"], cwd=repo, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout
    assert "release-1.0.0 is unpublished" in result.stdout
