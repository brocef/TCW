"""`tcw work rename` and `tcw work move`, files backend (TCW-114 Design 5, 6,
7.2; AC 11, AC 13, AC 14, AC 18, AC 25; plan Steps 17 and 18)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml

from tests.objectcli import findings, item, project, tcw  # noqa: F401
from tests.statefiles import ITEM_STATE, read_state, write_state

D = "2026-10-22"
EPIC = f"{D}-old-words"
NEW = f"{D}-new-words"
P = f"{D}-p"
Q = f"{D}-q"
R = f"{D}-r"


def wid(id_path: str) -> str:
    return f"demo.work/{id_path}"


def make_demo(tmp_path):
    root = project(tmp_path, "demo", work={})
    item(root, EPIC, "Epic")
    item(root, f"{EPIC}/{P}", "P", parent=wid(EPIC))
    item(root, f"{EPIC}/{P}/{Q}", "Q", parent=wid(f"{EPIC}/{P}"))
    item(root, R, "R", **{"blocked-by": [wid(f"{EPIC}/{P}")]})
    item(root, f"{EPIC}-two", "Two")
    spec = root / "docs/work" / R / "spec/spec.md"
    spec.parent.mkdir(parents=True)
    spec.write_text(f"First [p](tcw://{wid(EPIC + '/' + P)}).\n"
                    "```\n"
                    f"[p](tcw://{wid(EPIC + '/' + P)})\n"
                    "```\n"
                    f"Other [two](tcw://{wid(EPIC + '-two')}).\n"
                    f"Prose names {wid(EPIC + '/' + P)} here.\n")
    return root


@pytest.fixture
def demo(tmp_path):
    return make_demo(tmp_path)


def state(root, id_path):
    return read_state(root / "docs/work" / id_path / ITEM_STATE)


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file() and ".git" not in p.parts}


def three_lines():
    return [f"{wid(EPIC)} -> {wid(NEW)}",
            f"{wid(EPIC + '/' + P)} -> {wid(NEW + '/' + P)}",
            f"{wid(EPIC + '/' + P + '/' + Q)} -> {wid(NEW + '/' + P + '/' + Q)}"]


# -- AC 11 --------------------------------------------------------------------------------


def test_ac11_a_rename_carries_the_nested_items(tcw, demo):
    result = tcw(["work", "rename", EPIC, "new-words"], demo)
    assert result.code == 0, result.err
    assert result.out.splitlines() == three_lines()
    assert state(demo, f"{NEW}/{P}")["parent"] == wid(NEW)
    assert state(demo, f"{NEW}/{P}/{Q}")["parent"] == wid(f"{NEW}/{P}")
    assert state(demo, R)["blocked-by"] == [wid(f"{NEW}/{P}")]
    spec = (demo / "docs/work" / R / "spec/spec.md").read_text()
    assert spec == (f"First [p](tcw://{wid(NEW + '/' + P)}).\n"
                    "```\n"
                    f"[p](tcw://{wid(EPIC + '/' + P)})\n"
                    "```\n"
                    f"Other [two](tcw://{wid(EPIC + '-two')}).\n"
                    f"Prose names {wid(EPIC + '/' + P)} here.\n")
    said = [line for line in result.err.splitlines() if "not rewritten" in line
            and "spec.md" in line]
    assert [line.split("spec.md:")[1].split(":")[0] for line in said] == ["3", "6"]
    assert len(said) == len(set(said))                   # each once
    assert "-two" not in "\n".join(said)
    assert "references in other projects are not rewritten" in result.err
    checked = tcw(["validate"], demo)
    assert checked.code == 0, checked.out


def test_ac11_json(tcw, demo):
    result = tcw(["work", "rename", EPIC, "new-words", "--json"], demo)
    assert result.code == 0, result.err
    answer = json.loads(result.out)
    assert answer["schema"] == 2
    assert [f"{m['from']} -> {m['to']}" for m in answer["moved"]] == three_lines()


def test_ac11_the_renamed_items_own_id_follows(tcw, demo):
    path = demo / "docs/work" / EPIC / ITEM_STATE
    write_state(path, f"title: Epic\nstage: request\nid: {EPIC}\n")
    part = demo / "docs/work" / EPIC / P / ITEM_STATE
    write_state(part, f"title: P\nstage: request\nparent: {wid(EPIC)}\nid: {P}\n")
    assert tcw(["work", "rename", EPIC, "new-words"], demo).code == 0
    assert state(demo, NEW)["id"] == NEW
    assert state(demo, f"{NEW}/{P}")["id"] == P


def test_ac11_a_stop_is_finished_by_running_again(tcw, demo):
    clean = demo.parent / "clean"
    import shutil
    shutil.copytree(demo, clean)
    assert tcw(["work", "rename", EPIC, "new-words"], clean).code == 0
    expected = snapshot(clean)

    r_state = demo / "docs/work" / R / ITEM_STATE
    os.chmod(r_state.parent, 0o555)
    try:
        result = tcw(["work", "rename", EPIC, "new-words"], demo)
    finally:
        os.chmod(r_state.parent, 0o755)
    assert result.code == 1, result.err
    assert result.out == ""
    assert str(Path("docs/work") / R / ITEM_STATE) in result.err
    assert "run the same command again" in result.err
    assert "the folder is still at" in result.err
    assert "written so far" in result.err
    assert (demo / "docs/work" / EPIC).is_dir()
    again = tcw(["work", "rename", EPIC, "new-words"], demo)
    assert again.code == 0, again.err
    assert again.out.splitlines() == three_lines()
    assert snapshot(demo) == expected


# -- the rules of a rename -------------------------------------------------------------


@pytest.mark.parametrize("words,said", [
    ("New Words", "did you mean new-words?"),
    ("2026-01-01-other", "a rename keeps the date 2026-10-22"),
])
def test_rename_refuses_bad_words(tcw, demo, words, said):
    before = snapshot(demo)
    result = tcw(["work", "rename", EPIC, words], demo)
    assert result.code == 2
    assert said in result.err
    assert snapshot(demo) == before


def test_rename_to_the_same_name_is_refused(tcw, demo):
    result = tcw(["work", "rename", EPIC, "old-words"], demo)
    assert result.code == 3
    assert "already has that name" in result.err


def test_rename_onto_an_existing_folder_is_refused(tcw, demo):
    item(demo, NEW, "Taken")
    result = tcw(["work", "rename", EPIC, "new-words"], demo)
    assert result.code == 3
    assert "already exists" in result.err


def test_a_folder_named_alike_in_other_letter_case_is_refused(tcw, demo):
    """Compared ignoring letter case, so a disk that ignores it cannot merge
    two folders (Design 5.4 c)."""
    (demo / "docs/work" / f"{D}-NEW-WORDS").mkdir()
    result = tcw(["work", "rename", EPIC, "new-words"], demo)
    assert result.code == 3
    assert "already exists" in result.err
    assert (demo / "docs/work" / EPIC).is_dir()


def test_an_unreadable_item_stops_the_rename_before_anything(tcw, demo):
    write_state(demo / "docs/work" / R / ITEM_STATE, "title: [unclosed\n")
    before = snapshot(demo)
    result = tcw(["work", "rename", EPIC, "new-words"], demo)
    assert result.code == 1
    assert R in result.err
    assert snapshot(demo) == before


def test_a_reference_field_added_to_the_table_is_rewritten(tcw, demo, monkeypatch):
    """AC 26's rename half for the work-item rows (review S9)."""
    import tcw.reference_fields as table
    from tcw.reference_fields import Field
    monkeypatch.setattr(table, "FIELDS", (*table.FIELDS, Field(
        "work-item", "reviewed-by", False, "work")))
    # The item model reads only the keys it knows; the row is the rewrite's.
    import tcw.work.fs_backend as fs_backend
    monkeypatch.setattr(fs_backend, "KEYS", (*fs_backend.KEYS, "reviewed-by"))
    write_state(demo / "docs/work" / R / ITEM_STATE,
                f"title: R\nstage: request\nreviewed-by: {wid(EPIC + '/' + P)}\n")
    assert tcw(["work", "rename", EPIC, "new-words"], demo).code == 0, "rename"
    assert state(demo, R)["reviewed-by"] == wid(f"{NEW}/{P}")


