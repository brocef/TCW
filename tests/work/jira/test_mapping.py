"""Text to ADF and back, and ticket fields to item properties and back
(TCW-71 Design 3, 4, 14; AC 16's round trip)."""

from datetime import date

import pytest

from tcw.work.jira.config import JiraConfig, JiraFields
from tcw.work.jira.mapping import (
    block_link, blocker_keys, create_fields, document_text, label_updates,
    normalize_text, parse_created, read_props, scale_name, text_document,
    write_fields,
)
from tcw.work.model import UNSET, Changes

CONFIG = JiraConfig(site="https://acme.atlassian.net", project="TCW", email_env="E",
                    token_env="T", fields=JiraFields("TCW Project", "TCW Item",
                                                     "Effort", "Complexity"))
IDS = {"project": "customfield_1", "item": "customfield_2", "effort": "customfield_3",
       "complexity": "customfield_4"}
STATUSES = {"inbox": "To Do", "request": "Triage", "spec": "Specifying",
            "implement": "In Progress", "completed": "Done"}


# -- text ------------------------------------------------------------------------


def test_the_criterion_text_reads_back_exactly():
    text = "a [b] *c*\n\nd\ne"
    doc = text_document(text)
    assert document_text(doc) == text
    paragraphs = doc["content"]
    assert [p["type"] for p in paragraphs] == ["paragraph", "paragraph"]
    assert [n["type"] for n in paragraphs[1]["content"]] == ["text", "hardBreak", "text"]
    assert paragraphs[0]["content"] == [{"type": "text", "text": "a [b] *c*"}]


ROUND_TRIP = [
    "one\n\ntwo",
    "one\n\n\n\ntwo",
    "one\ntwo",
    "trailing   \nspaces  ",
    "windows\r\nline\r\n\r\nendings",
    "old mac\rline",
    "[link](x) and [ ] and ]",
    "*not bold* and ** and *",
    "  leading spaces kept inside\n    indented",
    "\n\nblank at the ends\n\n",
    "a\n   \nb",
    "",
    "tab\there",
]


@pytest.mark.parametrize("text", ROUND_TRIP)
def test_text_survives_the_round_trip(text):
    assert normalize_text(document_text(text_document(text))) == normalize_text(text)


def test_nothing_inside_a_line_is_stripped():
    assert document_text(text_document("a  \n  b")) == "a  \n  b"


