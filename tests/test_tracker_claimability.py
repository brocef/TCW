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
    AMBIGUOUS, CLAIM_NOT_OFFERED, CLAIMABLE, EXCLUSIVE, MISCONFIGURED,
    NOT_CLAIMABLE, NOT_CONFIGURED, NOT_DETERMINED, NOT_EXCLUSIVE, assess,
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

# A directed workflow before the claim applies, as reported in GitHub issue #36.
DIRECTED_IN_TRIAGE = [
    Transition(id="41", name="Accept", to_status="To Do", to_status_id="10012"),
    Transition(id="51", name="Cancel", to_status="Cancelled", to_status_id="10013"),
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


def test_a_claim_name_this_ticket_does_not_offer_is_reported_but_not_condemned():
    """One ticket cannot tell a typo from a ticket that has already been claimed.
    Found live: a ticket claimed during an experiment reported a misconfiguration,
    which would fire on every claimed ticket forever."""
    result = assess("Begin Work", current_status="To Do", offered=DIRECTED_IN_TODO)
    assert result.verdict is CLAIM_NOT_OFFERED
    assert result.verdict is not MISCONFIGURED
    assert "Begin Work" in result.detail
    assert "Start Progress" in result.detail, "must list what is actually offered"


def test_an_already_claimed_ticket_is_not_reported_as_misconfigured():
    """The live case that forced this distinction."""
    result = assess(CLAIM, current_status="In Progress", offered=DIRECTED_IN_PROGRESS)
    assert result.verdict is not MISCONFIGURED


def test_the_claim_not_offered_note_covers_a_ticket_that_has_not_reached_the_claim():
    """GitHub issue #36. A ticket in Triage, before the claim applies, was told it
    was either misnamed or past the point — neither was true. The note has to name
    all three situations, not two."""
    result = assess(CLAIM, current_status="Triage", offered=DIRECTED_IN_TRIAGE)
    assert "past the point where it applies — one ticket" not in result.detail
    assert "not reached it yet" in result.detail
    assert "already past it" in result.detail


def test_the_leads_to_note_does_not_send_the_reader_to_a_second_show():
    """GitHub issue #36. The note said exclusivity "can only be read from a ticket
    already in that status", but `show` on that ticket still says not determined
    on an exclusive workflow, because it never has the landing status."""
    result = assess(CLAIM, current_status="To Do", offered=DIRECTED_IN_TODO)
    assert "Exclusivity can only be read from a ticket already" not in result.detail
    assert "workflow definition" in result.detail
    # The claim that a second `show` answers it would be false on this workflow:
    later = assess(CLAIM, current_status="In Progress", offered=DIRECTED_IN_PROGRESS)
    assert later.exclusivity is NOT_DETERMINED


def test_a_ticket_that_does_not_offer_the_claim_lists_every_offered_name():
    result = assess("Begin Work", current_status="To Do", offered=GLOBAL_WORKFLOW)
    for name in ("To Do", "Start Progress", "Done"):
        assert name in result.detail


def test_misconfiguration_is_not_detectable_from_issue_reads():
    """The negative result, recorded as a test so nobody re-adds the heuristic.

    Two live attempts to infer a wrong claim-transition name from issue reads both
    produced false positives. A single ticket that does not offer the claim may have
    been claimed already. So may every ticket in a query — a fixture whose tickets
    had all been claimed reported a typo on a configuration that was correct.
    Detecting this needs the project's workflow definition, which is a later child.
    """
    import tcw.tracker.claim as claim
    assert not hasattr(claim, "misconfigured_across")
    for status, offered in (("To Do", DIRECTED_IN_TODO),
                            ("In Progress", DIRECTED_IN_PROGRESS),
                            ("Done", [])):
        assert assess("Begin Work", current_status=status,
                      offered=offered).verdict is not MISCONFIGURED


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


# ── no claim transition configured ───────────────────────────────────────────


@pytest.mark.parametrize("name", ["", "   "], ids=["empty", "blank"])
def test_an_unset_start_transition_is_its_own_verdict(name):
    """A name nobody set is a different thing from a name this ticket does not
    offer, and saying the second about the first sends the reader to look at the
    ticket's workflow when the answer is in their own configuration file."""
    result = assess(name, current_status="To Do", offered=DIRECTED_IN_TODO)
    assert result.verdict is NOT_CONFIGURED
    assert result.claimable is NOT_CLAIMABLE
    assert result.exclusivity is NOT_DETERMINED
    assert "work.tracker.transitions.start" in result.detail
    # The wording this replaces reported an empty name as a wrong one.
    assert "is ''" not in result.detail and "does not offer" not in result.detail