# -- AC 18 ---------------------------------------------------------------------------


def test_ac18_a_nested_identifier_too_long_moves_nothing(tcw, tmp_path):
    root = project(tmp_path, "demo", work={})
    item(root, f"{D}-e", "E")
    # demo.work/<D>-e/<part>: the part fills the identifier to 250.
    used = len(f"demo.work/{D}-e/{D}-")
    part = f"{D}-" + "-".join(["abcdefghi"] * 30)[:250 - used]
    item(root, f"{D}-e/{part}", "Part")
    assert len(wid(f"{D}-e/{part}")) == 250
    before = snapshot(root)
    result = tcw(["work", "rename", f"{D}-e", "e-abcde"], root)
    assert result.code == 2
    assert "256 characters; a full identifier is at most 255" in result.err
    assert wid(f"{D}-e-abcde/{part}") in result.err
    assert snapshot(root) == before


# -- AC 25 (the rename half) -----------------------------------------------------------


@pytest.mark.parametrize("argv", [
    ["work", "rename", EPIC, "new-words"],
    ["work", "move", R, "--into", EPIC],
])
def test_ac25_a_move_runs_no_hook_and_starts_no_process(tcw, demo, monkeypatch, argv):
    from tests.processes import allowed_read_only_git
    import subprocess
    started = []
    real_run, real_popen = subprocess.run, subprocess.Popen

    def run(argv, *a, **k):
        started.append(list(argv))
        return real_run(argv, *a, **k)

    class Popen(real_popen):
        def __init__(self, argv, *a, **k):
            started.append(list(argv))
            super().__init__(argv, *a, **k)
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(subprocess, "Popen", Popen)
    config = demo / ".tcw/tcw-config.yaml"
    data = yaml.safe_load(config.read_text())
    marker = demo.parent / "hook-ran"
    bound = [{"command": f"touch {marker}"}]
    data.setdefault("work", {})["stages"] = {
        s: {"pre": bound, "post": bound} for s in ("request", "spec", "plan")}
    from tests.projectfiles import write_config_file
    write_config_file(config, yaml.safe_dump({k: v for k, v in data.items()
                                              if k != "tcw-version"}))
    result = tcw(argv, demo)
    assert result.code == 0, result.err
    assert not marker.exists()
    assert all(allowed_read_only_git(argv) for argv in started), started


