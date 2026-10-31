"""A store path leaving a linked worktree, read as written in a checkout of
the repository the store declares, whatever form that checkout's remote URL
takes (TCW-118 evaluation).

A planning repository holds a child's work store; the child's store declares
the planning repository by its `https://github.com/...` URL, and linked
worktrees of both are made side by side. The planning checkout's remote may
be written through an SSH host alias, or rewritten by a `url.<base>.insteadOf`
rule, and still names the declared repository. Where the store path lands on a
checkout whose remotes do not name it, the store is read beside the main
checkout, and `tcw migrate` and `tcw validate` say so.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import yaml

from tests.migrate.test_migrate_config import make
from tests.objectcli import tcw  # noqa: F401  (a fixture)

DECLARED = "https://github.com/org/planning.git"
ITEM = "title: A\nstage: request\npriority: medium\n"
CHILD = ("id: child\nwork:\n  path: ../planning/sub/docs/work\n  repository:\n"
         f"    url: {DECLARED}\n    path: sub/docs/work\n")
NOTE = "is read beside the main checkout"


@pytest.fixture(autouse=True)
def _own_git_config(tmp_path, monkeypatch):
    """No user-wide git configuration but the test's own."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    (tmp_path / "home").mkdir()


def _git(*args) -> None:
    subprocess.run(["git", *map(str, args)], check=True, capture_output=True)


