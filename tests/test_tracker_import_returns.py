"""`import` and `inbox accept` put a ticket their claim moved back where the claim
found it, so it reads as not started, like the backlog item they create.

The claim itself still moves the ticket first: that transition is what keeps two
people importing the same ticket apart. Only once the item exists and is bound is
the ticket put back — and only when this run moved it, never under strict mode, and
never at the cost of the import: a ticket that cannot go back is a warning.
"""

from __future__ import annotations

import pytest

from tcw.store.fs import FsWorkStore
from tcw.tracker.jira import TrackerUnavailable
from test_tracker_pre_backlog import TRIAGE, post_fails, set_pre_backlog
from test_tracker_strict import set_tracker_key, strict_node
from test_tracker_sync import A, KEY, SENTINEL, TICKET_ID, cli, ladder_node
from tracker_fake import SYNC, FakeJira

STOP = ("71", "Stop", "To Do")
# `SYNC` with a way back from the working statuses to the backlog, as the TCW Jira
# workflow has had since 2026-09-24.
WITH_STOP = {**SYNC, "In Progress": [*SYNC["In Progress"], STOP],
             "In Review": [*SYNC["In Review"], STOP]}
START, BACK = "21", "71"
TRANSITIONS = f"/rest/api/3/issue/{TICKET_ID}/transitions"
ASSIGNEE = f"/rest/api/3/issue/{TICKET_ID}/assignee"


def items(root):
    return FsWorkStore.open(root).board()


def ticket(fake_):
    t = fake_.tickets[TICKET_ID]
    return t.status, t.assignee


def warnings(err: str) -> list[str]:
    return [line for line in err.splitlines() if line.startswith("warning:")]


@pytest.mark.parametrize("verb", [("tracker", "import"), ("inbox", "accept")])
def test_the_ticket_goes_back_to_where_the_claim_found_it(tmp_path, monkeypatch, verb):
    root, fake_ = ladder_node(tmp_path, monkeypatch, dict(WITH_STOP))
    set_tracker_key(root, "inbox-query", "project = SYNC")
    code, out, err = cli(root, "work", *verb, KEY)
    assert code == 0, err
    [item] = items(root)
    assert item.status == "backlog" and item.tracker is not None
    assert ticket(fake_) == ("To Do", A)
    assert fake_.applied == [START, BACK]
    assert fake_.writes() == [("POST", TRANSITIONS), ("PUT", ASSIGNEE),
                              ("POST", TRANSITIONS)]
    assert f"{KEY} is in 'To Do', claimed by this run" in err
    assert warnings(err) == []


def test_a_ticket_taken_out_of_triage_goes_back_to_the_backlog_not_triage(
        tmp_path, monkeypatch):
    workflow = {**TRIAGE, "In Progress": [*TRIAGE["In Progress"], STOP]}
    root, fake_ = ladder_node(tmp_path, monkeypatch, workflow, status="Triage")
    set_pre_backlog(root, {"Triage": "Accept"})
    code, _out, err = cli(root, "work", "tracker", "import", KEY)
    assert code == 0, err
    assert ticket(fake_) == ("To Do", A)
    assert fake_.applied == ["11", START, BACK]


def test_a_ticket_already_yours_and_under_way_is_left_alone(tmp_path, monkeypatch):
    root, fake_ = ladder_node(tmp_path, monkeypatch, dict(WITH_STOP),
                              status="In Progress", assignee=A)
    code, _out, err = cli(root, "work", "tracker", "import", KEY)
    assert code == 0, err
    assert len(items(root)) == 1
    assert ticket(fake_) == ("In Progress", A)
    assert fake_.writes() == []
    # Not even asked about: the claim's own read is the only one, so a tracker that
    # fails afterwards cannot turn work already under way into a warning.
    assert [p for m, p, _a in fake_.requests
            if m == "GET" and p == TRANSITIONS] == [TRANSITIONS]


