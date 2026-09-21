"""`work.tracker.pre-backlog`: taking a ticket out of a status that comes before the
backlog, such as Jira's `Triage`, before claiming it.

A project names each such status and the transition that takes a ticket from it to
`statuses.backlog`. Only then does a claim — from `start`, `link --sync-status`,
`sync`, `tracker import` or `inbox accept` — apply that transition first. Without
it the ticket stays where it is, and the refusal names the setting.
"""

from __future__ import annotations

import subprocess

import pytest
import yaml

from tcw.store.base import merge_tracker_blocks, parse_tracker_config, pre_backlog_entry
from tcw.validate import validate

VALID = {
    "provider": "jira-cloud",
    "base-url": "https://example.invalid",
    "candidate-query": "assignee = currentUser()",
    "credentials": {"email-env": "TCW_JIRA_EMAIL", "token-env": "TCW_JIRA_API_TOKEN"},
    "transitions": {"start": "Start Progress"},
}
BACKLOG_STATUSES = {"backlog": "To Do", "active": "In Progress", "review": "In Review",
                    "completed": "Done", "discarded": {"wontfix": "Won't Do"}}


def parsed(pre_backlog, statuses=BACKLOG_STATUSES):
    return parse_tracker_config({**VALID, "statuses": statuses, "pre-backlog": pre_backlog})


# ── Task 1: the setting ───────────────────────────────────────────────────────

@pytest.mark.parametrize("pre_backlog, statuses, key", [
    (["Triage"], BACKLOG_STATUSES, "work.tracker.pre-backlog"),
    ({"  ": "Accept"}, BACKLOG_STATUSES, "work.tracker.pre-backlog"),
    ({"Triage": 11}, BACKLOG_STATUSES, "work.tracker.pre-backlog.Triage"),
    ({"Triage": "Accept", "triage ": "Accept"}, BACKLOG_STATUSES,
     "work.tracker.pre-backlog."),
    ({"in progress": "Accept"}, BACKLOG_STATUSES, "work.tracker.pre-backlog.in progress"),
    ({"Won't Do": "Accept"}, BACKLOG_STATUSES, "work.tracker.pre-backlog.Won't Do"),
    ({"Triage": "Accept"}, {"active": "In Progress"}, "work.tracker.statuses.backlog"),
], ids=["not-a-mapping", "blank-status", "non-string-transition", "same-status-twice",
        "also-active", "also-a-discard-resolution", "no-backlog"])
def test_a_bad_pre_backlog_fails_closed_naming_the_key(pre_backlog, statuses, key):
    config, problems = parsed(pre_backlog, statuses)
    assert config is None
    assert any(p.startswith(key) for p in problems), problems


def test_a_valid_pre_backlog_parses():
    config, problems = parsed({" Triage ": " Accept "})
    assert problems == []
    assert config.pre_backlog == {"Triage": "Accept"}
    assert pre_backlog_entry(config.pre_backlog, "  triage ") == ("Triage", "Accept")
    assert pre_backlog_entry(config.pre_backlog, "To Do") == ("", "")


def test_no_pre_backlog_is_an_empty_mapping():
    config, problems = parse_tracker_config({**VALID, "statuses": BACKLOG_STATUSES})
    assert problems == [] and config.pre_backlog == {}


def test_validate_names_pre_backlog(tmp_path):
    from tcw.store.fs import init
    root = tmp_path / "node"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    init(["work"], root, project_id="probe")
    config = {"id": "probe", "work": {"tracker": {
        **VALID, "statuses": {"active": "In Progress"},
        "pre-backlog": {"Triage": "Accept"}}}}
    (root / "tcw-config.yaml").write_text(yaml.safe_dump(config, sort_keys=False),
                                          encoding="utf-8")
    problems = validate(root)
    assert any("work.tracker.statuses.backlog: required when pre-backlog is set" in p
               for p in problems), problems


def test_a_child_inherits_pre_backlog_entries():
    merged, _record, _whole = merge_tracker_blocks([
        ("child", {"pre-backlog": {"Needs Info": "Accept"}}),
        ("parent", {**VALID, "statuses": BACKLOG_STATUSES,
                    "pre-backlog": {"Triage": "Accept"}}),
    ])
    config, problems = parse_tracker_config(merged)
    assert problems == []
    assert config.pre_backlog == {"Triage": "Accept", "Needs Info": "Accept"}


# ── Task 2: the step, inside the claim ────────────────────────────────────────

