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


def test_a_failed_read_back_after_accept_is_pending_and_says_it_applied(fake):
    fake.fail("GET", REREAD, jira.TrackerUnavailable("could not be reached (fake)"))
    outcome = _claim()
    assert (outcome.row, outcome.claimed, outcome.left_status) == ("0-read", False, "Triage")
    assert "'Accept' applied, but" in outcome.message
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


# ── Task 3: through `deliver` — link, sync, start, and the moves that owe a claim ──

from test_tracker_sync import (KEY, STATUSES, TICKET_ID, binding_text,  # noqa: E402
                               cli, ladder_node, record, sync_link, transitions_fail,
                               under_way, with_record)
from tcw.store.fs import FsWorkStore  # noqa: E402

WITH_BACKLOG = {**STATUSES, "backlog": "To Do"}
MOVED = "moved out of 'Triage'"
HINT = "work.tracker.pre-backlog"


def set_pre_backlog(root, value) -> None:
    """Map `statuses.backlog` and set (or, with `None`, remove) `pre-backlog`."""
    path = root / "tcw-config.yaml"
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    tracker = config["work"]["tracker"]
    tracker["statuses"] = dict(WITH_BACKLOG)
    tracker.pop("pre-backlog", None)
    if value is not None:
        tracker["pre-backlog"] = value
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "pre-backlog"],
                   check=True)


def triage_node(tmp_path, monkeypatch, *, assignee, pre_backlog, workflow=TRIAGE,
                status="Triage"):
    root, fake_ = ladder_node(tmp_path, monkeypatch, dict(workflow), status=status,
                              assignee=assignee)
    set_pre_backlog(root, pre_backlog)
    return root, fake_


def set_binding_key(root, slug, key, value) -> None:
    st = FsWorkStore.open(root)
    content = yaml.safe_load(binding_text(root, slug))
    content[key] = value
    (st.path(slug) / "tracker.yaml").write_text(yaml.safe_dump(content, sort_keys=False),
                                                encoding="utf-8")


def plain_link(root, slug, *extra):
    code, _out, err = cli(root, "work", "tracker", "link", slug, KEY, *extra)
    assert code == 0, err


@pytest.mark.parametrize("assignee", [None, A], ids=["unassigned", "already-yours"])
def test_link_sync_status_accepts_then_claims(tmp_path, monkeypatch, assignee):
    root, fake_ = triage_node(tmp_path, monkeypatch, assignee=assignee,
                              pre_backlog={"Triage": "Accept"})
    slug = under_way(root)
    code, _out, err = sync_link(root, slug)
    assert code == 0, err
    ticket = fake_.tickets[TICKET_ID]
    assert (ticket.status, ticket.assignee) == ("In Progress", A)
    assert fake_.applied == ACCEPT_THEN_START
    assert MOVED in err
    assert "not brought forward" not in err


def test_sync_finishes_an_owed_catch_up_from_triage(tmp_path, monkeypatch):
    """A catch-up whose first attempt never got `Accept` through is finished by
    `sync`, walking on up a workflow with no shortcut."""
    from tracker_fake import STRICT_LADDER
    root, fake_ = triage_node(tmp_path, monkeypatch, assignee=None,
                              pre_backlog={"Triage": "Accept"},
                              workflow={**STRICT_LADDER, "Triage": TRIAGE["Triage"]})
    slug = under_way(root, "review")
    restore = transitions_fail(fake_, 1)
    code, _out, err = sync_link(root, slug)
    assert code == 1, err
    assert record(root, slug)["state"] == "pending"
    assert fake_.tickets[TICKET_ID].status == "Triage"
    restore()
    code, _out, err = cli(root, "work", "tracker", "sync", slug)
    assert code == 0, err
    assert fake_.applied == ["11", "21", "41"]
    assert fake_.tickets[TICKET_ID].status == "In Review"


def test_start_accepts_then_claims(tmp_path, monkeypatch):
    root, fake_ = triage_node(tmp_path, monkeypatch, assignee=None,
                              pre_backlog={"Triage": "Accept"})
    slug = FsWorkStore.open(root).create("Waiting in triage").slug
    plain_link(root, slug)
    code, _out, err = cli(root, "work", "start", slug)
    assert code == 0, err
    assert fake_.tickets[TICKET_ID].status == "In Progress"
    assert fake_.applied == ACCEPT_THEN_START
    assert MOVED in err


