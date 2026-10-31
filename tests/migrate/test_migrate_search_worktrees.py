"""`tcw migrate`'s prediction of 4.0's search (`family.search_4`) from a
linked git worktree: it must find what `tcw project path` finds, since a
run leaves out a manifest entry when the prediction finds the project's
folder (M6). Each test builds the layout with real git worktrees and asks
both."""

from __future__ import annotations

from pathlib import Path

from tcw.migrate import family
from tcw.migrate.family import read_family
from tests.projectfiles import write_manifest
from tests.test_manifest_worktree import _commit_all, _linked, _repository, _siblings, git, proj
from tests.test_project_files_cli import personal_env, tcw


def _agree(folder: Path, expected: Path | None) -> None:
    """The runtime finds `r2` from `folder` at `expected` (not at all for
    None), and the prediction finds it there alone, or not at all."""
    ran = tcw(folder, "project", "path", "r2")
    if expected is None:
        assert ran.code != 0, ran
        assert len(family.search_4(folder, "r2")) != 1
    else:
        assert ran.code == 0 and ran.out.strip() == str(expected), ran
        assert family.search_4(folder, "r2") == [expected]


def test_a_worktree_elsewhere_is_predicted_beside_the_main_checkout(tmp_path):
    r1, r2 = _siblings(tmp_path / "code")
    linked = _linked(r1, tmp_path / "elsewhere" / "r1-feat")
    proj(tmp_path / "elsewhere" / "r2", "r2")         # beside the worktree, not read
    _agree(linked, r2)


def test_a_worktree_in_a_workspace_repositorys_worktrees_folder(tmp_path):
    ws = _repository(tmp_path / "ws")
    r1, r2 = _siblings(ws)
    _agree(_linked(r1, ws / ".worktrees" / "r1-feat"), r2)


def test_a_worktree_in_a_home_folder_kept_in_git(tmp_path):
    home = _repository(tmp_path / "home")
    r1, r2 = _siblings(home / "code")
    _agree(_linked(r1, home / "elsewhere" / "r1-feat"), r2)


def test_nested_worktrees_holding_the_sibling_predict_the_copys(tmp_path):
    ws = _repository(tmp_path / "real" / "ws")
    r1, r2 = _siblings(ws)
    copy = _linked(ws, tmp_path / "copy" / "ws")
    _linked(r1, copy / "r1")
    copied = _linked(r2, copy / "r2")
    _agree(copy / "r1", copied)


def test_nested_worktrees_lacking_the_sibling_predict_none(tmp_path):
    ws = _repository(tmp_path / "real" / "ws")
    r1, _ = _siblings(ws)
    copy = _linked(ws, tmp_path / "copy" / "ws")
    _linked(r1, copy / "r1")
    _agree(copy / "r1", None)


def test_a_worktree_in_a_linked_worktrees_worktrees_folder(tmp_path):
    """The checkout holding the worktree is a linked worktree of a workspace
    repository, but the worktree's own main checkout is not inside that
    repository's main checkout: it is no copy, and the folders beside its
    main checkout are searched."""
    ws = _repository(tmp_path / "ws")
    feat = _linked(ws, tmp_path / "ws-feat")
    r1, r2 = _siblings(tmp_path / "code")
    _agree(_linked(r1, feat / ".worktrees" / "r1-feat"), r2)


def test_a_related_projects_search_reads_the_active_projects_worktree(tmp_path):
    """A related project `r2` sits in a linked worktree away from its main
    checkout and names a parent `r3` no manifest entry places, found only
    beside `r2`'s main checkout. 4.0 searches from `r2` with the active
    project's worktree information, and the active project is an ordinary
    checkout, so it looks beside the worktree alone; the prediction, made
    from `r1` as it migrates, must do the same."""
    code = tmp_path / "code"
    proj(code / "r3", "r3")
    main = proj(code / "r2", "r2", parent=["r3"])
    write_manifest(main, "tcw-version: 4.0.0\nprojects: {}\n")
    git(main, "init", "-q", "-b", "main")
    _commit_all(main)
    r2 = _linked(main, tmp_path / "wt" / "r2")
    r1 = proj(tmp_path / "active" / "r1", "r1", parent=["r2"])
    write_manifest(r1, {"r2": str(r2)}, local=True)
    ran = tcw(r1, "project", "info", env=personal_env(tmp_path))
    assert ran.code == 0, ran
    assert "load order incomplete: not on this machine: r3" in ran.out, ran
    found = read_family(r1, "r1", {"id": "r1", "projects": {"parent": {"r2": str(r2)}}})
    found._walk_to("\0")
    assert found.place("r3").how == "absent", found.place("r3")
