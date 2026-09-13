"""Claimability, and whether a workflow can exclude a second claimant.

The function under test is **pure**: it takes the configured claim transition name,
the ticket's current status, and the transitions the ticket offers. No client, no
HTTP. That is what lets the fixture cases below use the transition lists a live
experiment actually recorded rather than invented data.

The two words are different on purpose and the tests hold them apart:

- **claimable** — this ticket, right now, offers the configured claim transition.
- **exclusive** — the workflow will refuse a second claimant. Answerable only for a
  ticket already sitting in the status the claim leads to.

A reader who confuses them has been told something true and misleading at once,
which is why an earlier draft using one word for both was rejected.
"""

from __future__ import annotations

import pytest

from tcw.tracker.claim import (
    AMBIGUOUS, CLAIMABLE, EXCLUSIVE, MISCONFIGURED, NOT_CLAIMABLE,
    NOT_DETERMINED, NOT_EXCLUSIVE, assess,
)
from tcw.tracker.jira import Transition

CLAIM = "Start Progress"

# Measured on 2026-09-12 against the non-conforming fixture, whose workflow offers
# every transition from every status. See the epic's jira-claim-experiment.md.
GLOBAL_WORKFLOW = [
    Transition(id="11", name="To Do", to_status="To Do", to_status_id="10012"),
    Transition(id="21", name="Start Progress", to_status="In Progress", to_status_id="3"),
    Transition(id="31", name="Done", to_status="Done", to_status_id="10009"),
]

# The conforming fixture, in To Do: only the claim is offered.
DIRECTED_IN_TODO = [
    Transition(id="21", name="Start Progress", to_status="In Progress", to_status_id="3"),
]

# The conforming fixture, once claimed: the claim is gone.
DIRECTED_IN_PROGRESS = [
    Transition(id="31", name="Finish", to_status="Done", to_status_id="10009"),
]


# ── claimable: about this ticket now ─────────────────────────────────────────


def test_a_ticket_offering_the_claim_is_claimable():
    result = assess(CLAIM, current_status="To Do", offered=DIRECTED_IN_TODO)
    assert result.claimable is CLAIMABLE


def test_a_ticket_not_offering_the_claim_is_not_claimable():
    result = assess(CLAIM, current_status="In Progress", offered=DIRECTED_IN_PROGRESS)
    assert result.claimable is NOT_CLAIMABLE


def test_a_ticket_with_no_transitions_at_all_is_not_claimable():
    result = assess(CLAIM, current_status="Done", offered=[])
    assert result.claimable is NOT_CLAIMABLE


# ── exclusive: about the workflow, and only answerable in the landing status ──


def test_exclusivity_is_not_determined_outside_the_landing_status():
    """The common case, and it must not read as reassurance. A ticket in To Do
    says nothing about whether a second claimant would be refused."""
    result = assess(CLAIM, current_status="To Do", offered=DIRECTED_IN_TODO)
    assert result.exclusivity is NOT_DETERMINED


def test_a_directed_workflow_is_exclusive_once_in_the_landing_status():
    """The conforming fixture. The claim transition is gone from In Progress, which
    is exactly why four concurrent-race trials produced one winner each.

    `landing_status` has to be supplied, and that asymmetry is the point: a ticket
    that is not offering the claim cannot say where the claim would have led.
    """
    result = assess(CLAIM, current_status="In Progress",
                    offered=DIRECTED_IN_PROGRESS, landing_status="In Progress")
    assert result.exclusivity is EXCLUSIVE


def test_exclusivity_is_not_determined_without_the_landing_status():
    """The limitation, asserted rather than left implicit. Only NOT_EXCLUSIVE is
    detectable from a ticket alone; confirming EXCLUSIVE needs the destination from
    a ticket that does offer the claim, or from the code that just applied it."""
    result = assess(CLAIM, current_status="In Progress", offered=DIRECTED_IN_PROGRESS)
    assert result.exclusivity is NOT_DETERMINED


