"""The deciding manifest entry of a project, made readable (TCW-115 Design
8.1): `FsProjectRegistry.placement`, at the library level.

Provisioning needs more than the folder `project_folder` gives: the entry
that decided where a project is, the project whose lookup decided (`asked_by`,
for the way out of Design 7.8), the project whose `.tcw/` holds that manifest
(`owner`, for the bound), and where the repository goes (`repository_folder`,
Design 7.6). The commands built on it are tested in
`tests/test_project_provision.py`.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from tcw.errors import ProjectGraphError, UnknownProject
from tcw.store import project as project_module
from tcw.store.project import FsProjectRegistry, Placement
from tests.projectfiles import write_config, write_manifest
from tests.test_manifest_worktree import git, repository_with_worktree


def proj(root: Path, project_id: str, *, parents=(), children=()) -> Path:
    data: dict = {"id": project_id}
    if parents:
        data["parents"] = list(parents)
    if children:
        data["children"] = list(children)
    write_config(root, yaml.safe_dump(data, sort_keys=False))
    return root.resolve()


def test_a_project_found_by_its_manifest_entry(tmp_path):
    app = proj(tmp_path / "app", "app", parents=["core"])
    manifest = write_manifest(app, {"core": "../core"})
    core = proj(tmp_path / "core", "core")
    registry = FsProjectRegistry.open(app)
    assert registry.project_folder("core", app) == core
    found = registry.placement("core")
    assert isinstance(found, Placement)
    assert found.id == "core"
    assert found.folder == core
    assert found.entry.file == manifest
    assert found.owner == app
    assert found.asked_by == app


def test_not_on_this_machine_with_a_repository_and_a_subfolder(tmp_path):
    app = proj(tmp_path / "app", "app", parents=["server"])
    write_manifest(app, {"server": {"path": "../mono/apps/server",
                                    "repository": "/remote/mono#main",
                                    "subfolder": "apps/server"}})
    registry = FsProjectRegistry.open(app)
    found = registry.placement("server", app)
    assert found.folder is None
    assert found.entry.url == "/remote/mono"
    assert found.entry.branch == "main"
    assert found.entry_folder == (tmp_path / "mono" / "apps" / "server").resolve()
    assert found.repository_folder == (tmp_path / "mono").resolve()
    # As written, joined to the folder it is read from; nothing followed.
    assert found.repository_path == app / ".." / "mono"


def test_found_by_the_search_and_by_the_variable_has_no_entry(tmp_path, monkeypatch):
    app = proj(tmp_path / "app", "app", parents=["core", "lib"])
    core = proj(tmp_path / "core", "core")
    lib = proj(tmp_path / "elsewhere" / "lib", "lib")
    monkeypatch.setenv("TCW_PROJECT_LIB", str(lib))
    registry = FsProjectRegistry.open(app)
    by_search = registry.placement("core", app)
    assert by_search.entry is None and by_search.folder == core
    by_variable = registry.placement("lib", app)
    assert by_variable.entry is None and by_variable.folder == lib
    assert by_variable.owner is None and by_variable.repository_folder is None


def test_an_entry_in_an_ancestors_manifest_is_owned_by_the_ancestor(tmp_path):
    app = proj(tmp_path / "app", "app", parents=["core"])
    core = proj(tmp_path / "core", "core", parents=["base"])
    write_manifest(core, {"base": {"path": "../base", "repository": "/r/base"}})
    registry = FsProjectRegistry.open(app)
    found = registry.placement("base", app)
    assert found.folder is None
    assert found.owner == core
    assert found.asked_by == app
    assert found.repository_folder == (tmp_path / "base").resolve()


def test_a_personal_manifest_borrowed_by_a_worktree_is_owned_by_the_worktree(
        tmp_path, monkeypatch):
    monkeypatch.delenv("TCW_NO_PERSONAL_CONFIG")
    main = tmp_path / "main"
    proj(main, "app", parents=["core"])
    (main / ".tcw" / ".gitignore").write_text("/tcw-manifest.local.yaml\n")
    worktree = repository_with_worktree(main, tmp_path / "wt")
    borrowed = write_manifest(main, {"core": {"path": "../core", "repository": "/r/c"}},
                              local=True)
    registry = FsProjectRegistry.open(worktree)
    found = registry.placement("core", worktree)
    assert found.entry.file == borrowed
    assert found.owner == worktree
    # Leading outside the repository, so read from the main checkout (TCW-107
    # Design 4.3).
    assert found.repository_folder == (tmp_path / "core").resolve()


def test_without_named_by_nothing_is_read(tmp_path, monkeypatch):
    app = proj(tmp_path / "app", "app", parents=["core"])
    write_manifest(app, {"core": {"path": "../core", "repository": "/r/c"}})
    registry = FsProjectRegistry.open(app)
    first = registry.placement("core", app)

    def fail(path):
        pytest.fail(f"read {path}")

    monkeypatch.setattr(project_module, "_read_text", fail)
    monkeypatch.setattr(project_module, "_list_folder", fail)
    assert registry.placement("core") == first
    assert registry.placement("never-asked") is None


def test_with_named_by_an_unknown_id_and_a_graph_problem_raise(tmp_path):
    app = proj(tmp_path / "app", "app")
    registry = FsProjectRegistry.open(app)
    with pytest.raises(UnknownProject):
        registry.placement("nope", app)
    proj(tmp_path / "x1", "lib")
    proj(tmp_path / "x2", "lib")
    with pytest.raises(ProjectGraphError):
        FsProjectRegistry.open(app).placement("lib", app)


def test_the_active_project_itself(tmp_path):
    app = proj(tmp_path / "app", "app")
    found = FsProjectRegistry.open(app).placement("app", app)
    assert found.folder == app and found.entry is None