from tcw.store.base import TrackerConfig  # noqa: E402
from tcw.tracker import intake, jira  # noqa: E402

import tracker_fake  # noqa: E402
from tracker_fake import BASE_URL, SYNC, FakeJira  # noqa: E402

A, B = "acct-a", "acct-b"
ID, TKEY = "10052", "TRI-6"
# `SYNC` with a triage column in front of it, as proposit-app's workflow has.
TRIAGE = {"Triage": [("11", "Accept", "To Do"), ("12", "Cancel", "Won't Do")], **SYNC}
ACCEPT_THEN_START = ["11", "21"]


def _config(pre_backlog, *, statuses=BACKLOG_STATUSES) -> TrackerConfig:
    return TrackerConfig(provider="jira-cloud", base_url=BASE_URL,
                         candidate_query="assignee = currentUser()",
                         email_env="TCW_A_EMAIL", token_env="TCW_PROBE_TOKEN",
                         start_transition="Start Progress", timeout_seconds=15,
                         statuses=statuses, pre_backlog=pre_backlog)


@pytest.fixture()
def fake(monkeypatch):
    monkeypatch.setenv("TCW_A_EMAIL", "a@example.test")
    monkeypatch.setenv("TCW_PROBE_TOKEN", "sentinel-token")
    fake = FakeJira(workflow=dict(TRIAGE))
    fake.account("a@example.test", A, "Alice")
    fake.account("b@example.test", B, "Bob")
    fake.ticket(id=ID, key=TKEY, summary="Waiting in triage", status="Triage")
    return fake.install(monkeypatch)


def _claim(pre_backlog={"Triage": "Accept"}, **config):
    client = jira.JiraClient(_config(pre_backlog, **config))
    return intake.claim(client, intake.read_ticket(client, TKEY))


REREAD = f"/rest/api/3/issue/{ID}?"      # the step's read-back is by id; the first read is by key


def post_fails(fake, number: int, error: Exception, *, apply_first: bool = False):
    """Make the `number`th transition POST (1-based) raise `error`, after applying it
    when `apply_first` — a request that landed but whose answer was lost."""
    answer, posts = fake.answer, []

    def failing(client, method, path, body):
        if method == "POST" and path.endswith("/transitions"):
            posts.append(path)
            if len(posts) == number:
                if apply_first:
                    answer(client, method, path, body)
                raise error
        return answer(client, method, path, body)

    fake.answer = failing


def test_an_unassigned_triage_ticket_is_accepted_then_claimed(fake):
    outcome = _claim()
    assert (outcome.row, outcome.claimed, outcome.left_status) == ("3a", True, "Triage")
    assert fake.applied == ACCEPT_THEN_START
    assert (fake.tickets[ID].status, fake.tickets[ID].assignee) == ("In Progress", A)


def test_a_triage_ticket_already_yours_is_accepted_then_claimed(fake):
    """The reporter's case: a creator is often the ticket's assignee, and today that
    is row 1e — "already held" — with the ticket left in Triage."""
    fake.tickets[ID].assignee = A
    outcome = _claim()
    assert (outcome.row, outcome.left_status) == ("3a", "Triage")
    assert fake.applied == ACCEPT_THEN_START


def test_without_the_setting_nothing_leaves_triage(fake):
    outcome = _claim(pre_backlog={})
    assert (outcome.row, outcome.claimed, outcome.left_status) == ("1f", False, "")
    assert fake.writes() == []


@pytest.mark.parametrize("case", ["held-by-another", "resolved"])
def test_another_holder_or_a_resolved_ticket_sends_nothing(fake, monkeypatch, case):
    if case == "held-by-another":
        fake.tickets[ID].assignee = B
    else:
        monkeypatch.setitem(tracker_fake.CATEGORY, "Triage", "done")
    outcome = _claim()
    assert outcome.row == ("1b" if case == "held-by-another" else "1a")
    assert outcome.left_status == ""
    assert fake.writes() == []


@pytest.mark.parametrize("case", ["taken", "resolved"])
def test_someone_acting_between_the_hops_is_refused_on_the_fresh_read(fake, monkeypatch,
                                                                     case):
    """Everything after the step is decided from the read taken after it. Reusing
    the read from before would claim a ticket Bob took, or one somebody closed."""
    def meanwhile():
        if case == "taken":
            fake.tickets[ID].assignee = B
        else:
            monkeypatch.setitem(tracker_fake.CATEGORY, "To Do", "done")
    fake.before("GET", REREAD, meanwhile)
    outcome = _claim()
    assert (outcome.row, outcome.claimed) == ("1b" if case == "taken" else "1a", False)
    if case == "taken":
        assert "Bob" in outcome.message
    assert outcome.left_status == "Triage"
    assert fake.applied == ["11"]
    assert fake.tickets[ID].status == "To Do"