def test_a_supplied_landing_status_is_ignored_when_the_ticket_is_elsewhere():
    """A ticket in To Do says nothing, whatever the caller knows."""
    result = assess(CLAIM, current_status="To Do", offered=DIRECTED_IN_TODO,
                    landing_status="In Progress")
    assert result.exclusivity is NOT_DETERMINED


def test_a_global_workflow_is_not_exclusive_in_the_landing_status():
    """The non-conforming fixture. The claim is still offered from In Progress, so
    a loser that retries also claims — measured as 204 twice."""
    result = assess(CLAIM, current_status="In Progress", offered=GLOBAL_WORKFLOW)
    assert result.exclusivity is NOT_EXCLUSIVE


def test_the_landing_status_is_learned_from_the_claim_transition():
    """Not configured separately. The transition itself says where it leads, so
    there is no second key to get wrong."""
    result = assess(CLAIM, current_status="To Do", offered=DIRECTED_IN_TODO)
    assert result.landing_status == "In Progress"


def test_the_landing_status_is_unknown_when_the_claim_is_not_offered():
    """From In Progress on a directed workflow the claim is absent, so the ticket
    cannot say where it would have led."""
    result = assess(CLAIM, current_status="In Progress", offered=DIRECTED_IN_PROGRESS)
    assert result.landing_status == ""


# ── misconfiguration, the highest-value thing this reports ───────────────────


def test_a_claim_name_the_workflow_does_not_have_is_misconfigured():
    """The next child cannot detect this: a bad transition name and a lost race
    both come back as HTTP 400 with different bodies. Here it is unambiguous."""
    result = assess("Begin Work", current_status="To Do", offered=DIRECTED_IN_TODO)
    assert result.verdict is MISCONFIGURED
    assert "Begin Work" in result.detail
    assert "Start Progress" in result.detail, "must list what is actually offered"


def test_a_misconfigured_claim_lists_every_offered_name():
    result = assess("Begin Work", current_status="To Do", offered=GLOBAL_WORKFLOW)
    for name in ("To Do", "Start Progress", "Done"):
        assert name in result.detail


def test_a_duplicate_claim_name_is_refused_rather_than_guessed():
    """Two transitions with one name is a real Jira configuration. Picking either
    would be a coin flip performed silently."""
    offered = [
        Transition(id="21", name="Start Progress", to_status="In Progress", to_status_id="3"),
        Transition(id="41", name="Start Progress", to_status="In Review", to_status_id="10013"),
    ]
    result = assess(CLAIM, current_status="To Do", offered=offered)
    assert result.verdict is AMBIGUOUS
    assert "21" in result.detail and "41" in result.detail


def test_a_ticket_outside_the_landing_status_without_the_claim_is_not_misconfigured():
    """A ticket in Done offers neither; that is the workflow working, not a typo.
    Calling it misconfigured would cry wolf on every resolved ticket."""
    result = assess(CLAIM, current_status="Done", offered=[])
    assert result.verdict is not MISCONFIGURED


def test_matching_is_case_and_space_insensitive():
    """`claim: start progress` in YAML should not be a silent misconfiguration."""
    result = assess("  start progress  ", current_status="To Do", offered=DIRECTED_IN_TODO)
    assert result.claimable is CLAIMABLE
    assert result.verdict is not MISCONFIGURED


# ── the two words never collapse into one ────────────────────────────────────


def test_claimable_and_exclusive_are_independent():
    """The pairing an earlier draft would have hidden: a ticket can be claimable
    on a workflow that cannot exclude anybody."""
    result = assess(CLAIM, current_status="In Progress", offered=GLOBAL_WORKFLOW)
    assert result.claimable is CLAIMABLE
    assert result.exclusivity is NOT_EXCLUSIVE


@pytest.mark.parametrize("value", [CLAIMABLE, NOT_CLAIMABLE, EXCLUSIVE,
                                   NOT_EXCLUSIVE, NOT_DETERMINED])
def test_every_verdict_word_is_distinct(value):
    words = {CLAIMABLE, NOT_CLAIMABLE, EXCLUSIVE, NOT_EXCLUSIVE, NOT_DETERMINED}
    assert len(words) == 5
    assert value in words
