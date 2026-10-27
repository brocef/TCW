"""Store locations outside the project (TCW-116 Design 3, C5; Design 1.4,
6.3; B6, B7; criteria 28 and 47; plan Step 20).

Each converted location must name, in TCW 4, the folder TCW 3 resolved.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import yaml

from tcw.migrate.legacy import RepoDecl3, cache_folder_3x, store_folder_3x
from tests.migrate.test_migrate_config import make, tree
from tests.objectcli import tcw  # noqa: F401  (a fixture)

ITEM = "title: A\nstage: request\npriority: medium\n"


def project(folder: Path, text: str, files: dict | None = None, *, git: bool = False):
    return make(folder, {"tcw-config.yaml": text, **(files or {})}, git=git)


def migrate(tcw, root: Path, code: int = 0):
    done = tcw(["migrate", "--no-jira"], root)
    assert done.code == code, done.err
    return done


def shared(root: Path) -> dict:
    return yaml.safe_load((root / ".tcw/tcw-config.yaml").read_text())


def where_4(root: Path, component: str) -> Path:
    from tcw.store.fs import store_location
    from tcw.store.project import forget_registries
    forget_registries()
    section = shared(root).get(component) or {}
    return Path(os.path.realpath(store_location(root, component, section.get("path"))))


def where_3(root: Path, text: str, component: str) -> Path:
    section = yaml.safe_load(text).get(component)
    return Path(os.path.realpath(os.path.normpath(
        store_folder_3x(root, component, section).folder.absolute())))


def test_a_relative_path_inside_the_project_is_unchanged(tcw, tmp_path):
    text = "id: app\nwork:\n  path: records/work\n"
    app = project(tmp_path / "app", text, {"records/work/a/item.yaml": ITEM}, git=True)
    migrate(tcw, app)
    assert shared(app)["work"] == {"path": "records/work"}
    assert (app / "records/work/a/tcw-work-item.yaml").is_file()


def test_a_path_into_a_project_4_0_finds_becomes_its_address(tcw, tmp_path):
    ws = project(tmp_path / "ws", "id: ws\n", git=True)
    text = "id: app\nwork:\n  path: ../docs/app/work\n"
    app = project(ws / "app", text)
    make(ws, {"docs/app/work/a/item.yaml": ITEM})
    before = where_3(app, text, "work")
    migrate(tcw, app)
    assert shared(app)["work"] == {"path": "tcw://ws.path/docs/app/work"}
    assert (ws / "docs/app/work/a/tcw-work-item.yaml").is_file()
    migrate(tcw, ws)
    assert where_4(app, "work") == before


def test_a_path_out_of_the_project_into_no_project_4_0_finds_is_kept(tcw, tmp_path):
    text = "id: app\nwork:\n  path: ../shared/work\n"
    app = project(tmp_path / "w/app", text, git=True)
    make(tmp_path / "w/shared", {"work/a/item.yaml": ITEM})
    migrate(tcw, app)
    assert shared(app)["work"] == {"path": "../shared/work"}
    assert where_4(app, "work") == where_3(app, text, "work")


def test_an_absolute_path_inside_the_project_becomes_relative(tcw, tmp_path):
    app = tmp_path / "app"
    text = f"id: app\ntaxonomy:\n  path: {app / 'terms'}\n"
    project(app, text, {"terms/x/meta.yaml": "name: X\nkind: Vocabulary\nrelatesTo: []\n"},
            git=True)
    migrate(tcw, app)
    assert shared(app)["taxonomy"] == {"path": "terms"}


def test_an_absolute_path_inside_another_project_is_an_address_and_an_entry(
        tcw, tmp_path, monkeypatch):
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG")
    core = project(tmp_path / "far/core", "id: core\n", git=True)
    text = f"id: app\nwork:\n  path: {core / 'records/app'}\n"
    app = project(tmp_path / "w/app", text, git=True)
    make(core, {"records/app/a/item.yaml": ITEM})
    before = where_3(app, text, "work")
    migrate(tcw, app)
    assert shared(app)["work"] == {"path": "tcw://core.path/records/app"}
    personal = yaml.safe_load((app / ".tcw/tcw-manifest.local.yaml").read_text())
    assert personal["projects"] == {"core": {"path": str(core.resolve())}}
    migrate(tcw, core)
    assert where_4(app, "work") == before


def test_an_absolute_path_inside_no_project_is_b6(tcw, tmp_path):
    app = project(tmp_path / "w/app", f"id: app\nwork:\n  path: {tmp_path / 'loose/work'}\n",
                  git=True)
    before = tree(app)
    done = migrate(tcw, app, 3)
    assert "  B6 tcw-config.yaml: work.path: " in done.err
    assert tree(app) == before


def test_a_store_repository_is_kept_and_its_clone_converted(tcw, tmp_path):
    url = "https://example.invalid/terms.git"
    clone = cache_folder_3x(tmp_path, RepoDecl3(url))
    make(clone, {"x/meta.yaml": "name: X\nkind: Vocabulary\nrelatesTo: []\n"}, git=True)
    text = f"id: app\ntaxonomy:\n  repository:\n    url: {url}\n"
    app = project(tmp_path / "app", text, git=True)
    done = migrate(tcw, app)
    assert shared(app)["taxonomy"] == {"repository": {"url": url}}
    assert (clone / "x/tcw-taxonomy.yaml").is_file()
    said = done.err.splitlines()
    at = said.index(f"left in another repository: {clone.resolve()}")
    # The clone is in no checkout the project sits in: its files are named
    # by absolute paths, not by a relative path climbing towards `/`.
    held = clone.resolve()
    assert said[at + 1:at + 4] == [f"  {held}/x/description.md", f"  {held}/x/meta.yaml",
                                   f"  {held}/x/tcw-taxonomy.yaml"]
    assert not any("/.git/" in line for line in said)


def test_a_store_path_with_a_repository_keeps_the_repository(tcw, tmp_path):
    ws = project(tmp_path / "ws", "id: ws\n", git=True)
    text = ("id: app\nwork:\n  path: ../docs/app/work\n  repository:\n"
            "    url: https://example.invalid/ws.git\n    path: docs/app/work\n")
    app = project(ws / "app", text)
    migrate(tcw, app)
    assert shared(app)["work"] == {"path": "tcw://ws.path/docs/app/work",
                                   "repository": {"url": "https://example.invalid/ws.git",
                                                  "path": "docs/app/work"}}


# ── A planning workspace, two repositories (criterion 47, Design 6.3) ───────

def test_a_workspace_store_is_converted_and_left_in_the_workspace(tcw, tmp_path):
    ws = project(tmp_path / "ws", "id: ws\n", {"docs/work/w-1/item.yaml": ITEM}, git=True)
    app = project(ws / "app", "id: app\nwork:\n  path: ../docs/app/work\n", git=True)
    make(ws, {"docs/app/work/a-1/item.yaml": ITEM, "docs/app/work/a-1/notes.md": "N.\n"})
    done = migrate(tcw, app)
    assert shared(app)["work"] == {"path": "tcw://ws.path/docs/app/work"}
    said = done.err.splitlines()
    at = said.index(f"left in another repository: {ws.resolve()}")
    assert said[at + 1:] [:4] == ["  ../docs/app/work/a-1/item.yaml",
                                  "  ../docs/app/work/a-1/notes.md",
                                  "  ../docs/app/work/a-1/resources/notes.md",
                                  "  ../docs/app/work/a-1/tcw-work-item.yaml"]
    after_app = tree(ws / "docs/app/work")
    migrate(tcw, ws)
    assert tree(ws / "docs/app/work") == after_app
    assert (ws / "docs/work/w-1/tcw-work-item.yaml").is_file()


def test_a_store_that_is_a_related_project_s_store_is_b7(tcw, tmp_path):
    ws = project(tmp_path / "ws", "id: ws\nprojects:\n  children:\n    app: app\n",
                 {"docs/work/w-1/item.yaml": ITEM}, git=True)
    app = project(ws / "app", "id: app\nprojects:\n  parent:\n    ws: ..\n"
                              "work:\n  path: ../docs/work\n")
    before = tree(ws)
    done = migrate(tcw, app, 3)
    assert "  B7 ../docs/work: the work store is 'ws''s work store" in done.err
    assert tree(ws) == before


# ── A copy made with linked worktrees (Design 6.6, criterion 49) ────────────

def _commit(root: Path) -> None:
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t",
                    "commit", "-qm", "x"], check=True)


def _worktree(main: Path, at: Path) -> Path:
    subprocess.run(["git", "-C", str(main), "worktree", "add", "-q", "--detach", str(at)],
                   check=True)
    return at


def _workspace_with_a_child_repository(base: Path) -> Path:
    """A workspace repository holding its descendants' work stores, with a
    child project that is a repository of its own checked out inside it,
    and a grandchild below the child."""
    ws = project(base / "ws", "id: ws\nprojects:\n  children:\n    app: app\n",
                 {".gitignore": "/app/\n", "docs/work/w-1/item.yaml": ITEM,
                  "docs/app/work/a-1/item.yaml": ITEM,
                  "docs/app/work/a-1/attachments/a.txt": "A.\n",
                  "docs/srv/work/s-1/item.yaml": ITEM,
                  "docs/srv/work/s-1/attachments/s.txt": "S.\n"}, git=True)
    app = project(ws / "app", "id: app\nprojects:\n  parent:\n    ws: ..\n  children:\n"
                              "    srv: apps/server\nwork:\n  path: ../docs/app/work\n",
                  {"apps/server/tcw-config.yaml":
                   "id: srv\nprojects:\n  parent:\n    app: ../..\n"
                   "work:\n  path: ../../../docs/srv/work\n"}, git=True)
    _commit(ws)
    _commit(app)
    return ws


def test_a_copy_of_nested_worktrees_never_changes_the_main_checkouts(tcw, tmp_path):
    ws = _workspace_with_a_child_repository(tmp_path / "real")
    copy = _worktree(ws, tmp_path / "copy/ws")
    _worktree(ws / "app", copy / "app")
    real = tree(ws)
    for folder in (copy / "app/apps/server", copy / "app"):
        dry = tcw(["migrate", "--dry-run", "--no-jira"], folder)
        assert dry.code == 3, dry.err
        b18 = [line for line in dry.err.splitlines() if line.startswith("  B18 ")]
        assert len(b18) == 1, dry.err
        assert b18[0].startswith(f"  B18 {ws.resolve()}: ")
        assert not any("../real/" in line for line in dry.err.splitlines()), dry.err
        done = migrate(tcw, folder, 3)
        assert "  B18 " in done.err
    assert tree(ws) == real


def test_a_worktree_beside_the_workspace_still_reaches_its_store(tcw, tmp_path):
    """A worktree of the child made away from the workspace: the store path
    leaves it and lands on nothing, so it is read beside the main checkout,
    as 3.x read it; files there are named by absolute paths."""
    ws = _workspace_with_a_child_repository(tmp_path / "real")
    linked = _worktree(ws / "app", tmp_path / "elsewhere/app")
    done = migrate(tcw, linked)
    assert "B18" not in done.err
    assert (ws / "docs/app/work/a-1/tcw-work-item.yaml").is_file()
    said = done.err.splitlines()
    assert f"left in another repository: {ws.resolve()}" in said
    assert f"  {ws.resolve()}/docs/app/work/a-1/tcw-work-item.yaml" in said
    assert not any("../" in line for line in said), done.err
