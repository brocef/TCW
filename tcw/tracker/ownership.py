"""Holding a ticket, and letting go of it, without moving it.

This is the tracker half of `tcw work tracker claim` and `tcw work tracker
release`. It answers one question — *who holds this ticket* — and it answers it
by writing the assignee and reading it back, never by moving the ticket through
a workflow.

**Why not reuse `intake.claim`.** That function exists to take a ticket *and*
start it, and it cannot be told apart from what it does: it reads the transition
name from `client.config.start_transition` directly, so it can only ever apply
the one transition a project configured for starting work. Reusing it here would
mean either moving every claimed ticket — the thing this whole change exists to
stop — or editing it, which belongs to the child that rewrites the lifecycle
moves. So this is a second, smaller implementation, and `intake.claim` is left
exactly as it was.

**Exclusivity has a floor and an optional ceiling.**

The floor, which every project gets: *assign, then read back*. The loser of a
race sees the winner and backs off. This is weaker than routing the claim through
a workflow, and the window is real rather than theoretical — two claims that
interleave as *A assigns, A reads, B assigns, B reads* both succeed. What it does
catch is the far likelier *A assigns, B assigns, A reads*, where A would
otherwise have its assignment overwritten with nobody told.

The ceiling, for a project whose workflow genuinely refuses a second claimant:
name a transition in `work.tracker.exclusive-claim-transition` and it is applied
first, so a second claimant's transition is refused and never reaches the assign.
That is `intake.claim`'s own reasoning, and it is the one case where claiming
does move the ticket — which is why it is opt-in, and why the guide says plainly
what opting in costs.

One rule is carried across from `intake.claim` by hand rather than by import: a
ticket already assigned to the caller is already held, whatever the workflow now
offers (its row `1e`). Without it, a second `claim` under an assertion would fail
for want of a transition that has already been applied, and the verb would stop
being idempotent the moment a project opted in.
"""

from __future__ import annotations

from dataclasses import dataclass

from tcw.tracker.claim import _normalize
from tcw.tracker.jira import TrackerError, TrackerRequestInvalid


@dataclass(frozen=True)
class OwnershipOutcome:
    """What one claim or release attempt established.

    `settled` is whether the tracker now says what the caller asked it to say —
    held by them for a claim, held by nobody for a release. Everything else is
    for the message.
    """
    settled: bool
    message: str
    holder_id: str = ""
    holder_name: str = ""
    status: str = ""
    detail: str = ""
    transitioned: bool = False


def _holder(client, ticket):
    """`(account id, display name, status, category)` as the tracker says now."""
    from tcw.tracker.intake import _fields
    return _fields(client.issue(ticket.issue_id))


