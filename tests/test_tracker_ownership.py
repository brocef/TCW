"""Holding and releasing a ticket, at the level below the CLI.

The thing these tests exist to pin is a **negative**: with no assertion transition
configured, claiming sends no transition at all. Asserting that from the ticket's
resulting status would be worthless — a claim that applied a transition landing
back on the same status would pass — so it is asserted against the requests the
fake actually received.

The race tests use the fake's `before` hook, which runs a second account's whole
claim inside the first's, between its write and its read-back. That proves the
*logic* of read-after-write. It does not prove Jira's own consistency behaves the
same way, which only a live two-account attempt can.
"""

from __future__ import annotations

import pytest

from tcw.store.base import TrackerConfig
from tcw.tracker import jira
from tcw.tracker.intake import read_ticket
from tcw.tracker.ownership import assert_ownership, drop_ownership
from tracker_fake import BASE_URL, GLOBAL, SYNC, FakeJira

A, B = "acct-a", "acct-b"
TICKET = "10052"


def _config(email_env: str) -> TrackerConfig:
    return TrackerConfig(provider="jira-cloud", base_url=BASE_URL,
                         candidate_query="assignee = currentUser()",
                         email_env=email_env, token_env="TCW_PROBE_TOKEN",
                         start_transition="Start Progress", timeout_seconds=15)


def _fake(monkeypatch, workflow=SYNC, **ticket):
    monkeypatch.setenv("TCW_A_EMAIL", "a@example.test")
    monkeypatch.setenv("TCW_B_EMAIL", "b@example.test")
    monkeypatch.setenv("TCW_PROBE_TOKEN", "sentinel-token")
    fake = FakeJira(workflow=workflow)
    fake.account("a@example.test", A, "Alice")
    fake.account("b@example.test", B, "Bob")
    fake.ticket(id=TICKET, key="TCWOWN-1", summary="A ticket", **ticket)
    return fake.install(monkeypatch)


@pytest.fixture()
def fake(monkeypatch):
    return _fake(monkeypatch)


@pytest.fixture()
def alice():
    return jira.JiraClient(_config("TCW_A_EMAIL"))


@pytest.fixture()
def bob():
    return jira.JiraClient(_config("TCW_B_EMAIL"))


def _transitions_posted(fake):
    return [path for method, path, _a in fake.requests
            if method == "POST" and path.endswith("/transitions")]


# ── the claim ────────────────────────────────────────────────────────────────


def test_claiming_assigns_the_ticket_and_moves_it_nowhere(fake, alice):
    before = fake.tickets[TICKET].status
    outcome = assert_ownership(alice, read_ticket(alice, TICKET))
    assert outcome.settled, outcome.message
    assert fake.tickets[TICKET].assignee == A
    assert fake.tickets[TICKET].status == before
    assert _transitions_posted(fake) == []


def test_claiming_twice_is_the_same_answer_and_still_moves_nothing(fake, alice):
    """Idempotence for the holder, which is what makes the verb safe to re-run
    after a failure that left the tracker half done."""
    before = fake.tickets[TICKET].status
    first = assert_ownership(alice, read_ticket(alice, TICKET))
    second = assert_ownership(alice, read_ticket(alice, TICKET))
    assert first.settled and second.settled
    assert "already held by you" in second.message
    assert fake.tickets[TICKET].assignee == A
    assert fake.tickets[TICKET].status == before
    assert _transitions_posted(fake) == []


def test_a_ticket_somebody_else_holds_is_refused_by_name(fake, alice, bob):
    assert assert_ownership(bob, read_ticket(bob, TICKET)).settled
    outcome = assert_ownership(alice, read_ticket(alice, TICKET))
    assert not outcome.settled
    assert "Bob" in outcome.message and outcome.holder_id == B
    assert fake.tickets[TICKET].assignee == B


def test_take_over_claims_a_ticket_somebody_else_holds(fake, alice, bob):
    assert assert_ownership(bob, read_ticket(bob, TICKET)).settled
    outcome = assert_ownership(alice, read_ticket(alice, TICKET), take_over=True)
    assert outcome.settled, outcome.message
    assert fake.tickets[TICKET].assignee == A


