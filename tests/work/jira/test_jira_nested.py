"""Jira-mode items nested in other items' folders or in organising folders
(TCW-111 Design 6; AC 10, and AC 3's nested Jira case), on the fake. The
folders are made by hand: this file is about finding, listing and checking
them."""

import json

import pytest

from tests.statefiles import ITEM_STATE, write_state
from tests.work.jira.conftest import Result, key_folder
from tests.work.jira.fake import FIELDS, SITE

PROJECT, ITEM = FIELDS["TCW Project"], FIELDS["TCW Item"]


def ticket(project, summary, id_path, status="Triage"):
    """A ticket that is the item at `id_path`, and its folder."""
    t = project.fake.ticket(summary, project="TCW", status=status)
    t.custom[PROJECT] = "tcw"
    t.custom[ITEM] = f"tcw.work/{id_path}"
    key_folder(project.work, id_path)
    return t.key


@pytest.fixture
def validate(monkeypatch, capsys):
    from tcw.cli import main

    def run(project, *flags):
        project.fake.log.clear()
        monkeypatch.chdir(project.root)
        try:
            code = main(["validate", *flags])
        except SystemExit as stop:
            code = stop.code if isinstance(stop.code, int) else 1
        captured = capsys.readouterr()
        return Result(code, captured.out, captured.err)
    return run


def test_a_nested_item_is_listed_and_shown_by_key(jira_project, tcw):
    ticket(jira_project, "Epic", "TCW-1-epic")
    ticket(jira_project, "Part", "TCW-1-epic/TCW-2-part")
    listed = tcw(["list", "--json"], jira_project.root)
    assert listed.code == 0, listed.err
    assert [i["full-id"] for i in json.loads(listed.out)["items"]] == \
        ["tcw.work/TCW-1-epic", "tcw.work/TCW-1-epic/TCW-2-part"]
    shown = tcw(["show", "TCW-2", "--json"], jira_project.root)
    assert shown.code == 0, shown.err
    assert json.loads(shown.out)["item"]["full-id"] == "tcw.work/TCW-1-epic/TCW-2-part"
    by_path = tcw(["show", "TCW-1-epic/TCW-2-part"], jira_project.root)
    assert by_path.code == 0, by_path.err


def test_two_folders_for_one_key_at_any_depth(jira_project, tcw):
    ticket(jira_project, "Epic", "TCW-1-epic")
    key_folder(jira_project.work, "TCW-1-epic/TCW-5-a")
    key_folder(jira_project.work, "TCW-5-b")
    shown = tcw(["show", "TCW-5"], jira_project.root)
    assert shown.code == 1
    assert "TCW-1-epic/TCW-5-a, TCW-5-b" in shown.err


def test_the_remote_check_compares_a_nested_item_with_its_ticket(
        jira_project, validate):
    ticket(jira_project, "Epic", "TCW-1-epic")
    key = ticket(jira_project, "Part", "TCW-1-epic/TCW-2-part")
    jira_project.fake.tickets[key].custom[ITEM] = "tcw.work/TCW-2-part"
    run = validate(jira_project, "--remote")
    assert "error: tcw.work/TCW-1-epic/TCW-2-part: its ticket's TCW Item is " \
           "'tcw.work/TCW-2-part', not 'tcw.work/TCW-1-epic/TCW-2-part'" in run.out, run.out


def test_an_organising_folder_holding_an_item_passes(jira_project, validate, tcw):
    ticket(jira_project, "In a year", "2026/TCW-1-x")
    assert validate(jira_project).code == 0
    listed = tcw(["list", "--json"], jira_project.root)
    assert [i["full-id"] for i in json.loads(listed.out)["items"]] == ["tcw.work/2026/TCW-1-x"]


def test_a_key_named_folder_with_no_state_file_is_no_item(jira_project, validate, tcw):
    (jira_project.work / "TCW-7-x").mkdir(parents=True)
    checked = validate(jira_project)
    assert checked.code == 1
    assert "error: docs/work/TCW-7-x/tcw-work-item.yaml: is missing; it holds the " \
           "ticket's link" in checked.out
    assert tcw(["show", "TCW-7"], jira_project.root).code == 4