def test_nested_blocks_read_one_per_line():
    doc = {"type": "doc", "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "intro"}]},
        {"type": "bulletList", "content": [
            {"type": "listItem", "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "one"}]}]},
            {"type": "listItem", "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "two"}]}]}]},
        {"type": "paragraph", "content": [
            {"type": "text", "text": "hi "},
            {"type": "mention", "attrs": {"id": "a1", "text": "@Ann"}}]}]}
    assert document_text(doc) == "intro\n\none\ntwo\n\nhi @Ann"


@pytest.mark.parametrize("value", [None, "text", [], {"content": "x"},
                                   {"content": [7, "x"]}])
def test_anything_not_a_document_reads_as_no_text(value):
    assert document_text(value) == ""


def test_normalize_text():
    assert normalize_text("a  \r\n\r\n\r\nb\n\n") == "a\n\nb"


# -- reading ---------------------------------------------------------------------


def issue(**fields):
    return {"key": "TCW-7", "fields": fields}


def test_every_property_is_read():
    props = read_props(issue(
        summary="Dark mode", status={"name": "Specifying"},
        created="2026-10-08T22:30:00.000-0400", priority={"name": "High"},
        labels=["ui", "Someone-Else", "api"], assignee={"accountId": "a1",
                                                       "displayName": "Ann"},
        parent={"key": "TCW-1"}, issuetype={"name": "Task"},
        issuelinks=[
            {"type": {"name": "Blocks"}, "inwardIssue": {"key": "TCW-2"}},
            {"type": {"name": "Blocks"}, "outwardIssue": {"key": "TCW-3"}},
            {"type": {"name": "Relates"}, "inwardIssue": {"key": "TCW-4"}}],
        customfield_1="tcw", customfield_2="tcw/TCW-7-dark-mode",
        customfield_3={"value": "Very High"}, customfield_4={"value": "low"}),
        CONFIG, IDS, {"ui", "api"}, STATUSES)
    assert (props.key, props.title, props.status, props.stage) == (
        "TCW-7", "Dark mode", "Specifying", "spec")
    assert props.created == date(2026, 10, 9)          # 22:30 at -04:00 is 02:30 UTC
    assert (props.priority, props.effort, props.complexity) == ("high", "very-high", "low")
    assert props.tags == ("ui", "api")
    assert (props.assignee, props.assignee_name) == ("a1", "Ann")
    assert (props.parent_key, props.blocker_keys) == ("TCW-1", ("TCW-2",))
    assert (props.tcw_project, props.tcw_item, props.issue_type) == (
        "tcw", "tcw/TCW-7-dark-mode", "Task")


def test_unmapped_and_absent_values_read_as_none():
    props = read_props(issue(summary="x", status={"name": "Backlog"},
                             priority={"name": "Blocker"},
                             customfield_3={"value": "huge"}, customfield_4=None),
                       CONFIG, IDS, set(), STATUSES)
    assert (props.stage, props.priority, props.effort, props.complexity) == (
        None, None, None, None)
    assert (props.assignee, props.parent_key, props.tags, props.blocker_keys) == (
        None, None, (), ())
    assert props.tcw_item is None and props.created is None


def test_a_status_matches_exactly():
    props = read_props(issue(summary="x", status={"name": "specifying"}),
                       CONFIG, IDS, set(), STATUSES)
    assert props.stage is None


def test_a_disabled_or_absent_stage_has_no_status_to_match():
    props = read_props(issue(summary="x", status={"name": "In Review"}),
                       CONFIG, IDS, set(), STATUSES)
    assert props.stage is None


@pytest.mark.parametrize("value, expected", [
    ("2026-10-08T00:30:00.000+0200", date(2026, 10, 7)),
    ("2026-10-08T01:00:00.000+0100", date(2026, 10, 8)),
    ("2026-10-08T12:00:00.000-0000", date(2026, 10, 8)),
    ("2026-10-08T20:00:00.000-0500", date(2026, 10, 9)),
    ("2026-10-08T23:59:59+0000", date(2026, 10, 8)),
    ("2026-10-08T23:00:00-01:00", date(2026, 10, 9)),
    ("2026-10-08", None),
    ("2026-10-08T10:00:00", None),
    (None, None),
])
def test_created_is_the_utc_date(value, expected):
    assert parse_created(value) == expected


def test_three_offsets_reach_the_same_utc_date():
    stamps = ["2026-10-08T09:00:00.000+0900", "2026-10-08T00:00:00.000+0000",
              "2026-10-07T19:00:00.000-0500"]
    assert {parse_created(s) for s in stamps} == {date(2026, 10, 8)}


@pytest.mark.parametrize("value, expected", [
    ({"value": "Very High"}, "very-high"), ({"value": "very-high"}, "very-high"),
    ({"value": "MEDIUM"}, "medium"), ({"value": "huge"}, None), (None, None),
    ({"id": "1"}, None),
])
def test_scale_name(value, expected):
    assert scale_name(value) == expected


def test_block_link_and_blocker_keys_agree():
    """Whatever direction Jira uses (a live-check question), a link made with
    `block_link(blocker, blocked)` reads back as a blocker of `blocked`."""
    inward, outward = block_link("TCW-2", "TCW-7")
    on_blocked = [{"type": {"name": "Blocks"}, "inwardIssue": {"key": inward}}]
    assert blocker_keys(on_blocked) == ("TCW-2",)
    assert outward == "TCW-7"


# -- writing ---------------------------------------------------------------------


def test_write_fields():
    fields, update = write_fields(
        Changes(title="New", priority="low", effort="very-high", complexity=None,
                add_tags=("ui",), remove_tags=("old",)),
        CONFIG, IDS, assignee="a2", parent=None,
        options={"effort": {"very-high": "Very High"}})
    assert fields == {"summary": "New", "priority": {"name": "Low"},
                      "customfield_3": {"value": "Very High"}, "customfield_4": None,
                      "assignee": {"accountId": "a2"}, "parent": None}
    assert update == {"labels": [{"add": "ui"}, {"remove": "old"}]}


def test_an_empty_change_writes_nothing():
    assert write_fields(Changes(), CONFIG, IDS) == ({}, {})


def test_an_unconfigured_estimate_field_is_not_written():
    fields, _ = write_fields(Changes(effort="low"), CONFIG, {"project": "c1", "item": "c2"})
    assert fields == {}


def test_label_updates():
    assert label_updates(["a"], ["b", "c"]) == [{"add": "a"}, {"remove": "b"},
                                                {"remove": "c"}]


def test_create_fields():
    fields = create_fields(
        "T", Changes(add_tags=("ui",), effort="low"), "req\n\nmore", config=CONFIG,
        field_ids=IDS, project_id="tcw", issue_type="10001", has_priority=True,
        assignee="a1", parent="TCW-1")
    assert fields == {
        "project": {"key": "TCW"}, "issuetype": {"id": "10001"}, "summary": "T",
        "customfield_1": "tcw", "description": text_document("req\n\nmore"),
        "priority": {"name": "Medium"}, "labels": ["ui"],
        "assignee": {"accountId": "a1"}, "parent": {"key": "TCW-1"},
        "customfield_3": {"value": "low"}}


def test_create_fields_without_priority_or_request():
    fields = create_fields("T", Changes(priority=UNSET), None, config=CONFIG,
                           field_ids=IDS, project_id="tcw", issue_type="1",
                           has_priority=False)
    assert "priority" not in fields and "description" not in fields
    assert "customfield_2" not in fields                    # TCW Item comes later
