"""Keeping a bound item's ticket where the item's status says it should be.

A local transition has already happened, and been committed, when anything here
runs: nothing in this module refuses or undoes one. It claims the ticket for a start,
moves it to the status `work.tracker.statuses` maps the item's new status to, and
records in the binding only what did **not** reach the tracker — so a ticket that
follows first time costs no file change at all. The item's committed status is the
durable statement of where the ticket should be; the record says it is not there yet.

**TCW never follows the tracker and never pulls a ticket back.** A ticket is moved
only when it is assigned to the account the credentials authenticate as and sits
where the item's previous status left it (*expected*). Anything else is reported as
conflicting. Every decision is taken from what the tracker says, read fresh; the
binding is never proof of anything.

States: `current` (the ticket is where it should be), `pending` (the tracker could
not be reached or asked), `conflicting` (it answered, and the answer stops the move),
`held` (another open item here shares the ticket, so this one does not move it), and
`none` (nothing is mapped for this status).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from tcw.store.base import RESOLVED_STATUSES, target_status
from tcw.tracker.claim import _normalize
from tcw.tracker.intake import (BINDING_SIDECAR, Bound, binding_of, claim, read_ticket,
                                same_site, with_sync_record)
from tcw.tracker.jira import (TrackerAuthError, TrackerError, TrackerRateLimited,
                              TrackerUnavailable)

CURRENT, PENDING, CONFLICTING, HELD, NONE = (
    "current", "pending", "conflicting", "held", "none")

# The local status each move leaves an item in.
MOVE_STATUS = {"start": "active", "submit": "review", "rework": "active",
               "complete": "completed", "discard": "discarded"}
# Where to look for the status a ticket was left in, from an item's previous status.
_EARLIER = {"active": ("active",), "review": ("review", "active")}
# The same, from a recorded move whose `since` is unknown: where that move started.
# A discard can start from `backlog`, where nothing is known, so it has none.
_MOVED_FROM = {"start": ("active",), "submit": ("active",), "rework": ("review",),
               "complete": ("review", "active"), "discard": ()}
REASON_LIMIT = 300


@dataclass(frozen=True)
class Outcome:
    state: str
    reason: str = ""
    recorded: bool = False       # a record was written (pending/conflicting only)
    claimed: str = ""            # the claim's own message, when this run claimed


def classify_error(error: TrackerError) -> str:
    """Pending when the tracker was not reached or cannot yet be asked; conflicting
    when it answered and the answer stops the move."""
    if isinstance(error, (TrackerUnavailable, TrackerRateLimited, TrackerAuthError)):
        return PENDING
    return CONFLICTING


def expected_statuses(statuses: dict, previous_status: str | None, record: dict | None,
                      resolution: str | None, *, shared: bool = False) -> tuple[str, ...]:
    """Where the ticket may be before this move without it counting as drift.

    With a record: its `since`, or the target of its move — a person who moved the
    ticket by hand to where TCW meant to put it is not punished. Otherwise the
    mapped status of the previous local status, falling back to earlier ones. Empty
    when unknown (a move out of `backlog`). With `shared` — an item for another part of
    the same ticket is here — every earlier mapped status is expected: a move this
    item made while that part was open was held, so the ticket can still be behind.
    """
    if record is not None:
        if record["since"]:
            since: tuple[str, ...] = (record["since"],)
        else:
            # Unknown when the record was written (the tracker block was broken, or
            # the move left `backlog`): where the recorded move started from.
            # Only the nearest mapped one: accepting both review and active would let a
            # ticket someone sent back to active be carried forward.
            since = tuple(filter(None, (target_status(statuses, earlier, None)
                                        for earlier in _MOVED_FROM[record["move"]])))[:1]
            if not since:
                return ()
        moved_to = target_status(statuses, MOVE_STATUS[record["move"]], resolution)
        return tuple(dict.fromkeys(filter(None, (*since, moved_to))))
    mapped = tuple(filter(None, (target_status(statuses, earlier, None)
                                 for earlier in _EARLIER.get(previous_status or "", ()))))
    return mapped if shared else mapped[:1]


def assess_move(ticket, *, target: str, expected: tuple[str, ...]):
    """Steps 4–7 of a status move, over one ticket read. Pure. Returns `(state, reason)`, or
    `("apply", transition)` when exactly one offered transition leads to `target`."""
    key, where = ticket.key, ticket.status
    if _normalize(where) == _normalize(target):
        return CURRENT, ""
    if ticket.assignee_id != ticket.me_id:
        holder = ticket.assignee_name if ticket.assignee_id else "nobody"
        return CONFLICTING, (f"{key} is assigned to {holder}, not to you, so it was not "
                             f"moved from '{where}' to '{target}'.")
    if expected:
        if _normalize(where) not in {_normalize(status) for status in expected}:
            wanted = " or ".join(f"'{status}'" for status in expected)
            return CONFLICTING, (f"{key} is in '{where}', not {wanted}; it was moved in "
                                 f"the tracker, or TCW held it there for another part "
                                 f"of the ticket whose item is not in this checkout. "
                                 f"TCW does not move it back: put it in {wanted}, or "
                                 f"move it on by hand.")
    elif ticket.category == "done":
        return CONFLICTING, f"{key} is already resolved ('{where}'), so it was not moved."
    leads = [t for t in ticket.offered if _normalize(t.to_status) == _normalize(target)]
    if not leads:
        offers = ", ".join(f"'{t.name}' to '{t.to_status}'" for t in ticket.offered)
        return CONFLICTING, (f"{key} in '{where}' offers no transition to '{target}'. "
                             f"It offers: {offers or 'nothing'}.")
    if len(leads) > 1:
        ids = ", ".join(sorted(t.id for t in leads))
        return CONFLICTING, (f"{key} offers more than one transition to '{target}' "
                             f"(ids {ids}); TCW will not guess which.")
    return "apply", leads[0]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _siblings(store, slug: str, bound: Bound) -> tuple[list[str], bool]:
    """Other items here bound to the same ticket: the open ones, which hold this item's
    status moves, and whether any — open or finished — is for another part, which
    may have held this item's earlier moves. A second item for the same part is a
    re-take of the ticket, not a part that held it."""
    held, shared = [], False
    for item in store.query():
        value = item.tracker
        if item.slug == slug or not isinstance(value, dict) or "problem" in value:
            continue
        if ((value["project"], value["provider"], value["ticket"]["id"])
                != (bound.project, bound.provider, bound.ticket_id)):
            continue
        if item.status not in RESOLVED_STATUSES:
            held.append(item.slug)
        shared = shared or value["part"] != bound.part
    return held, shared


def deliver(store, slug: str, client, config, *, move: str | None,
            previous_status: str | None, check_only: bool = False) -> Outcome:
    """Bring `slug`'s ticket to where its local status says, and record what did not.

    `move` is the transition that just happened, or `None` from `sync`. With
    `check_only`, nothing is sent to the tracker and nothing is written: `sync` on an
    item with no record uses it, since without a record "not where the item says"
    cannot be told from a ticket somebody else moved.
    """
    item = store.get(slug)
    bound, revision = binding_of(store, slug)
    if not isinstance(bound, Bound):
        return Outcome(NONE)
    record = bound.sync if bound.sync and "problem" not in bound.sync else None
    local = item.status
    target = target_status(config.statuses, local, item.resolution)
    starting = move == "start"
    owed = starting or (record is not None and record["claim"] == "owed")
    move = move or (record["move"] if record else None)

    others, shared = _siblings(store, slug, bound)
    if not starting:
        # Held even when this item's claim is owed: the open part will claim and move
        # the ticket, and claiming it here could only lead to closing it early.
        if others:
            # An open item owes the ticket no move while another part holds it, so an
            # earlier record — unless it still owes the claim — no longer says
            # anything true, and under strict mode it would lock the item. A finished
            # item's record is kept: if the other part goes away, it is the only thing
            # left that can still deliver this item's move.
            stale = (bound.sync is not None and local not in RESOLVED_STATUSES
                     and (record is None or record["claim"] != "owed"))
            if stale and not store.pending_deletion(slug) and (
                    not check_only or record is None):
                content = store.read_sidecar(slug, BINDING_SIDECAR).content
                store.write_sidecar(slug, BINDING_SIDECAR,
                                    with_sync_record(content, None), revision=revision)
            return Outcome(HELD, f"{bound.ticket_key} not moved: also bound to "
                                 f"{', '.join(others)}.")

    expected = expected_statuses(config.statuses, previous_status, record,
                                 item.resolution, shared=shared)
    since = record["since"] if record else (expected[0] if expected else "")
    claimed_message = ""

    def finish(state: str, reason: str = "") -> Outcome:
        # A folder about to be removed takes no write: git must hold all of it for
        # the removal to go ahead, and a staged record — or its removal — would stop it.
        if check_only and not (state in (CURRENT, NONE) and bound.sync is not None
                               and "problem" in bound.sync):
            return Outcome(state, reason)
        if store.pending_deletion(slug):
            return Outcome(state, reason, claimed=claimed_message)
        if state in (PENDING, CONFLICTING):
            content = store.read_sidecar(slug, BINDING_SIDECAR).content
            store.write_sidecar(slug, BINDING_SIDECAR, with_sync_record(content, {
                "state": state, "move": move, "since": since,
                "claim": "owed" if owed else "done",
                "reason": reason[:REASON_LIMIT], "at": _now(),
            }), revision=revision)
            return Outcome(state, reason, recorded=True, claimed=claimed_message)
        if bound.sync is not None and not owed:
            content = store.read_sidecar(slug, BINDING_SIDECAR).content
            store.write_sidecar(slug, BINDING_SIDECAR, with_sync_record(content, None),
                                revision=revision)
        return Outcome(state, reason, claimed=claimed_message)

    if not same_site(bound.ticket_url, config.base_url):
        return finish(CONFLICTING, (
            f"{bound.ticket_key}'s binding points at "
            f"{bound.ticket_url or 'no recorded URL'}, which is not on {config.base_url}; "
            f"nothing was sent. Unlink and link it again if the site changed."))
    if not target and (not owed or local in RESOLVED_STATUSES):
        # Nothing is owed to the tracker for this status. For finished work that
        # includes a claim, which would take a ticket only to leave it held; open work
        # with no mapping still owes its claim, below.
        owed = False
        return finish(NONE)

    try:
        ticket = read_ticket(client, bound.ticket_id)
    except TrackerError as error:
        return finish(classify_error(error), str(error))

    if owed:
        at_target = bool(target) and _normalize(ticket.status) == _normalize(target)
        if at_target and (local in RESOLVED_STATUSES or ticket.assignee_id == ticket.me_id):
            # Already where it goes, and either the item is finished (nothing is left
            # to claim for) or the ticket is already this account's. Retrying the
            # claim could only move it back first, on a workflow that offers it.
            owed = False
            return finish(CURRENT)
        if check_only:
            return Outcome(CONFLICTING, f"the claim of {bound.ticket_key} is still owed.")
        try:
            outcome = claim(client, ticket)
        except TrackerError as error:
            return finish(classify_error(error), str(error))
        if not outcome.claimed:
            state = PENDING if outcome.row in ("3-read", "3f") else CONFLICTING
            detail = f" ({outcome.detail})" if outcome.detail else ""
            return finish(state, outcome.message + detail)
        if config.strict:
            # Under strict mode a claim the workflow cannot make exclusive authorizes
            # nothing, so it stays owed and nothing moves.
            refusal = claim_refusal(client, config, bound.ticket_id, outcome)
            if refusal:
                return finish(CONFLICTING, refusal)
        owed = False
        claimed_message = outcome.message
        active = target_status(config.statuses, "active", None)
        if starting:
            if active and _normalize(outcome.status) != _normalize(active):
                return finish(CONFLICTING, (
                    f"claimed {bound.ticket_key}, but it is in '{outcome.status}', not "
                    f"'{active}'."))
            return finish(CURRENT)
        expected = (active,) if active else ()
        since = active
        if not target:
            return finish(NONE)
        try:
            ticket = read_ticket(client, bound.ticket_id)
        except TrackerError as error:
            return finish(classify_error(error), str(error))

    verdict, detail = assess_move(ticket, target=target, expected=expected)
    if verdict != "apply":
        return finish(verdict, detail)
    if check_only:
        return Outcome(CONFLICTING, (
            f"{ticket.key} is in '{ticket.status}', not '{target}', and no undelivered "
            f"change is recorded, so it is not moved."))
    failure: TrackerError | None = None
    try:
        client.apply_transition(ticket.issue_id, detail.id)
    except TrackerError as error:
        failure = error
    try:
        again = read_ticket(client, bound.ticket_id)
    except TrackerError as error:
        return finish(classify_error(failure or error), str(failure or error))
    if _normalize(again.status) == _normalize(target) and again.assignee_id == again.me_id:
        return finish(CURRENT)
    if failure is not None:
        return finish(classify_error(failure), str(failure))
    return finish(CONFLICTING, (f"{again.key} did not reach '{target}': it is in "
                                f"'{again.status}'."))


def record_unsent(store, slug: str, *, move: str, reason: str) -> Outcome:
    """Record that a move was not sent at all — the tracker configuration has
    problems, so there is no client to send it with. Pending: fixing the
    configuration and running `sync` sends it. Keeps an existing record's `since`
    and `claim`, as any later transition does."""
    bound, revision = binding_of(store, slug)
    if not isinstance(bound, Bound):
        return Outcome(NONE)
    if store.pending_deletion(slug):
        return Outcome(PENDING, reason)
    record = bound.sync if bound.sync and "problem" not in bound.sync else None
    content = store.read_sidecar(slug, BINDING_SIDECAR).content
    store.write_sidecar(slug, BINDING_SIDECAR, with_sync_record(content, {
        "state": PENDING, "move": move,
        "since": record["since"] if record else "",
        "claim": "owed" if move == "start" or (record and record["claim"] == "owed")
                 else "done",
        "reason": reason[:REASON_LIMIT], "at": _now(),
    }), revision=revision)
    return Outcome(PENDING, reason, recorded=True)


# ── strict mode ──────────────────────────────────────────────────────────────
#
# `deliver` never refuses: it runs after a move. These run before one, for
# `work.tracker.strict`, and never write — a refused change moved nothing, so there
# is nothing for a `sync` record to say.


def binding_refusal(store, slug: str, config) -> tuple[Bound | None, str | None]:
    """The checks strict mode makes on `slug`'s binding before reading its ticket:
    `(bound, None)`, or `(None, why not)`. Nothing here asks the tracker."""
    try:
        bound, _revision = binding_of(store, slug)
    except (OSError, UnicodeDecodeError):
        bound = None
    if not isinstance(bound, Bound):
        return None, (f"{slug} is not bound to a readable ticket. Link it with "
                      f"`tcw work tracker link {slug} <ticket>` first.")
    key = bound.ticket_key
    if not same_site(bound.ticket_url, config.base_url):
        return None, (f"{key}'s binding points at {bound.ticket_url or 'no recorded URL'}, "
                      f"which is not on {config.base_url}.")
    if bound.sync is not None:
        what = bound.sync.get("state", "an unreadable record")
        return None, (f"{key} has a change that has not reached the tracker ({what}). Run "
                      f"`tcw work tracker sync {slug}` first; if that cannot clear it, "
                      f"fix the ticket in the tracker, or unlink the item and discard it.")
    return bound, None


def authorize(store, slug: str, client, config, *, target: str) -> str | None:
    """`None` when the ticket bound to `slug` authorizes a change leading to the
    tracker status `target` (empty when that status is unmapped); otherwise why not.

    Assignment is checked before any status comparison, including "already at the
    target": a ticket someone else holds authorizes nothing, wherever it is.
    """
    bound, refusal = binding_refusal(store, slug, config)
    if bound is None:
        return refusal
    key = bound.ticket_key
    try:
        ticket = read_ticket(client, bound.ticket_id)
    except TrackerError as error:
        return (f"the tracker could not answer ({error}), so whether this change is "
                f"authorized is unknown. Run it again once the tracker answers.")
    # Where `deliver` would expect the ticket before moving it on, or already the
    # target. For an item sharing the ticket with another part that includes earlier
    # statuses, since that part may have held this one's moves.
    _held, shared = _siblings(store, slug, bound)
    allowed = tuple(dict.fromkeys(filter(None, (
        *expected_statuses(config.statuses, store.get(slug).status, None, None,
                           shared=shared), target))))
    where = " or ".join(f"'{status}'" for status in allowed) or "its mapped status"
    if ticket.assignee_id != ticket.me_id:
        holder = ticket.assignee_name if ticket.assignee_id else "nobody"
        return (f"{key} is assigned to {holder}, not to you. Assign it to yourself in "
                f"the tracker and put it in {where}, then run this again; discarding "
                f"the item is always allowed.")
    if _normalize(ticket.status) not in {_normalize(status) for status in allowed}:
        return (f"{key} is in '{ticket.status}', not {where}. Either it was moved in the "
                f"tracker, or TCW held it there for another part of the ticket whose item "
                f"is not in this checkout. Put it in {where}, then run this again; "
                f"discarding the item is always allowed.")
    return None


def claim_refusal(client, config, ticket_id: str, outcome) -> str | None:
    """`None` when a successful claim authorizes work under strict mode; otherwise why
    not. Asked right after the claim, when the ticket is where the claim leads and so
    shows whether the workflow would let a second claimant claim it too."""
    from tcw.tracker.claim import NOT_EXCLUSIVE, assess
    active = target_status(config.statuses, "active", None)
    key = outcome.key
    if active and _normalize(outcome.status) != _normalize(active):
        return (f"{key} is assigned to you but is in '{outcome.status}', not '{active}', "
                f"so this is not a claim of it.")
    try:
        offered = client.transitions(ticket_id)
    except TrackerError as error:
        return (f"{key} was claimed, but whether its workflow can refuse a second "
                f"claimant could not be read ({error}). TCW leaves the ticket claimed; "
                f"run this again once the tracker answers.")
    verdict = assess(config.claim_transition, current_status=outcome.status,
                     offered=offered, landing_status=active or outcome.status)
    if verdict.exclusivity == NOT_EXCLUSIVE:
        return (f"{key} was claimed, but its workflow still offers "
                f"'{config.claim_transition}' from '{outcome.status}', so a second person "
                f"could claim it too. TCW leaves the ticket claimed.")
    return None
