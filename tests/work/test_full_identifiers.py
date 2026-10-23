"""Work items are named by their full identifier (TCW-110 Design 1, 3, 4, 5):
`<project>.work/<folder>` is what every command prints, what every record
carries, and what `item.yaml` stores, in a files-backend project `demo`."""

from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pytest
import yaml

from tcw.cli import main
from tests.fullids import addr, wid
from tests.work.projects import make_project, write_item

TODAY = date.today().isoformat()
REPO = Path(__file__).resolve().parents[2]


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
def demo(tmp_path):
    return make_project(tmp_path, "demo", config={})


def _new(tcw, root, title) -> str:
    r = tcw(["work", "new", title], root)
    assert r.code == 0, r.err
    return r.out.strip()


def _item_yaml(root, folder):
    return yaml.safe_load((root / "docs" / "work" / folder / "item.yaml").read_text())


def test_ac4_new_and_list_print_the_full_identifier(tcw, demo):
    made = _new(tcw, demo, "Add login")
    folder = f"{TODAY}-add-login"
    assert made == wid("demo", folder) == f"demo.work/{folder}"
    assert tcw(["work", "list"], demo).out == f"demo.work/{folder}\n"


def test_ac5_show_starts_with_full_id_and_owner(tcw, demo):
    _new(tcw, demo, "Add login")
    lines = tcw(["work", "show", f"{TODAY}-add-login"], demo).out.splitlines()
    assert lines[0] == f"full-id: demo.work/{TODAY}-add-login"
    assert lines[1] == "owner: demo"
    assert not any(line.startswith("slug:") for line in lines)


def test_ac6_json_is_schema_2_with_full_ids(tcw, demo):
    parent = _new(tcw, demo, "Epic")
    child = _new(tcw, demo, "Part")
    blocker = _new(tcw, demo, "First")
    child_folder = child.partition("/")[2]
    assert tcw(["work", "edit", child_folder, "--parent", parent,
                "--blocked-by", blocker.partition("/")[2]], demo).code == 0
    listed = json.loads(tcw(["work", "list", "--json"], demo).out)
    assert listed["schema"] == 2
    for record in listed["items"]:
        assert {"full-id", "owner"} <= set(record) and "slug" not in record
        assert record["owner"] == "demo"
    shown = json.loads(tcw(["work", "show", child_folder, "--json"], demo).out)
    assert shown["schema"] == 2
    item = shown["item"]
    assert item["full-id"] == child and "slug" not in item
    assert (item["parent"], item["blocked-by"]) == (parent, [blocker])
    parent_record = json.loads(tcw(["work", "show", parent, "--json"], demo).out)["item"]
    assert parent_record["children"] == [child]
    blocker_record = json.loads(tcw(["work", "show", blocker, "--json"], demo).out)["item"]
    assert blocker_record["blocks"] == [child]


def test_ac6_work_help_shows_schema_2(tcw, demo):
    for command in (["list"], ["show"]):
        r = tcw(["work", *command, "--help"], demo)
        assert '"schema": 1' not in r.out and "full slug" not in r.out
    assert '"schema": 2' in tcw(["work", "list", "--help"], demo).out


def test_ac8_a_bare_folder_is_stored_as_a_full_identifier(tcw, demo):
    other = _new(tcw, demo, "Other").partition("/")[2]
    item = _new(tcw, demo, "Item").partition("/")[2]
    assert tcw(["work", "edit", item, "--parent", other, "--blocked-by", other],
               demo).code == 0
    stored = _item_yaml(demo, item)
    assert stored["parent"] == wid("demo", other)
    assert stored["blocked-by"] == [wid("demo", other)]


def test_ac7_a_full_identifier_and_a_folder_name_show_the_same_item(tcw, demo):
    made = _new(tcw, demo, "Add login")
    folder = made.partition("/")[2]
    by_id = tcw(["work", "show", made], demo)
    by_folder = tcw(["work", "show", folder], demo)
    assert by_id.code == by_folder.code == 0
    assert by_id.out == by_folder.out


def test_ac11_a_3x_parent_makes_the_item_unreadable_naming_tcw_migrate(tcw, demo):
    folder = f"{TODAY}-x"
    write_item(demo, folder, {"title": "X", "stage": "request",
                              "parent": f"demo/{TODAY}-y"})
    shown = tcw(["work", "show", folder], demo)
    assert shown.code != 0
    assert "parent" in shown.err and "tcw migrate" in shown.err
    checked = tcw(["validate"], demo)
    assert checked.code == 1
    assert "parent" in checked.out + checked.err
    assert "tcw migrate" in checked.out + checked.err


def _bound(root, stages):
    path = root / ".tcw" / "tcw-config.yaml"
    document = yaml.safe_load(path.read_text())
    document.setdefault("work", {})["stages"] = stages
    path.write_text(yaml.safe_dump(document, sort_keys=False))


def test_ac19_a_pre_command_sees_the_full_identifier(tcw, demo, tmp_path):
    seen = tmp_path / "seen.txt"
    _bound(demo, {"spec": {"pre": [{"command": f'printf "%s" "$TCW_SLUG" > {seen}'}]}})
    made = _new(tcw, demo, "Add login")
    assert tcw(["work", "advance", made], demo).code == 0
    assert seen.read_text() == made == wid("demo", f"{TODAY}-add-login")


def test_ac19_the_stage_prompt_names_the_full_identifier(tcw, demo):
    made = _new(tcw, demo, "Add login")
    folder = made.partition("/")[2]
    text = tcw(["work", "stage", "prompt", "spec", folder], demo).out
    assert made in text
    assert f"demo/{folder}" not in text


def test_ac19_a_generate_binding_gets_schema_2_and_the_marker_follows(tcw, demo, tmp_path):
    saved = tmp_path / "payload.json"
    _bound(demo, {"spec": {"prompt": [{"generate": f"cat > {saved}; printf ok"}]}})
    made = _new(tcw, demo, "Add login")
    folder = made.partition("/")[2]
    assert tcw(["work", "stage", "prompt", "spec", folder], demo).code == 0
    payload = json.loads(saved.read_text())
    assert payload["schema"] == 2
    assert payload["item"]["full-id"] == made and "slug" not in payload["item"]
    generator = REPO / "evals" / "assets" / "gen_requirement.py"
    out = subprocess.run([sys.executable, str(generator)], input=saved.read_text(),
                         capture_output=True, text=True, check=True).stdout
    expected = hashlib.sha256(f"__SEED__:{made}".encode()).hexdigest()[:16]
    assert f"Round marker: {expected}" in out


def test_an_address_names_the_item_too(tcw, demo):
    made = _new(tcw, demo, "Add login")
    folder = made.partition("/")[2]
    assert tcw(["work", "show", addr("demo", "work", folder)], demo).out == \
        tcw(["work", "show", folder], demo).out
