"""Taking a tracker ticket as TCW work: the binding, and the claim.

**The binding** is the `tracker.yaml` sidecar that records which ticket a work item
answers. It is read and written only through the store's abstract sidecar surface,
and found by querying items — nothing here walks a folder — so any store that can
hold a named sidecar per item can hold a binding.

**A binding is never proof that a claim was made.** It is a file in the user's own
repository and anyone can write one. Every command that acts on a ticket re-reads
the ticket from the tracker and decides from that.

`project` arrives as a plain string. This module does not import the filesystem
project registry; the caller resolves the node's id and passes it in.

**What a binding classifies as** — `Unbound`, `Malformed` or `Bound` — is decided in
`tcw/store/base.py` (`classify_binding`), because the store classifies it too, to
fill `WorkItem.tracker`, and a board read must not import this package. The names
are re-exported here; `read_binding` adds only the parsing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import yaml

from tcw.store.base import (RESOLVED_STATUSES, Bound, Malformed, Unbound,  # noqa: F401
                            classify_binding, unreadable_binding)

BINDING_SIDECAR = "tracker.yaml"
DEFAULT_PART = "default"
_PART = re.compile(r"[a-z0-9][a-z0-9-]*")


class BindingProblem(ValueError):
    """A binding could not be trusted to answer "is this ticket already bound?".

    Raised for a malformed binding and for two items holding one key. Both refuse
    rather than guess: skipping a binding that cannot be read would report a ticket
    as unbound when it may not be.
    """


# ── reading a binding ────────────────────────────────────────────────────────


def read_binding(content: str | None) -> Unbound | Malformed | Bound:
    """Classify one item's `tracker.yaml` content (`None` when there is no file).

    No file is unbound, and text that is not YAML is malformed; everything else is
    `classify_binding`'s rules.
    """
    if content is None:
        return Unbound()
    try:
        data = yaml.safe_load(content)
    except (yaml.YAMLError, RecursionError) as error:
        return unreadable_binding(error)
    return classify_binding(data)


def validate_part(value: str | None) -> str:
    """A part name, or `default` when none was given."""
    if value is None:
        return DEFAULT_PART
    if not _PART.fullmatch(value):
        raise ValueError(
            f"part {value!r} is not a valid part name: use lowercase letters, digits "
            f"and hyphens, starting with a letter or digit")
    return value


def binding_of(store, slug: str) -> tuple[Unbound | Malformed | Bound, str | None]:
    """One item's binding, and the revision to write it back with.

    The revision is `None` when there is no file, which the caller turns into
    `""` — "must not exist yet" — for `write_sidecar`.
    """
    resource = store.read_sidecar(slug, BINDING_SIDECAR)
    if resource is None:
        return Unbound(), None
    return read_binding(resource.content), resource.revision


def find_binding(store, *, project: str, provider: str, ticket_id: str,
                 part: str) -> str | None:
    """The slug of the unresolved item bound to this key, or `None`.

    Resolved items are not consulted, because a ticket whose item was discarded
    may be taken again. The cost is that a ticket held by a resolved item can be
    bound to a second, open item without a refusal — a known limit, kept because
    consulting them would refuse the discarded case this skip exists for.
    """
    wanted = (project, provider, ticket_id, part)
    matches: list[str] = []
    for item in store.query():
        if item.status in RESOLVED_STATUSES:
            continue
        binding, _revision = binding_of(store, item.slug)
        if isinstance(binding, Malformed):
            raise BindingProblem(
                f"{item.slug} has a {BINDING_SIDECAR} that cannot be read "
                f"({binding.reason}), so it cannot be told whether this ticket is "
                f"already bound. Repair or unlink that binding first.")
        if isinstance(binding, Bound) and binding.key() == wanted:
            matches.append(item.slug)
    if len(matches) > 1:
        raise BindingProblem(
            f"more than one item is bound to this ticket and part: "
            f"{', '.join(matches)}. Unlink all but one first.")
    return matches[0] if matches else None


# ── writing a binding ────────────────────────────────────────────────────────


def binding_document(*, provider: str, project: str, part: str, ticket_id: str,
                     ticket_key: str, ticket_url: str, bound: str,
                     unlinked: list) -> str:
    """The `tracker.yaml` text for a new binding. No credential goes in it.

    The document records that an item and a ticket are the same work and nothing
    more: it names no account, because binding does not claim the ticket.
    """
    return yaml.safe_dump({
        "schema": 1,
        "provider": provider,
        "project": project,
        "part": part,
        "ticket": {"id": ticket_id, "key": ticket_key, "url": ticket_url},
        "bound": bound,
        "unlinked": list(unlinked),
    }, sort_keys=False, allow_unicode=True)


_BINDING_KEYS = ("provider", "project", "part", "ticket", "bound", "sync")


def unlinked_history(content: str | None) -> list:
    """The `unlinked` entries an existing document carries, for a new binding."""
    if content is None:
        return []
    data = yaml.safe_load(content)
    history = data.get("unlinked") if isinstance(data, dict) else None
    return list(history) if isinstance(history, list) else []


def with_sync_record(content: str, record: dict | None) -> str:
    """`content` with its `sync` record set to `record`, or removed for `None`.
    Every other key keeps its value and its place."""
    data = yaml.safe_load(content)
    data.pop("sync", None)
    if record is not None:
        data["sync"] = dict(record)
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def unlink_document(content: str, *, reason: str, today: str) -> str:
    """`content` with its binding moved into `unlinked`, beside the reason.

    The file is kept rather than deleted so the record of what was bound, and why
    it stopped being, survives.
    """
    data = yaml.safe_load(content)
    entry = {key: data.pop(key) for key in _BINDING_KEYS if key in data}
    entry["unlinked-on"] = today
    entry["reason"] = reason
    history = unlinked_history(content)
    data.pop("unlinked", None)
    data["unlinked"] = [*history, entry]
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


# ── the claim ────────────────────────────────────────────────────────────────
#
# Row ids ("1a" … "3f") are the spec's decision tables, carried on every outcome so
# tests assert decisions rather than wording.


@dataclass(frozen=True)
class TicketRead:
    """What step 1 read: the ticket, what it offers now, and who is asking."""
    issue_id: str
    key: str
    url: str
    summary: str
    status: str
    category: str
    assignee_id: str
    assignee_name: str
    offered: tuple
    me_id: str
    me_name: str


@dataclass(frozen=True)
class ClaimOutcome:
    row: str
    claimed: bool
    message: str
    detail: str = ""
    issue_id: str = ""
    key: str = ""
    url: str = ""
    summary: str = ""
    status: str = ""
    account_id: str = ""
    account_name: str = ""
    transitioned: bool = False


def _fields(issue: dict) -> tuple[str, str, str, str]:
    """(status, status category, assignee id, assignee name) from an issue."""
    fields = issue.get("fields") or {}
    status = fields.get("status") or {}
    assignee = fields.get("assignee") or {}
    return (str(status.get("name", "")),
            str((status.get("statusCategory") or {}).get("key", "")),
            str(assignee.get("accountId", "")),
            str(assignee.get("displayName", "")))


def read_ticket(client, key: str) -> TicketRead:
    """Step 1's reads. Separate from `claim` so a caller can check for an existing
    binding between reading the ticket and changing it."""
    issue = client.issue(key)
    issue_id = str(issue.get("id", ""))
    canonical = str(issue.get("key", key))
    status, category, assignee_id, assignee_name = _fields(issue)
    offered = tuple(client.transitions(issue_id or canonical))
    me = client.myself()
    return TicketRead(
        issue_id=issue_id, key=canonical,
        url=f"{client.config.base_url}/browse/{canonical}",
        summary=str((issue.get("fields") or {}).get("summary", "")),
        status=status, category=category,
        assignee_id=assignee_id, assignee_name=assignee_name, offered=offered,
        me_id=str(me.get("accountId", "")), me_name=str(me.get("displayName", "")))


def claim(client, ticket: TicketRead) -> ClaimOutcome:
    """Claim `ticket` for the signed-in account, deciding only from what the tracker
    says afterwards.

    **Transition first; assign only after an applied transition.** On a workflow
    that refuses the claim from its own destination, a second claimant's transition
    is refused, so it never reaches the assign and cannot overwrite the first
    claimant's assignment. Assigning first would let two accounts overwrite each
    other before either transition ran.

    Authentication, permission, rate-limit and not-found errors on the transition
    propagate: the transition did not apply and there is nothing to read back.
    """
    from tcw.tracker.claim import AMBIGUOUS, _normalize, assess
    from tcw.tracker.jira import (TrackerAuthError, TrackerError, TrackerNotFound,
                                  TrackerPermissionError, TrackerRateLimited,
                                  TrackerRequestInvalid)

    key, status = ticket.key, ticket.status
    name = client.config.claim_transition

    def refused(row: str, message: str, detail: str = "") -> ClaimOutcome:
        return ClaimOutcome(row=row, claimed=False, message=message, detail=detail,
                            issue_id=ticket.issue_id, key=key, url=ticket.url,
                            summary=ticket.summary, status=status)

    def claimed(row: str, message: str, now_status: str, transitioned: bool):
        return ClaimOutcome(row=row, claimed=True, message=message,
                            issue_id=ticket.issue_id, key=key, url=ticket.url,
                            summary=ticket.summary, status=now_status,
                            account_id=ticket.me_id, account_name=ticket.me_name,
                            transitioned=transitioned)

    # ── step 1 ──
    if ticket.category == "done":
        return refused("1a", f"{key} is resolved ('{status}'), so it cannot be claimed.")
    if ticket.assignee_id and ticket.assignee_id != ticket.me_id:
        return refused("1b", f"{key} is assigned to {ticket.assignee_name} in "
                             f"'{status}', so it cannot be claimed.")
    assessment = assess(name, current_status=status, offered=ticket.offered)
    if assessment.verdict == AMBIGUOUS:
        return refused("1c", f"{key} cannot be claimed: the claim transition name "
                             f"is ambiguous on this ticket.", assessment.detail)
    matches = [t for t in ticket.offered if _normalize(t.name) == _normalize(name)]
    if not matches:
        if ticket.assignee_id == ticket.me_id:
            return claimed("1e", f"not claimed by this run: {key} is already in "
                                 f"'{status}' and assigned to you.", status, False)
        offers = ", ".join(repr(t.name) for t in ticket.offered) or "nothing"
        return refused("1f", f"{key} is in '{status}', unassigned, and does not "
                             f"offer {name!r}. It offers: {offers}.")
    transition = matches[0]
    landing = transition.to_status

    # ── step 2 ──
    detail = ""
    try:
        client.apply_transition(ticket.issue_id, transition.id)
        result = "applied"
    except TrackerRequestInvalid as error:
        result, detail = "refused", str(error)
    except (TrackerAuthError, TrackerPermissionError, TrackerRateLimited,
            TrackerNotFound):
        raise
    except TrackerError as error:
        result, detail = "unknown", str(error)
    if result == "applied" and not ticket.assignee_id:
        try:
            client.assign(ticket.issue_id, ticket.me_id)
        except TrackerError as error:
            detail = str(error)

    # ── step 3 ──
    try:
        now_status, now_category, now_id, now_name = _fields(client.issue(ticket.issue_id))
    except TrackerError as error:
        return refused("3-read", f"could not read {key} back, so whether this run's "
                                 f"claim applied is unknown. Running this command "
                                 f"again will find out.", str(error))
    status = now_status
    landed = _normalize(now_status) == _normalize(landing) and now_category != "done"
    if now_id == ticket.me_id and landed:
        return claimed("3a", f"claimed {key}: now in '{now_status}' and assigned to "
                             f"you.", now_status, result == "applied")
    if now_id:
        if now_id != ticket.me_id:
            also = (" This run's transition applied; the assignment is theirs."
                    if result == "applied" else "")
            return refused("3b", f"not claimed: {key} is assigned to {now_name} in "
                                 f"'{now_status}'.{also}", detail)
        return refused("3c", f"the claim did not take effect: {key} is assigned to "
                             f"you but is in '{now_status}', not '{landing}'.", detail)
    if result == "refused":
        return refused("3d", f"the claim did not apply: {key} is in '{now_status}', "
                             f"unassigned.", detail)
    if result == "applied":
        return refused("3e", f"{key} moved to '{now_status}' but is not assigned to "
                             f"you. Assign it to yourself in the tracker, then run "
                             f"this command again.", detail)
    return refused("3f", f"could not tell whether this run's claim applied: {key} is "
                         f"in '{now_status}', unassigned. Check the ticket's history "
                         f"in the tracker before assigning it.", detail)
