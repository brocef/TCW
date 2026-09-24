"""The claim: read the ticket, apply the claim transition, assign, read back.

Every test asserts the decision by its row id from the spec's tables, and the write
requests that were sent, rather than message wording. Three properties carry the
design and each has a mutation check recorded in the item's outcome:

- **Assign only after an applied transition.** On a workflow that excludes a second
  claimant, that is what stops a loser from ever overwriting the winner's
  assignment.
- **The read-back requires the landing status, not only the assignee.** A refused
  transition on a ticket already assigned to you must not count as a claim.
- **No refusal tells an arbitrary reader to assign the ticket to themselves**,
  except where this run's own transition is the one that moved it.
"""

from __future__ import annotations

import pytest

from tcw.store.base import TrackerConfig
from tcw.tracker import intake, jira
from tracker_fake import BASE_URL, GLOBAL, FakeJira

A, B = "acct-a", "acct-b"


def _config(email_env: str) -> TrackerConfig:
    return TrackerConfig(provider="jira-cloud", base_url=BASE_URL,
                         candidate_query="assignee = currentUser()",
                         email_env=email_env, token_env="TCW_PROBE_TOKEN",
                         start_transition="Start Progress", timeout_seconds=15)


@pytest.fixture()
def fake(monkeypatch):
    monkeypatch.setenv("TCW_A_EMAIL", "a@example.test")
    monkeypatch.setenv("TCW_B_EMAIL", "b@example.test")
    monkeypatch.setenv("TCW_PROBE_TOKEN", "sentinel-token")
    fake = FakeJira()
    fake.account("a@example.test", A, "Alice")
    fake.account("b@example.test", B, "Bob")
    fake.ticket(id="10052", key="TCWCLAIM-6", summary="A ready ticket")
    return fake.install(monkeypatch)


@pytest.fixture()
def alice():
    return jira.JiraClient(_config("TCW_A_EMAIL"))


@pytest.fixture()
def bob():
    return jira.JiraClient(_config("TCW_B_EMAIL"))


def _claim(client, key="TCWCLAIM-6"):
    return intake.claim(client, intake.read_ticket(client, key))


TRANSITION = ("POST", "/rest/api/3/issue/10052/transitions")
ASSIGN = ("PUT", "/rest/api/3/issue/10052/assignee")


# ── the ordinary paths ───────────────────────────────────────────────────────


def test_a_ready_unassigned_ticket_is_transitioned_then_assigned(fake, alice):
    outcome = _claim(alice)
    assert (outcome.row, outcome.claimed, outcome.transitioned) == ("3a", True, True)
    assert fake.writes() == [TRANSITION, ASSIGN]
    ticket = fake.tickets["10052"]
    assert (ticket.status, ticket.assignee) == ("In Progress", A)
    assert (outcome.issue_id, outcome.key, outcome.account_id) == ("10052", "TCWCLAIM-6", A)
    assert outcome.url == f"{BASE_URL}/browse/TCWCLAIM-6"


def test_a_claim_records_the_status_it_found_the_ticket_in(fake, alice):
    """What `import` puts the ticket back to once its item exists."""
    assert _claim(alice).claimed_from == "To Do"


def test_a_refused_claim_records_no_status(fake, alice):
    fake.tickets["10052"].assignee = B
    assert _claim(alice).claimed_from == ""


def test_the_key_the_user_typed_resolves_to_the_canonical_one(fake, alice):
    assert _claim(alice, "tcwclaim-6").key == "TCWCLAIM-6"


def test_a_ticket_already_assigned_to_you_is_transitioned_and_not_reassigned(fake, alice):
    fake.tickets["10052"].assignee = A
    outcome = _claim(alice)
    assert (outcome.row, outcome.claimed) == ("3a", True)
    assert fake.writes() == [TRANSITION]


# ── refused at step 1, before any write ──────────────────────────────────────


