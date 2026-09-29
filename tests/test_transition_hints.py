"""What `tcw work` prints after it creates or moves an item: the next step, the
item's new location, and what `complete --confirm` acknowledged (spec:
2026-09-29-make-start-submit-rework-and-complete-print-the-true-next-step-the-
item-s-new-folder-and-what-confirm-acknowledged).

Each hint is read as an instruction by the agent that ran the command, so every
test asserts the misleading text it replaces is absent, not only that the new
text is present."""

import subprocess
from pathlib import Path

from tcw.store.fs import FsWorkStore, init


def _node(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    for cmd in (["init", "-q"], ["config", "user.email", "t@t"],
                ["config", "user.name", "t"]):
        subprocess.run(["git", "-C", str(root), *cmd], check=True)
    init(["work"], root, "repo")
    return root


def _tcw(root: Path, *args: str, stdin: str | None = None):
    return subprocess.run(["tcw", "work", *args], cwd=str(root), input=stdin,
                          capture_output=True, text=True)


def _next_lines(err: str) -> list[str]:
    return [line for line in err.splitlines() if line.startswith("→ next:")]


def _assert_next(out, command: str) -> None:
    """Exactly one next-step line, naming `command`, and never the hint that sent
    readers straight to `complete` or told them to delete a file."""
    lines = _next_lines(out.stderr)
    assert len(lines) == 1, out.stderr
    assert command in lines[0], lines[0]
    for stale in ("tcw work complete", "when done & verified",
                  "when you begin implementing", "delete"):
        assert stale not in lines[0], lines[0]


# ── criteria 1-3: after creating an item ─────────────────────────────────────

def test_new_points_at_the_request_stage(tmp_path):
    root = _node(tmp_path)
    out = _tcw(root, "new", "Thing", stdin="body\n")
    assert out.returncode == 0, out.stderr
    slug = out.stdout.strip()
    _assert_next(out, f"tcw work stage gate request {slug}")
    assert "tcw work start" not in out.stderr, out.stderr


def test_inbox_accept_points_at_the_request_stage(tmp_path):
    root = _node(tmp_path)
    inbox = Path(_tcw(root, "inbox", "path").stdout.strip())
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "2026-01-01-some-request.md").write_text("# Some request\n\nbody\n")
    out = _tcw(root, "inbox", "accept", "2026-01-01-some-request")
    assert out.returncode == 0, out.stderr
    slug = out.stdout.strip()
    _assert_next(out, f"tcw work stage gate request {slug}")


def test_an_epic_points_at_the_request_stage_too(tmp_path):
    root = _node(tmp_path)
    out = _tcw(root, "new", "Big thing", "--epic")
    assert out.returncode == 0, out.stderr
    slug = out.stdout.strip()
    _assert_next(out, f"tcw work stage gate request {slug}")