def test_a_resolved_ticket_cannot_be_held(monkeypatch):
    fake = _fake(monkeypatch, status="Done")
    alice = jira.JiraClient(_config("TCW_A_EMAIL"))
    outcome = assert_ownership(alice, read_ticket(alice, TICKET))
    assert not outcome.settled and "resolved" in outcome.message
    assert fake.tickets[TICKET].assignee is None


# ── the race ─────────────────────────────────────────────────────────────────


def test_the_loser_of_a_race_sees_the_winner_and_backs_off(fake, alice, bob):
    """A assigns, B's whole claim runs, A reads back and finds Bob.

    The interleaving the floor is built to catch: without the read-back, A would
    report success on an assignment B had already overwritten.
    """
    # Both read the ticket while it is unassigned, which is what makes this a race
    # rather than a queue. The hook is registered after both reads, so the one-shot
    # lands on Alice's read-back rather than on either of them — by which point her
    # assignment has been applied and Bob is about to overwrite it.
    mine, theirs = read_ticket(alice, TICKET), read_ticket(bob, TICKET)
    fake.before("GET", f"/rest/api/3/issue/{TICKET}",
                lambda: assert_ownership(bob, theirs), account=A)
    outcome = assert_ownership(alice, mine)
    assert not outcome.settled
    assert outcome.holder_id == B and "Bob" in outcome.message
    assert fake.tickets[TICKET].assignee == B


def test_the_loser_leaves_the_ticket_with_the_winner_and_can_retry(fake, alice, bob):
    """What a lost race leaves behind, pinned so a later change has to argue with
    a test rather than with a paragraph.

    The assignment A already sent is deliberately not rolled back: undoing it would
    hand the ticket to nobody and stamp on the winner's claim. So the ticket is
    Bob's, and A's way back is to run it again once Bob lets go.
    """
    mine, theirs = read_ticket(alice, TICKET), read_ticket(bob, TICKET)
    fake.before("GET", f"/rest/api/3/issue/{TICKET}",
                lambda: assert_ownership(bob, theirs), account=A)
    assert not assert_ownership(alice, mine).settled
    assert fake.tickets[TICKET].assignee == B

    assert drop_ownership(bob, read_ticket(bob, TICKET)).settled
    again = assert_ownership(alice, read_ticket(alice, TICKET))
    assert again.settled, again.message
    assert fake.tickets[TICKET].assignee == A


def test_a_ticket_unassigned_mid_claim_is_not_reported_as_somebody_elses(fake, alice,
                                                                         bob):
    """The read-back can find nobody rather than a rival. Saying "they took it" there
    would name a holder that does not exist, and there is no claim to stamp on."""
    mine = read_ticket(alice, TICKET)
    fake.before("GET", f"/rest/api/3/issue/{TICKET}",
                lambda: drop_ownership(bob, read_ticket(bob, TICKET), force=True),
                account=A)
    outcome = assert_ownership(alice, mine)
    assert not outcome.settled
    assert outcome.holder_id == "" and outcome.holder_name == ""
    assert "somebody unassigned it" in outcome.message
    assert "held by" not in outcome.message
    assert fake.tickets[TICKET].assignee is None


# ── the release ──────────────────────────────────────────────────────────────


def test_releasing_unassigns_and_moves_nothing(fake, alice):
    assert assert_ownership(alice, read_ticket(alice, TICKET)).settled
    before = fake.tickets[TICKET].status
    outcome = drop_ownership(alice, read_ticket(alice, TICKET))
    assert outcome.settled, outcome.message
    assert fake.tickets[TICKET].assignee is None
    assert fake.tickets[TICKET].status == before
    assert _transitions_posted(fake) == []


def test_releasing_a_ticket_nobody_holds_is_already_done(fake, alice):
    outcome = drop_ownership(alice, read_ticket(alice, TICKET))
    assert outcome.settled and "nobody" in outcome.message


def test_releasing_somebody_elses_ticket_is_refused_unless_forced(fake, alice, bob):
    assert assert_ownership(bob, read_ticket(bob, TICKET)).settled
    refused = drop_ownership(alice, read_ticket(alice, TICKET))
    assert not refused.settled and "Bob" in refused.message
    assert fake.tickets[TICKET].assignee == B

    forced = drop_ownership(alice, read_ticket(alice, TICKET), force=True)
    assert forced.settled, forced.message
    assert fake.tickets[TICKET].assignee is None


