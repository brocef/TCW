"""The live checks, replayed from responses captured off a real Jira Cloud site.

Captured 2026-09-13 from two throwaway projects on one site, then scrubbed: the host,
the account id, the email address and the avatar URLs are placeholders, because TCW
is published and the transition graph is the only part with any value here. The
scrub is checked by a test below rather than trusted, since a future recapture could
reintroduce real identities.

Why replay rather than mock: these are the bytes the real API actually returns. The
hand-written stubs elsewhere encode what I *believe* the shape is, and the difference
between those two things is where a client breaks. One of this item's findings — that
the search endpoint had been removed outright — is exactly that gap.

The two fixtures are a matched pair and both are needed:

- **conforming** — a workflow with directed transitions only. The claim transition
  disappears once applied, and four live race trials produced exactly one winner.
- **non-conforming** — Jira's default workflow, every transition offered from every
  status. Applying the claim twice succeeded, and concurrent claims all succeeded.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from tcw.tracker.claim import (
    CLAIM_NOT_OFFERED, CLAIMABLE, EXCLUSIVE, MISCONFIGURED, NOT_CLAIMABLE,
    NOT_DETERMINED, NOT_EXCLUSIVE, assess,
)
from tcw.tracker.jira import Transition

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "tracker"
CLAIM = "Start Progress"
# The non-conforming project's claim transition is named for its destination,
# because its workflow's transitions are "set status to X" rather than real moves.
NONCONFORMING_CLAIM = "In Progress"


def _transitions(name: str) -> list[Transition]:
    """Parse a captured response exactly as the client does."""
    payload = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    out = []
    for raw in payload.get("transitions") or []:
        to = raw.get("to") or {}
        out.append(Transition(id=str(raw.get("id", "")), name=str(raw.get("name", "")),
                              to_status=str(to.get("name", "")),
                              to_status_id=str(to.get("id", ""))))
    return out


# ── the captured data is what it claims to be ────────────────────────────────


def test_every_fixture_is_valid_json():
    files = sorted(FIXTURES.glob("*.json"))
    assert files, "no fixtures captured"
    for f in files:
        json.loads(f.read_text(encoding="utf-8"))


def test_no_fixture_carries_a_real_identity_or_host():
    """The scrub, checked rather than trusted. A recapture that forgets it fails here
    instead of publishing an email address and an account id."""
    for f in sorted(FIXTURES.glob("*.json")):
        text = f.read_text(encoding="utf-8")
        for forbidden in ("proposit", "atlassian.net/rest/api/3/user?accountId=712020",
                          "admin@", "d256da6b"):
            assert forbidden not in text, (f.name, forbidden)


def test_the_two_workflows_really_do_differ():
    """If a recapture pointed both at the same project, every verdict test below
    would still pass while proving nothing. This is the guard against that."""
    conforming = {t.id for t in _transitions("conforming-ready-transitions.json")}
    nonconforming = {t.id for t in _transitions("nonconforming-claimed-transitions.json")}
    assert conforming != nonconforming
    assert len(nonconforming) == 3, "the non-conforming workflow offers all three"
    assert len(conforming) == 1, "the conforming workflow offers only the claim"


# ── the verdicts, against real bytes ─────────────────────────────────────────


def test_a_ready_ticket_on_the_conforming_workflow_is_claimable():
    result = assess(CLAIM, current_status="To Do",
                    offered=_transitions("conforming-ready-transitions.json"))
    assert result.claimable is CLAIMABLE
    assert result.landing_status == "In Progress"
    # Exclusivity is unanswerable from a ready ticket, and saying so is the point.
    assert result.exclusivity is NOT_DETERMINED


def test_a_claimed_ticket_on_the_conforming_workflow_is_exclusive():
    """The destination has to be supplied: a ticket no longer offering the claim
    cannot say where the claim led. This is the asymmetry implementation found."""
    result = assess(CLAIM, current_status="In Progress",
                    offered=_transitions("conforming-claimed-transitions.json"),
                    landing_status="In Progress")
    assert result.exclusivity is EXCLUSIVE
    assert result.claimable is NOT_CLAIMABLE


def test_a_claimed_ticket_on_the_nonconforming_workflow_is_not_exclusive():
    """The failure this whole item exists to surface. The claim is still offered from
    the status it leads to, so a second claimant would not be refused — which is
    exactly what the live race measured."""
    result = assess(NONCONFORMING_CLAIM, current_status="In Progress",
                    offered=_transitions("nonconforming-claimed-transitions.json"))
    assert result.exclusivity is NOT_EXCLUSIVE
    assert result.claimable is CLAIMABLE


def test_the_two_workflows_reach_opposite_verdicts_from_the_same_status():
    """Side by side, which is the comparison a reader wants."""
    conforming = assess(CLAIM, current_status="In Progress",
                        offered=_transitions("conforming-claimed-transitions.json"),
                        landing_status="In Progress")
    nonconforming = assess(NONCONFORMING_CLAIM, current_status="In Progress",
                           offered=_transitions("nonconforming-claimed-transitions.json"))
    assert conforming.exclusivity is EXCLUSIVE
    assert nonconforming.exclusivity is NOT_EXCLUSIVE


def test_a_claimed_ticket_is_reported_informationally_not_as_a_typo():
    """The live case that forced `misconfigured` to become unreachable: this ticket
    has simply been claimed, and calling that a configuration error would fire on
    every claimed ticket forever."""
    result = assess(CLAIM, current_status="In Progress",
                    offered=_transitions("conforming-claimed-transitions.json"))
    assert result.verdict is CLAIM_NOT_OFFERED
    assert result.verdict is not MISCONFIGURED
    assert "Finish" in result.detail, "must say what the ticket does offer"


# ── the issue payload parses as the client expects ───────────────────────────


def test_the_captured_issue_yields_the_fields_show_prints():
    payload = json.loads((FIXTURES / "conforming-ready-issue.json").read_text())
    fields = payload["fields"]
    assert payload["key"]
    assert fields["status"]["name"] == "To Do"
    assert (fields.get("assignee") or {}).get("displayName")
    assert "summary" in fields