def test_a_fresh_adoption_beside_a_stateless_folder_is_refused(jira_project, tcw):
    fake = jira_project.fake
    (jira_project.work / "TCW-1-x").mkdir(parents=True)
    key = fake.ticket("Other words", project="TCW", status="To Do").key
    assert key == "TCW-1"
    fake.log.clear()
    adopted = tcw(["tickets", "adopt", key], jira_project.root)
    assert adopted.code == 3 and "TCW-1-x" in adopted.err, adopted
    assert fake.writes() == []
    assert sorted(p.name for p in jira_project.work.iterdir()
                  if not p.name.startswith(".")) == ["TCW-1-x"]
    assert list((jira_project.work / "TCW-1-x").iterdir()) == []


def test_a_resumed_adoption_finishes_a_stateless_folder(jira_project, tcw):
    fake = jira_project.fake
    t = fake.ticket("y", project="TCW", status="Triage")
    t.custom[PROJECT] = "tcw"
    t.custom[ITEM] = f"tcw.work/{t.key}-y"
    folder = jira_project.work / f"{t.key}-y"
    folder.mkdir(parents=True)
    adopted = tcw(["tickets", "adopt", t.key], jira_project.root)
    assert adopted.code == 0, adopted.err
    assert (folder / ITEM_STATE).is_file()


def test_a_state_file_in_a_folder_not_named_for_a_key(jira_project, validate):
    key_folder(jira_project.work, "notes")
    checked = validate(jira_project)
    assert checked.code == 1
    assert "error: docs/work/notes: is not a Jira item folder" in checked.out


def test_a_nested_state_file_of_a_newer_tcw_is_read_from_jira(jira_project, tcw,
                                                              validate):
    ticket(jira_project, "Epic", "TCW-1-epic")
    key = ticket(jira_project, "Part", "TCW-1-epic/TCW-2-part")
    path = jira_project.work / "TCW-1-epic" / "TCW-2-part" / ITEM_STATE
    write_state(path, f"tcw-version: '99.1'\nticket: {SITE}/browse/{key}\nadded: x\n")
    assert tcw(["show", key], jira_project.root).code == 0
    checked = validate(jira_project)
    assert checked.code == 1
    assert "newer than this TCW" in checked.out and "must hold exactly" not in checked.out


# -- AC 9 and 9a: creating a nested item --------------------------------------------

def made_epic(jira_project, tcw):
    epic = tcw(["new", "Epic"], jira_project.root)
    assert epic.code == 0, epic.err
    return epic.out.strip().split("/", 1)[1]


def test_new_with_nest_makes_the_folder_inside_the_parents(jira_project, tcw):
    epic = made_epic(jira_project, tcw)
    made = tcw(["new", "Part", "--parent", epic, "--nest"], jira_project.root)
    assert made.code == 0, made.err
    assert made.out.strip() == f"tcw.work/{epic}/TCW-2-part"
    assert (jira_project.work / epic / "TCW-2-part" / ITEM_STATE).is_file()
    assert jira_project.fake.tickets["TCW-2"].custom[ITEM] == f"tcw.work/{epic}/TCW-2-part"
    shown = tcw(["show", "TCW-2", "--json"], jira_project.root)
    assert json.loads(shown.out)["item"]["full-id"] == f"tcw.work/{epic}/TCW-2-part"
    flat = tcw(["new", "Flat", "--parent", epic], jira_project.root)
    assert flat.out.strip() == "tcw.work/TCW-3-flat"


def test_nest_without_a_parent_makes_no_request(jira_project, tcw):
    jira_project.fake.log.clear()
    refused = tcw(["new", "Part", "--nest"], jira_project.root)
    assert refused.code == 2 and "--parent" in refused.err
    assert jira_project.fake.log == []


def test_a_failed_folder_write_is_finished_by_adopt_inside_the_parent(jira_project, tcw):
    epic = made_epic(jira_project, tcw)
    in_the_way = jira_project.work / epic / "TCW-2-part"
    in_the_way.write_text("in the way")
    made = tcw(["new", "Part", "--parent", epic, "--nest"], jira_project.root)
    assert (made.code, made.out.strip()) == (1, "TCW-2")
    assert "tcw work tickets adopt TCW-2" in made.err
    in_the_way.unlink()
    adopted = tcw(["tickets", "adopt", "TCW-2"], jira_project.root)
    assert adopted.code == 0, adopted.err
    assert (in_the_way / ITEM_STATE).is_file()