# -- every stop (plan choice 10) ---------------------------------------------------------


def test_every_stop_of_a_rename_is_finished_by_running_again(tcw, tmp_path):
    from tests.move_stops import Fixture, every_stop
    made = []

    def make():
        folder = tmp_path / f"run-{len(made)}"
        folder.mkdir()
        made.append(folder)
        return Fixture(make_demo(folder))

    def command(fixture):
        return tcw(["work", "rename", EPIC, "new-words"], fixture.root)
    total = every_stop(pytest.MonkeyPatch.context, make, command)
    # P's, Q's and R's state files, R's spec, and the folder.
    assert total == 5


# -- tcw work move (AC 13, AC 14; plan Step 18) --------------------------------------------

E, A, B = f"{D}-e", f"{D}-a", f"{D}-b"


@pytest.fixture
def board(tmp_path):
    root = project(tmp_path, "demo", work={})
    item(root, E, "Epic")
    item(root, A, "A", parent=wid(E))
    item(root, B, "B")
    return root


def folder_warnings(tcw, root):
    return [line for line in findings(tcw(["validate"], root))
            if "sits in the folder of" in line]


def test_ac13_into_an_epic_and_back(tcw, board):
    result = tcw(["work", "move", A, "--into", E], board)
    assert result.code == 0, result.err
    assert result.out.splitlines() == [f"{wid(A)} -> {wid(E + '/' + A)}"]
    assert (board / "docs/work" / E / A / ITEM_STATE).is_file()
    assert folder_warnings(tcw, board) == []
    back = tcw(["work", "move", f"{E}/{A}", "--top"], board)
    assert back.code == 0, back.err
    assert (board / "docs/work" / A / ITEM_STATE).is_file()


