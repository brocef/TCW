"""The test helper that writes manifests (TCW-107 plan, step 2), tested on
literal inputs, and the `tmp_path` override in `tests/conftest.py` that keeps
test folders apart."""

from __future__ import annotations

import yaml

from tcw.project_files import version_line
from tests.projectfiles import manifest_file, write_manifest


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


def test_each_test_folder_is_alone_in_its_parent(tmp_path):
    """The lookup lists the folder holding a project's root (TCW-107 Design
    2.4), so a fixture project at `tmp_path` must not sit beside another
    test's folders. `tests/conftest.py` overrides `tmp_path` to see to it."""
    assert [p.name for p in tmp_path.parent.iterdir()] == [tmp_path.name]