def _commit(root: Path) -> None:
    _git("-C", root, "add", "-A")
    _git("-C", root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x")


def _repositories(base: Path, remote: str | None) -> tuple[Path, Path]:
    """The planning repository, its remote `remote` (none when None), holding
    the child's 3.x work store, and the child, both committed."""
    planning = make(base / "planning", {"sub/docs/work/2026-01-01-first-item/item.yaml": ITEM})
    if remote is not None:
        _git("-C", planning, "remote", "add", "origin", remote)
    child = make(base / "child", {"tcw-config.yaml": CHILD})
    _commit(planning)
    _commit(child)
    return planning, child


def _side_by_side(base: Path, at: Path) -> tuple[Path, Path]:
    """Linked worktrees of both, made side by side in `at`."""
    for name in ("planning", "child"):
        _git("-C", base / name, "worktree", "add", "-q", "--detach", at / name)
    return (at / "planning").resolve(), (at / "child").resolve()


def _store(child: Path) -> Path:
    from tcw.store.fs import declared_url, store_location
    section = yaml.safe_load((child / "tcw-config.yaml").read_text())["work"]
    return Path(os.path.realpath(
        store_location(child, "work", section["path"], url=declared_url(section))))


def _insteadof(config: Path) -> None:
    config.parent.mkdir(parents=True, exist_ok=True)
    with config.open("a", encoding="utf-8") as out:
        out.write('[url "https://git.example.com/mirror/org/"]\n'
                  "\tinsteadOf = https://github.com/org/\n")


@pytest.mark.parametrize("remote", [
    "https://github.com/org/planning.git",
    "git@github.com:org/planning.git",
    "git@github-work:org/planning.git",       # an SSH host alias
    "git@github-work:Org/Planning",           # its owner and name in another case
    "git@github.com-work:org/planning.git",   # an alias that adds to the real host
    "git@work.github.com:org/planning.git",
])
def test_a_checkout_of_the_declared_repository_is_read_as_written(tcw, tmp_path, remote):
    planning, child = _repositories(tmp_path / "real", remote)
    copy, linked = _side_by_side(tmp_path / "real", tmp_path / "copy")
    assert _store(linked) == copy / "sub/docs/work"
    dry = tcw(["migrate", "--dry-run", "--no-jira"], linked)
    assert dry.code == 0, dry.err
    assert f"left in another repository: {copy}" in dry.err.splitlines()
    assert NOTE not in dry.err


@pytest.mark.parametrize("where", ["home", "xdg", "checkout"])
def test_an_insteadof_rule_rewrites_the_declared_url(tcw, tmp_path, where):
    """A mirror's URL names the declared repository only through the rule,
    read from the user's own git configuration or the checkout's."""
    planning, child = _repositories(tmp_path / "real",
                                    "https://git.example.com/mirror/org/planning.git")
    copy, linked = _side_by_side(tmp_path / "real", tmp_path / "copy")
    assert _store(linked) != copy / "sub/docs/work"     # no rule yet
    from tcw.store import project
    project._REPOSITORY_CACHE.clear()
    _insteadof({"home": tmp_path / "home/.gitconfig",
                "xdg": tmp_path / "xdg/git/config",
                "checkout": planning / ".git/config"}[where])
    assert _store(linked) == copy / "sub/docs/work"
    dry = tcw(["migrate", "--dry-run", "--no-jira"], linked)
    assert f"left in another repository: {copy}" in dry.err.splitlines()


@pytest.mark.parametrize("remote", ["git@github-work:org/other.git",
                                    "https://gitlab.example.com/org/planning.git",
                                    "git@evilgithub.com:org/planning.git",
                                    "git@github.com-evil.example:org/planning.git",
                                    None])
def test_a_checkout_of_another_repository_is_passed_over_and_said(tcw, tmp_path, remote):
    """Another owner or name, the same owner and name on another real host,
    and no remote at all: the store is read beside the main checkout, and
    `tcw migrate` says which folder it passed over."""
    planning, child = _repositories(tmp_path / "real", remote)
    copy, linked = _side_by_side(tmp_path / "real", tmp_path / "copy")
    beside = planning.resolve() / "sub/docs/work"
    assert _store(linked) == beside
    dry = tcw(["migrate", "--dry-run", "--no-jira"], linked)
    assert dry.code == 0, dry.err
    said = [line for line in dry.err.splitlines() if NOTE in line]
    assert len(said) == 1, dry.err
    assert str(copy / "sub/docs/work") in said[0] and str(beside) in said[0]
    assert DECLARED in said[0] and "remote" in said[0]
    assert f"left in another repository: {copy}" not in dry.err.splitlines()


def test_validate_warns_of_a_store_read_beside_the_main_checkout(tcw, tmp_path):
    planning, child = _repositories(tmp_path / "real", None)
    assert tcw(["migrate", "--no-jira"], child).code == 0
    _commit(planning)
    _commit(child)
    copy, linked = _side_by_side(tmp_path / "real", tmp_path / "copy")
    done = tcw(["validate"], linked)
    assert done.code == 0, done.out + done.err
    said = [line for line in (done.out + done.err).splitlines() if NOTE in line]
    assert len(said) == 1, done.out + done.err
    assert "warning" in said[0] and str(copy / "sub/docs/work") in said[0]


def test_validate_is_silent_when_the_store_is_read_as_written(tcw, tmp_path):
    planning, child = _repositories(tmp_path / "real", "git@github-work:org/planning.git")
    assert tcw(["migrate", "--no-jira"], child).code == 0
    _commit(planning)
    _commit(child)
    copy, linked = _side_by_side(tmp_path / "real", tmp_path / "copy")
    done = tcw(["validate"], linked)
    assert NOTE not in done.out + done.err


def test_a_worktree_made_elsewhere_is_unchanged_and_silent(tcw, tmp_path):
    """Nothing where the path lands: read beside the main checkout, as
    before, and nothing is said about it."""
    planning, child = _repositories(tmp_path / "real", None)
    linked = (tmp_path / "elsewhere/child")
    _git("-C", child, "worktree", "add", "-q", "--detach", linked)
    linked = linked.resolve()
    assert _store(linked) == planning.resolve() / "sub/docs/work"
    dry = tcw(["migrate", "--dry-run", "--no-jira"], linked)
    assert dry.code == 0, dry.err
    assert NOTE not in dry.err
    assert f"left in another repository: {planning.resolve()}" in dry.err.splitlines()
