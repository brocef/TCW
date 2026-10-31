"""References stored in taxonomy entries and capabilities are full
identifiers (TCW-110 Design 5.1, 5.2, 5.3, 6, AC 8, 11): a project `demo`
with the term `term`, the feature `pay-feature`, and the capabilities
`cli/x` and `roles/admin`, beside a project `core` holding the term `term`
that `demo` names as a parent passing nothing (`inherit: none`) and does not
inherit from."""

from __future__ import annotations

import io
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from tcw.cli import main
from tcw.store.fs import init
from tests.fullids import fid
from tests.inherit import entry
from tests.projectfiles import connect_projects
from tests.work.projects import make_project
from tests.statefiles import (write_state, CAPABILITY_STATE, STATE_OF, TAXONOMY_STATE)


@dataclass
class Result:
    code: int
    out: str
    err: str


@pytest.fixture
def tcw(monkeypatch, capsys):
    def run(argv, cwd):
        monkeypatch.chdir(cwd)
        monkeypatch.setattr(sys, "stdin", io.StringIO(""))
        try:
            code = main(argv)
        except SystemExit as stop:
            code = stop.code if isinstance(stop.code, int) else 1
        captured = capsys.readouterr()
        return Result(code, captured.out, captured.err)
    return run


@pytest.fixture
def demo(tmp_path) -> Path:
    demo = make_project(tmp_path, "demo", config={})
    core = make_project(tmp_path, "core", config={})
    for root in (demo, core):
        init(["taxonomy", "capabilities"], root)
        entry(root, "taxonomy", "term", kind="Vocabulary")
    entry(demo, "taxonomy", "pay-feature", kind="Feature",
          vocabulary=[fid("demo", "taxonomy", "term")])
    entry(demo, "capabilities", "cli/x", Status="Supported")
    entry(demo, "capabilities", "roles/admin", Status="Supported")
    connect_projects(demo, "parent", "core", inherit="none")
    return demo


def _meta(root: Path, tree: str, path: str) -> dict:
    return yaml.safe_load((root / "docs" / tree / path / STATE_OF[tree]).read_text())


def _set(root: Path, path: str, **fields) -> None:
    meta_path = root / "docs" / "capabilities" / path / CAPABILITY_STATE
    meta = yaml.safe_load(meta_path.read_text())
    meta.update(fields)
    write_state(meta_path, yaml.safe_dump(meta))


def test_ac8_set_stores_the_full_identifier_of_a_subject(tcw, demo):
    found = tcw(["capabilities", "set", "cli/x", "--field", "Subject=term"], demo)
    assert found.code == 0, found.err
    assert _meta(demo, "capabilities", "cli/x")["Subject"] == ["demo.taxonomy/term"]


def test_ac8_add_stores_the_full_identifier_of_a_vocabulary_entry(tcw, demo):
    found = tcw(["taxonomy", "add", "Pay", "--kind", "feature", "--vocab", "term"], demo)
    assert found.code == 0, found.err
    assert _meta(demo, "taxonomy", "pay")["vocabulary"] == ["demo.taxonomy/term"]


@pytest.mark.parametrize("tree, path, field, value, namespace", [
    ("capabilities", "cli/x", "Subject", ["term"], "taxonomy"),
    ("capabilities", "cli/x", "Feature", "pay-feature", "taxonomy"),
    ("capabilities", "cli/x", "Roles", "roles/admin", "capabilities"),
    ("capabilities", "cli/x", "Blocked by", "roles/admin", "capabilities"),
    ("taxonomy", "term", "relatesTo", ["pay-feature"], "taxonomy"),
])
def test_ac11_validate_reports_a_3x_value_naming_the_field_and_tcw_migrate(
        tcw, demo, tree, path, field, value, namespace):
    meta_path = demo / "docs" / tree / path / STATE_OF[tree]
    meta = yaml.safe_load(meta_path.read_text())
    meta[field] = value
    write_state(meta_path, yaml.safe_dump(meta))
    checked = tcw(["validate"], demo)
    assert checked.code == 1
    [line] = [line for line in checked.out.splitlines() if field in line]
    assert line.startswith("error: ")
    assert "TCW 3.x reference" in line and "tcw migrate" in line
    assert f"<project>.{namespace}/<id-path>" in line


def test_a_reference_into_a_project_not_inherited_from_is_checked(tcw, demo):
    """TCW-99 principle 1: naming is not inheriting (Design 6.2)."""
    _set(demo, "cli/x", Subject=[fid("core", "taxonomy", "term")])
    assert tcw(["validate"], demo).code == 0
    _set(demo, "cli/x", Subject=[fid("core", "taxonomy", "missing")])
    checked = tcw(["validate"], demo)
    assert checked.code == 1
    assert "dangling ref 'core.taxonomy/missing'" in checked.out


def test_a_reference_into_a_project_not_on_this_machine_is_unresolved(tcw, demo):
    _set(demo, "cli/x", Subject=[fid("core", "taxonomy", "term")])
    shutil.rmtree(demo.parent / "core")
    checked = tcw(["validate"], demo)
    assert checked.code == 0, checked.out
    [line] = [line for line in checked.out.splitlines() if "core.taxonomy/term" in line]
    assert line.startswith("unresolved: ")


def test_a_reference_naming_an_unknown_project_is_an_error(tcw, demo):
    _set(demo, "cli/x", Subject=[fid("cor", "taxonomy", "term")])
    checked = tcw(["validate"], demo)
    assert checked.code == 1
    assert "check the spelling" in checked.out


def test_a_negated_role_keeps_its_negation_and_is_checked(tcw, demo):
    admin = fid("demo", "capabilities", "roles/admin")
    found = tcw(["capabilities", "set", "cli/x", "--field", "Roles=!roles/admin"], demo)
    assert found.code == 0, found.err
    assert _meta(demo, "capabilities", "cli/x")["Roles"] == f"!{admin}"
    assert tcw(["validate"], demo).code == 0
    _set(demo, "cli/x", Roles=f"!{fid('demo', 'capabilities', 'roles/ghost')}")
    checked = tcw(["validate"], demo)
    assert checked.code == 1
    assert "Roles → dangling identifier 'demo.capabilities/roles/ghost'" in checked.out


def test_a_reference_to_another_projects_entry_does_not_block_a_removal(tcw, demo):
    """Only this project's own entry is what `rm` compares a reference with:
    `core.taxonomy/term` is not `demo.taxonomy/term`."""
    core_term = fid("core", "taxonomy", "term")
    meta = demo / "docs" / "taxonomy" / "pay-feature" / TAXONOMY_STATE
    write_state(meta, yaml.safe_dump({"name": "Pay", "kind": "Feature",
                                    "vocabulary": [core_term]}))
    _set(demo, "cli/x", Subject=[core_term])
    removed = tcw(["taxonomy", "rm", "term"], demo)
    assert removed.code == 0, removed.err
    assert not (demo / "docs" / "taxonomy" / "term").exists()


@pytest.mark.parametrize("field, value", [("Roles", "cli/x"), ("When", "!roles/admin")])
def test_a_role_or_condition_outside_its_folder_is_refused(tcw, demo, field, value):
    before = (demo / "docs" / "capabilities" / "cli" / "x" / CAPABILITY_STATE).read_bytes()
    found = tcw(["capabilities", "set", "cli/x", "--field", f"{field}={value}"], demo)
    assert found.code == 2
    folder = "roles" if field == "Roles" else "conditions"
    assert f"{field} '{value}' must be a {folder}/ slug" in found.err
    assert (demo / "docs" / "capabilities" / "cli" / "x" / CAPABILITY_STATE).read_bytes() == before
