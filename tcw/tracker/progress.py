"""Short progress comments on a bound ticket, one per lifecycle move.

Runs after `sync.deliver`, with `work.tracker.comments: true`. The status result
decides first: a ticket that did not follow its item owes its comment too. Otherwise
the ticket is read fresh and the comment is posted only when the ticket is assigned
to the account the credentials authenticate as. A ticket that is not is left alone,
and nothing is recorded, since such a record could never clear.

**What goes outward** is a fixed sentence naming the item's title, its part when it
is not `default`, and the move; the project's `link`, when set; and a `tcw-event:`
line. No lifecycle document, capability text or code reference is ever copied.

**Not twice.** A fresh move posts without looking, since it cannot have posted before.
Only an owed comment is looked for first, by its event id, among the account's own
newest comments — which is what catches a post that landed but whose answer was lost.
A comment not found there is posted: a repeat is better than a lost note.

**One owed comment at a time**, in the binding's `comment` key, apart from `sync`: a
note that did not post authorizes nothing and must not lock an item under strict
mode. The newest move decides — a comment posted or skipped clears an older one.
"""

from __future__ import annotations

import secrets

from tcw.store.base import link_for
from tcw.tracker.intake import (BINDING_SIDECAR, Bound, binding_of, read_ticket,
                                same_site, with_comment_record)
from tcw.tracker.jira import TrackerError
from tcw.tracker.sync import (CONFLICTING, CURRENT, MOVES_ALLOWING_UNASSIGNED, NONE,
                              PENDING, REASON_LIMIT, Outcome, _now, classify_error)

SKIPPED, CLEARED = "skipped", "cleared"

_WORDS = {"start": "started", "submit": "went to review", "rework": "went back to work",
          "complete": "was completed", "discard": "was discarded as {resolution}"}


def new_event(move: str) -> str:
    """An id for one move's comment. Random, not a time: an agent can run `submit`,
    `rework` and `submit` inside one second."""
    return f"{move}-{secrets.token_hex(4)}"


def comment_text(title: str, part: str, move: str, resolution: str | None) -> str:
    part_clause = f" (part {part})" if part != "default" else ""
    what = _WORDS[move].format(resolution=resolution or "")
    return f'TCW: "{title}"{part_clause} {what}.'


def document(text: str, link: str, event: str) -> dict:
    """The comment as a Jira document: the sentence, the link, the marker."""
    def paragraph(node: dict) -> dict:
        return {"type": "paragraph", "content": [node]}
    blocks = [paragraph({"type": "text", "text": text})]
    if link:
        blocks.append(paragraph({"type": "text", "text": link,
                                 "marks": [{"type": "link", "attrs": {"href": link}}]}))
    blocks.append(paragraph({"type": "text", "text": f"tcw-event: {event}"}))
    return {"type": "doc", "version": 1, "content": blocks}


def publish(store, slug: str, client, config, *, move: str,
            status_state: str) -> Outcome:
    """The comment for `move`, which has just happened and whose status step ended in
    `status_state`."""
    bound = _bound(store, slug, config)
    if bound is None:
        return Outcome(NONE)
    event = new_event(move)
    if status_state in (PENDING, CONFLICTING):
        return _owe(store, slug, move, event, status_state,
                    f"{bound.ticket_key} did not follow its item, so its comment waits "
                    f"for it.")
    return _send(store, slug, client, config, bound, move, event)


def retry(store, slug: str, client, config) -> Outcome:
    """Send the comment `slug` owes, unless the ticket already has it."""
    bound, _revision = binding_of(store, slug)
    if not isinstance(bound, Bound) or bound.comment is None:
        return Outcome(NONE)
    record = bound.comment
    if "problem" in record or not config.comments:
        why = ("its record cannot be read" if "problem" in record
               else "comments are turned off")
        _write(store, slug, None)
        return Outcome(CLEARED, f"the owed comment was removed: {why}.")
    if not same_site(bound.ticket_url, config.base_url):
        return _owe(store, slug, record["move"], record["event"], CONFLICTING,
                    f"{bound.ticket_key}'s binding is not on {config.base_url}, so its "
                    f"comment is not sent.")
    return _send(store, slug, client, config, bound, record["move"], record["event"],
                 look_first=True)


def hold(store, slug: str, state: str, reason: str) -> None:
    """Carry a status step that is still failing onto the owed comment's record."""
    bound, _revision = binding_of(store, slug)
    if isinstance(bound, Bound) and bound.comment and "problem" not in bound.comment:
        _owe(store, slug, bound.comment["move"], bound.comment["event"], state, reason)


def _bound(store, slug: str, config) -> Bound | None:
    if not config.comments:
        return None
    bound, _revision = binding_of(store, slug)
    if not isinstance(bound, Bound) or not same_site(bound.ticket_url, config.base_url):
        return None
    return bound


def _send(store, slug: str, client, config, bound: Bound, move: str, event: str, *,
          look_first: bool = False) -> Outcome:
    key = bound.ticket_key
    try:
        ticket = read_ticket(client, bound.ticket_id)
    except TrackerError as error:
        return _owe(store, slug, move, event, classify_error(error), str(error))
    # A move that may act on a ticket nobody holds must be able to say so on it: the
    # comment is the only record of why the ticket closed, and skipping it would close
    # the ticket silently. A ticket somebody *else* holds is still theirs to annotate.
    if ticket.assignee_id != ticket.me_id and not (
            not ticket.assignee_id and move in MOVES_ALLOWING_UNASSIGNED):
        holder = ticket.assignee_name if ticket.assignee_id else "nobody"
        _write(store, slug, None)
        return Outcome(SKIPPED, f"{key} is assigned to {holder}, so no progress comment "
                                f"was posted.")
    marker = f"tcw-event: {event}"
    try:
        if look_first and any(
                author == ticket.me_id and marker in text.splitlines()
                for author, text in client.recent_comments(ticket.issue_id)):
            _write(store, slug, None)
            return Outcome(CURRENT)
        item = store.get(slug)
        text = comment_text(item.title, bound.part, move, item.resolution)
        link = link_for(config.link, bound.project, slug) if config.link else ""
        client.add_comment(ticket.issue_id, document(text, link, event))
    except TrackerError as error:
        return _owe(store, slug, move, event, classify_error(error), str(error))
    _write(store, slug, None)
    return Outcome(CURRENT)


def _owe(store, slug: str, move: str, event: str, state: str, reason: str) -> Outcome:
    if store.pending_deletion(slug):
        # A folder about to be removed takes no write; the note is lost, not the removal.
        return Outcome(state, reason)
    _write(store, slug, {"move": move, "event": event, "state": state,
                         "reason": reason[:REASON_LIMIT],
                         "at": _now()})
    return Outcome(state, reason, recorded=True)


def _write(store, slug: str, record: dict | None) -> None:
    """Set or remove the `comment` key, reading the binding fresh: `deliver` may have
    just written it."""
    bound, revision = binding_of(store, slug)
    if not isinstance(bound, Bound) or (record is None and bound.comment is None):
        return
    if store.pending_deletion(slug):
        return
    content = store.read_sidecar(slug, BINDING_SIDECAR).content
    store.write_sidecar(slug, BINDING_SIDECAR, with_comment_record(content, record),
                        revision=revision)
