"""State files replace `meta.yaml` and `item.yaml`, each with the version of
the TCW that wrote it (TCW-111 Design 1; AC 1, 2, 3 and 8), in a project
`demo` with a files-backend work store."""

from __future__ import annotations

import json
import re
from datetime import date

import pytest
import yaml

from tcw import __version__
from tests.objectcli import findings, item, obj, project, store, tcw  # noqa: F401
from tests.statefiles import CAPABILITY_STATE, ITEM_STATE, TAXONOMY_STATE

TODAY = date.today().isoformat()

#: TCW-106 Design 3.4's rows a-d, as a state file's first lines.
VERSION_ROWS = {
    "a": "name: X\n",
    "b": "tcw-version: 4\nname: X\n",
    "c": "tcw-version: '3.0'\nname: X\n",
    "d": "tcw-version: '99.1'\nname: X\n",
}


@pytest.fixture
def demo(tmp_path):
    return project(tmp_path, work={})


def first_line(path) -> str:
    return path.read_text().splitlines()[0]


# -- AC 1 -------------------------------------------------------------------------

def test_each_add_writes_its_state_file_with_the_version_first(tcw, demo):
    assert tcw(["taxonomy", "add", "Invoice"], demo).code == 0
    term = store(demo, "taxonomy") / "invoice"
    assert sorted(p.name for p in term.iterdir()) == ["description.md", TAXONOMY_STATE]
    assert first_line(term / TAXONOMY_STATE) == f"tcw-version: {__version__}"
    assert "id" not in yaml.safe_load((term / TAXONOMY_STATE).read_text())

    assert tcw(["capabilities", "add", "cli/x"], demo).code == 0
    cap = store(demo, "capabilities") / "cli" / "x"
    assert sorted(p.name for p in cap.iterdir()) == ["description.md", CAPABILITY_STATE]
    assert first_line(cap / CAPABILITY_STATE) == f"tcw-version: {__version__}"
    assert re.fullmatch(r"cap-[0-9a-f]{6}",
                        yaml.safe_load((cap / CAPABILITY_STATE).read_text())["id"])

    assert tcw(["work", "new", "Add login"], demo).code == 0
    folder = store(demo, "work") / f"{TODAY}-add-login"
    assert [p.name for p in folder.iterdir()] == [ITEM_STATE]
    assert first_line(folder / ITEM_STATE) == f"tcw-version: {__version__}"
    assert "id" not in yaml.safe_load((folder / ITEM_STATE).read_text())
    assert not list(demo.rglob("meta.yaml")) and not list(demo.rglob("item.yaml"))


def test_the_printed_version_is_the_one_written(tcw, demo):
    printed = tcw(["--version"], demo).out.split()[-1]
    tcw(["taxonomy", "add", "Invoice"], demo)
    assert first_line(store(demo, "taxonomy") / "invoice" / TAXONOMY_STATE) == \
        f"tcw-version: {printed}"


# -- AC 2 -------------------------------------------------------------------------

def test_edits_keep_the_version_line(tcw, demo, monkeypatch):
    cap = obj(demo, "capabilities", "cli/x", id="cap-aaaaaa", name="X", Status="Missing")
    work = item(demo, f"{TODAY}-x")
    for path in (cap / CAPABILITY_STATE, work / ITEM_STATE):
        path.write_text(path.read_text().replace(f"tcw-version: {__version__}",
                                                 "tcw-version: 4.0.0"))
    monkeypatch.setattr("tcw.project_files.__version__", "4.1.0")
    assert tcw(["capabilities", "set", "cli/x", "--status", "Supported"], demo).code == 0
    assert tcw(["work", "edit", f"{TODAY}-x", "--priority", "high"], demo).code == 0
    assert first_line(cap / CAPABILITY_STATE) == "tcw-version: 4.0.0"
    assert first_line(work / ITEM_STATE) == "tcw-version: 4.0.0"
    assert "Status: Supported" in (cap / CAPABILITY_STATE).read_text()
    assert "priority: high" in (work / ITEM_STATE).read_text()


# -- AC 3 -------------------------------------------------------------------------

