"""Keeping a bound item's ticket where the item's status says it should be.

A local transition has already happened, and been committed, when anything here
runs: nothing in this module refuses or undoes one. It claims the ticket for a start,
moves it to the status `work.tracker.statuses` maps the item's new status to, and
records in the binding only what did **not** reach the tracker — so a ticket that
follows first time costs no file change at all. The item's committed status is the
durable statement of where the ticket should be; the record says it is not there yet.

**The work item is the source of truth for status.** After a lifecycle move, the
ticket must sit where the item's previous status left it, or anywhere on the path
from there to where the move is going; that window is what tells a hand move apart
from a move TCW itself has not managed to deliver yet. `tcw work tracker sync` has
no such window — no local transition just happened — so it puts the ticket where the
item says it belongs from wherever the ticket sits: **one that was moved on is
brought back, and one that fell behind is brought forward.** A backwards move is
reported, so somebody who moved the ticket on purpose sees that it was undone.

Three things stop a move in either direction, and none of them is about which way it
goes: a ticket assigned to another account, a ticket nobody holds, and a ticket
already resolved, whose resolution TCW never changes. The first two do not stop a
completion or a discard: a claim gates work, not resolution
(`MOVES_NEEDING_NO_CLAIM`). Anything else that stops a move is reported as
conflicting.

A ticket the user bound as a named `--part` is left alone by `sync` when nothing is
recorded for it: several items share it, another part may be holding it back, and a
hold leaves no evidence outside the checkout it happened in.

A move that takes the ticket — a start, a record naming the `start` (that start's
delivery never finished), or a binding still carrying `catch-up: true` from an older
`link --sync-status` — takes it first when it is not already this account's. Taking
it is an assignment, read back (`assert_ownership`), and moves it only when
`work.tracker.exclusive-claim-transition` names a transition to assert through.
Delivery then carries on from wherever the ticket is, and a catch-up is walked
forward rung by rung. Nothing else takes a ticket: taking one in any other
circumstance is `tcw work tracker claim`.

A lifecycle move delivers forward only. A ticket it finds already past where its
item is going, with no window to say this move put it there, is left where it is
and reported as held.

Every decision is taken from what the tracker says, read fresh; the binding is never
proof of anything.

Which transition a move applies is derived from the target status — exactly one
offered transition must lead there — unless the project names one for that move under
`work.tracker.transitions`, which is what makes a workflow with two routes into one
status reachable at all.

States: `current` (the ticket is where it should be), `pending` (the tracker could
not be reached or asked), `conflicting` (it answered, and the answer stops the move),
`held` (another open item here shares the ticket, so this one does not move it; or it
was linked without syncing its status, so moves do not bring it along), and
`none` (nothing is mapped for this status).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from tcw.store.base import (RESOLVED_STATUSES, bound_value, mapped_statuses,
                            target_status, transition_name)
from tcw.tracker.claim import _normalize
from tcw.tracker.intake import (BINDING_SIDECAR, Bound, binding_of, leave_pre_backlog,
                                moved_out, pre_backlog_hint, read_ticket, same_site,
                                with_status_synced, with_sync_record)
from tcw.tracker.jira import (TrackerAuthError, TrackerError, TrackerRateLimited,
                              TrackerUnavailable)
from tcw.tracker.ownership import assert_ownership

CURRENT, PENDING, CONFLICTING, HELD, NONE = (
    "current", "pending", "conflicting", "held", "none")

# The local status each move leaves an item in.
MOVE_STATUS = {"start": "active", "submit": "review", "rework": "active",
               "complete": "completed", "discard": "discarded"}
# The move that lands an item — or its ticket — on each local status: `MOVE_STATUS`
# inverted. `active` is `start`, not `rework`: reaching it from nothing is starting,
# and `transitions.start` names the transition that does it.
MOVE_ONTO = {"active": "start", "review": "submit", "completed": "complete",
             "discarded": "discard"}
# The moves that need no claim: they move a ticket whoever holds it, or nobody. A
# claim gates work, not resolution. Finishing and abandoning work are not statements
# that you are doing it — they say nobody is any longer — and refusing them on
# ownership would leave a resolved item with a ticket nothing can close. This
# reverses the rule this set used to state, that only a discard could act on a
# ticket nobody held: every other move then had to be a claim first, and a claim
# assigns. `start`, `submit` and `rework` are still work, and still need one.
MOVES_NEEDING_NO_CLAIM = frozenset({"complete", "discard"})
# Where to look for the status a ticket was left in, from an item's previous status.
_EARLIER = {"active": ("active",), "review": ("review", "active")}
# The same, from a recorded move whose `since` is unknown: where that move started.
# A start and a discard can start from `backlog`, where nothing is known, so they have
# none (`expected_statuses` returns early for a start).
_MOVED_FROM = {"start": (), "submit": ("active",), "rework": ("review",),
               "complete": ("review", "active"), "discard": ()}
# The rungs of the ladder, in the order the local lifecycle reaches them. A discard and
# a completion share the top rung: both are where a ticket stops.
_RUNG_ORDER = {"active": 0, "review": 1, "completed": 2, "discarded": 2}
REASON_LIMIT = 300


def ladder_steps(statuses: dict, local_target: str,
                 resolution: str | None) -> tuple[tuple[str, str], ...]:
    """The ladder as `(tracker status, the local status it stands for)`, in local
    lifecycle order and ending at `local_target`.

    Deduplicated, so two local statuses mapped to one tracker status share a rung —
    which is right: the journey simply has one hop fewer — named for the higher. An unmapped status has no
    rung and is skipped.
    """
    # A discard has no rungs below it. Work can be abandoned from anywhere — which is
    # why `_MOVED_FROM["discard"]` is empty — and marching a ticket up through the
    # statuses that mean somebody is doing the work, only to close it, is the opposite
    # of what a discard says: three sets of notifications and SLA clocks to abandon it.
    upto = 0 if local_target == "discarded" else _RUNG_ORDER[local_target]
    steps = [(target_status(statuses, name, None), name)
             for name, index in _RUNG_ORDER.items() if index < upto]
    steps.append((target_status(statuses, local_target, resolution), local_target))
    # A shared rung keeps its first place but the *last* local status's name: reaching
    # it lands the ticket on the higher of them, so its hop must use that status's
    # move — `transitions.complete`, not `transitions.submit`, when both map to Done.
    out: dict[str, tuple[str, str]] = {}
    for mapped, local in steps:
        if mapped:
            out[_normalize(mapped)] = (out.get(_normalize(mapped), (mapped,))[0], local)
    return tuple(out.values())


def ladder(statuses: dict, local_target: str, resolution: str | None) -> tuple[str, ...]:
    """`ladder_steps` without the local names."""
    return tuple(mapped for mapped, _local in ladder_steps(statuses, local_target,
                                                           resolution))


def lowest_rung(statuses: dict, status: str) -> int | None:
    """The lowest rung `status` is mapped to, or `None` when it is on none.

    The lowest, because a status two local statuses share is only certainly as high as
    the lower of them."""
    rungs = [index for local, index in _RUNG_ORDER.items()
             if any(_normalize(mapped) == _normalize(status)
                    for mapped in mapped_statuses(statuses, local))]
    return min(rungs, default=None)


def forward_from(rungs: tuple[str, ...], status: str) -> tuple[str, ...]:
    """The rungs from `status` onward, inclusive — or `()` when it is not on `rungs`.

    Direction is the whole point: a ticket somebody moved *back* is below where it
    was left, so it never appears in the path forward from there and is still drift.
    """
    for index, rung in enumerate(rungs):
        if _normalize(rung) == _normalize(status):
            return rungs[index:]
    return ()


@dataclass(frozen=True)
class Outcome:
    state: str
    reason: str = ""
    recorded: bool = False       # a record was written (pending/conflicting only)
    claimed: str = ""            # the claim's own message, when this run claimed
    note: str = ""               # a warning for the caller to print: set when the
                                 # move that was made took the ticket backwards


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
        if record["move"] == "start":
            # A start leaves `backlog`, where nothing is known, and the start it records
            # is delivered exactly as it would have been: with no window. Taking the
            # ticket no longer puts it on `statuses.active` first, so there is no
            # status a claim left it in to measure from.
            return ()
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
        local_target = MOVE_STATUS[record["move"]]
        # Every rung from where the ticket was left up to where the move was taking it.
        # A person who moved it part of the way did by hand what TCW failed to do; only
        # the two ends used to be accepted, so an ordinary intermediate read as drift.
        onward = forward_from(ladder(statuses, local_target, resolution), since[0])
        if onward:
            return onward
        moved_to = target_status(statuses, local_target, resolution)
        return tuple(dict.fromkeys(filter(None, (*since, moved_to))))
    mapped = tuple(filter(None, (target_status(statuses, earlier, None)
                                 for earlier in _EARLIER.get(previous_status or "", ()))))
    return mapped if shared else mapped[:1]


def assess_move(ticket, *, target: str, expected: tuple[str, ...], move: str | None = None,
                named_transition: str = ""):
    """Steps 4–7 of a status move, over one ticket read. Pure. Returns `(state, reason)`, or
    `("apply", transition)` when one transition to apply can be identified.

    `move` is the lifecycle move being served, which decides whether who holds the
    ticket matters at all (`MOVES_NEEDING_NO_CLAIM`). `named_transition` is what the
    project configured for that move, if anything; without one the transition is derived
    from the target status, which is the only rule that existed before.
    """
    key, where = ticket.key, ticket.status
    if _normalize(where) == _normalize(target):
        return CURRENT, ""
    # Before the assignment, and before the window. With no window the ticket is not
    # moved wherever it sits, so who holds it changes nothing — and telling somebody to
    # take a closed ticket, or to put it back where its item is, only leads them to this
    # refusal one command later.
    if not expected and ticket.category == "done":
        return CONFLICTING, f"{key} is already resolved ('{where}'), so it was not moved."
    # Skipped whole for a resolution, not only for a ticket nobody holds: one held by
    # another account is theirs to work, not theirs to keep open.
    if move not in MOVES_NEEDING_NO_CLAIM and ticket.assignee_id != ticket.me_id:
        if ticket.assignee_id:
            return CONFLICTING, (f"{key} is assigned to {ticket.assignee_name}, not to "
                                 f"you, so it was not moved from '{where}' to "
                                 f"'{target}'.")
        return CONFLICTING, (f"{key} is unassigned, so it was not moved from "
                             f"'{where}' to '{target}'. Take it with `tcw work "
                             f"tracker claim`, or assign it to yourself in the "
                             f"tracker.")
    if expected:
        if _normalize(where) not in {_normalize(status) for status in expected}:
            wanted = " or ".join(f"'{status}'" for status in expected)
            return CONFLICTING, (f"{key} is in '{where}', not {wanted}; it was moved in "
                                 f"the tracker, or TCW held it there for another part "
                                 f"of the ticket whose item is not in this checkout. "
                                 f"TCW does not move it back: put it in {wanted}, or "
                                 f"move it on by hand.")
    if named_transition:
        named = [t for t in ticket.offered
                 if _normalize(t.name) == _normalize(named_transition)]
        if not named:
            offers = ", ".join(f"'{t.name}' to '{t.to_status}'" for t in ticket.offered)
            # `transitions.start` is the one key of the five that cannot be removed:
            # a start has no status-derived rule to fall back to, so the parser
            # requires it (`TRACKER_MOVE_TRANSITION_KEYS` in `tcw/store/base.py`).
            # Offering to remove it would advise something `tcw validate` refuses.
            drop = ("" if move == "start"
                    else ", or remove it to let TCW find the transition itself")
            return CONFLICTING, (f"{key} in '{where}' offers no transition named "
                                 f"'{named_transition}'. It offers: {offers or 'nothing'}."
                                 f" Fix work.tracker.transitions.{move}{drop}.")
        if len(named) > 1:
            ids = ", ".join(sorted(t.id for t in named))
            return CONFLICTING, (f"'{named_transition}' matches more than one transition "
                                 f"offered by {key} (ids {ids}); TCW will not guess which.")
        # Refused rather than applied: the mapped status is how a delivered move is told
        # from an undelivered one, so a transition landing anywhere else leaves a ticket
        # that never reads as delivered — and applying it cannot be undone.
        if _normalize(named[0].to_status) != _normalize(target):
            return CONFLICTING, (f"{key}'s transition '{named_transition}' leads to "
                                 f"'{named[0].to_status}', not '{target}', so nothing was "
                                 f"sent. Check work.tracker.transitions.{move} against "
                                 f"work.tracker.statuses.")
        return "apply", named[0]
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
        value = bound_value(item.tracker)
        if item.slug == slug or value is None:
            continue
        if ((value["project"], value["provider"], value["ticket"]["id"])
                != (bound.project, bound.provider, bound.ticket_id)):
            continue
        if item.status not in RESOLVED_STATUSES:
            held.append(item.slug)
        shared = shared or value["part"] != bound.part
    return held, shared


def deliver(store, slug: str, client, config, *, move: str | None,
            previous_status: str | None) -> Outcome:
    """Bring `slug`'s ticket to where its local status says, and record what did not.

    `move` is the transition that just happened, or `None` from `sync`.
    """
    item = store.get(slug)
    bound, revision = binding_of(store, slug)
    if not isinstance(bound, Bound):
        return Outcome(NONE)
    record = bound.sync if bound.sync and "problem" not in bound.sync else None
    local = item.status
    # **Never a target for a backlog item**, whatever `statuses` says.
    #
    # `statuses.backlog` exists so `tcw work tracker create` knows where to put a
    # ticket it is making. Delivery is a different question: an item in the
    # backlog has not moved anywhere, so there is nothing for its ticket to
    # follow. Letting the mapping through here made `sync` pull a ticket
    # *backwards* — `tcw work tracker import` of a ticket you are already working
    # binds an `In Progress` ticket to a backlog item, and the next sync sent it
    # to `To Do` with nothing printed. The backwards guard below could not catch
    # it either: `_RUNG_ORDER` has no backlog rung, so its fallback compares
    # `ticket_rung > ticket_rung`, which is never true.
    target = ("" if local == "backlog"
              else target_status(config.statuses, local, item.resolution))
    syncing = move is None                   # `sync`, not a lifecycle move
    starting = move == "start"
    # Whether this is a move that takes the ticket: a start, a binding still carrying
    # `catch-up: true` (which older versions' `link --sync-status` wrote), or a record
    # whose move is the `start`, meaning that start's delivery never finished. A
    # property of the move alone, so the early exit below can decide on it without
    # asking the tracker anything. Whether the ticket is actually still to be taken is
    # the ticket's to answer, once it has been read: `owed`, below.
    takes_ticket = starting or bound.catch_up or (record is not None
                                                  and record["move"] == "start")
    move = move or (record["move"] if record else None)
    # A resolution takes no ticket (`MOVES_NEEDING_NO_CLAIM`) — except on a catch-up
    # binding toward a completion, whose walk climbs the working statuses on the way
    # and so still needs the ticket held, exactly as it always did.
    resolving = move in MOVES_NEEDING_NO_CLAIM and not (bound.catch_up
                                                       and move == "complete")
    # Nothing is sent and nothing is written: the ticket is only reported on. A `sync`
    # with no record has no window of statuses the ticket may be in — no local move
    # just happened — so it reconciles the ticket to the item from wherever it sits, in
    # whichever direction that is. A binding for a named part is the exception: several
    # items share that ticket, another part may be holding it back, and a hold leaves no
    # evidence outside the checkout it happened in, so nothing here can tell the two
    # apart and the ticket is reported on instead.
    check_only = syncing and record is None and bound.part != "default"

    others, shared = _siblings(store, slug, bound)
    if not starting:
        # Held even when this item still owes its ticket a claim: the open part will
        # claim and move it, and claiming it here could only lead to closing it early.
        if others:
            # An open item owes the ticket no move while another part holds it, so an
            # earlier record no longer says anything true, and under strict mode it
            # would lock the item out of its own lifecycle. A finished item's record is
            # kept: if the other part goes away, it is the only thing left that can
            # still deliver this item's move.
            #
            # A record naming the `start` goes with the rest, and that costs something:
            # it is what says this item's ticket has never been claimed, so once the
            # other part closes nothing claims the ticket on this item's behalf, and the
            # next move reports the ticket unassigned and names `tcw work tracker claim`.
            # Keeping it was tried and is worse — it locks an item out of submitting
            # finished work until an unrelated part closes, for a claim one command
            # recovers. Claim state riding on this record is what `claim: owed | done`
            # was, and it is not coming back under another name.
            stale = bound.sync is not None and local not in RESOLVED_STATUSES
            if stale and not store.pending_deletion(slug):
                content = store.read_sidecar(slug, BINDING_SIDECAR).content
                store.write_sidecar(slug, BINDING_SIDECAR,
                                    with_sync_record(content, None), revision=revision)
            return Outcome(HELD, f"{bound.ticket_key} not moved: also bound to "
                                 f"{', '.join(others)}.")

    expected = expected_statuses(config.statuses, previous_status, record,
                                 item.resolution, shared=shared)
    since = record["since"] if record else (expected[0] if expected else "")
    claimed_message = ""
    backwards = ""

    def finish(state: str, reason: str = "") -> Outcome:
        # A folder about to be removed takes no write: git must hold all of it for
        # the removal to go ahead, and a staged record — or its removal — would stop it.
        # Checking writes nothing, except to remove what is no longer true: an
        # unreadable record once nothing is owed, or the unsynced note once the ticket
        # is found where its item says.
        if check_only and not (
                (state in (CURRENT, NONE, HELD) and bound.sync is not None
                 and "problem" in bound.sync)
                or (state == CURRENT and not bound.status_synced)):
            return Outcome(state, reason)
        if store.pending_deletion(slug):
            return Outcome(state, reason, claimed=claimed_message,
                           note=backwards if state == CURRENT else "")
        if state in (PENDING, CONFLICTING):
            content = store.read_sidecar(slug, BINDING_SIDECAR).content
            store.write_sidecar(slug, BINDING_SIDECAR, with_sync_record(content, {
                "state": state, "move": move, "since": since,
                "reason": reason[:REASON_LIMIT], "at": _now(),
            }), revision=revision)
            return Outcome(state, reason, recorded=True, claimed=claimed_message)
        drop_record = bound.sync is not None
        # Once the ticket is where its item says, however it got there, the note that
        # its status was never synced is no longer true.
        drop_note = state == CURRENT and (not bound.status_synced or bound.catch_up)
        if drop_record or drop_note:
            content = store.read_sidecar(slug, BINDING_SIDECAR).content
            if drop_record:
                content = with_sync_record(content, None)
            if drop_note:
                content = with_status_synced(content)
            store.write_sidecar(slug, BINDING_SIDECAR, content, revision=revision)
        return Outcome(state, reason, claimed=claimed_message,
                       note=backwards if state == CURRENT else "")

    def taken_back(state: str, reason: str) -> Outcome:
        # A failure while taking the ticket. Whatever this run already did to it — took
        # it out of triage — belongs in the recorded reason, and is then not printed a
        # second time as though it were a separate success.
        nonlocal claimed_message
        reason, claimed_message = claimed_message + reason, ""
        return finish(state, reason)

    def hint(verdict: str, ticket) -> str:
        # A ticket taken from a status nothing in the configuration accounts for may be
        # waiting in a triage column the project never named. Only for a move that
        # takes the ticket: for any other, the status is not the claim's problem.
        # And only while it is still where it was found: a status this run's own
        # transition put it in is not one it was waiting in.
        if (verdict != CONFLICTING or not takes_ticket
                or _normalize(ticket.status) != _normalize(found)):
            return ""
        return pre_backlog_hint(config, ticket.status, ticket.category)

    def unsynced_and_out_of_step(ticket) -> bool:
        # Only the refusal a never-synced link explains: the ticket's status is out of
        # the window. One somebody else holds, or a transition the project misnamed, is
        # a real conflict and stays one; so is an unclaimed ticket once it is in step.
        if not bound.status_synced and ticket.assignee_id in ("", None, ticket.me_id):
            window = {_normalize(status) for status in expected or (target,)}
            return _normalize(ticket.status) not in window
        return False

    def unsynced(ticket) -> Outcome:
        # `link` bound work already under way and was not asked to sync the ticket's
        # status, so a ticket that does not match is what the user chose — not drift,
        # and not something `sync` should retry. Held, with the way to opt in; any
        # record an outage left is dropped, since nothing will deliver it.
        return finish(HELD, (f"{ticket.key} not moved to '{target}': it is in "
                             f"'{ticket.status}' and was linked without syncing its "
                             f"status. {unsynced_hint(slug, ticket.key)}"))

    def walk(ticket) -> Outcome:
        # A ticket TCW has never held can be several rungs below its item — it was
        # linked to work already under way, and `link --sync-status` asked for it to
        # catch up. It goes straight to the target when the workflow offers that;
        # otherwise it walks the rungs the project itself mapped, one at a time,
        # re-reading between them because what a workflow offers depends on where the
        # ticket is. Bounded by the ladder: at most one hop per rung, each strictly
        # higher, so it ends without a counter. Two paths get here: a claim that is
        # owed, and a recorded move whose ticket is inside its window but has no
        # transition straight to the target — a walk a failure interrupted. Both only
        # on a binding `link --sync-status` made. A ticket somebody moved *back*
        # reaches neither, so it is never walked forward.
        nonlocal since
        if ticket.category == "done" and _normalize(ticket.status) != _normalize(target):
            # Each hop passes the ticket's own status as `expected`, which skips
            # `assess_move`'s resolved check, so it is made here: a ticket somebody
            # already closed is never moved to a different closed status.
            since = ticket.status
            return finish(CONFLICTING, f"{ticket.key} is already resolved "
                                       f"('{ticket.status}'), so it was not moved.")
        # From the item's status, not the recorded move's: a move that happened while
        # nothing was sent leaves the record naming an earlier one.
        steps = ladder_steps(config.statuses, local, item.resolution)
        reached = forward_from(tuple(rung for rung, _local in steps), ticket.status)
        remaining = list(steps[len(steps) - len(reached) + 1:] if reached else steps)
        while remaining:
            # Before every hop, not only the first: the claim no longer puts the ticket
            # on the first rung, and the shortcut is often offered only from there.
            if len(remaining) > 1:
                hop = MOVE_ONTO[local]
                verdict, _detail = assess_move(
                    ticket, target=target, expected=(ticket.status,), move=hop,
                    named_transition=transition_name(config.move_transitions, hop,
                                                     item.resolution))
                if verdict == "apply":
                    remaining = remaining[-1:]           # a shortcut: take it
            rung, local_name = remaining.pop(0)
            hop = MOVE_ONTO[local_name]
            verdict, detail = assess_move(
                ticket, target=rung, expected=(ticket.status,), move=hop,
                named_transition=transition_name(config.move_transitions, hop,
                                                 item.resolution))
            if verdict == CURRENT:
                continue
            since = ticket.status
            if verdict != "apply":
                # Not undone: the ticket is nearer where it belongs than it was, and
                # every resting place is a mapped rung, so a later sync resumes here.
                return finish(verdict, detail + hint(verdict, ticket))
            try:
                client.apply_transition(ticket.issue_id, detail.id)
            except TrackerError as error:
                since = ticket.status          # nothing moved
                return finish(classify_error(error), str(error))
            try:
                ticket = read_ticket(client, bound.ticket_id)
            except TrackerError as error:
                # The hop was applied, so the ticket is on `rung` even though the read
                # that would have confirmed it failed. Recording where it actually is
                # beats recording where it was: `since` is what the next run measures
                # its window from.
                since = rung
                return finish(classify_error(error), str(error))
        since = ticket.status
        if _normalize(ticket.status) == _normalize(target):
            return finish(CURRENT)
        return finish(CONFLICTING, f"{ticket.key} did not reach '{target}': it is in "
                                   f"'{ticket.status}'.")

    if not same_site(bound.ticket_url, config.base_url):
        return finish(CONFLICTING, (
            f"{bound.ticket_key}'s binding points at "
            f"{bound.ticket_url or 'no recorded URL'}, which is not on {config.base_url}; "
            f"nothing was sent. Unlink and link it again if the site changed."))
    if not target and (not takes_ticket or local in RESOLVED_STATUSES):
        # Nothing is owed to the tracker for this status. For finished work that
        # includes the claim an undelivered start or a catch-up still owes, which would
        # take a ticket only to leave it held; open work with no mapping still owes it.
        return finish(NONE)

    try:
        ticket = read_ticket(client, bound.ticket_id)
    except TrackerError as error:
        return finish(classify_error(error), str(error))
    found = ticket.status
    # A move that takes the ticket first takes it out of a `pre-backlog` status such as
    # Triage, whoever it is assigned to: a reporter's own ticket is already theirs, and
    # still has to leave triage before it can be worked. Never for a move that takes no
    # ticket — `submit`, `rework`, `complete`, a discard — and never for a report-only
    # check, which sends nothing.
    if takes_ticket and not check_only and not resolving:
        try:
            ticket, refusal, left = leave_pre_backlog(client, ticket)
        except TrackerError as error:
            return finish(classify_error(error), str(error))
        claimed_message = moved_out(ticket.key, left)
        if refusal is not None:
            detail = f" ({refusal.detail})" if refusal.detail else ""
            return taken_back(PENDING if refusal.row in ("0-read", "0f") else CONFLICTING,
                              refusal.message + detail)
    # The claim is owed only while the ticket is not already this account's. Both
    # halves are needed: without `takes_ticket`, a `submit` on a ticket nobody holds
    # would claim it, which is taking work on behalf of somebody who never took it.
    owed = takes_ticket and ticket.assignee_id != ticket.me_id

    # Somebody moved the ticket on past where its item is, and it is about to be put
    # back. Said rather than confirmed: `sync` is already something a person asked
    # for, a prompt would stop `--all` and every script, and a successful move leaves
    # no record by design. The transcript is where a deliberate move that got undone
    # has to be visible.
    #
    # Only for a `sync`. A lifecycle move that finds its ticket a rung up is `rework`,
    # which moves an item from review back to active every time it runs — telling the
    # user that their own move was drift somebody else caused would be a lie.
    ticket_rung = lowest_rung(config.statuses, ticket.status)
    if syncing and target and ticket_rung is not None and ticket_rung > _RUNG_ORDER.get(
            local, ticket_rung):
        backwards = (f"{ticket.key} was in '{ticket.status}', past where {slug} is, "
                     f"and was put back to '{target}'.")

    if owed:
        at_target = bool(target) and _normalize(ticket.status) == _normalize(target)
        if at_target and local in RESOLVED_STATUSES:
            # Already where it goes, and the item is finished: nothing is left to claim
            # for. Retrying the claim could only move it back first, on a workflow that
            # offers it.
            return finish(CURRENT)
        rung = lowest_rung(config.statuses, ticket.status)
        if resolving:
            # A resolution claims nothing. Finishing or abandoning work is not a
            # statement that you are doing it, and claiming would assign the ticket —
            # and, for a discard, move it into a working status purely so it could be
            # closed. Nothing is owed afterwards either: the item is resolved, so no
            # later move will ever want a claim. `assess_move`, with no window, still
            # refuses a ticket that is already resolved.
            owed = False
            since = ticket.status
            expected = ()
        elif check_only:
            # Reached by a part binding still carrying `catch-up: true` with nothing
            # recorded. Nothing writes that key any more, but it is still read, and a
            # report-only check must never take the ticket.
            return Outcome(CONFLICTING, f"the claim of {bound.ticket_key} is still owed.")
        elif not starting and rung is not None and rung > 0:
            # Already past the claim's own status. Applying the claim transition from
            # above it could only move it back — a workflow may offer it from anywhere
            # — and TCW never pulls a ticket back.
            if rung > _RUNG_ORDER.get(local, rung):
                return finish(CONFLICTING, (
                    f"{ticket.key} is in '{ticket.status}', which is past where its item "
                    f"is, so it was not claimed or moved back."))
            if ticket.category == "done":
                # `claim` refuses a resolved ticket first, and skipping it must not lose
                # that: with the window set to where the ticket is, `assess_move`
                # would not look, and a closed ticket could change resolution. Before
                # the assignment, so a closed ticket is never "assign it to yourself".
                return finish(CONFLICTING, (
                    f"{ticket.key} is already resolved ('{ticket.status}'), so it was "
                    f"not moved."))
            # Nobody here holds it — `owed` says so — and claiming it from above the
            # claim's own status could move it back.
            whose = (f"assigned to {ticket.assignee_name}" if ticket.assignee_id
                     else "unassigned")
            return finish(CONFLICTING, (
                f"{ticket.key} is in '{ticket.status}' and {whose}. Claiming it from "
                f"there could move it back, so nothing was sent. Assign it to yourself "
                f"in the tracker, then run `tcw work tracker sync {slug}`."))
        else:
            # Taking the ticket is an assignment, read back — never a move, unless the
            # project names `exclusive-claim-transition`, which is applied first so a
            # workflow that refuses a second claimant stops one here. Whatever status
            # it is left in, the move below delivers from there.
            since = ticket.status
            try:
                outcome = assert_ownership(
                    client, ticket, assertion=config.exclusive_claim_transition)
            except TrackerError as error:
                return taken_back(classify_error(error), str(error))
            if not outcome.settled:
                detail = f" ({outcome.detail})" if outcome.detail else ""
                # Where the claim lives now, for a ticket nobody else holds. Said only
                # then: telling somebody to claim a ticket another account holds would
                # send them to a refusal naming that account, which this message
                # already does.
                where = ("" if outcome.holder_id not in ("", ticket.me_id) else
                         f" Take it with `tcw work tracker claim {slug}`, then run "
                         f"`tcw work tracker sync {slug}`.")
                return taken_back(PENDING if outcome.retry else CONFLICTING,
                                  outcome.message + detail + where)
            owed = False
            claimed_message += outcome.message
            if not target:
                return finish(NONE)
            try:
                ticket = read_ticket(client, bound.ticket_id)
            except TrackerError as error:
                return finish(classify_error(error), str(error))
            if outcome.transitioned:
                since = ticket.status
    elif takes_ticket and not check_only and not resolving:
        # Already this account's, so nothing is sent to take it — but a start still
        # says so, as the claim it replaces always did.
        claimed_message += f"{ticket.key} is already held by you."

    if bound.catch_up and not check_only:
        # A binding an older `link --sync-status` wrote: the ticket is walked up rung by
        # rung, whoever held it before this run. Never from above where its item is:
        # a walk takes hops by the item's moves, and from there the first one could
        # only move it back.
        rung = lowest_rung(config.statuses, ticket.status)
        if rung is not None and rung > _RUNG_ORDER.get(local, rung):
            return finish(CONFLICTING, (
                f"{ticket.key} is in '{ticket.status}', which is past where its item "
                f"is, so it was not claimed or moved back."))
        return walk(ticket)
    # Without a catch-up, delivery after a claim is the one transition it always was;
    # walking a ticket through several statuses is only ever asked for.
    #
    # With one exception, which keeps what the claim used to do as part of taking the
    # ticket: a recorded `start` the item has since moved past is delivered first, as
    # the start it records, then the move that followed it. Only for a ticket this
    # account now holds and still below the ladder — one already on it has had its
    # start, and one nobody holds is a resolution's to move, which needs no start.
    active = target_status(config.statuses, "active", None)
    if (record is not None and record["move"] == "start" and local != "active"
            and active and not check_only and ticket.assignee_id == ticket.me_id
            and lowest_rung(config.statuses, ticket.status) is None):
        verdict, detail = assess_move(
            ticket, target=active, expected=(), move="start",
            named_transition=transition_name(config.move_transitions, "start", None))
        if verdict != "apply":
            return finish(verdict, detail + hint(verdict, ticket))
        try:
            client.apply_transition(ticket.issue_id, detail.id)
        except TrackerError as error:
            return finish(classify_error(error), str(error))
        try:
            ticket = read_ticket(client, bound.ticket_id)
        except TrackerError as error:
            since = active                  # applied, so that is where it is
            return finish(classify_error(error), str(error))
        # TCW has just put it on `statuses.active`, so that is where the move that
        # followed the start measures from — what the claim transition left, before.
        since, expected = ticket.status, (active,)

    # Forward only, for a lifecycle move. A move with a window already refuses a ticket
    # outside it (`assess_move`); one with none — a start out of `backlog` — would
    # otherwise pull a ticket somebody already moved on back down to its item, and
    # nobody running `tcw work start` is asking about where the ticket is. Held, not
    # conflicting: nothing is wrong and nothing is owed, so no record is written and
    # the move exits cleanly. `sync` is where a person asks for reconciliation, and it
    # still reconciles in both directions. A resolved ticket is left to `assess_move`,
    # which refuses it.
    if (not syncing and not expected and target and ticket.category != "done"
            and _normalize(ticket.status) != _normalize(target)
            and ticket_rung is not None and ticket_rung > _RUNG_ORDER.get(local, ticket_rung)):
        return finish(HELD, (f"{ticket.key} not moved to '{target}': it is already in "
                             f"'{ticket.status}', past where {slug} is, and a {move} does "
                             f"not move a ticket back. `tcw work tracker sync {slug}` "
                             f"would."))

    # Only when the move's own mapped status is the one being moved to. `move` here can
    # be a *recorded* move the item is already past — `move = move or record["move"]`
    # above — and the transition configured for that move leads where it lands, not to
    # `target`, so naming it could only ever refuse. Every move a caller passes agrees
    # with `local` by construction, so this narrows nothing a caller asked for; what it
    # catches is a stale record, where deriving the transition from the target status is
    # the only honest answer left. It applies to all five keys: a record naming
    # `complete` under an item back in `review` was wrong the same way before `start`
    # joined them, and reached the same refusal wherever a project had named that one.
    named = (transition_name(config.move_transitions, move, item.resolution)
             if move and MOVE_STATUS.get(move) == local else "")
    verdict, detail = assess_move(ticket, target=target, expected=expected, move=move,
                                  named_transition=named)
    if verdict != "apply":
        # A recorded move whose ticket is inside its window, with more than one rung
        # still to climb, is a walk a failure stopped part-way — the claim landed, so
        # the record no longer says it is owed. One transition cannot finish it on a
        # workflow with no shortcut, so it resumes the walk instead of refusing.
        if (verdict == CONFLICTING and bound.catch_up and record is not None
                and _normalize(ticket.status) in {_normalize(s) for s in expected}
                and len(forward_from(ladder(config.statuses, local, item.resolution),
                                     ticket.status)) > 2):
            return walk(ticket)
        if verdict == CONFLICTING and unsynced_and_out_of_step(ticket):
            return unsynced(ticket)
        return finish(verdict, detail + hint(verdict, ticket))
    if check_only:
        if unsynced_and_out_of_step(ticket):
            return unsynced(ticket)
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
    # The assignment clause is relaxed for finished work exactly as the owed
    # short-circuit above relaxes it: a completion or a discard may move a ticket
    # whoever holds it, and moving it assigns nothing, so demanding the ticket be ours
    # afterwards would turn that success into "did not reach 'Won't Do': it is in
    # 'Won't Do'".
    if _normalize(again.status) == _normalize(target) and (
            local in RESOLVED_STATUSES or again.assignee_id == again.me_id):
        return finish(CURRENT)
    if failure is not None:
        return finish(classify_error(failure), str(failure))
    return finish(CONFLICTING, (f"{again.key} did not reach '{target}': it is in "
                                f"'{again.status}'."))


def record_unsent(store, slug: str, *, move: str, reason: str) -> Outcome:
    """Record that a move was not sent at all — the tracker configuration has
    problems, so there is no client to send it with. Pending: fixing the
    configuration and running `sync` sends it. Keeps an existing record's `since`,
    as any later transition does."""
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
        "reason": reason[:REASON_LIMIT], "at": _now(),
    }), revision=revision)
    return Outcome(PENDING, reason, recorded=True)


# ── strict mode ──────────────────────────────────────────────────────────────
#
# `deliver` never refuses: it runs after a move. These run before one, for
# `work.tracker.strict`, and never write — a refused change moved nothing, so there
# is nothing for a `sync` record to say.


def binding_refusal(store, slug: str, config, *, own=None) -> tuple[Bound | None, str | None]:
    """The checks strict mode makes on `slug`'s binding before reading its ticket:
    `(bound, None)`, or `(None, why not)`. Nothing here asks the tracker.

    `own` is where *this item's* own state is read from, when that is not `store`.
    `complete` passes the branch copy of a `--worktree` item: the moves made during
    the work are committed on the branch, so the primary checkout's binding and
    owner are as stale as its status until the merge-back.
    """
    own = own or store
    try:
        bound, _revision = binding_of(own, slug)
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
        # `sync` acts as whoever runs it and skips an item somebody else started, so
        # pointing at it without naming the owner sends the caller into a loop: the
        # refusal says run sync, and sync says skipped. `owner` is a field on the item,
        # not an identity this layer resolves — that stays in the CLI.
        item = own.get(slug)
        owner = item.owner if item is not None else ""
        whose = (f" It is held by {owner}, so run it as them: "
                 f"`TCW_WORK_OWNER={owner} tcw work tracker sync {slug}`." if owner else "")
        return None, (f"{key} has a change that has not reached the tracker ({what}). Run "
                      f"`tcw work tracker sync {slug}` first;{whose} if that cannot clear "
                      f"it, fix the ticket in the tracker, or unlink the item and discard "
                      f"it.")
    return bound, None


def authorize(store, slug: str, client, config, *, target: str, own=None,
              ownership: bool = True) -> str | None:
    """`None` when the ticket bound to `slug` authorizes a change leading to the
    tracker status `target` (empty when that status is unmapped); otherwise why not.

    Assignment is checked before any status comparison, including "already at the
    target": a ticket someone else holds authorizes nothing, wherever it is.

    `own`, when given, is the store holding *this item's* own state — see
    `binding_refusal`. `store` still answers for every *other* item: `_siblings`
    asks which other items share the ticket, and the primary checkout is where
    their current state is. The split is deliberate; they are different questions.

    `ownership=False` skips the assignment check, for a completion: a claim gates
    work, not resolution. Where the ticket is is still asked.
    """
    own = own or store
    bound, refusal = binding_refusal(store, slug, config, own=own)
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
        *expected_statuses(config.statuses, own.get(slug).status, None, None,
                           shared=shared), target))))
    where = " or ".join(f"'{status}'" for status in allowed) or "its mapped status"
    unsynced = ("" if bound.status_synced else
                f" It was linked without syncing its status. {unsynced_hint(slug, key)}")
    if ownership and ticket.assignee_id != ticket.me_id:
        whose = (f"is assigned to {ticket.assignee_name}, not to you"
                 if ticket.assignee_id else "is unassigned")
        return (f"{key} {whose}. Assign it to yourself in "
                f"the tracker and put it in {where}, then run this again; discarding "
                f"the item is always allowed.{unsynced}")
    if _normalize(ticket.status) not in {_normalize(status) for status in allowed}:
        return (f"{key} is in '{ticket.status}', not {where}. Either it was moved in the "
                f"tracker, or TCW held it there for another part of the ticket whose item "
                f"is not in this checkout. Put it in {where}, then run this again; "
                f"discarding the item is always allowed.{unsynced}")
    return None


def unsynced_hint(slug: str, key: str) -> str:
    """How to bring along a ticket that `link` bound without its status."""
    return (f"To bring {key} along, take it with `tcw work tracker claim {slug}`, then "
            f"run `tcw work tracker sync {slug}`; where the workflow has no one "
            f"transition from its status to where {slug} is, move it yourself in the "
            f"tracker.")


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
    verdict = assess(config.start_transition, current_status=outcome.status,
                     offered=offered, landing_status=active or outcome.status)
    if verdict.exclusivity == NOT_EXCLUSIVE:
        return (f"{key} was claimed, but its workflow still offers "
                f"'{config.start_transition}' from '{outcome.status}', so a second person "
                f"could claim it too. TCW leaves the ticket claimed.")
    return None