def test_a_claim_refused_after_the_step_is_resumed_by_sync(tmp_path, monkeypatch):
    root, fake_ = triage_node(tmp_path, monkeypatch, assignee=None,
                              pre_backlog={"Triage": "Accept"})
    slug = under_way(root)
    to_do = fake_.workflow["To Do"]
    fake_.workflow["To Do"] = []                  # the start transition, refused once
    code, _out, err = sync_link(root, slug)
    assert code == 1, err
    assert fake_.tickets[TICKET_ID].status == "To Do"
    assert MOVED in err
    assert record(root, slug)["state"] == "conflicting"
    fake_.workflow["To Do"] = to_do
    code, _out, err = cli(root, "work", "tracker", "sync", slug)
    assert code == 0, err
    assert fake_.applied == ACCEPT_THEN_START           # no second Accept
    assert fake_.tickets[TICKET_ID].status == "In Progress"


def test_a_step_that_may_not_have_applied_is_recorded_pending(tmp_path, monkeypatch):
    from tcw.tracker.jira import TrackerUnavailable
    root, fake_ = triage_node(tmp_path, monkeypatch, assignee=None,
                              pre_backlog={"Triage": "Accept"})
    slug = FsWorkStore.open(root).create("Waiting in triage").slug
    plain_link(root, slug)
    post_fails(fake_, 1, TrackerUnavailable("could not be reached (fake)"))
    code, _out, err = cli(root, "work", "start", slug)
    assert code == 1, err
    assert record(root, slug)["state"] == "pending"
    assert fake_.tickets[TICKET_ID].status == "Triage"


def test_a_claim_raising_after_the_step_still_reports_the_move(tmp_path, monkeypatch):
    from tcw.tracker.jira import TrackerRateLimited
    root, fake_ = triage_node(tmp_path, monkeypatch, assignee=None,
                              pre_backlog={"Triage": "Accept"})
    slug = under_way(root)
    post_fails(fake_, 2, TrackerRateLimited("slow down (fake)"))
    code, _out, err = sync_link(root, slug)
    assert code == 1, err
    assert fake_.tickets[TICKET_ID].status == "To Do"
    assert MOVED in err


@pytest.mark.parametrize("move", ["submit", "rework", "complete"])
@pytest.mark.parametrize("recorded", [False, True], ids=["no-record", "record-for-submit"])
def test_moves_with_no_claim_owed_never_accept(tmp_path, monkeypatch, move, recorded):
    """A ticket TCW already holds, found back in Triage, is drift: only a claim
    takes a ticket out of triage."""
    root, fake_ = triage_node(tmp_path, monkeypatch, assignee=A,
                              pre_backlog={"Triage": "Accept"},
                              status="In Progress" if move == "submit" else "In Review")
    slug = under_way(root, "active" if move == "submit" else "review")
    plain_link(root, slug)
    if recorded:
        with_record(root, slug, {"state": "pending", "move": "submit",
                                 "since": "In Progress", "reason": "x",
                                 "at": "2026-09-21T00:00:00Z"})
    fake_.tickets[TICKET_ID].status = "Triage"
    argv = {"submit": ("submit",), "rework": ("rework",),
            "complete": ("complete", "--resolution", "done", "--confirm", "--force")}
    cli(root, "work", *argv[move][:1], slug, *argv[move][1:])
    assert "11" not in fake_.applied
    assert fake_.tickets[TICKET_ID].status == "Triage"


@pytest.mark.parametrize("owed", ["catch-up", "start-record"])
def test_a_submit_that_owes_the_claim_accepts_then_claims(tmp_path, monkeypatch, owed):
    """A claim still owed is the same debt `sync` settles, so the move that pays it
    takes the ticket out of triage first."""
    root, fake_ = triage_node(tmp_path, monkeypatch, assignee=None,
                              pre_backlog={"Triage": "Accept"})
    slug = under_way(root)
    plain_link(root, slug)
    if owed == "catch-up":
        set_binding_key(root, slug, "catch-up", True)
    else:
        with_record(root, slug, {"state": "pending", "move": "start", "since": "",
                                 "reason": "x", "at": "2026-09-21T00:00:00Z"})
    code, _out, err = cli(root, "work", "submit", slug)
    assert code == 0, err
    assert fake_.applied[:2] == ACCEPT_THEN_START
    assert fake_.tickets[TICKET_ID].status == "In Review"


def test_a_discard_never_accepts(tmp_path, monkeypatch):
    root, fake_ = triage_node(tmp_path, monkeypatch, assignee=None,
                              pre_backlog={"Triage": "Accept"})
    slug = FsWorkStore.open(root).create("Never started").slug
    plain_link(root, slug)
    cli(root, "work", "complete", slug, "--resolution", "wontfix", "--confirm", "--force")
    assert "11" not in fake_.applied


