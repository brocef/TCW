"""The project's own files (TCW-106): where they are, the version every
`tcw-*.yaml` file records, and the naming rule for keys.

Unit tests of `tcw.project_files`; the commands built on it are tested in
`tests/test_project_files_cli.py`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import tcw
from tcw import project_files as pf


def _running(major_offset: int = 0, minor_offset: int = 0) -> str:
    major, minor, *_ = (int(p) for p in tcw.__version__.split("."))
    return f"{major + major_offset}.{minor + minor_offset}.0"


# ---------------------------------------------------------------------------
# Finding the nearest marker (spec Design 2)


def _v4(root: Path) -> Path:
    (root / ".tcw").mkdir(parents=True, exist_ok=True)
    (root / ".tcw" / "tcw-config.yaml").write_text(pf.version_line() + "id: x\n")
    return root


def _v3(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "tcw-config.yaml").write_text("id: x\n")
    return root


def test_a_4_0_project_is_found_from_a_subfolder(tmp_path):
    root = _v4(tmp_path / "p")
    (root / "a" / "b").mkdir(parents=True)
    assert pf.find_marker(root / "a" / "b") == (root.resolve(), "4")


def test_a_3_x_project_is_found_as_3_x(tmp_path):
    root = _v3(tmp_path / "p")
    assert pf.find_marker(root) == (root.resolve(), "3")


def test_a_folder_holding_both_is_4_0(tmp_path):
    root = _v3(_v4(tmp_path / "p"))
    assert pf.find_marker(root) == (root.resolve(), "4")


def test_a_tcw_folder_without_its_file_is_no_project(tmp_path):
    (tmp_path / "p" / ".tcw").mkdir(parents=True)
    assert pf.find_marker(tmp_path / "p") is None


def test_the_nearest_marker_wins(tmp_path):
    outer = _v4(tmp_path / "outer")
    inner = _v3(outer / "inner")
    assert pf.find_marker(inner) == (inner.resolve(), "3")
    nested = _v4(_v3(tmp_path / "old") / "new")
    assert pf.find_marker(nested) == (nested.resolve(), "4")


def test_inside_the_tcw_folder_the_project_is_its_parent(tmp_path):
    """`.tcw/` holds `tcw-config.yaml` and no `.tcw/` of its own, which would
    read as a 3.x project if the folder's name were not checked."""
    root = _v4(tmp_path / "p")
    assert pf.find_marker(root / ".tcw") == (root.resolve(), "4")


def test_root_of_a_config_path_is_the_folder_holding_tcw(tmp_path):
    assert pf.root_of(tmp_path / ".tcw" / "tcw-config.yaml") == tmp_path
    assert pf.root_of(tmp_path / ".tcw" / "tcw-config.local.yaml") == tmp_path
    assert tmp_path / pf.SENTINEL == tmp_path / ".tcw" / "tcw-config.yaml"


# ---------------------------------------------------------------------------
# The version (spec Design 3.4)


def _problem(text: str) -> str | None:
    return pf.version_problem(yaml.safe_load(text))


def test_a_missing_version_is_read_as_3_x():
    problem = _problem("id: x\n")
    assert problem and "has no tcw-version" in problem and "tcw migrate" in problem
    assert f"tcw-version: {tcw.__version__}" in problem


@pytest.mark.parametrize("value", ["4.0", "4", "true", "four", "4.0.0-rc1", "v4.0.0"])
def test_a_version_not_written_as_text_of_the_form_is_refused(value):
    problem = _problem(f"tcw-version: {value}\n")
    assert problem and "must be a TCW version written as text" in problem, value


@pytest.mark.parametrize("value", ['"4.0"', "4.0.0", f"{_running()}"])
def test_a_version_at_or_below_the_running_one_is_read(value):
    assert _problem(f"tcw-version: {value}\nid: x\n") is None


def test_a_version_anywhere_at_the_top_level_is_read():
    assert _problem(f"id: x\ntcw-version: {tcw.__version__}\n") is None


def test_a_3_x_version_names_migrate():
    problem = _problem("tcw-version: 3.0.2\n")
    assert problem and "format of TCW 3.0" in problem and "tcw migrate" in problem


@pytest.mark.parametrize("value", [_running(minor_offset=1), _running(major_offset=1)])
def test_a_newer_version_names_an_upgrade(value):
    problem = _problem(f"tcw-version: {value}\n")
    assert problem and "newer than this TCW" in problem and "upgrade" in problem


def test_a_newer_patch_is_read():
    major, minor, *_ = tcw.__version__.split(".")
    assert _problem(f"tcw-version: {major}.{minor}.99\n") is None


def test_the_version_line_is_the_running_version():
    assert pf.version_line() == f"tcw-version: {tcw.__version__}\n"


# ---------------------------------------------------------------------------
# The naming rule (spec Design 5)


def _keys(text: str) -> list:
    return pf.key_problems(yaml.safe_load(text))


@pytest.mark.parametrize("key", ["Work", "my_key", "a--b", "-a", "a-", "a b"])
def test_a_badly_named_key_is_a_problem(key):
    found = _keys(f"work:\n  '{key}': 1\n")
    assert [path for path, _ in found] == [("work", key)], found
    assert "lowercase letters and digits joined by single hyphens" in found[0][1]


def test_well_named_keys_pass():
    assert _keys("tcw-version: 4.0.0\nid: x\nwork:\n  output-cap: 1\n  a1-b2: x\n") == []


def test_not_tags_names_its_replacement():
    found = _keys("work:\n  stages:\n    spec:\n      prompt:\n"
                  "      - file: x.md\n        when:\n          not_tags: [bug]\n")
    assert [path for path, _ in found] == [
        ("work", "stages", "spec", "prompt", 0, "when", "not_tags")], found
    assert "write 'not-tags'" in found[0][1]


@pytest.mark.parametrize("text", ["on: 1\n", "1: x\n"])
def test_a_key_that_is_not_text_is_a_problem(text):
    found = _keys(text)
    assert len(found) == 1 and "must be text" in found[0][1], found


def test_values_are_not_checked():
    assert _keys("work:\n  tags: [My_Tag]\n  backend: Jira_X\n") == []
