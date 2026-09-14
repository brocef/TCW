"""Is this ticket claimable, and will the workflow refuse a second claimant?

Pure: it takes the configured claim transition name, the ticket's current status,
and the transitions the ticket offers. No client, no HTTP, no config object. That is
what lets it be tested against transition lists a live experiment recorded.

**Why the ticket rather than the workflow definition.** Reading a project's
workflow answers the exclusivity question definitively and in advance, but it needs
a project identifier no configuration key carries, it may require site-administrator
permission, and putting it behind `tcw validate` would make completing a work item
depend on the tracker being reachable — `tcw validate` is bound as a `pre` hook on
`complete`. Reading what one ticket offers needs no permission beyond viewing that
ticket and behaves the same on team-managed and company-managed projects. It
answers less, and what it gives up is needed only once strict mode gates work,
which is a later child. That child gets the authoritative read.

**Two words, held apart.** *Claimable* is about this ticket now. *Exclusive* is
about the workflow. A ticket can be claimable on a workflow that would let a second
person claim it too — that pair is the whole reason one word will not do.
"""

from __future__ import annotations

from dataclasses import dataclass

# Claimability of this ticket, now.
CLAIMABLE = "claimable"
NOT_CLAIMABLE = "not claimable"

# Whether the workflow refuses a second claimant.
EXCLUSIVE = "exclusive"
NOT_EXCLUSIVE = "not exclusive"
NOT_DETERMINED = "not determined from this ticket"

# Configuration verdicts, which override the above when they fire.
OK = "ok"
# The configured claim name is not among this ticket's transitions. **Informational,
# not an error.** Every ticket that has already been claimed is in this state, and
# reporting a misconfiguration for each of them would cry wolf constantly — found by
# running against a real ticket that had been claimed during an experiment.
CLAIM_NOT_OFFERED = "claim not offered by this ticket"
# Reserved, and deliberately unreachable from this module. Detecting a wrong claim
# transition name needs the project's workflow definition, which is a later child's
# job. Two live attempts to infer it from issue reads both produced false positives:
# one ticket that does not offer the claim may simply have been claimed already, and
# so may *every* ticket in a query — which is exactly what a fixture full of claimed
# tickets looks like. Reporting a typo on a correct configuration is worse than not
# reporting one at all.
MISCONFIGURED = "misconfigured"
AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class Assessment:
    """What one ticket's offered transitions say."""
    claimable: str
    exclusivity: str
    verdict: str
    landing_status: str = ""
    detail: str = ""


def _normalize(name: str) -> str:
    """Match on a trimmed, case-folded name.

    `claim: start progress` in YAML should not be a silent misconfiguration when
    the transition is called `Start Progress`.
    """
    return " ".join(name.strip().split()).casefold()


def assess(claim_transition: str, *, current_status: str, offered,
           landing_status: str = "") -> Assessment:
    """Assess one ticket.

    `offered` is the transitions the ticket offers right now — whatever
    `JiraClient.transitions` returned. `current_status` is the ticket's status.

    **`landing_status` is the asymmetry, and it is not optional decoration.** A
    ticket that offers the claim tells us where the claim leads. A ticket that does
    *not* offer it cannot: the destination was only ever readable from the
    transition itself. So without help, only `NOT_EXCLUSIVE` is ever detectable —
    the case where the claim is still offered from its own destination. Confirming
    `EXCLUSIVE` needs the destination from somewhere else, and a caller that knows
    it passes it here.

    Two callers legitimately know it. One that read a second ticket in the ready
    state and learned the destination from that. And, in the next child, the code
    that has just applied the claim and watched where the ticket landed — which is
    exactly the moment exclusivity is about to be relied upon.

    With no `landing_status` and no offered claim, the answer is `NOT_DETERMINED`.
    That is a real limitation, reported rather than papered over.
    """
    wanted = _normalize(claim_transition)
    matches = [t for t in offered if _normalize(t.name) == wanted]
    offered_names = [t.name for t in offered]

    if len(matches) > 1:
        ids = ", ".join(sorted(t.id for t in matches))
        return Assessment(
            claimable=NOT_CLAIMABLE,
            exclusivity=NOT_DETERMINED,
            verdict=AMBIGUOUS,
            detail=(f"{claim_transition!r} matches more than one transition on this "
                    f"ticket (ids {ids}). Refusing to guess which was meant; name a "
                    f"transition that is unique, or rename one in the tracker."),
        )

    if matches:
        landing = matches[0].to_status
        # Exclusivity is answerable only from the status the claim leads to. The
        # claim is offered here, so this ticket is in the landing status only if it
        # is already there — which is precisely the non-exclusive case.
        if _normalize(current_status) == _normalize(landing):
            return Assessment(
                claimable=CLAIMABLE,
                exclusivity=NOT_EXCLUSIVE,
                verdict=OK,
                landing_status=landing,
                detail=(f"{matches[0].name!r} is still offered from {landing!r}, the "
                        f"status it leads to, so applying it twice succeeds and a "
                        f"second claimant would not be refused."),
            )
        return Assessment(
            claimable=CLAIMABLE,
            exclusivity=NOT_DETERMINED,
            verdict=OK,
            landing_status=landing,
            detail=(f"{matches[0].name!r} leads to {landing!r}. A ticket already in "
                    f"that status can show a workflow that is not exclusive, but never "
                    f"one that is. That is confirmed only when a claim is made, or "
                    f"from the workflow definition."),
        )

    # The claim is not offered. Two very different situations.
    #
    # If this ticket is in a status a claim would have led to, the absence is the
    # workflow doing its job, and that is the exclusive answer. But the ticket
    # cannot tell us where the claim leads, since it is not offering it — so the
    # only way to know we are in a landing status is that a claim already happened.
    # That is the next child's business at claim time, and here the honest answer
    # for a ticket with *some* transitions is "not determined".
    #
    # A configured name matching nothing at all, on a ticket that does offer
    # transitions, is a likely typo and worth saying plainly: the next child cannot
    # detect it, because a bad transition name and a lost race both return HTTP 400.
    # When the caller supplied the destination and this ticket is sitting in it,
    # the claim's absence *is* the exclusive answer — the workflow refuses a second
    # claimant, which is why the conforming fixture produced one winner per race.
    if landing_status and _normalize(current_status) == _normalize(landing_status):
        return Assessment(
            claimable=NOT_CLAIMABLE,
            exclusivity=EXCLUSIVE,
            verdict=OK,
            landing_status=landing_status,
            detail=(f"{claim_transition!r} is not offered from {landing_status!r}, the "
                    f"status it leads to, so a second claimant would be refused."),
        )

    if offered:
        return Assessment(
            claimable=NOT_CLAIMABLE,
            exclusivity=NOT_DETERMINED,
            verdict=CLAIM_NOT_OFFERED,
            detail=(f"work.tracker.transitions.claim is {claim_transition!r}, which "
                    f"this ticket does not offer. It offers: "
                    f"{', '.join(repr(n) for n in offered_names)}. Either the name "
                    f"is wrong, or this ticket is not at the point where it applies — "
                    f"it has not reached it yet, or is already past it. One ticket "
                    f"cannot tell those apart."),
        )

    # No transitions at all: a resolved ticket, or one this account cannot move.
    # Reporting a misconfiguration here would cry wolf on every closed ticket.
    return Assessment(
        claimable=NOT_CLAIMABLE,
        exclusivity=NOT_DETERMINED,
        verdict=OK,
        detail="This ticket offers no transitions, so it says nothing about the "
               "claim configuration.",
    )