@pytest.mark.parametrize("row", sorted(VERSION_ROWS))
def test_a_capability_whose_version_cannot_be_read(tcw, demo, row):
    obj(demo, "capabilities", "cli/w", id="cap-bbbbbb", name="W", Status="Missing")
    cap = obj(demo, "capabilities", "cli/x", id="cap-aaaaaa", name="X", Status="Missing")
    path = cap / CAPABILITY_STATE
    path.write_text(VERSION_ROWS[row] + "id: cap-aaaaaa\nStatus: Missing\n")
    before = path.read_bytes()

    checked = tcw(["validate"], demo)
    assert checked.code == 1
    assert any(CAPABILITY_STATE in line and "tcw-version" in line
               and line.startswith("error:") for line in findings(checked)), checked.out

    for argv in (["capabilities", "show", "cli/x"],
                 ["capabilities", "set", "cli/x", "--status", "Supported"]):
        r = tcw(argv, demo)
        assert r.code == 1, (argv, r)
        assert path.read_bytes() == before

    listed = tcw(["capabilities", "list"], demo)
    assert listed.code == 1
    assert listed.out == "demo.capabilities/cli/w\n"
    assert CAPABILITY_STATE in listed.err and "cli/x" in listed.err
    as_json = tcw(["capabilities", "list", "--json"], demo)
    assert as_json.code == 1
    assert [r["full-id"] for r in json.loads(as_json.out)["capabilities"]] == \
        ["demo.capabilities/cli/w"]


@pytest.mark.parametrize("row", sorted(VERSION_ROWS))
def test_a_term_whose_version_cannot_be_read_is_left_out(tcw, demo, row):
    obj(demo, "taxonomy", "good", name="Good")
    term = obj(demo, "taxonomy", "bad", name="Bad")
    (term / TAXONOMY_STATE).write_text(VERSION_ROWS[row])
    listed = tcw(["taxonomy", "list"], demo)
    assert (listed.code, listed.out) == (1, "demo.taxonomy/good\n")
    assert TAXONOMY_STATE in listed.err
    assert tcw(["taxonomy", "show", "bad"], demo).code == 1


@pytest.mark.parametrize("row", sorted(VERSION_ROWS))
def test_an_item_whose_version_cannot_be_read(tcw, demo, row):
    folder = item(demo, f"{TODAY}-x")
    (folder / ITEM_STATE).write_text(VERSION_ROWS[row].replace("name: X", "title: x")
                                     + "stage: request\n")
    shown = tcw(["work", "show", f"{TODAY}-x"], demo)
    assert shown.code == 1 and ITEM_STATE in shown.err
    listed = tcw(["work", "list"], demo)
    assert listed.code == 1 and ITEM_STATE in listed.err
    if row == "d":
        assert "unknown key" not in shown.err


# -- AC 8 -------------------------------------------------------------------------

def test_an_id_must_be_the_folder_name(tcw, demo):
    folder = item(demo, f"{TODAY}-x", id=f"{TODAY}-x")
    assert tcw(["validate"], demo).code == 0
    item(demo, f"{TODAY}-x", id="other")
    checked = tcw(["validate"], demo)
    assert checked.code == 1
    assert any(ITEM_STATE in line and "id 'other'" in line for line in findings(checked))
    assert tcw(["work", "show", f"{TODAY}-x"], demo).code == 0
    assert folder.is_dir()


def test_a_term_id_must_be_the_folder_name(tcw, demo):
    obj(demo, "taxonomy", "invoice", name="Invoice", id="invoice")
    assert tcw(["validate"], demo).code == 0
    obj(demo, "taxonomy", "invoice", name="Invoice", id="bill")
    checked = tcw(["validate"], demo)
    assert checked.code == 1 and any("id 'bill'" in f for f in findings(checked))


def test_an_edit_keeps_a_hand_written_id(tcw, demo):
    folder = item(demo, f"{TODAY}-x", id=f"{TODAY}-x")
    assert tcw(["work", "edit", f"{TODAY}-x", "--priority", "high"], demo).code == 0
    assert yaml.safe_load((folder / ITEM_STATE).read_text())["id"] == f"{TODAY}-x"