def test_a_failed_item_edit_is_adopted_at_the_top(jira_project, monkeypatch, tcw):
    from tcw.work.jira import client as jira
    epic = made_epic(jira_project, tcw)
    fake = jira_project.fake
    original = fake._edit

    def refused(*args, **kwargs):
        raise jira._for_status(400, {}, "refused by the test", "/x")
    monkeypatch.setattr(fake, "_edit", refused)
    made = tcw(["new", "Part", "--parent", epic, "--nest"], jira_project.root)
    assert (made.code, made.out.strip()) == (1, "TCW-2")
    monkeypatch.setattr(fake, "_edit", original)
    adopted = tcw(["tickets", "adopt", "TCW-2"], jira_project.root)
    assert adopted.code == 0, adopted.err
    assert (jira_project.work / "TCW-2-part" / ITEM_STATE).is_file()
    assert not (jira_project.work / epic / "TCW-2-part").exists()


# -- AC 14: the 255-character limit in Jira mode -------------------------------------
# Lengths are of full identifiers: `tcw.work/` is 9 characters.

def jira_parent(project, total: int) -> str:
    """A ticket's item nested in another's, whose full identifier is `total`
    characters; returns its id-path."""
    letters = total - len("tcw.work/") - len("TCW-1-/TCW-2-")
    first = letters // 2
    outer = f"TCW-1-{'a' * first}"
    inner = f"{outer}/TCW-2-{'b' * (letters - first)}"
    assert len(f"tcw.work/{inner}") == total
    ticket(project, "Outer", outer)
    ticket(project, "Parent", inner)
    return inner


def creates(fake):
    return [path for method, path, _ in fake.log if (method, path) == ("POST", "/rest/api/3/issue")]


def test_under_a_227_character_parent_no_ticket_is_made(jira_project, tcw):
    parent = jira_parent(jira_project, 227)
    jira_project.fake.log.clear()
    refused = tcw(["new", "Part", "--parent", parent, "--nest"], jira_project.root)
    assert refused.code == 2 and f"tcw.work/{parent}" in refused.err, refused
    assert creates(jira_project.fake) == []


def test_a_long_title_under_a_200_character_parent_is_shortened(jira_project, tcw):
    parent = jira_parent(jira_project, 200)
    made = tcw(["new", "A very long title " * 8, "--parent", parent, "--nest"],
               jira_project.root)
    assert made.code == 0, made.err
    assert made.out.strip().startswith(f"tcw.work/{parent}/TCW-3-")
    assert len(made.out.strip()) <= 255


def rekey(fake, monkeypatch, key):
    """The fake answers the next create with `key`."""
    original = fake._create

    def answered(body, route):
        answer = original(body, route)
        made = fake.tickets.pop(answer["key"])
        made.key = key
        fake.tickets[key] = made
        return {**answer, "key": key}
    monkeypatch.setattr(fake, "_create", answered)


def test_after_the_ticket_exists_the_words_are_cut_to_the_room(jira_project, monkeypatch,
                                                                tcw):
    parent = jira_parent(jira_project, 226)
    rekey(jira_project.fake, monkeypatch, "ABCDEFGHIJKLMNOPQRSTU-12")
    made = tcw(["new", "Part of it", "--parent", parent, "--nest"], jira_project.root)
    assert made.code == 0, made.err
    full = f"tcw.work/{parent}/ABCDEFGHIJKLMNOPQRSTU-12-par"
    assert made.out.strip() == full and len(full) <= 255
    assert jira_project.fake.tickets["ABCDEFGHIJKLMNOPQRSTU-12"].custom[ITEM] == full


def test_a_key_that_leaves_no_room_stops_before_the_item_edit(jira_project, monkeypatch,
                                                               tcw):
    parent = jira_parent(jira_project, 226)
    rekey(jira_project.fake, monkeypatch, "ABCDEFGHIJKLMNOPQRSTUVWXY-12")
    made = tcw(["new", "Part", "--parent", parent, "--nest"], jira_project.root)
    assert made.code == 1, made
    assert "tcw work tickets adopt ABCDEFGHIJKLMNOPQRSTUVWXY-12" in made.err
    assert ITEM not in jira_project.fake.tickets["ABCDEFGHIJKLMNOPQRSTUVWXY-12"].custom


