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
from tests.inherit import demo_inheriting_core


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
    lines = tcw(["capabilities", "show", "core/cli/y"], demo).out.splitlines()
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
