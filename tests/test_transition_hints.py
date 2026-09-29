"""What `tcw work` prints after it creates or moves an item: the next step, the
item's new location, and what `complete --confirm` acknowledged (spec:
2026-09-29-make-start-submit-rework-and-complete-print-the-true-next-step-the-
item-s-new-folder-and-what-confirm-acknowledged).

Each hint is read as an instruction by the agent that ran the command, so every
test asserts the misleading text it replaces is absent, not only that the new
text is present."""

import subprocess
from pathlib import Path

import pytest
import yaml

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


# ── criterion 4: after `start` ───────────────────────────────────────────────

def _item(root: Path, *artifacts: str) -> str:
    st = FsWorkStore.open(root)
    slug = st.create("Thing", created="2026-01-01").slug
    for name in artifacts:
        st.write_artifact(slug, name, f"# {name}\n")
    return slug


def _committed(root: Path) -> None:
    """`--worktree` branches from HEAD, so the item must be in a commit."""
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "seed"], check=True)


@pytest.mark.parametrize("worktree", [False, True])
@pytest.mark.parametrize("artifacts, stage", [
    ((), "spec"),
    (("spec",), "plan"),
    (("spec", "plan"), "implement"),
])
def test_start_points_at_the_first_unwritten_stage(tmp_path, artifacts, stage,
                                                   worktree):
    root = _node(tmp_path)
    slug = _item(root, *artifacts)
    if worktree:
        _committed(root)
    out = _tcw(root, "start", slug, *(["--worktree"] if worktree else []))
    assert out.returncode == 0, out.stderr
    _assert_next(out, f"tcw work stage gate {stage} {slug}")


@pytest.mark.parametrize("artifacts, stage", [
    (("spec", "plan", "outcome", "rework"), "implement"),
    (("spec", "plan", "outcome"), "verify"),
])
def test_starting_an_unheld_active_item_points_past_its_outcome(tmp_path,
                                                                artifacts, stage):
    """`start` takes an `active` item nobody holds — what `tracker release`
    leaves — and such an item can already hold an outcome."""
    root = _node(tmp_path)
    slug = _item(root, *artifacts)
    FsWorkStore.open(root).start(slug)            # active, with no owner
    assert FsWorkStore.open(root).get(slug).owner == ""
    out = _tcw(root, "start", slug)
    assert out.returncode == 0, out.stderr
    _assert_next(out, f"tcw work stage gate {stage} {slug}")


def test_start_advises_a_qualified_reference_as_typed(tmp_path):
    root = _node(tmp_path)
    child = root / "kid"
    child.mkdir()
    init(["work"], child, "kid")
    for path, links in ((root, {"children": {"kid": "kid"}}),
                        (child, {"parent": {"repo": ".."}})):
        cfg = yaml.safe_load((path / "tcw-config.yaml").read_text()) or {}
        cfg["connected-projects"] = links
        (path / "tcw-config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    slug = _item(child, "spec", "plan")
    out = _tcw(root, "start", f"kid/{slug}")
    assert out.returncode == 0, out.stderr
    _assert_next(out, f"tcw work stage gate implement kid/{slug}")


# ── criteria 5-6: after `submit` and `rework` ────────────────────────────────

def _submitted(root: Path) -> tuple[str, subprocess.CompletedProcess]:
    slug = _item(root, "spec", "plan", "outcome")
    assert _tcw(root, "start", slug).returncode == 0
    return slug, _tcw(root, "submit", slug)


def test_submit_names_the_new_folder_and_the_verify_stage(tmp_path):
    slug, out = _submitted(_node(tmp_path))
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == f"submitted {slug} → docs/work/review/{slug}"
    _assert_next(out, f"tcw work stage gate verify {slug}")
    line = _next_lines(out.stderr)[0]
    assert "refined-outcome.md" in line and "rework.md" in line, line


def test_rework_names_the_new_folder_and_the_implement_stage(tmp_path):
    root = _node(tmp_path)
    slug, _ = _submitted(root)
    FsWorkStore.open(root).write_artifact(slug, "rework", "# Rework\n")
    out = _tcw(root, "rework", slug)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == f"reworking {slug} → docs/work/active/{slug}"
    _assert_next(out, f"tcw work stage gate implement {slug}")
    assert "rework.md" in _next_lines(out.stderr)[0]
