"""Work items nested in other items' folders, or in organising folders, in a
files-backend project `demo` (TCW-111 Design 2, 5, 7; AC 4, 5, 6, 6a, 9's
reading half, and AC 17's work half). The folders are made by hand: this
file is about finding, listing and checking them."""

from __future__ import annotations

import json

import pytest

from tests.objectcli import findings, item, project, store, tcw  # noqa: F401

EPIC = "2026-10-01-epic"
PART = "2026-10-02-part"


@pytest.fixture
def demo(tmp_path):
    return project(tmp_path, work={"tags": ["ui"]})


def listed(tcw, root, *flags):
    result = tcw(["work", "list", "--all", *flags], root)
    assert result.code == 0, result.err
    return result.out.split()


# -- AC 4 -------------------------------------------------------------------------

def test_an_item_in_an_organising_folder_is_listed_by_its_id_path(tcw, demo):
    item(demo, "2026/2026-10-01-x")
    assert listed(tcw, demo) == ["demo.work/2026/2026-10-01-x"]
    assert tcw(["validate"], demo).code == 0


# -- AC 5 -------------------------------------------------------------------------

def test_a_loose_file_in_an_item_folder(tcw, demo):
    folder = item(demo, EPIC)
    (folder / "notes.md").write_text("n")
    checked = tcw(["validate"], demo)
    assert (checked.code, findings(checked)) == (1, [
        f"error: docs/work/{EPIC}/notes.md: is not one of demo.work/{EPIC}'s files; "
        f"move it into resources/"])


def test_a_folder_named_as_an_item_with_no_state_file(tcw, demo):
    (store(demo, "work") / "2026-10-03-x").mkdir()
    checked = tcw(["validate"], demo)
    assert (checked.code, findings(checked)) == (1, [
        "error: docs/work/2026-10-03-x/tcw-work-item.yaml: is missing; it holds the "
        "item's properties and stage"])
    assert listed(tcw, demo) == []


def test_a_state_file_in_a_folder_not_named_as_an_item(tcw, demo):
    item(demo, "notes")
    checked = tcw(["validate"], demo)
    assert (checked.code, findings(checked)) == (1, [
        "error: docs/work/notes: is not an item folder: its name must be a date, "
        "then title words"])
    assert listed(tcw, demo) == []


def test_resources_pass_and_an_empty_organising_folder_warns(tcw, demo):
    folder = item(demo, EPIC)
    (folder / "resources" / "a").mkdir(parents=True)
    (folder / "resources" / "notes.md").write_text("n")
    (folder / "resources" / "a" / "b.png").write_bytes(b"\x89PNG")
    assert tcw(["validate"], demo).code == 0
    (store(demo, "work") / "empty").mkdir()
    checked = tcw(["validate"], demo)
    assert (checked.code, findings(checked)) == (0, [
        "warning: docs/work/empty: holds no TCW object"])


# -- AC 6 and 6a ------------------------------------------------------------------

def test_a_misplaced_folder_hides_nothing(tcw, demo):
    item(demo, "review/2026-10-01-x")
    item(demo, EPIC)
    item(demo, f"{EPIC}/drafts/{PART}")
    assert listed(tcw, demo) == [f"demo.work/{EPIC}", f"demo.work/{EPIC}/drafts/{PART}",
                                 "demo.work/review/2026-10-01-x"]
    for id_path in ("review/2026-10-01-x", f"{EPIC}/drafts/{PART}"):
        shown = tcw(["work", "show", id_path], demo)
        assert shown.code == 0 and f"demo.work/{id_path}" in shown.out, shown
    checked = tcw(["validate"], demo)
    assert (checked.code, findings(checked)) == (1, [
        f"error: docs/work/{EPIC}/drafts: is not a child object of demo.work/{EPIC}: "
        f"it has no tcw-work-item.yaml; give it one, or move it into resources/",
        "error: docs/work/review: 'review' is reserved in the work store; see "
        "docs/migration-guide-2.8-to-3.0.0.md for the work store layout",
    ])


# -- AC 9, reading ----------------------------------------------------------------

def test_a_nested_part_is_read_by_its_id_path(tcw, demo):
    item(demo, EPIC, title="Epic")
    item(demo, f"{EPIC}/{PART}", title="Part", parent=f"demo.work/{EPIC}")
    nested = f"{EPIC}/{PART}"
    for name in (nested, f"demo.work/{nested}"):
        shown = tcw(["work", "show", name, "--json"], demo)
        assert shown.code == 0, shown.err
        assert json.loads(shown.out)["item"]["full-id"] == f"demo.work/{nested}"
    assert tcw(["work", "edit", nested, "--priority", "high"], demo).code == 0
    assert "priority: high" in (store(demo, "work") / nested /
                                "tcw-work-item.yaml").read_text()
    assert tcw(["work", "comment", nested], demo, stdin="a note\n").code == 0
    assert list((store(demo, "work") / nested / "comments").iterdir())
    assert tcw(["work", "advance", nested, "--dry-run"], demo).code in (0, 3)
    path = tcw(["work", "path", nested], demo)
    assert path.code == 0 and path.out.strip().endswith(f"docs/work/{nested}")
    assert tcw(["validate"], demo).code == 0