def test_a_workflow_with_no_way_back_warns_and_still_imports(tmp_path, monkeypatch):
    root, fake_ = ladder_node(tmp_path, monkeypatch, dict(SYNC))
    code, _out, err = cli(root, "work", "tracker", "import", KEY)
    assert code == 0, err
    [item] = items(root)
    assert item.tracker is not None
    assert ticket(fake_) == ("In Progress", A)
    assert fake_.applied == [START]
    [warning] = warnings(err)
    assert KEY in warning and "'In Progress'" in warning and "backlog" in warning
    assert ".." not in warning
    assert f"{KEY} is in 'In Progress', claimed by this run" in err


def test_a_tracker_error_on_the_way_back_warns_and_still_imports(tmp_path, monkeypatch):
    root, fake_ = ladder_node(tmp_path, monkeypatch, dict(WITH_STOP))
    post_fails(fake_, 2, TrackerUnavailable("the tracker went away (fake)"))
    code, _out, err = cli(root, "work", "tracker", "import", KEY)
    assert code == 0, err
    [item] = items(root)
    assert item.tracker is not None
    assert ticket(fake_) == ("In Progress", A)
    [warning] = warnings(err)
    assert KEY in warning and "went away" in warning


def test_strict_mode_leaves_the_ticket_where_the_claim_put_it(tmp_path, monkeypatch):
    monkeypatch.setenv("TCW_A_EMAIL", "a@example.test")
    monkeypatch.setenv("TCW_PROBE_TOKEN", SENTINEL)
    monkeypatch.setenv("TCW_WORK_OWNER", "a@example.test")
    fake_ = FakeJira(workflow=dict(WITH_STOP))
    fake_.account("a@example.test", A, "Alice")
    fake_.ticket(id=TICKET_ID, key=KEY, summary="t")
    fake_.install(monkeypatch)
    root = strict_node(tmp_path, strict=True, claim_transition="Start Progress")
    code, _out, err = cli(root, "work", "tracker", "import", KEY)
    assert code == 0, err
    assert len(items(root)) == 1
    assert ticket(fake_) == ("In Progress", A)
    assert fake_.applied == [START]


def test_a_ticket_moved_by_someone_else_during_the_claim_is_left_alone(
        tmp_path, monkeypatch):
    """The claim still counts — the ticket is yours and where the claim leads — but
    this run's transition did not move it: somebody else did. That is work under
    way, not a move of ours to undo."""
    root, fake_ = ladder_node(tmp_path, monkeypatch, dict(WITH_STOP), assignee=A)

    def moved_first():
        fake_.tickets[TICKET_ID].status = "In Progress"

    fake_.before("POST", "/transitions", moved_first)
    code, _out, err = cli(root, "work", "tracker", "import", KEY)
    assert code == 0, err
    assert len(items(root)) == 1
    assert ticket(fake_) == ("In Progress", A)
    assert fake_.applied == []


def test_an_unanswered_way_back_reports_where_the_ticket_really_is(tmp_path, monkeypatch):
    root, fake_ = ladder_node(tmp_path, monkeypatch, dict(WITH_STOP))
    post_fails(fake_, 2, TrackerUnavailable("no answer (fake)"), apply_first=True)
    code, _out, err = cli(root, "work", "tracker", "import", KEY)
    assert code == 0, err
    assert ticket(fake_) == ("To Do", A)
    assert f"{KEY} is in 'To Do', claimed by this run" in err
    assert warnings(err) == []


def test_starting_an_imported_item_moves_its_ticket_on(tmp_path, monkeypatch):
    root, fake_ = ladder_node(tmp_path, monkeypatch, dict(WITH_STOP))
    code, out, err = cli(root, "work", "tracker", "import", KEY)
    assert code == 0, err
    code, _out, err = cli(root, "work", "start", out.strip())
    assert code == 0, err
    assert ticket(fake_) == ("In Progress", A)
    assert fake_.applied == [START, BACK, START]