def test_a_fresh_adoption_where_the_project_id_leaves_no_room(tmp_path, fake, tcw):
    from tests.work.jira.conftest import JiraProject, jira_config
    from tests.work.projects import make_project
    long = "p" * 237
    root = make_project(tmp_path, long, config=jira_config(long), name="long")
    project = JiraProject(root, long, fake)
    key = fake.ticket("Adopt me", project="TCW", status="To Do").key
    fake.log.clear()
    refused = tcw(["tickets", "adopt", key], project.root)
    assert refused.code == 2 and long in refused.err, refused
    assert fake.writes() == []


def test_a_256_character_nested_folder_is_reported_offline(jira_project, validate):
    letters = 256 - len("tcw.work/") - len("TCW-1-/TCW-2-")
    outer = f"TCW-1-{'a' * (letters // 2)}"
    inner = f"{outer}/TCW-2-{'b' * (letters - letters // 2)}"
    key_folder(jira_project.work, outer)
    key_folder(jira_project.work, inner)
    checked = validate(jira_project)
    assert checked.code == 1
    assert (f"error: docs/work/{inner}/tcw-work-item.yaml: tcw.work/{inner} is 256 "
            f"characters; a full identifier is at most 255") in checked.out, checked.out


def test_a_delegation_into_a_project_with_little_room_fits_its_item(tmp_path, fake, tcw):
    from tests.work.jira.conftest import jira_config
    from tests.work.projects import commit_all, connect, make_project
    long = "t" * 237
    target = make_project(tmp_path, long, config=jira_config(long), name="target")
    here = make_project(tmp_path, "p", config={})
    connect(here, target, "children")
    commit_all(target)
    commit_all(here)
    made = tcw(["new", "Add export", "--project", long], here)
    assert made.code == 0, made.err
    item = fake.tickets["TCW-1"].custom[ITEM]
    # Whole words, as title_words cuts them: `add-ex` would fit, `add` is kept.
    assert item == f"{long}.work/TCW-1-add" and len(item) <= 255


# -- AC 16: renaming in Jira mode ----------------------------------------------------

def test_a_nested_rename_sets_the_item_field_to_the_new_id_path(jira_project, tcw):
    ticket(jira_project, "Epic", "TCW-1-epic")
    key = ticket(jira_project, "Part", "TCW-1-epic/TCW-2-part")
    renamed = tcw(["rename", "TCW-1-epic/TCW-2-part", "new-words"], jira_project.root)
    assert renamed.code == 0, renamed.err
    assert renamed.out.strip() == "tcw.work/TCW-1-epic/TCW-2-new-words"
    assert jira_project.fake.tickets[key].custom[ITEM] == "tcw.work/TCW-1-epic/TCW-2-new-words"
    assert (jira_project.work / "TCW-1-epic" / "TCW-2-new-words" / ITEM_STATE).is_file()


def test_a_failed_nested_move_sets_the_item_field_back(jira_project, monkeypatch, tcw):
    import os
    ticket(jira_project, "Epic", "TCW-1-epic")
    key = ticket(jira_project, "Part", "TCW-1-epic/TCW-2-part")

    def refused(*args, **kwargs):
        raise OSError("refused by the test")
    monkeypatch.setattr(os, "rename", refused)
    renamed = tcw(["rename", "TCW-1-epic/TCW-2-part", "new-words"], jira_project.root)
    monkeypatch.undo()
    assert renamed.code == 1 and "set back" in renamed.err, renamed
    assert jira_project.fake.tickets[key].custom[ITEM] == "tcw.work/TCW-1-epic/TCW-2-part"


def test_an_epic_with_a_nested_item_is_not_renamed_in_jira_mode(jira_project, tcw):
    key = ticket(jira_project, "Epic", "TCW-1-epic")
    ticket(jira_project, "Part", "TCW-1-epic/TCW-2-part")
    jira_project.fake.log.clear()
    refused = tcw(["rename", "TCW-1-epic", "new-words"], jira_project.root)
    assert refused.code == 3 and "TCW-114" in refused.err
    assert jira_project.fake.writes() == []
    assert jira_project.fake.tickets[key].custom[ITEM] == "tcw.work/TCW-1-epic"
