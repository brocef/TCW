"""Taxonomy entries and capabilities are printed by full identifier (TCW-110
Design 4, AC 4, 5 and 6): a project `demo` with a term `term` and a
capability `cli/x`, inheriting both trees from a project `core`."""

from __future__ import annotations

import io
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from tcw.cli import main
from tests.fullids import fid
from tests.inherit import demo_inheriting_core, entry
from tests.work.projects import make_project


@dataclass
class Result:
    code: int
    out: str
    err: str


@pytest.fixture
def tcw(monkeypatch, capsys):
    def run(argv, cwd, stdin=""):
        monkeypatch.chdir(cwd)
        monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))
        try:
            code = main(argv)
        except SystemExit as stop:
            code = stop.code if isinstance(stop.code, int) else 1
        captured = capsys.readouterr()
        return Result(code, captured.out, captured.err)
    return run


@pytest.fixture
def demo(tmp_path) -> Path:
    return demo_inheriting_core(tmp_path)


def test_ac4_list_prints_full_identifiers_own_entries_first(tcw, demo):
    assert tcw(["taxonomy", "list"], demo).out.splitlines() == [
        fid("demo", "taxonomy", "term"), fid("core", "taxonomy", "shared")]
    assert tcw(["capabilities", "list"], demo).out.splitlines() == [
        fid("demo", "capabilities", "cli/x"), fid("core", "capabilities", "cli/y")]


def test_ac4_add_prints_the_new_full_identifier(tcw, demo):
    assert tcw(["taxonomy", "add", "Invoice"], demo).out == "demo.taxonomy/invoice\n"
    assert tcw(["capabilities", "add", "cli/z"], demo).out == "demo.capabilities/cli/z\n"


@pytest.mark.parametrize("command, full_id", [
    (["taxonomy", "show", "term"], "demo.taxonomy/term"),
    (["capabilities", "show", "cli/x"], "demo.capabilities/cli/x"),
])
def test_ac5_show_starts_with_full_id_and_owner(tcw, demo, command, full_id):
    lines = tcw(command, demo).out.splitlines()
    assert lines[:2] == [f"full-id: {full_id}", "owner: demo"]
    assert not any(line.startswith(("path:", "origin:")) for line in lines)


def test_ac5_an_inherited_entry_shows_its_owner(tcw, demo):
    lines = tcw(["capabilities", "show", "core.capabilities/cli/y"], demo).out.splitlines()
    assert lines[:2] == ["full-id: core.capabilities/cli/y", "owner: core"]


@pytest.mark.parametrize("command, key", [
    (["taxonomy", "list", "--json"], "terms"),
    (["capabilities", "list", "--json"], "capabilities"),
    (["taxonomy", "show", "term", "--json"], "term"),
    (["capabilities", "show", "cli/x", "--json"], "capability"),
])
def test_ac6_json_records_carry_full_id_and_owner(tcw, demo, command, key):
    document = json.loads(tcw(command, demo).out)
    assert document["schema"] == 2
    records = document[key] if isinstance(document[key], list) else [document[key]]
    for record in records:
        assert {"full-id", "owner"} <= set(record)
        assert not {"path", "origin", "slug"} & set(record)
        assert record["full-id"].startswith(f"{record['owner']}.")


@pytest.mark.parametrize("command", [
    ["taxonomy", "list"], ["taxonomy", "show"], ["taxonomy", "search"],
    ["capabilities", "list"], ["capabilities", "show"], ["capabilities", "search"],
])
def test_ac6_help_shows_schema_2_and_no_3x_wording(tcw, demo, command):
    out = tcw([*command, "--help"], demo).out
    assert '"schema": 2' in out
    assert "qualified path" not in out and "full slug" not in out


# -- what commands accept (TCW-110 Design 3, Step 8) ------------------------------------


def test_ac7_a_full_identifier_and_an_id_path_show_the_same_capability(tcw, demo):
    by_id = tcw(["capabilities", "show", "demo.capabilities/cli/x"], demo)
    by_path = tcw(["capabilities", "show", "cli/x"], demo)
    by_address = tcw(["capabilities", "show", "tcw://demo.capabilities/cli/x"], demo)
    assert by_id.code == by_path.code == by_address.code == 0, by_id.err
    assert by_id.out == by_path.out == by_address.out


def test_ac7_another_namespace_is_a_usage_error_naming_the_one_expected(tcw, demo):
    found = tcw(["capabilities", "show", "demo.taxonomy/term"], demo)
    assert found.code == 2
    assert "capabilities" in found.err and "taxonomy" in found.err


def test_ac13a_an_id_nothing_knows_exits_1_saying_check_the_spelling(tcw, demo):
    found = tcw(["taxonomy", "show", "cor.taxonomy/term"], demo)
    assert found.code == 1
    assert "check the spelling" in found.err


def test_ac13a_two_folders_declaring_one_id_exit_1(tcw, demo, tmp_path):
    make_project(tmp_path, "lib")
    make_project(tmp_path, "lib", name="lib-copy")
    found = tcw(["taxonomy", "show", "lib.taxonomy/term"], demo)
    assert found.code == 1, found.err
    assert "check the spelling" not in found.err


def test_the_3x_hint_names_the_full_identifier_to_write(tcw, demo):
    found = tcw(["capabilities", "show", "core/cli/y"], demo)
    assert found.code == 4
    assert "to name an object in project 'core', write core.capabilities/cli/y" \
        in found.err