def test_a_part_with_no_state_file_is_not_shown(tcw, demo):
    item(demo, EPIC)
    (store(demo, "work") / EPIC / PART).mkdir()
    assert tcw(["work", "show", f"{EPIC}/{PART}"], demo).code == 4


def test_an_id_path_naming_no_item_still_gets_the_3x_hint_rule(tcw, demo):
    shown = tcw(["work", "show", "demo/2026-10-01-x"], demo)
    assert shown.code == 4 and "no work item" in shown.err


# -- AC 17, work ------------------------------------------------------------------

def test_a_3x_item_folder_is_not_listed_and_is_reported(tcw, demo):
    old = store(demo, "work") / "2026-10-01-old"
    old.mkdir()
    (old / "item.yaml").write_text("title: Old\nstage: plan\n")
    assert listed(tcw, demo) == []
    checked = tcw(["validate"], demo)
    assert (checked.code, findings(checked)) == (1, [
        "error: docs/work/2026-10-01-old: holds a TCW 3.x item.yaml; run 'tcw migrate' "
        "in this project"])


def test_a_targeted_check_of_an_epic_leaves_its_parts_out(demo):
    """The check of one object (how `tcw serve` checks what it just wrote)
    keeps what is found in a nested item's folder for that item."""
    from tcw.validate import ValidationTarget, validate

    def check(id_path):
        return [str(f) for f in validate(demo, target=ValidationTarget("work", id_path))]
    epic = item(demo, EPIC)
    part = item(demo, f"{EPIC}/{PART}")
    (part / "notes.md").write_text("the part's own problem")
    assert check(EPIC) == []
    assert any("notes.md" in f for f in check(f"{EPIC}/{PART}"))
    (epic / "loose.txt").write_text("the epic's own")
    found = check(EPIC)
    assert any("loose.txt" in f for f in found) and not any("notes.md" in f for f in found)


# -- AC 9, creating ---------------------------------------------------------------
# The real clock: the parents are dated 2000-01-01, so a part given its
# parent's date instead of today's shows.

OLD_EPIC = "2000-01-01-epic"


def made(result):
    assert result.code == 0, result.err
    return result.out.strip()


def test_new_with_a_parent_is_made_at_the_top_unless_nested(tcw, demo):
    from datetime import date
    today = date.today().isoformat()
    item(demo, OLD_EPIC, title="Epic")
    flat = made(tcw(["work", "new", "Flat", "--parent", OLD_EPIC], demo))
    assert flat == f"demo.work/{today}-flat"
    part = made(tcw(["work", "new", "Part", "--parent", OLD_EPIC, "--nest"], demo))
    assert part == f"demo.work/{OLD_EPIC}/{today}-part"
    assert (store(demo, "work") / OLD_EPIC / f"{today}-part" / "tcw-work-item.yaml").is_file()
    assert listed(tcw, demo) == sorted([f"demo.work/{OLD_EPIC}", flat, part])
    children = listed(tcw, demo, "--parent", OLD_EPIC)
    assert children == sorted([flat, part])
    shown = json.loads(tcw(["work", "show", part, "--json"], demo).out)["item"]
    assert shown["created"] == today


def test_a_nested_part_under_a_parent_in_an_organising_folder(tcw, demo):
    from datetime import date
    today = date.today().isoformat()
    item(demo, f"2026/{OLD_EPIC}", title="Epic")
    made_ = tcw(["work", "new", "Part", "--parent", f"2026/{OLD_EPIC}", "--nest"], demo)
    assert "Traceback" not in made_.err
    part = made(made_)
    assert part == f"demo.work/2026/{OLD_EPIC}/{today}-part"
    shown = json.loads(tcw(["work", "show", part, "--json"], demo).out)["item"]
    assert shown["created"] == today


def test_nest_without_a_parent_is_refused_making_nothing(tcw, demo):
    refused = tcw(["work", "new", "Part", "--nest"], demo, stdin="asks\n")
    assert refused.code == 2 and "--parent" in refused.err
    assert [p for p in store(demo, "work").iterdir() if not p.name.startswith(".")] == []


def test_nest_with_a_parent_of_another_project_is_made_at_the_top(tcw, tmp_path):
    from datetime import date
    from tests.work.projects import connect, make_project, write_item
    here, other = make_project(tmp_path, "p"), make_project(tmp_path, "q")
    connect(here, other, "parent")
    write_item(other, OLD_EPIC, {"title": "Epic", "stage": "spec"})
    result = tcw(["work", "new", "Part", "--parent", f"q.work/{OLD_EPIC}", "--nest"], here)
    assert made(result) == f"p.work/{date.today().isoformat()}-part"
    assert f"not nested: q.work/{OLD_EPIC} belongs to project 'q'" in result.err
    assert not (other / "docs" / "work" / OLD_EPIC / f"{date.today().isoformat()}-part").exists()


# -- AC 16: renaming --------------------------------------------------------------

def state_bytes(root):
    return sorted((str(p), p.read_bytes()) for p in store(root, "work").rglob("tcw-work-item.yaml"))


