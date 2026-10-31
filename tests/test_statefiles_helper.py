"""`tests/statefiles.py`, the fixtures' one way to write a state file."""

from __future__ import annotations

from tcw.object_folders import STATE_FILES
from tcw.project_files import version_line
from tests.statefiles import (
    CAPABILITY_STATE, ITEM_STATE, TAXONOMY_STATE, read_state, write_state,
    write_state_data,
)


def test_a_mapping_gets_the_version_line(tmp_path):
    path = write_state(tmp_path / "a" / TAXONOMY_STATE, "name: x\n")
    assert path.read_text() == version_line() + "name: x\n"


def test_text_already_versioned_is_written_as_it_is(tmp_path):
    path = write_state(tmp_path / ITEM_STATE, "tcw-version: '3.0'\ntitle: x\n")
    assert path.read_text() == "tcw-version: '3.0'\ntitle: x\n"


def test_a_list_and_broken_text_are_written_as_they_are(tmp_path):
    assert write_state(tmp_path / "l.yaml", "- a\n").read_text() == "- a\n"
    assert write_state(tmp_path / "b.yaml", "a: [unclosed\n").read_text() == "a: [unclosed\n"


def test_bytes_that_are_not_utf8_are_written_as_they_are(tmp_path):
    assert write_state(tmp_path / "u.yaml", b"\xff\xfe").read_bytes() == b"\xff\xfe"


def test_an_empty_file_gets_the_version_line_alone(tmp_path):
    assert write_state(tmp_path / CAPABILITY_STATE).read_text() == version_line()


def test_write_and_read_a_mapping(tmp_path):
    path = write_state_data(tmp_path / CAPABILITY_STATE, {"name": "x", "Status": "Missing"})
    assert path.read_text().startswith(version_line())
    assert read_state(path) == {"name": "x", "Status": "Missing"}


def test_the_names_agree_with_the_code():
    assert (TAXONOMY_STATE, CAPABILITY_STATE, ITEM_STATE) == (
        STATE_FILES["taxonomy"], STATE_FILES["capabilities"], STATE_FILES["work"])