def test_the_3x_hint_is_left_out_for_a_project_nothing_finds(tcw, demo):
    found = tcw(["capabilities", "show", "cli/nope"], demo)
    assert found.code == 4
    assert "no such capability: 'cli/nope'" in found.err
    assert "to name an object" not in found.err


def test_looking_for_the_3x_hint_never_changes_the_exit(tcw, demo, tmp_path):
    """Two folders declaring `cli` make the lookup a graph problem (exit 1
    elsewhere); here it only means no hint."""
    make_project(tmp_path, "cli")
    make_project(tmp_path, "cli", name="cli-copy")
    found = tcw(["capabilities", "show", "cli/nope"], demo)
    assert found.code == 4, found.err
    assert "to name an object" not in found.err


def test_ac18_a_name_breaking_the_rule_is_refused_and_writes_nothing(tcw, demo):
    found = tcw(["capabilities", "add", "cli/has.dot"], demo)
    assert found.code == 2
    assert not (demo / "docs" / "capabilities" / "cli" / "has.dot").exists()
    assert tcw(["taxonomy", "add", "Dotted", "--parent", "te.rm"], demo).code == 2


def test_ac18_a_hand_made_folder_breaking_the_rule_is_listed_and_reported(tcw, demo):
    entry(demo, "capabilities", "cli/has.dot", id="cap-dot", Status="Missing")
    assert "demo.capabilities/cli/has.dot" in tcw(["capabilities", "list"], demo).out
    checked = tcw(["validate"], demo)
    assert checked.code == 1
    [line] = [line for line in checked.out.splitlines() if "has.dot" in line]
    assert line.startswith("error: ")
    assert "rename it by hand" in line and "letters, digits" in line
    for argv in (["show", "cli/has.dot"], ["set", "cli/has.dot", "--field", "Status=Partial"],
                 ["rm", "cli/has.dot"], ["show", "demo.capabilities/cli/has.dot"],
                 ["show", "tcw://demo.capabilities/cli/has.dot"],
                 ["set", "tcw://demo.capabilities/cli/has.dot", "--field", "Status=Partial"],
                 ["rm", "tcw://demo.capabilities/cli/has.dot"]):
        refused = tcw(["capabilities", *argv], demo)
        assert refused.code == 2, refused.err
        assert "letters, digits" in refused.err and "rename it by hand" in refused.err
        assert "or its id-path" not in refused.err
    assert (demo / "docs" / "capabilities" / "cli" / "has.dot" / "meta.yaml").is_file()
    entry(demo, "taxonomy", "has.dot")
    for argv in (["show", "has.dot"], ["rm", "has.dot"]):
        refused = tcw(["taxonomy", *argv], demo)
        assert refused.code == 2, refused.err
        assert "names no term" in refused.err and "rename it by hand" in refused.err
    for argv in (["show", "tcw://demo.taxonomy/has.dot"],
                 ["rm", "tcw://demo.taxonomy/has.dot"]):
        refused = tcw(["taxonomy", *argv], demo)
        assert refused.code == 2, refused.err
        assert "letters, digits" in refused.err and "rename it by hand" in refused.err
    assert (demo / "docs" / "taxonomy" / "has.dot").is_dir()


def _overridden(demo: Path) -> Path:
    """`demo`'s 3.x override of `core`'s `cli/y`, setting `Omitted`."""
    entry(demo, "capabilities", "ov/y", overrides="core/cap-y", Status="Omitted")
    return demo.parent / "core" / "docs" / "capabilities" / "cli" / "y" / "meta.yaml"


def test_ac23_an_inherited_capability_is_read_through_this_projects_view(tcw, demo):
    _overridden(demo)
    listed = json.loads(tcw(["capabilities", "list", "--json"], demo).out)
    [y] = [c for c in listed["capabilities"] if c["full-id"] == "core.capabilities/cli/y"]
    assert y["status"] == "Omitted"
    shown = json.loads(tcw(["capabilities", "show", "core.capabilities/cli/y", "--json"],
                           demo).out)
    assert shown["capability"]["status"] == "Omitted"


def test_ac23_set_of_an_inherited_capability_changes_the_override_only(tcw, demo):
    upstream = _overridden(demo)
    before = upstream.read_bytes()
    found = tcw(["capabilities", "set", "core.capabilities/cli/y", "--status", "Partial"],
                demo)
    assert found.code == 0, found.err
    override = demo / "docs" / "capabilities" / "ov" / "y" / "meta.yaml"
    assert "Partial" in override.read_text()
    assert upstream.read_bytes() == before


@pytest.mark.parametrize("typed", ["Cli/x", "demo.capabilities/Cli/x"])
def test_ac25_letter_case_is_compared_exactly(tcw, demo, typed):
    found = tcw(["capabilities", "show", typed], demo)
    assert found.code == 4
    assert "spelled cli/x" in found.err


def test_a_project_this_one_does_not_inherit_from_refuses_writes(tcw, demo):
    tcw(["capabilities", "extends", "rm", "core"], demo)
    shown = tcw(["capabilities", "show", "core.capabilities/cli/y"], demo)
    assert shown.code == 0, shown.err
    assert shown.out.splitlines()[:2] == ["full-id: core.capabilities/cli/y", "owner: core"]
    found = tcw(["capabilities", "set", "core.capabilities/cli/y", "--status", "Partial"],
                demo)
    assert found.code == 3
    assert "belongs to project 'core'" in found.err