def test_a_part_bound_report_only_sync_sends_nothing(tmp_path, monkeypatch):
    root, fake_ = triage_node(tmp_path, monkeypatch, assignee=None,
                              pre_backlog={"Triage": "Accept"})
    slug = under_way(root)
    plain_link(root, slug, "--part", "api")
    set_binding_key(root, slug, "catch-up", True)
    cli(root, "work", "tracker", "sync", slug)
    assert fake_.applied == []


def test_without_the_setting_the_reporters_case_names_it(tmp_path, monkeypatch):
    root, fake_ = triage_node(tmp_path, monkeypatch, assignee=A, pre_backlog=None)
    slug = under_way(root)
    code, _out, err = sync_link(root, slug)
    assert code == 1, err
    assert fake_.applied == []
    assert "offers no transition named 'Start Progress'" in err
    assert HINT in err and HINT in record(root, slug)["reason"]


def test_a_claim_landing_off_the_ladder_does_not_name_pre_backlog(tmp_path, monkeypatch):
    """The claim transition itself led to an unmapped status; naming `pre-backlog`
    there would be wrong advice."""
    workflow = {"To Do": [("21", "Start Progress", "Triage")],
                "Triage": [("22", "Begin", "In Progress")],
                "In Progress": [("31", "Finish", "Done")], "Done": []}
    root, fake_ = triage_node(tmp_path, monkeypatch, assignee=None, pre_backlog=None,
                              workflow=workflow, status="To Do")
    slug = under_way(root)
    code, _out, err = sync_link(root, slug)
    assert code == 1, err
    assert fake_.applied == ["21"]
    assert "not brought forward from there" in err
    assert "pre-backlog" not in err


# ── Task 4: strict start, import, inbox accept, `tracker claim`, `show` ────────

from test_tracker_strict import set_tracker_key  # noqa: E402


def items(root):
    return FsWorkStore.open(root).board()


def test_strict_start_accepts_then_claims(tmp_path, monkeypatch):
    root, fake_ = ladder_node(tmp_path, monkeypatch, dict(TRIAGE), status="Triage")
    set_tracker_key(root, "strict", True)
    set_tracker_key(root, "exclusive-claim-transition", "Start Progress")
    set_pre_backlog(root, {"Triage": "Accept"})
    slug = FsWorkStore.open(root).create("Waiting in triage").slug
    plain_link(root, slug)
    code, _out, err = cli(root, "work", "start", slug)
    assert code == 0, err
    assert fake_.tickets[TICKET_ID].status == "In Progress"
    assert fake_.applied == ACCEPT_THEN_START
    assert MOVED in err


def test_strict_start_refused_after_the_step_is_retried_by_start(tmp_path, monkeypatch):
    """A strict refusal happens before the item moves and writes no sync record, so
    `sync` has nothing to resume: the refusal says to start again, and that works."""
    root, fake_ = ladder_node(tmp_path, monkeypatch, dict(TRIAGE), status="Triage")
    set_tracker_key(root, "strict", True)
    set_tracker_key(root, "exclusive-claim-transition", "Start Progress")
    set_pre_backlog(root, {"Triage": "Accept"})
    slug = FsWorkStore.open(root).create("Waiting in triage").slug
    plain_link(root, slug)
    to_do = fake_.workflow["To Do"]
    fake_.workflow["To Do"] = []
    code, _out, err = cli(root, "work", "start", slug)
    assert code == 1, err
    assert FsWorkStore.open(root).get(slug).status == "backlog"
    assert record(root, slug) is None
    assert MOVED in err and f"tcw work start {slug}` again" in err
    fake_.workflow["To Do"] = to_do
    code, _out, err = cli(root, "work", "start", slug)
    assert code == 0, err
    assert fake_.applied == ACCEPT_THEN_START


@pytest.mark.parametrize("verb", [("tracker", "import"), ("inbox", "accept")])
def test_import_and_inbox_accept_accept_then_claim(tmp_path, monkeypatch, verb):
    root, fake_ = ladder_node(tmp_path, monkeypatch, dict(TRIAGE), status="Triage")
    set_tracker_key(root, "inbox-query", "project = SYNC AND status = Triage")
    set_pre_backlog(root, {"Triage": "Accept"})
    code, _out, err = cli(root, "work", *verb, KEY)
    assert code == 0, err
    assert len(items(root)) == 1 and items(root)[0].tracker is not None
    assert fake_.applied == ACCEPT_THEN_START
    assert MOVED in err