@pytest.mark.parametrize("case", ["not-offered", "leads-elsewhere", "offered-twice"])
def test_a_misconfigured_step_sends_nothing(fake, case):
    pre_backlog = {"Triage": "Accept"}
    if case == "not-offered":
        pre_backlog = {"Triage": "Approve"}
    elif case == "leads-elsewhere":
        fake.workflow["Triage"] = [("11", "Accept", "In Review")]
    else:
        fake.workflow["Triage"] = [("11", "Accept", "To Do"), ("13", "Accept", "To Do")]
    outcome = _claim(pre_backlog=pre_backlog)
    assert (outcome.row, outcome.claimed, outcome.left_status) == ("0a", False, "")
    assert "work.tracker.pre-backlog.Triage" in outcome.message
    assert fake.writes() == []
    if case == "offered-twice":
        assert "11, 13" in outcome.message
    else:
        assert "It offers:" in outcome.message


def test_the_step_is_chosen_by_status_not_by_transition_name(fake):
    """A status that is not a `pre-backlog` key gets no step, even when it offers a
    transition of the configured name."""
    fake.tickets[ID].status = "To Do"
    fake.workflow["To Do"] = [("21", "Start Progress", "In Progress"),
                              ("11", "Accept", "Later")]
    outcome = _claim()
    assert "11" not in fake.applied
    assert (outcome.row, outcome.left_status) == ("3a", "")


def test_the_configured_status_is_matched_as_statuses_are(fake):
    outcome = _claim(pre_backlog={"triage": "Accept"})
    assert (outcome.row, outcome.left_status) == ("3a", "triage")
    assert fake.applied == ACCEPT_THEN_START


def test_an_unanswered_accept_that_did_not_land_is_pending(fake):
    post_fails(fake, 1, jira.TrackerUnavailable("could not be reached (fake)"))
    outcome = _claim()
    assert (outcome.row, outcome.claimed, outcome.left_status) == ("0f", False, "")
    assert fake.tickets[ID].status == "Triage"


def test_an_unanswered_accept_that_landed_carries_on(fake):
    post_fails(fake, 1, jira.TrackerUnavailable("could not be reached (fake)"),
               apply_first=True)
    outcome = _claim()
    assert (outcome.row, outcome.left_status) == ("3a", "Triage")


def test_a_refused_accept_is_conflicting(fake):
    post_fails(fake, 1, jira.TrackerRequestInvalid("Action 11 is invalid"))
    outcome = _claim()
    assert (outcome.row, outcome.claimed, outcome.left_status) == ("0d", False, "")


def test_a_failed_read_back_after_accept_is_pending_and_says_it_was_sent(fake):
    fake.fail("GET", REREAD, jira.TrackerUnavailable("could not be reached (fake)"))
    outcome = _claim()
    assert (outcome.row, outcome.claimed, outcome.left_status) == ("0-read", False, "Triage")
    assert "'Accept' was sent" in outcome.message
    assert fake.applied == ["11"]


def test_an_accept_landing_somewhere_else_is_conflicting(fake):
    fake.before("GET", REREAD, lambda: setattr(fake.tickets[ID], "status", "In Review"))
    outcome = _claim()
    assert (outcome.row, outcome.claimed, outcome.left_status) == ("0b", False, "Triage")
    assert "'In Review'" in outcome.message


def test_a_claim_that_raises_after_the_step_carries_left_status(fake):
    post_fails(fake, 2, jira.TrackerRateLimited("slow down (fake)"))
    with pytest.raises(jira.TrackerRateLimited) as raised:
        _claim()
    assert raised.value.left_status == "Triage"
    assert fake.tickets[ID].status == "To Do"


def test_row_1f_names_pre_backlog_only_for_an_unmapped_status(fake):
    outcome = _claim(pre_backlog={})
    assert "work.tracker.pre-backlog" in outcome.message
    assert "'Triage' is where tickets wait before your backlog" in outcome.message
    fake.tickets[ID].status = "To Do"
    fake.workflow["To Do"] = []
    outcome = _claim(pre_backlog={})
    assert outcome.row == "1f"
    assert "pre-backlog" not in outcome.message
