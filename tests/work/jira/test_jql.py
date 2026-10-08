"""Every JQL string TCW sends, and the fake's parser for them (TCW-71 AC 12,
and AC 11's last line: no query uses `~`)."""

import itertools

import pytest

from tcw.work.jira import jql
from tests.work.jira import fake_jql

ITEM = "customfield_10042"
DISPLAY_NAMES = ("TCW Item", "TCW Project", "Effort", "Complexity")


def test_quote_escapes_backslash_and_double_quote():
    assert jql.quote('a "b" \\c') == '"a \\"b\\" \\\\c"'
    assert fake_jql._tokens(jql.quote('a "b" \\c')) == [("string", 'a "b" \\c')]


def test_custom_fields_are_addressed_by_id():
    assert jql.field("customfield_10042") == "cf[10042]"
    with pytest.raises(ValueError):
        jql.field("TCW Item")


OPTIONS = {
    "statuses": [None, ["In Progress"], ["Triage", 'Odd "name"']],
    "not_statuses": [None, ["Done", "Won't Do"]],
    "parent": [None, "TCW-1"],
    "assignee": [None, "5b10a2844c20165700ede21g"],
    "labels": [None, ["ui"], ["ui", "api"]],
}


def every_item_query():
    keys = list(OPTIONS)
    for values in itertools.product(*(OPTIONS[k] for k in keys)):
        yield jql.item_query("TCW", ITEM, **dict(zip(keys, values)))


def every_query():
    yield from every_item_query()
    yield jql.inbox_query("TCW", ITEM, "To Do")
    yield jql.inbox_query("TCW", ITEM, "To Do", 'project = "TCW" AND labels IN ("triage")')
    yield jql.keys_query(["TCW-1"])
    yield jql.keys_query([f"TCW-{n}" for n in range(1, 101)])
    yield jql.sample_query("TCW", "Sub-task", "In Review")


QUERIES = list(every_query())


def test_the_table_covers_every_clause():
    assert len(QUERIES) == 3 * 2 * 2 * 2 * 3 + 5
    text = " ".join(QUERIES)
    for clause in ("status IN", "status NOT IN", "parent =", "assignee =", "labels IN",
                   "IS EMPTY", "IS NOT EMPTY", " OR ", "key IN", "issuetype ="):
        assert clause in text, clause


@pytest.mark.parametrize("query", QUERIES)
def test_the_fake_parses_every_query_tcw_builds(query):
    fake_jql.parse(query)


@pytest.mark.parametrize("query", QUERIES)
def test_no_query_uses_a_word_search_or_a_display_name(query):
    assert "~" not in query
    for name in DISPLAY_NAMES:
        assert name not in query


def test_custom_fields_appear_as_cf():
    assert "cf[10042] IS NOT EMPTY" in jql.item_query("TCW", ITEM)
    assert "cf[10042] IS EMPTY" in jql.inbox_query("TCW", ITEM, "To Do")


def test_the_key_search_takes_at_most_a_hundred_keys():
    with pytest.raises(ValueError):
        jql.keys_query([f"TCW-{n}" for n in range(101)])
    with pytest.raises(ValueError):
        jql.keys_query([])


@pytest.mark.parametrize("query", [
    'summary ~ "x"', 'project != "TCW"', 'created > "2026-01-01"',
    'project = TCW', 'project = "TCW" ORDER BY summary', 'status WAS "Done"'])
def test_the_fake_refuses_any_other_shape(query):
    with pytest.raises(fake_jql.JqlError):
        fake_jql.parse(query)


# -- evaluation -----------------------------------------------------------------

TICKETS = [
    {"key": "TCW-1", "project": "TCW", "status": "Triage", "labels": ["ui"],
     ITEM: "tcw/TCW-1-a", "created": "2026-01-02"},
    {"key": "TCW-2", "project": "TCW", "status": "Done", "labels": ["UI", "api"],
     ITEM: "tcw/TCW-2-b", "created": "2026-01-01", "parent": "TCW-1"},
    {"key": "TCW-3", "project": "TCW", "status": "To Do", "labels": [],
     ITEM: None, "created": "2026-01-03"},
    {"key": "WEB-1", "project": "WEB", "status": "Triage", "labels": ["ui"],
     ITEM: "web/WEB-1-c", "created": "2026-01-04"},
]


def keys(query, **kw):
    return [t["key"] for t in fake_jql.select(query, TICKETS, lambda t, n: t.get(n), **kw)]


def test_evaluation():
    assert keys(jql.item_query("TCW", ITEM)) == ["TCW-2", "TCW-1"]
    assert keys(jql.item_query("TCW", ITEM, not_statuses=["Done"])) == ["TCW-1"]
    assert keys(jql.item_query("TCW", ITEM, statuses=["Done"], parent="TCW-1")) == ["TCW-2"]
    assert keys(jql.item_query("TCW", ITEM, labels=["api", "ui"])) == ["TCW-2", "TCW-1"]
    assert keys(jql.inbox_query("TCW", ITEM, "To Do")) == ["TCW-3"]
    assert keys(jql.inbox_query("TCW", ITEM, "To Do", 'project = "WEB"')) == [
        "TCW-3", "WEB-1"]
    assert keys(jql.keys_query(["WEB-1", "TCW-9"])) == ["WEB-1"]


def test_labels_compare_exactly_unless_told_otherwise():
    query = jql.item_query("TCW", ITEM, labels=["ui"])
    assert keys(query) == ["TCW-1"]
    assert keys(query, ignore_label_case=True) == ["TCW-2", "TCW-1"]