def test_a_resolved_ticket_is_refused(fake, alice):
    fake.tickets["10052"].status = "Done"
    outcome = _claim(alice)
    assert (outcome.row, outcome.claimed) == ("1a", False)
    assert "resolved" in outcome.message
    assert fake.writes() == []


def test_a_ticket_assigned_to_someone_else_is_refused_naming_them(fake, alice):
    fake.tickets["10052"].assignee = B
    outcome = _claim(alice)
    assert (outcome.row, outcome.claimed) == ("1b", False)
    assert "Bob" in outcome.message and "To Do" in outcome.message
    assert fake.writes() == []


def test_a_claim_name_matching_two_transitions_is_refused(fake, alice):
    fake.workflow = {"To Do": [("21", "Start Progress", "In Progress"),
                               ("22", "start progress", "Doing")],
                     "In Progress": [], "Done": []}
    outcome = _claim(alice)
    assert (outcome.row, outcome.claimed) == ("1c", False)
    assert fake.writes() == []


def test_a_ticket_already_yours_past_the_claim_is_bound_without_a_write(fake, alice):
    ticket = fake.tickets["10052"]
    ticket.status, ticket.assignee = "In Progress", A
    outcome = _claim(alice)
    assert (outcome.row, outcome.claimed, outcome.transitioned) == ("1e", True, False)
    assert "not claimed by this run" in outcome.message
    assert fake.writes() == []


def test_an_unassigned_ticket_not_offering_the_claim_is_refused_without_advice(fake, alice):
    """The account reading this may not be the one that moved the ticket, so it
    must not be told to take it."""
    fake.tickets["10052"].status = "In Progress"
    outcome = _claim(alice)
    assert (outcome.row, outcome.claimed) == ("1f", False)
    assert "Finish" in outcome.message
    assert "assign it" not in f"{outcome.message} {outcome.detail}".lower()
    assert fake.writes() == []


# ── step 2 and the read-back ─────────────────────────────────────────────────


def test_a_refused_transition_on_a_ticket_already_yours_is_not_a_claim(fake, alice):
    """The read-back shows the ticket assigned to you — as it was before — but it
    never moved. Deciding from the assignee alone would bind it."""
    fake.tickets["10052"].assignee = A
    fake.fail("POST", "/transitions", jira._for_status(
        400, {}, "the work item is missing required information", "/transitions"))
    outcome = _claim(alice)
    assert (outcome.row, outcome.claimed) == ("3c", False)
    assert fake.tickets["10052"].status == "To Do"


def test_a_refused_transition_on_an_unmoved_unassigned_ticket(fake, alice):
    body = "Can't move (TCWCLAIM-6). You might not have permission"
    fake.fail("POST", "/transitions", jira._for_status(400, {}, body, "/transitions"))
    outcome = _claim(alice)
    assert (outcome.row, outcome.claimed) == ("3d", False)
    assert fake.writes() == [TRANSITION]
    assert "permission" not in outcome.message
    assert body in outcome.detail


def test_an_assign_refused_after_the_transition_applied(fake, alice):
    fake.fail("PUT", "/assignee", jira._for_status(403, {}, "no assign", "/assignee"))
    outcome = _claim(alice)
    assert (outcome.row, outcome.claimed) == ("3e", False)
    assert "assign it to yourself" in outcome.message.lower()
    assert "no assign" in outcome.detail
    # The advice is followed, and the next run finishes the job.
    fake.tickets["10052"].assignee = A
    again = _claim(alice)
    assert (again.row, again.claimed) == ("1e", True)


def test_a_transition_that_times_out_but_landed_on_a_ticket_already_yours(fake, alice):
    fake.tickets["10052"].assignee = A
    fake.fail("POST", "/transitions", jira.TrackerUnavailable("timed out"), apply_first=True)
    outcome = _claim(alice)
    assert (outcome.row, outcome.claimed) == ("3a", True)


