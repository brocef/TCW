"""Writes outside a git repository refuse before touching the filesystem.

TCW's contract is that **reads** work anywhere and **writes** need a repository.
The refusal used to be inconsistent: `tcw init` said so in one line, while every
store write died in `git_stage` with an unhandled `CalledProcessError` — after
creating the item, moving it, or rewriting the config it was about to stage.

The guard is a filesystem-adapter precondition (`require_repository`), not a
model concept: a remote store has no repository to require. It sits in two
places — the `_stage`/`_rm`/`_mv` funnel, so no git failure can escape as a
traceback, and the public write methods whose first mutation *precedes* their
staging call, so nothing lands before the refusal.
"""
import subprocess
from pathlib import Path

import pytest

from tcw.store.fs import (
    NOT_A_REPOSITORY, FsTaxonomyStore, FsTreeStore, FsWorkStore, init,
    require_repository,
)


def repo(tmp_path: Path, name: str = "repo") -> Path:
    """A committed TCW node inside a git repository."""
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    init(["taxonomy", "capabilities", "work"], root, name.lower())
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "init"], check=True)
    return root


# ── The precondition itself ──────────────────────────────────────────────────


def test_require_repository_accepts_a_repository(tmp_path):
    assert require_repository(repo(tmp_path)) is None


def test_require_repository_refuses_a_plain_directory(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(ValueError) as e:
        require_repository(plain)
    assert str(e.value) == NOT_A_REPOSITORY


def test_each_store_checks_the_repository_it_actually_writes_to(tmp_path):
    """A work store's repository can differ from its node's (`work.path`)."""
    root = repo(tmp_path)
    work = FsWorkStore.open(root)
    assert work._write_git_root() == work.store_git_root
    taxonomy = FsTaxonomyStore.open(root)
    assert taxonomy._write_git_root() == taxonomy.node_root


def test_the_guard_holds_no_state_because_it_could_not_be_initialized(tmp_path):
    """Why `_require_repository` re-probes instead of caching.

    `FsWorkStore.__init__` does not chain to `FsTreeStore.__init__` — it assigns
    `root`/`node_root`/`store_git_root`/`config` itself — so any attribute added
    to the base initializer is simply absent on every work store, and the first
    work write would raise `AttributeError`. If someone makes the guard stateful
    later, this is the test that has to be read first.
    """
    assert FsWorkStore.__init__ is not FsTreeStore.__init__
    root = repo(tmp_path)
    assert FsWorkStore.open(root)._require_repository() is None
