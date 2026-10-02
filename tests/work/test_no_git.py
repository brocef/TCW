"""A forced move with hooks leaves git exactly as it was (TCW-69 AC 19)."""

import subprocess

from tcw.work.advance import advance
from tcw.work.config import parse_work_config
from tcw.work.layout import Layout
from tcw.work.model import Changes
from tests.work.fake_reader import FakeReader
from tests.work.memory_backend import MemoryBackend


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True, text=True).stdout


def snapshot(root):
    return (git(root, "rev-parse", "HEAD"), git(root, "status", "--porcelain"),
            git(root, "for-each-ref"))


def test_a_forced_advance_with_hooks_changes_no_git_state(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "t@t")
    git(root, "config", "user.name", "t")
    (root / "README").write_text("x")
    git(root, "add", "README")
    git(root, "commit", "-qm", "seed")

    config, problems = parse_work_config({"stages": {"implement": {
        "pre": [{"command": "true"}, {"command": "false"}],
        "post": [{"command": "true"}]}}})
    assert problems == []
    backend = MemoryBackend(root / "work")
    item = backend.create("thing", Changes(), stage="request", request=None)
    backend.set_reported_stage(item.slug.folder, "spec")
    layout = Layout(root / "work", config.enabled, frozenset())

    before = snapshot(root)
    outcome = advance(backend, config, layout, FakeReader(), root, item.slug,
                      to="implement", force=True, reason="check git is untouched")
    assert outcome.stage == "implement" and len(outcome.overridden) == 1
    assert snapshot(root) == before
