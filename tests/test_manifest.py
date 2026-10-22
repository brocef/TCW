"""The manifest files and their parser (TCW-107 Design 1).

Unit tests of `tcw.store.manifest.parse_manifest`, which reads no file, and
of `tcw.project_files.personal_files_skipped`. The commands that read
manifests are tested in `tests/test_manifest_cli.py`, and the lookup that uses
them in `tests/test_project_lookup.py`.
"""

from __future__ import annotations

import pytest

import tcw
from tcw import project_files as pf
from tcw.store.manifest import ManifestEntry, parse_manifest

FILE = "/p/.tcw/tcw-manifest.yaml"


def _running() -> str:
    return tcw.__version__


def _parse(projects, *, personal=False, **top):
    mapping = {"tcw-version": _running(), **top}
    if projects is not None:
        mapping["projects"] = projects
    return parse_manifest(mapping, FILE, personal=personal)


def _refused(projects, *, personal=False, **top) -> str:
    entries, problems = _parse(projects, personal=personal, **top)
    assert entries == {}, "a manifest with a problem is not used (Design 1.8)"
    assert problems
    return "\n".join(problems)


# ---------------------------------------------------------------------------
# The file names


def test_the_two_manifest_files_sit_in_the_tcw_folder():
    assert pf.MANIFEST_NAME == "tcw-manifest.yaml"
    assert pf.LOCAL_MANIFEST_NAME == "tcw-manifest.local.yaml"
    assert pf.MANIFEST == ".tcw/tcw-manifest.yaml"
    assert pf.LOCAL_MANIFEST == ".tcw/tcw-manifest.local.yaml"


# ---------------------------------------------------------------------------
# Accepted forms (Design 1.1-1.6)


def test_an_empty_file_and_a_file_holding_only_the_version_have_no_entries():
    assert parse_manifest(None, FILE, personal=False) == ({}, [])
    assert _parse(None) == ({}, [])
    assert _parse({}) == ({}, [])


def test_a_path_alone():
    entries, problems = _parse({"shared": "packages/shared"})
    assert problems == []
    assert entries == {"shared": ManifestEntry(id="shared", path="packages/shared",
                                               file=FILE)}


def test_a_mapping_with_path_repository_and_subfolder():
    entries, problems = _parse({
        "core": {"path": "../core",
                 "repository": "https://github.com/example/core.git#release"},
        "server": {"path": "../app/apps/server",
                   "repository": "git@github.com:example/app.git",
                   "subfolder": "apps/server"},
    })
    assert problems == []
    core, server = entries["core"], entries["server"]
    assert (core.path, core.url, core.branch, core.subfolder) == (
        "../core", "https://github.com/example/core.git", "release", None)
    assert core.repository == "https://github.com/example/core.git#release"
    assert (server.url, server.branch, server.subfolder) == (
        "git@github.com:example/app.git", None, "apps/server")
    assert server.repository == "git@github.com:example/app.git"


def test_the_repository_is_split_at_the_first_hash():
    entries, _ = _parse({"lib": {"path": "../lib",
                                 "repository": "ssh://h/lib.git#v1.2"}})
    assert (entries["lib"].url, entries["lib"].branch) == ("ssh://h/lib.git", "v1.2")


@pytest.mark.parametrize("path", ["/abs/lib", "~/lib", "~", "../lib"])
def test_the_personal_manifest_may_give_an_absolute_or_home_path(path):
    entries, problems = _parse({"lib": path}, personal=True)
    assert problems == []
    assert entries["lib"].path == path


def test_a_subfolder_whose_path_ends_with_it_is_accepted():
    entries, problems = _parse({"server": {"path": "../app/apps/server",
                                           "repository": "u",
                                           "subfolder": "apps/server/"}})
    assert problems == []
    assert entries["server"].subfolder == "apps/server"


# ---------------------------------------------------------------------------
# Refusals (Design 1.2-1.6, AC 2)


def test_no_tcw_version_names_the_line_to_write_and_not_tcw_migrate():
    entries, problems = parse_manifest({"projects": {"lib": "../lib"}}, FILE,
                                       personal=False)
    assert entries == {}
    text = "\n".join(problems)
    assert f"a manifest starts with 'tcw-version: {_running()}'" in text
    assert "tcw migrate" not in text


