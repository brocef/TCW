"""The test helpers that write manifests and move 3.x locations out of
`projects:` (TCW-107 plan, step 2), tested on literal inputs, and the
`tmp_path` override in `tests/conftest.py` that keeps test folders apart."""

from __future__ import annotations

import os

import pytest
import yaml

from tcw.project_files import VERSION_KEY, version_line
from tests.projectfiles import (config_file, manifest_file, write_config,
                                write_connected_config, write_connected_config_file,
                                write_manifest)


def _read(path):
    return yaml.safe_load(path.read_text())


def test_write_manifest_writes_projects_under_the_version_line(tmp_path):
    path = write_manifest(tmp_path, {"lib": "../lib"})
    assert path == tmp_path / ".tcw" / "tcw-manifest.yaml" == manifest_file(tmp_path)
    assert path.read_text().startswith(version_line())
    assert _read(path)["projects"] == {"lib": "../lib"}


def test_write_manifest_merges_into_a_manifest_already_there(tmp_path):
    write_manifest(tmp_path, {"lib": "../lib"})
    write_manifest(tmp_path, {"core": {"path": "../core"}})
    assert _read(manifest_file(tmp_path))["projects"] == {
        "lib": "../lib", "core": {"path": "../core"}}


def test_write_manifest_local(tmp_path):
    path = write_manifest(tmp_path, {"lib": "/abs/lib"}, local=True)
    assert path == tmp_path / ".tcw" / "tcw-manifest.local.yaml"
    assert path == manifest_file(tmp_path, local=True)
    assert _read(path)["projects"] == {"lib": "/abs/lib"}


def test_write_manifest_text_gets_the_version_line_only_when_it_has_none(tmp_path):
    path = write_manifest(tmp_path, "projects: {lib: ../lib}\n")
    assert path.read_text() == version_line() + "projects: {lib: ../lib}\n"
    path = write_manifest(tmp_path, "tcw-version: 99.0.0\nprojects: {}\n")
    assert path.read_text() == "tcw-version: 99.0.0\nprojects: {}\n"
    path = write_manifest(tmp_path, "projects: [unclosed\n")
    assert path.read_text() == "projects: [unclosed\n"


def test_a_bare_locator_moves_into_the_manifest(tmp_path):
    write_connected_config(tmp_path, "id: app\nprojects:\n  upstream:\n    lib: ../lib\n")
    config = _read(config_file(tmp_path))
    assert config["projects"] == {"upstream": {"lib": None}}
    assert config[VERSION_KEY]
    assert _read(manifest_file(tmp_path))["projects"] == {"lib": "../lib"}


def test_an_absolute_locator_is_written_relative_to_the_root(tmp_path):
    lib = tmp_path.parent / "elsewhere" / "lib"
    write_connected_config(tmp_path / "app",
                           f"id: app\nprojects:\n  children:\n    lib: {lib}\n")
    assert _read(manifest_file(tmp_path / "app"))["projects"] == {
        "lib": os.path.relpath(lib, tmp_path / "app")}


def test_a_path_and_repository_mapping_becomes_one_manifest_entry(tmp_path):
    write_connected_config(tmp_path, (
        "id: app\nprojects:\n  upstream:\n    server:\n      path: ../app/apps/server\n"
        "      repository: {url: 'https://h/app.git', ref: main, path: apps/server}\n"))
    assert _read(config_file(tmp_path))["projects"] == {"upstream": {"server": None}}
    assert _read(manifest_file(tmp_path))["projects"] == {"server": {
        "path": "../app/apps/server", "repository": "https://h/app.git#main",
        "subfolder": "apps/server"}}


def test_a_jira_block_stays_in_the_configuration(tmp_path):
    write_connected_config(tmp_path, (
        "id: app\nprojects:\n  children:\n"
        "    lib: {path: ../lib, jira: {project: LIB}}\n"))
    assert _read(config_file(tmp_path))["projects"] == {
        "children": {"lib": {"jira": {"project": "LIB"}}}}
    assert _read(manifest_file(tmp_path))["projects"] == {"lib": "../lib"}


@pytest.mark.parametrize("text", [
    "id: app\nprojects: [unclosed\n",
    "id: app\n",
    "id: app\nprojects:\n  parent:\n    root:\n",
])
def test_text_with_nothing_to_move_is_written_as_write_config_writes_it(tmp_path, text):
    write_connected_config(tmp_path / "a", text)
    write_config(tmp_path / "b", text)
    assert config_file(tmp_path / "a").read_text() == config_file(tmp_path / "b").read_text()
    assert not manifest_file(tmp_path / "a").exists()


@pytest.mark.parametrize("entry", [
    "{repository: {url: 'https://h/lib.git'}}",
    "{path: ../lib, repository: {url: 'https://h/lib.git', checkout: ../x}}",
])
def test_an_entry_the_helper_cannot_move_is_refused(tmp_path, entry):
    with pytest.raises(AssertionError, match="by hand"):
        write_connected_config(tmp_path,
                               f"id: app\nprojects:\n  upstream:\n    lib: {entry}\n")


def test_write_connected_config_file_takes_the_configuration_path(tmp_path):
    path = config_file(tmp_path)
    write_connected_config_file(path, "id: app\nprojects:\n  children:\n    lib: lib\n")
    assert _read(manifest_file(tmp_path))["projects"] == {"lib": "lib"}


def test_each_test_folder_is_alone_in_its_parent(tmp_path):
    """The lookup lists the folder holding a project's root (TCW-107 Design
    2.4), so a fixture project at `tmp_path` must not sit beside another
    test's folders. `tests/conftest.py` overrides `tmp_path` to see to it."""
    assert [p.name for p in tmp_path.parent.iterdir()] == [tmp_path.name]