def test_import_of_a_triage_ticket_already_yours(tmp_path, monkeypatch):
    root, fake_ = triage_node(tmp_path, monkeypatch, assignee=A,
                              pre_backlog={"Triage": "Accept"})
    code, _out, err = cli(root, "work", "tracker", "import", KEY)
    assert code == 0, err
    assert fake_.applied == ACCEPT_THEN_START
    assert "warning:" not in err


def test_without_the_setting_import_of_a_triage_ticket_already_yours_warns(tmp_path,
                                                                          monkeypatch):
    """Today's behaviour is kept — the item is made and the ticket stays in Triage —
    and it now says why, and what would change it."""
    root, fake_ = triage_node(tmp_path, monkeypatch, assignee=A, pre_backlog=None)
    code, _out, err = cli(root, "work", "tracker", "import", KEY)
    assert code == 0, err
    assert len(items(root)) == 1
    assert fake_.tickets[TICKET_ID].status == "Triage"
    assert fake_.applied == []
    assert f"warning: {KEY} stays in 'Triage'." in err and HINT in err


def test_import_refused_after_the_step_is_retried_by_import(tmp_path, monkeypatch):
    root, fake_ = triage_node(tmp_path, monkeypatch, assignee=None,
                              pre_backlog={"Triage": "Accept"})
    to_do = fake_.workflow["To Do"]
    fake_.workflow["To Do"] = []
    code, _out, err = cli(root, "work", "tracker", "import", KEY)
    assert code == 1, err
    assert items(root) == []
    assert MOVED in err
    assert fake_.tickets[TICKET_ID].status == "To Do"
    fake_.workflow["To Do"] = to_do
    code, _out, err = cli(root, "work", "tracker", "import", KEY)
    assert code == 0, err
    assert fake_.applied == ACCEPT_THEN_START
    assert len(items(root)) == 1


def test_import_that_raises_after_the_step_reports_the_move(tmp_path, monkeypatch):
    from tcw.tracker.jira import TrackerRateLimited
    root, fake_ = triage_node(tmp_path, monkeypatch, assignee=None,
                              pre_backlog={"Triage": "Accept"})
    post_fails(fake_, 2, TrackerRateLimited("slow down (fake)"))
    code, _out, err = cli(root, "work", "tracker", "import", KEY)
    assert code == 1, err
    assert MOVED in err and "slow down" in err
    assert items(root) == []


def test_without_the_setting_import_names_it(tmp_path, monkeypatch):
    root, fake_ = triage_node(tmp_path, monkeypatch, assignee=None, pre_backlog=None)
    code, _out, err = cli(root, "work", "tracker", "import", KEY)
    assert code == 1, err
    assert fake_.applied == []
    assert "does not offer 'Start Progress'" in err and HINT in err


def test_tracker_claim_moves_nothing(tmp_path, monkeypatch):
    """`tracker claim` asserts ownership and never moves a status, triage or not."""
    root, fake_ = triage_node(tmp_path, monkeypatch, assignee=None,
                              pre_backlog={"Triage": "Accept"})
    slug = FsWorkStore.open(root).create("Waiting in triage").slug
    plain_link(root, slug)
    code, _out, err = cli(root, "work", "tracker", "claim", slug)
    assert code == 0, err
    ticket = fake_.tickets[TICKET_ID]
    assert (ticket.status, ticket.assignee) == ("Triage", A)
    assert fake_.applied == []


def test_import_of_an_already_bound_ticket_moves_nothing(tmp_path, monkeypatch):
    root, fake_ = triage_node(tmp_path, monkeypatch, assignee=None,
                              pre_backlog={"Triage": "Accept"})
    slug = FsWorkStore.open(root).create("Waiting in triage").slug
    plain_link(root, slug)
    code, _out, err = cli(root, "work", "tracker", "import", KEY)
    assert code == 1, err
    assert "already linked" in err
    assert fake_.applied == []


def test_show_notes_the_step(tmp_path, monkeypatch):
    root, _fake = triage_node(tmp_path, monkeypatch, assignee=None,
                              pre_backlog={"Triage": "Accept"})
    code, out, err = cli(root, "work", "tracker", "show", KEY)
    assert code == 0, err
    assert "note: a claim first takes it out of 'Triage' through 'Accept'." in out


# ── verify: what `tcw work start` prints, read whole ─────────────────────────