def test_a_nested_part_is_renamed_inside_its_parents_folder(tcw, demo):
    item(demo, EPIC, title="Epic")
    item(demo, "2026-10-09-other-epic", title="Other epic")
    item(demo, f"{EPIC}/{PART}", title="Part")
    third = item(demo, "2026-10-03-third", title="Third",
                 **{"blocked-by": [f"demo.work/{EPIC}/{PART}"]})
    (third / "resources").mkdir()
    (third / "resources" / "names-it.md").write_text(f"see {EPIC}/{PART}\n")
    (third / "resources" / "names-another.md").write_text(
        f"see 2026-10-09-other-epic/{PART}\n")
    renamed = tcw(["work", "rename", f"{EPIC}/{PART}", "new-words"], demo)
    assert renamed.code == 0, renamed.err
    new = f"demo.work/{EPIC}/2026-10-02-new-words"
    assert renamed.out == f"demo.work/{EPIC}/{PART} -> {new}\n"
    assert (store(demo, "work") / EPIC / "2026-10-02-new-words").is_dir()
    assert f"- {new}" in (third / "tcw-work-item.yaml").read_text()
    assert "names-it.md:1" in renamed.err
    assert "names-another.md" not in renamed.err


def test_a_rename_beyond_255_characters_moves_nothing(tcw, demo):
    from tests.test_identifier_length import nested_parent
    path = nested_parent(250)
    item(demo, path.split("/")[0])
    item(demo, path)
    before = state_bytes(demo)
    old_words = path.rpartition("/")[2][11:]
    # Six characters longer: 256 in all.
    refused = tcw(["work", "rename", path, "c" * (len(old_words) + 6)], demo)
    assert refused.code == 2 and "at most 255" in refused.err
    assert state_bytes(demo) == before


# -- AC 12 and 16a: the folder and parent disagree ------------------------------------

DISAGREE = ("sits in the folder of demo.work/{epic}, but its parent is {named}; "
            "parent: decides (set it to demo.work/{epic}, or move the folder)")


def test_a_nested_item_whose_parent_is_another_warns(tcw, demo):
    item(demo, EPIC, title="Epic")
    item(demo, "2026-10-05-other", title="Other")
    item(demo, f"{EPIC}/{PART}", title="Part", parent="demo.work/2026-10-05-other")
    item(demo, "2026-10-06-flat", title="Flat", parent=f"demo.work/{EPIC}")
    checked = tcw(["validate"], demo)
    assert (checked.code, findings(checked)) == (0, [
        f"warning: docs/work/{EPIC}/{PART}/tcw-work-item.yaml: demo.work/{EPIC}/{PART} "
        + DISAGREE.format(epic=EPIC, named="demo.work/2026-10-05-other")])


def test_edit_parent_prints_the_warning(tcw, demo):
    item(demo, EPIC, title="Epic")
    item(demo, "2026-10-05-other", title="Other")
    item(demo, f"{EPIC}/{PART}", title="Part", parent=f"demo.work/{EPIC}")
    edited = tcw(["work", "edit", f"{EPIC}/{PART}", "--parent", "2026-10-05-other"], demo)
    assert edited.code == 0, edited.err
    assert DISAGREE.format(epic=EPIC, named="demo.work/2026-10-05-other") in edited.err
    again = tcw(["work", "edit", f"{EPIC}/{PART}", "--parent", EPIC], demo)
    assert "sits in the folder" not in again.err


def test_a_parent_in_another_project_never_warns(tcw, tmp_path):
    from tests.work.projects import connect, make_project, write_item
    here, other = make_project(tmp_path, "p"), make_project(tmp_path, "q")
    connect(here, other, "parent")
    write_item(other, "2026-10-01-theirs", {"title": "Theirs", "stage": "spec"})
    write_item(here, "2026-10-02-flat", {"title": "Flat", "stage": "spec",
                                        "parent": "q.work/2026-10-01-theirs"})
    checked = tcw(["validate"], here)
    assert "sits in the folder" not in checked.out


def test_the_merge_case_is_reported_and_mended_by_hand(tcw, demo):
    """S-7: the epic renamed by hand, its part left behind in the old folder."""
    import shutil
    old, new = "2026-10-01-old-words", "2026-10-01-new-words"
    item(demo, new, title="Epic")
    part = item(demo, f"{old}/{PART}", title="Part", parent=f"demo.work/{old}")
    checked = tcw(["validate"], demo)
    assert checked.code == 1
    found = findings(checked)
    assert any(f.startswith(f"error: docs/work/{old}/tcw-work-item.yaml: is missing")
               for f in found), found
    assert any(f"demo.work/{old}" in f and PART in f and "parent" in f for f in found), found
    assert tcw(["work", "show", f"{old}/{PART}"], demo).code == 0
    shutil.move(str(part), str(store(demo, "work") / new / PART))
    (store(demo, "work") / old).rmdir()
    assert tcw(["work", "edit", f"{new}/{PART}", "--parent", new], demo).code == 0
    checked = tcw(["validate"], demo)
    assert (checked.code, findings(checked)) == (0, [])