def assert_ownership(client, ticket, *, assertion: str = "",
                     take_over: bool = False) -> OwnershipOutcome:
    """Make `ticket` held by the account `client` authenticates as.

    Idempotent for whoever already holds it. Refuses a second holder by name,
    unless `take_over`. Applies no transition unless `assertion` names one.

    Authentication, permission, rate-limit and not-found errors propagate: none of
    them is an answer about who holds the ticket.
    """
    key = ticket.key

    def refused(message: str, detail: str = "", holder=("", "")) -> OwnershipOutcome:
        return OwnershipOutcome(settled=False, message=message, detail=detail,
                                holder_id=holder[0], holder_name=holder[1],
                                status=ticket.status)

    if ticket.category == "done":
        return refused(f"{key} is resolved ('{ticket.status}'), so there is nothing "
                       f"to hold.")
    if ticket.assignee_id and ticket.assignee_id != ticket.me_id and not take_over:
        return refused(f"{key} is held by {ticket.assignee_name}.",
                       holder=(ticket.assignee_id, ticket.assignee_name))

    # Already ours: `intake.claim`'s row `1e`, carried across. Nothing is sent —
    # not even the assignment, which would be a write with no change to make.
    if ticket.assignee_id == ticket.me_id:
        return OwnershipOutcome(settled=True, status=ticket.status,
                                holder_id=ticket.me_id, holder_name=ticket.me_name,
                                message=f"{key} is already held by you.")

    transitioned = False
    if assertion:
        matches = [t for t in ticket.offered
                   if _normalize(t.name) == _normalize(assertion)]
        if len(matches) > 1:
            ids = ", ".join(sorted(t.id for t in matches))
            return refused(f"'{assertion}' matches more than one transition offered "
                           f"by {key} (ids {ids}); TCW will not guess which.")
        if not matches:
            offers = ", ".join(repr(t.name) for t in ticket.offered) or "nothing"
            return refused(f"{key} is in '{ticket.status}' and does not offer "
                           f"{assertion!r}, the transition "
                           f"work.tracker.exclusive-claim-transition names. It "
                           f"offers: {offers}.")
        try:
            client.apply_transition(ticket.issue_id, matches[0].id)
            transitioned = True
        except TrackerRequestInvalid as error:
            # The workflow refused it, which is the whole point of naming one: on a
            # workflow that excludes a second claimant this is where they stop, and
            # they never reach the assignment below.
            return refused(f"{key} would not accept {assertion!r}, so it was not "
                           f"claimed. Somebody else may hold it.", str(error))

    try:
        client.assign(ticket.issue_id, ticket.me_id)
    except TrackerError as error:
        return refused(f"{key} could not be assigned to you, so it is not held.",
                       str(error))

    # The read-back. Everything above is what we asked for; this is what is true.
    try:
        status, category, now_id, now_name = _holder(client, ticket)
    except TrackerError as error:
        return refused(f"{key} was assigned to you, but reading it back failed, so "
                       f"whether you hold it is unknown. Run this again to find out.",
                       str(error))
    if now_id == ticket.me_id:
        return OwnershipOutcome(settled=True, message=f"{key} is held by you.",
                                holder_id=now_id, holder_name=now_name,
                                status=status, transitioned=transitioned)
    if not now_id:
        # Assigned, then unassigned before the read-back — somebody released it out
        # from under this claim. Nobody holds it, so saying somebody does would be a
        # lie, and there is nobody whose claim re-running could stamp on.
        return OwnershipOutcome(
            settled=False, status=status, transitioned=transitioned,
            message=(f"{key} was assigned to you and then to nobody, so you do not "
                     f"hold it: somebody unassigned it while this claim was in "
                     f"flight. Run this again to take it."))
    # Lost the race. The assignment is **not** undone: it would hand the ticket to
    # nobody, and on the likely reading of this state — somebody else assigned it
    # between our write and our read — undoing it would stamp on their claim.
    return OwnershipOutcome(
        settled=False, holder_id=now_id, holder_name=now_name, status=status,
        transitioned=transitioned,
        message=(f"{key} is held by {now_name or 'another account'}, not by you: they "
                 f"took it while this claim was in flight. Nothing here is yours; "
                 f"run this again if they let it go."))


def drop_ownership(client, ticket, *, force: bool = False) -> OwnershipOutcome:
    """Make `ticket` held by nobody.

    Idempotent on a ticket nobody holds. Refuses one held by another account by
    name, unless `force`. Applies no transition, and does not look at the ticket's
    status to decide anything — a ticket is released wherever it happens to sit.
    """
    key = ticket.key
    if not ticket.assignee_id:
        return OwnershipOutcome(settled=True, status=ticket.status,
                                message=f"{key} is already held by nobody.")
    if ticket.assignee_id != ticket.me_id and not force:
        return OwnershipOutcome(
            settled=False, status=ticket.status,
            holder_id=ticket.assignee_id, holder_name=ticket.assignee_name,
            message=f"{key} is held by {ticket.assignee_name}.")
    try:
        client.assign(ticket.issue_id, None)
    except TrackerError as error:
        # A project configured to forbid unassigned issues answers this with 400.
        # That is a refusal to report, not a crash — and the caller must not clear
        # the local owner after it, or ownership becomes two disagreeing facts.
        return OwnershipOutcome(
            settled=False, status=ticket.status,
            holder_id=ticket.assignee_id, holder_name=ticket.assignee_name,
            detail=str(error),
            message=(f"{key} could not be released: the tracker refused to leave it "
                     f"unassigned. Some projects do not allow unassigned issues; "
                     f"assign it to somebody in the tracker instead."))
    return OwnershipOutcome(settled=True, status=ticket.status,
                            message=f"{key} is no longer held by anyone.")