def started_from_triage(tmp_path, monkeypatch):
    """A backlog item bound to an unassigned Triage ticket, ready for `start`."""
    root, fake_ = triage_node(tmp_path, monkeypatch, assignee=None,
                              pre_backlog={"Triage": "Accept"})
    fake_.account("b@example.test", B, "Bob")
    slug = FsWorkStore.open(root).create("Waiting in triage").slug
    plain_link(root, slug)
    return root, fake_, slug


def around_first_post(fake_, *, answer_it=True, then=None):
    """Wrap the first transition POST: answer it or not (a request that never got a
    reply), then run `then` — something another person or a workflow rule did."""
    answer, posts = fake_.answer, []

    def wrapped(client, method, path, body):
        if method == "POST" and path.endswith("/transitions"):
            posts.append(path)
            if len(posts) == 1:
                result = answer(client, method, path, body) if answer_it else (204, {}, b"")
                if then is not None:
                    then()
                return result
        return answer(client, method, path, body)

    fake_.answer = wrapped


def fail_reads_after_first_post(fake_, error):
    answer, posted = fake_.answer, []

    def wrapped(client, method, path, body):
        if method == "POST" and path.endswith("/transitions"):
            posted.append(path)
        elif method == "GET" and posted and "/transitions" not in path \
                and "/myself" not in path:
            raise error
        return answer(client, method, path, body)

    fake_.answer = wrapped


def test_a_ticket_taken_between_the_hops_is_not_advised_to_be_claimed(tmp_path,
                                                                     monkeypatch):
    root, fake_, slug = started_from_triage(tmp_path, monkeypatch)
    around_first_post(fake_, then=lambda: setattr(fake_.tickets[TICKET_ID], "assignee", B))
    code, _out, err = cli(root, "work", "start", slug)
    assert code == 1, err
    assert f"{KEY} was moved out of 'Triage'." in err
    assert "assigned to Bob" in err
    assert "tcw work tracker claim" not in err


def test_an_accept_landing_elsewhere_does_not_claim_it_reached_the_backlog(tmp_path,
                                                                         monkeypatch):
    root, fake_, slug = started_from_triage(tmp_path, monkeypatch)
    around_first_post(fake_, then=lambda: setattr(fake_.tickets[TICKET_ID], "status",
                                                  "In Review"))
    code, _out, err = cli(root, "work", "start", slug)
    assert code == 1, err
    assert f"{KEY} was moved out of 'Triage'." in err
    assert "it is in 'In Review'" in err
    assert "to the backlog status first" not in err
    assert "tcw work tracker claim" not in err


def test_an_unanswered_accept_that_cannot_be_read_back_is_not_called_a_move(tmp_path,
                                                                          monkeypatch):
    from tcw.tracker.jira import TrackerUnavailable
    root, fake_, slug = started_from_triage(tmp_path, monkeypatch)
    post_fails(fake_, 1, TrackerUnavailable("no answer (fake)"))
    fail_reads_after_first_post(fake_, TrackerUnavailable("no answer (fake)"))
    code, _out, err = cli(root, "work", "start", slug)
    assert code == 1, err
    assert "'Accept' was sent; whether it applied is unknown" in err
    assert "moved out of" not in err
    assert "tcw work tracker claim" not in err
    assert f"Run `tcw work tracker sync {slug}`" in err
    assert record(root, slug)["state"] == "pending"


def test_an_uncertain_accept_points_at_sync_not_at_rerunning_start(tmp_path, monkeypatch):
    from tcw.tracker.jira import TrackerUnavailable
    root, fake_, slug = started_from_triage(tmp_path, monkeypatch)
    post_fails(fake_, 1, TrackerUnavailable("no answer (fake)"))
    code, _out, err = cli(root, "work", "start", slug)
    assert code == 1, err
    assert f"Run `tcw work tracker sync {slug}`" in err
    assert "Running this command again" not in err
    assert "tcw work tracker claim" not in err
    assert record(root, slug)["state"] == "pending"


def test_an_accept_the_tracker_took_but_did_not_apply_says_so(tmp_path, monkeypatch):
    root, fake_, slug = started_from_triage(tmp_path, monkeypatch)
    around_first_post(fake_, answer_it=False)
    code, _out, err = cli(root, "work", "start", slug)
    assert code == 1, err
    assert "the tracker accepted 'Accept', but" in err
    assert "is still in 'Triage'" in err
    assert "could not tell whether" not in err
    assert "tcw work tracker claim" not in err
    assert record(root, slug)["state"] == "conflicting"
