"""A Jira project names its items by full identifier, and one part way through
`tcw migrate` still holds 3.x `TCW Item` values (TCW-110 Design 5.2, AC 9 and
9a)."""

from __future__ import annotations

import pytest

from tcw.cli import main
from tcw.work.backend import Query
from tcw.work.jira.backend import three_x_item
from tests.fullids import wid
from tests.work.jira.fake import FIELDS

ITEM = FIELDS["TCW Item"]


def test_ac9_new_writes_the_full_identifier_and_show_reads_it_by_key(jira_project, tcw):
    made = tcw(["new", "Add login"], jira_project.root)
    assert made.code == 0, made.err
    full_id = made.out.strip()
    ticket = next(t for t in jira_project.fake.tickets.values()
                  if t.summary == "Add login")
    assert full_id == wid("tcw", f"{ticket.key}-add-login")
    assert ticket.custom[ITEM] == full_id
    shown = tcw(["show", ticket.key], jira_project.root)
    assert shown.code == 0, shown.err
    assert shown.out.splitlines()[0] == f"full-id: {full_id}"


def test_ac9_a_parent_holding_a_3x_value_with_no_folder_here_is_untracked(jira_project):
    epic, _ = jira_project.item("Epic", "epic", folder=False,
                                item="tcw/TCW-1-epic")
    _, child = jira_project.item("Child", "child", parent=epic)
    item = jira_project.backend().read(child)
    assert item.parent is None
    assert item.untracked == (epic,)


def _two_3x_tickets(jira_project):
    """One ticket whose folder is here and one whose folder is not, both still
    holding the 3.x value."""
    here, folder = jira_project.item("Here", "here")
    jira_project.fake.tickets[here].custom[ITEM] = f"tcw/{folder}"
    gone, _ = jira_project.item("Gone", "gone", folder=False, item="tcw/TCW-9-gone")
    _, kept = jira_project.item("Kept", "kept")
    return here, gone, kept


def test_ac9a_list_leaves_3x_tickets_out_with_one_warning(jira_project, capsys):
    here, gone, kept = _two_3x_tickets(jira_project)
    capsys.readouterr()
    items = jira_project.backend().list(Query())
    assert [i.slug.folder for i in items] == [kept]
    err = capsys.readouterr().err
    warnings = [line for line in err.splitlines() if line.startswith("warning:")]
    assert len(warnings) == 1, err
    assert "2 Jira tickets" in warnings[0]
    assert "TCW 3.x TCW Item value" in warnings[0]
    assert here in warnings[0] and gone in warnings[0]
    assert "tcw migrate" in warnings[0]
    assert "another copy of this repository" not in err


def test_ac9a_the_other_copy_warning_stays_for_a_4_0_value(jira_project, capsys):
    elsewhere, _ = jira_project.item("Elsewhere", "elsewhere", folder=False)
    capsys.readouterr()
    jira_project.backend().list(Query())
    err = capsys.readouterr().err
    assert elsewhere in err and "another copy of this repository" in err
    assert "TCW 3.x" not in err


def test_ac9a_validate_remote_reports_each_3x_ticket_once(jira_project, monkeypatch,
                                                         capsys):
    here, gone, _ = _two_3x_tickets(jira_project)
    here_folder = next(p.name for p in jira_project.work.iterdir()
                       if p.name.startswith(f"{here}-"))
    monkeypatch.chdir(jira_project.root)
    code = main(["validate", "--remote"])
    lines = capsys.readouterr().out.splitlines()
    assert code == 1
    at_item = [line for line in lines
               if line.startswith(f"error: {wid('tcw', here_folder)}: ")]
    at_key = [line for line in lines if line.startswith(f"error: {gone}: ")]
    for found in (at_item, at_key):
        assert len(found) == 1, lines
        assert "TCW 3.x value" in found[0] and "tcw migrate" in found[0]
    assert not any(line.startswith(f"error: {here}: ") for line in lines), lines
    assert not any("its ticket's TCW Item is" in line and "not" in line
                   for line in lines), lines


@pytest.mark.parametrize("value, is_3x", [
    ("tcw/TCW-1-x", True),
    ("tcw.work/TCW-1-x", False),
    ("tcw/a/b", False),
    ("Tcw/TCW-1-x", False),
    ("tcw/", False),
    ("TCW-1-x", False),
    (None, False),
])
def test_a_3x_value_is_project_slash_folder(value, is_3x):
    assert three_x_item(value) is is_3x


# -- what commands accept (TCW-110 Design 3.1, 3.2) ---------------------------------------


def test_ac9_a_key_in_a_full_identifier_shows_the_item(jira_project, tcw):
    made = tcw(["new", "Add login"], jira_project.root).out.strip()
    key = made.split("/", 1)[1].split("-add", 1)[0]
    for typed in (f"tcw.work/{key}", f"tcw://tcw.work/{key}"):
        shown = tcw(["show", typed], jira_project.root)
        assert shown.code == 0, shown.err
        assert shown.out.splitlines()[0] == f"full-id: {made}"


def test_ac10_a_key_no_folder_carries_is_not_found_naming_the_project(jira_project, tcw):
    for typed in ("TCW-999", "tcw.work/TCW-999"):
        found = tcw(["show", typed], jira_project.root)
        assert found.code == 4
        assert "no work item in project 'tcw' carries the key TCW-999" in found.err


def test_a_parent_given_by_key_is_stored_as_its_full_identifier(jira_project, tcw):
    epic = tcw(["new", "Epic"], jira_project.root).out.strip()
    key = epic.split("/", 1)[1].split("-epic", 1)[0]
    made = tcw(["new", "Part", "--parent", key], jira_project.root)
    assert made.code == 0, made.err
    shown = tcw(["show", made.out.strip()], jira_project.root).out
    assert f"parent: {epic}" in shown