def test_ac13_into_a_folder_that_is_not_its_parent_warns(tcw, board):
    result = tcw(["work", "move", B, "--into", E], board)
    assert result.code == 0, result.err
    assert "parent: decides" in result.err
    assert "parent" not in state(board, f"{E}/{B}")


def test_ac13_organising_folders_are_made_and_removed(tcw, board):
    result = tcw(["work", "move", B, "--into", "2026/q4"], board)
    assert result.code == 0, result.err
    assert (board / "docs/work/2026/q4" / B / ITEM_STATE).is_file()
    back = tcw(["work", "move", f"2026/q4/{B}", "--top"], board)
    assert back.code == 0, back.err
    assert not (board / "docs/work/2026").exists()
    assert "docs/work/2026/q4/" in back.err and "docs/work/2026/" in back.err


def test_ac13_a_failed_folder_move_leaves_no_organising_folder(tcw, board, monkeypatch):
    import tcw.object_folders as folders

    def rename(a, b):
        raise PermissionError(13, "Permission denied")
    monkeypatch.setattr(folders.os, "rename", rename)
    result = tcw(["work", "move", B, "--into", "2026/q4"], board)
    assert result.code == 1, result.err
    assert not (board / "docs/work/2026").exists()


@pytest.mark.parametrize("argv", [
    ["--into", f"{E}/drafts"], ["--into", f"{E}/plan"], ["--into", "resources"],
    ["--into", A], ["--into", E, "--top"], [],
])
def test_ac13_destinations_refused_as_usage_errors(tcw, board, argv):
    before = snapshot(board)
    result = tcw(["work", "move", A, *argv], board)
    assert result.code == 2, (argv, result.err)
    assert snapshot(board) == before


def test_ac13_a_folder_named_alike_in_the_destination_is_refused(tcw, board):
    (board / "docs/work" / E / B.upper()).mkdir()
    result = tcw(["work", "move", B, "--into", E], board)
    assert result.code == 3, result.err


def test_ac14_a_rename_and_a_nested_create_that_met_on_merge(tcw, tmp_path):
    """TCW-111 AC 16a's layout: one clone renamed the epic, another made a
    part inside its old folder."""
    root = project(tmp_path, "demo", work={})
    item(root, NEW, "Epic")
    part = f"{D}-part"
    item(root, f"{EPIC}/{part}", "Part", parent=wid(EPIC))
    result = tcw(["work", "move", f"{EPIC}/{part}", "--into", NEW], root)
    assert result.code == 0, result.err
    assert not (root / "docs/work" / EPIC).exists()
    fixed = tcw(["work", "edit", f"{NEW}/{part}", "--parent", NEW], root)
    assert fixed.code == 0, fixed.err
    checked = tcw(["validate"], root)
    assert checked.code == 0, checked.out


def test_every_stop_of_a_move_into_new_folders(tcw, tmp_path):
    from tests.move_stops import Fixture, every_stop
    made = []

    def make():
        folder = tmp_path / f"run-{len(made)}"
        folder.mkdir()
        made.append(folder)
        root = project(folder, "demo", work={})
        item(root, E, "Epic")
        item(root, B, "B")
        return Fixture(root)

    def command(fixture):
        return tcw(["work", "move", B, "--into", "2026/q4"], fixture.root)
    # The two folders made, and the move.
    assert every_stop(pytest.MonkeyPatch.context, make, command) == 3