def test_a_tracker_that_refuses_the_unassignment_is_reported_not_raised(fake, alice):
    """A project configured to forbid unassigned issues answers this with 400.

    The fake is made to fail on demand, which proves the handling. Nothing here
    proves *when* Jira would refuse — that needs a live project, and it is on the
    item's verification list for exactly that reason.
    """
    assert assert_ownership(alice, read_ticket(alice, TICKET)).settled
    fake.fail("PUT", "/assignee", jira.TrackerRequestInvalid("cannot be unassigned"))
    outcome = drop_ownership(alice, read_ticket(alice, TICKET))
    assert not outcome.settled
    assert "could not be released" in outcome.message
    assert fake.tickets[TICKET].assignee == A


# ── the opt-in ceiling ───────────────────────────────────────────────────────


def test_a_named_assertion_transition_is_applied_before_the_assignment(monkeypatch):
    """Opting in buys exclusivity and costs a status move. Both are asserted here,
    so nobody reads the key as free."""
    fake = _fake(monkeypatch)
    alice = jira.JiraClient(_config("TCW_A_EMAIL"))
    outcome = assert_ownership(alice, read_ticket(alice, TICKET),
                               assertion="Start Progress")
    assert outcome.settled and outcome.transitioned
    assert fake.tickets[TICKET].assignee == A
    assert fake.tickets[TICKET].status == "In Progress"
    assert len(_transitions_posted(fake)) == 1


def test_an_assertion_the_ticket_does_not_offer_refuses_the_claim(monkeypatch):
    fake = _fake(monkeypatch)
    alice = jira.JiraClient(_config("TCW_A_EMAIL"))
    outcome = assert_ownership(alice, read_ticket(alice, TICKET),
                               assertion="No Such Transition")
    assert not outcome.settled
    assert "does not offer" in outcome.message
    assert fake.tickets[TICKET].assignee is None


def test_claiming_under_an_assertion_stays_idempotent(monkeypatch):
    """The reason `intake.claim`'s row `1e` had to be carried across by hand.

    After the first claim the transition is no longer offered, so a rule that
    needed it would refuse the holder's own second run.
    """
    fake = _fake(monkeypatch)
    alice = jira.JiraClient(_config("TCW_A_EMAIL"))
    assert assert_ownership(alice, read_ticket(alice, TICKET),
                            assertion="Start Progress").settled
    second = assert_ownership(alice, read_ticket(alice, TICKET),
                              assertion="Start Progress")
    assert second.settled, second.message
    assert len(_transitions_posted(fake)) == 1
    assert fake.tickets[TICKET].status == "In Progress"


def test_a_workflow_that_excludes_a_second_claimant_is_what_the_key_buys(monkeypatch):
    """On a directed workflow the loser's transition is refused, so they never
    reach the assignment — the guarantee read-after-write cannot give."""
    fake = _fake(monkeypatch)
    alice = jira.JiraClient(_config("TCW_A_EMAIL"))
    bob = jira.JiraClient(_config("TCW_B_EMAIL"))
    assert assert_ownership(alice, read_ticket(alice, TICKET),
                            assertion="Start Progress").settled
    # Bob reads the ticket in 'In Progress', which does not offer 'Start Progress'.
    outcome = assert_ownership(bob, read_ticket(bob, TICKET),
                               assertion="Start Progress", take_over=True)
    assert not outcome.settled
    assert fake.tickets[TICKET].assignee == A


def test_on_a_global_workflow_the_assertion_alone_does_not_exclude(monkeypatch):
    """The honest limit of the opt-in key, stated as a test.

    Where the workflow offers the claim transition from every status, applying it
    excludes nobody — and the floor underneath is what catches the race instead.
    """
    fake = _fake(monkeypatch, workflow=GLOBAL)
    alice = jira.JiraClient(_config("TCW_A_EMAIL"))
    bob = jira.JiraClient(_config("TCW_B_EMAIL"))
    assert assert_ownership(alice, read_ticket(alice, TICKET),
                            assertion="Start Progress").settled
    outcome = assert_ownership(bob, read_ticket(bob, TICKET),
                               assertion="Start Progress", take_over=True)
    assert outcome.settled          # the workflow let Bob straight in
    assert fake.tickets[TICKET].assignee == B