def test_a_transition_that_times_out_on_an_unassigned_ticket_is_unknown(fake, alice):
    fake.fail("POST", "/transitions", jira.TrackerUnavailable("timed out"), apply_first=True)
    outcome = _claim(alice)
    assert (outcome.row, outcome.claimed) == ("3f", False)
    assert fake.writes() == [TRANSITION]            # no assign after an unknown result
    assert "history" in outcome.message


def test_a_failed_read_back_reports_the_result_as_unknown(fake, alice):
    ticket = intake.read_ticket(alice, "TCWCLAIM-6")
    fake.fail("GET", "/rest/api/3/issue/10052?", jira.TrackerUnavailable("down"))
    outcome = intake.claim(alice, ticket)
    assert outcome.claimed is False
    assert "unknown" in outcome.message


def test_a_permission_refusal_on_the_transition_stops_without_a_read_back(fake, alice):
    ticket = intake.read_ticket(alice, "TCWCLAIM-6")
    reads_before = len(fake.requests)
    fake.fail("POST", "/transitions", jira._for_status(403, {}, "", "/transitions"))
    with pytest.raises(jira.TrackerPermissionError):
        intake.claim(alice, ticket)
    assert len(fake.requests) == reads_before + 1


# ── two accounts, one ticket, a workflow that excludes ───────────────────────


def test_order_a_the_second_account_starts_after_the_first_finished(fake, alice, bob):
    assert _claim(alice).claimed
    outcome = _claim(bob)
    assert (outcome.row, outcome.claimed) == ("1b", False)
    assert "Alice" in outcome.message and "In Progress" in outcome.message
    assert fake.writes(B) == []


def test_order_b_the_loser_reads_back_before_the_winner_assigns(fake, alice, bob):
    ticket_a = intake.read_ticket(alice, "TCWCLAIM-6")
    ticket_b = intake.read_ticket(bob, "TCWCLAIM-6")
    losers = []
    fake.before("PUT", "/assignee", lambda: losers.append(intake.claim(bob, ticket_b)),
                account=A)
    winner = intake.claim(alice, ticket_a)
    [loser] = losers
    assert (winner.row, winner.claimed) == ("3a", True)
    assert (loser.row, loser.claimed) == ("3d", False)
    assert "In Progress" in loser.message
    assert ASSIGN not in fake.writes(B)
    assert fake.tickets["10052"].assignee == A


def test_order_c_the_loser_reads_back_after_the_winner_assigns(fake, alice, bob):
    ticket_a = intake.read_ticket(alice, "TCWCLAIM-6")
    ticket_b = intake.read_ticket(bob, "TCWCLAIM-6")
    assert intake.claim(alice, ticket_a).claimed
    loser = intake.claim(bob, ticket_b)
    assert (loser.row, loser.claimed) == ("3b", False)
    assert "Alice" in loser.message
    assert ASSIGN not in fake.writes(B)
    assert fake.tickets["10052"].assignee == A


# ── a workflow that does not exclude ─────────────────────────────────────────


def test_a_global_workflow_claims_like_any_other(fake, alice, bob):
    fake.workflow = GLOBAL
    assert _claim(alice).row == "3a"
    assert _claim(bob).row == "1b"


# ── the fake's own guard ─────────────────────────────────────────────────────


def test_the_fake_refuses_an_assignee_it_does_not_know(fake, alice):
    """The fixture must not certify an assignment real Jira would reject.

    It used to write whatever it was handed onto the ticket and answer 204, so
    `assign(id, "")` set an empty-string assignee that later reads treated as
    unassigned — an unassign that passes here and 400s against Jira. Only `None`
    and a registered account id are accepted now.
    """
    with pytest.raises(AssertionError):
        alice.assign("10052", "")
    with pytest.raises(AssertionError):
        alice.assign("10052", "nobody-at-all")
    alice.assign("10052", A)
    assert fake.tickets["10052"].assignee == A
    alice.assign("10052", None)
    assert fake.tickets["10052"].assignee is None