def test_a_newer_tcw_version_is_refused_with_the_upgrade_message():
    entries, problems = parse_manifest(
        {"tcw-version": "99.0.0", "projects": {"lib": "../lib"}}, FILE, personal=False)
    assert entries == {}
    assert problems == [pf.version_problem({"tcw-version": "99.0.0"})]
    assert "upgrade TCW" in problems[0]


def test_a_manifest_that_is_not_a_mapping_is_refused():
    entries, problems = parse_manifest(["lib"], FILE, personal=False)
    assert entries == {} and problems


def test_an_unknown_top_level_key_is_refused():
    assert "'other'" in _refused({"lib": "../lib"}, other=1)


def test_projects_that_is_not_a_mapping_is_refused():
    assert "projects" in _refused(["lib"])


def test_an_unknown_entry_key_is_refused():
    assert "'ref'" in _refused({"lib": {"path": "../lib", "ref": "main"}})


@pytest.mark.parametrize("path", ["/abs/lib", "~/lib", "~"])
def test_the_shared_manifest_refuses_an_absolute_or_home_path(path):
    text = _refused({"lib": path})
    assert "relative" in text and "tcw-manifest.local.yaml" in text


def test_an_entry_mapping_needs_a_path():
    assert "path" in _refused({"lib": {"repository": "https://h/lib.git"}})


@pytest.mark.parametrize("path", ["", "   ", 3, None])
def test_a_path_must_be_nonempty_text(path):
    assert _refused({"lib": {"path": path}})


@pytest.mark.parametrize("repository, words", [
    ("https://example.invalid/lib.git#", "after '#'"),
    ("#main", "before '#'"),
    ("x#a#b", "second '#'"),
    ("x#a b", "space"),
    ("", "repository"),
    (7, "repository"),
])
def test_a_malformed_repository_is_refused(repository, words):
    assert words in _refused({"lib": {"path": "../lib", "repository": repository}})


@pytest.mark.parametrize("repository", ["-uexploit", "https://h/lib.git#-x"])
def test_a_repository_or_its_suffix_beginning_with_a_dash_is_refused(repository):
    """TCW-115's handoff: a value beginning with `-` would be read as an option
    by the program that fetches it, so it is refused here, where `tcw validate`
    sees it, as well as by TCW-115 before fetching."""
    assert "'-'" in _refused({"lib": {"path": "../lib", "repository": repository}})


@pytest.mark.parametrize("subfolder", ["../x", "a/../b", "./a", "/abs", ""])
def test_a_subfolder_must_be_relative_without_dot_parts(subfolder):
    assert "subfolder" in _refused({"x": {"path": "../a/x", "repository": "u",
                                          "subfolder": subfolder}})


def test_a_subfolder_the_path_does_not_end_with_is_refused():
    text = _refused({"x": {"path": "../app", "repository": "u",
                           "subfolder": "apps/x"}})
    assert "apps/x" in text and "../app" in text


def test_a_subfolder_without_a_repository_is_refused():
    assert "repository" in _refused({"x": {"path": "../a/x", "subfolder": "x"}})


@pytest.mark.parametrize("project_id", ["Lib", "t", "a_b", ""])
def test_an_invalid_project_id_is_refused(project_id):
    assert "project ID" in _refused({project_id: "../lib"})


def test_one_bad_entry_makes_the_whole_manifest_unused():
    entries, problems = _parse({"good": "../good", "bad": {"path": "../b", "x": 1}})
    assert entries == {} and len(problems) == 1


# ---------------------------------------------------------------------------
# The switch that skips personal files (Design 1.10)


@pytest.mark.parametrize("value, skipped", [
    (None, False), ("", False), ("1", True), ("true", True)])
def test_personal_files_skipped_agrees_with_the_configuration_reader(
        monkeypatch, tmp_path, value, skipped):
    from tcw.config import _personal_layers
    if value is None:
        monkeypatch.delenv(pf.SKIP_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(pf.SKIP_VARIABLE, value)
    assert pf.personal_files_skipped() is skipped
    problems: list = []
    layers = _personal_layers(tmp_path, problems)
    assert (layers == []) is skipped
