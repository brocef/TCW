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
from dataclasses import dataclass, replace

import yaml

from tcw.store.base import (RESOLVED_STATUSES, Bound, Malformed, Unbound,  # noqa: F401
                            _binding_text, classify_binding, unreadable_binding)

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
    except Exception as error:   # YAML errors, nesting too deep, and values YAML
        # cannot build (`2026-02-30`, `!!int abc`) raise ValueError, KeyError and others
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


def ever_bound(store, slug: str) -> bool:
    """Whether `slug` holds a binding, or holds the record of one it used to.

    Not "whether a sidecar file exists". A `created` or `owed` record is a
    sidecar with no binding in it and none in its history: the item has never
    been bound to anything. Reading that as "was bound" made `tcw work drop`
    refuse an item with "It is, or was, bound to a ticket, and dropping would
    erase that record" when there was no such record — and the web app's drop
    gate said the same, with `unlink` refusing the item too, so hand-editing
    `tracker.yaml` was the only way out.

    Unreadable counts as bound. When the file cannot be read, the safe answer is
    the one that refuses to destroy it.
    """
    try:
        found = store.read_sidecar(slug, BINDING_SIDECAR)
    except (OSError, UnicodeDecodeError):
        return True
    if found is None:
        return False
    try:
        data = yaml.safe_load(found.content)
        # Any `unlinked` content at all, not just the list `unlink` writes: a
        # hand-written one in another shape still says a binding was removed.
        if isinstance(data, dict) and data.get("unlinked"):
            return True
        return not isinstance(classify_binding(data), Unbound)
    except Exception:                   # noqa: BLE001 — see the docstring
        return True


def binding_of(store, slug: str) -> tuple[Unbound | Malformed | Bound, str | None]:
    """One item's binding, and the revision to write it back with.

    The revision is `None` when there is no file, which the caller turns into
    `""` — "must not exist yet" — for `write_sidecar`.
    """
    resource = store.read_sidecar(slug, BINDING_SIDECAR)
    if resource is None:
        return Unbound(), None
    return read_binding(resource.content), resource.revision


def same_site(ticket_url: str, base_url: str) -> bool:
    """Whether a binding's ticket URL is on the configured Jira site.

    A binding does not record its site except through `ticket.url`, and ticket ids
    are numbered per site, so a binding made before `base-url` changed can name a
    ticket id that belongs to an unrelated ticket now. Same scheme and host,
    ignoring case, and a path under the site's own path followed by `/browse/`. An
    empty or unparseable URL is not on any site.
    """
    from urllib.parse import urlsplit
    try:
        ticket, site = urlsplit(ticket_url), urlsplit(base_url)
    except ValueError:
        return False
    if not ticket.scheme or not ticket.netloc:
        return False
    return (ticket.scheme.lower() == site.scheme.lower()
            and ticket.netloc.lower() == site.netloc.lower()
            and ticket.path.startswith(site.path.rstrip("/") + "/browse/"))


def find_binding(store, *, project: str, provider: str, ticket_id: str,
                 part: str, base_url: str | None = None) -> str | None:
    """The slug of the unresolved item bound to this key, or `None`.

    Resolved items are not consulted, because a ticket whose item was discarded
    may be taken again. The cost is that a ticket held by a resolved item can be
    bound to a second, open item without a refusal — a known limit, kept because
    consulting them would refuse the discarded case this skip exists for.

    With `base_url`, a binding for the same ticket id whose URL is on another site
    refuses rather than counting as a match or a miss: the id may name a different
    ticket there. The site is deliberately not part of the key, or every binding
    would look new after a site rename and imports would create duplicates.
    """
    wanted = (project, provider, ticket_id, part)
    matches: list[str] = []
    for item in store.query():
        if item.status in RESOLVED_STATUSES:
            continue
        try:
            binding, _revision = binding_of(store, item.slug)
        except (OSError, UnicodeDecodeError) as error:
            # Same answer as `Malformed`, and for the same reason: this scan
            # cannot say whether the ticket is taken, so it must refuse rather
            # than guess. Raised as a `BindingProblem` because every caller
            # already reports one in words; letting the read error through gave
            # a traceback, and gave it while binding some *other* item, since
            # this scan visits the whole board.
            raise BindingProblem(
                f"{item.slug} has a {BINDING_SIDECAR} that cannot be read "
                f"({error}), so it cannot be told whether this ticket is "
                f"already bound. Repair or remove that file first.") from error
        if isinstance(binding, Malformed):
            raise BindingProblem(
                f"{item.slug} has a {BINDING_SIDECAR} that cannot be read "
                f"({binding.reason}), so it cannot be told whether this ticket is "
                f"already bound. Repair or unlink that binding first.")
        if (base_url is not None and isinstance(binding, Bound)
                and binding.key()[:3] == wanted[:3]
                and not same_site(binding.ticket_url, base_url)):
            raise BindingProblem(
                f"{item.slug} is bound to ticket id {ticket_id} at "
                f"{binding.ticket_url or 'an unrecorded URL'}, which is not on "
                f"{base_url}. The same id may be a different ticket there. Unlink "
                f"{item.slug} if its binding is stale, or restore the site.")
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
                     unlinked: list, status_synced: bool = True) -> str:
    """The `tracker.yaml` text for a new binding. No credential goes in it.

    The document records that an item and a ticket are the same work and nothing
    more: it names no account, because binding does not claim the ticket.
    `status_synced=False` notes that the item was already past `backlog` and the
    ticket was not brought along.

    Nothing writes `catch-up: true` any more — `link --sync-status` did, and is
    retired — but a binding already carrying it is still read (`Bound.catch_up`), so
    the multi-rung walk it asked for stays reachable until those bindings age out.
    """
    document = {
        "schema": 1,
        "provider": provider,
        "project": project,
        "part": part,
        "ticket": {"id": ticket_id, "key": ticket_key, "url": ticket_url},
        "bound": bound,
        "unlinked": list(unlinked),
    }
    if not status_synced:
        document["status-synced"] = False
    return yaml.safe_dump(document, sort_keys=False, allow_unicode=True)


_BINDING_KEYS = ("provider", "project", "part", "ticket", "bound", "sync", "comment",
                 "status-synced", "catch-up", "created", "owed")


def unlinked_history(content: str | None) -> list:
    """The `unlinked` entries an existing document carries, for a new binding."""
    if content is None:
        return []
    data = yaml.safe_load(content)
    history = data.get("unlinked") if isinstance(data, dict) else None
    return list(history) if isinstance(history, list) else []


def created_record(content: str | None) -> dict | None:
    """The `created` record an item's `tracker.yaml` carries, or `None`.

    Written between "the tracker made a ticket" and "the binding was written",
    which is the only window in `tcw work tracker create` that costs something
    nothing here can undo — TCW never deletes a ticket. A run interrupted in that
    window leaves this behind, and the next run binds the key it names instead of
    creating a second ticket.

    It deliberately carries no `ticket` key, so `classify_binding` still reads the
    item as **unbound**: it is not a binding and must not be mistaken for one by
    anything that counts bindings, least of all `find_binding`.
    """
    if content is None:
        return None
    try:
        data = yaml.safe_load(content)
    except Exception:       # the same breadth as `read_binding`, for the same reason
        return None
    if not isinstance(data, dict):
        return None
    record = data.get("created")
    if not isinstance(record, dict):
        return None
    key, issue_id = _binding_text(record.get("key")), _binding_text(record.get("id"))
    return {"key": key, "id": issue_id} if key and issue_id else None


def with_created_record(content: str | None, record: dict | None) -> str:
    """`content` with its `created` record set, or removed for `None`.

    Unlike its siblings this accepts `None` content, because the record is written
    by `create` onto an item that has no sidecar at all in the ordinary case.
    """
    return _with_key(content if content is not None else "{}\n", "created", record)


#: The longest an owed reason may be. The reason is usually a tracker's own
#: error text — `_for_status` carries up to 500 characters of raw response body
#: — and it is written into `tracker.yaml`, which is committed, and read back
#: into the middle of a sentence by `tcw work show`. One line, bounded.
OWED_REASON_LIMIT = 200


def owed_reason(reason: str) -> str:
    """`reason` as one bounded line, safe to commit and to read in a sentence."""
    folded = " ".join(str(reason).split())
    if len(folded) <= OWED_REASON_LIMIT:
        return folded
    return folded[:OWED_REASON_LIMIT - 1].rstrip() + "…"


def record_owed(store, slug: str, *, reason: str, since: str) -> None:
    """Note on `slug` that a ticket was to be created on filing and was not.

    Shared by the CLI and the web app. The web app runs no tracker code by
    design, so it cannot attempt creation — but it can record the debt, and must:
    an item filed there in a project with creation-on-filing enabled would
    otherwise look exactly like one filed in a project that never turned it on,
    which is the quiet accumulation `Unbound.owed` exists to prevent.

    Raises what the store raises. Both callers decide for themselves what a
    failure to record means, because neither may fail the filing over it.
    """
    found = store.read_sidecar(slug, BINDING_SIDECAR)
    store.write_sidecar(
        slug, BINDING_SIDECAR,
        with_owed_record(found.content if found else None,
                         {"since": since, "reason": owed_reason(reason)}),
        revision=found.revision if found else "")


def with_owed_record(content: str | None, record: dict | None) -> str:
    """`content` with its `owed` record set, or removed for `None`.

    Written when filing was configured to make a ticket and could not reach the
    tracker. Like `created`, it carries no `ticket` key, so the item stays
    **unbound** — it owes a ticket, it does not have one.
    """
    return _with_key(content if content is not None else "{}\n", "owed", record)


def with_sync_record(content: str, record: dict | None) -> str:
    """`content` with its `sync` record set to `record`, or removed for `None`.
    Every other key keeps its value and its place."""
    return _with_key(content, "sync", record)


def with_status_synced(content: str) -> str:
    """`content` without the notes about syncing its ticket's status — that it was
    never synced, or that a catch-up was asked for — once the ticket is in step."""
    return _with_key(_with_key(content, "status-synced", None), "catch-up", None)


def with_comment_record(content: str, record: dict | None) -> str:
    """`content` with its owed `comment` set to `record`, or removed for `None`."""
    return _with_key(content, "comment", record)


def _with_key(content: str, key: str, record: dict | None) -> str:
    data = yaml.safe_load(content)
    data.pop(key, None)
    if record is not None:
        data[key] = dict(record)
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def created_but_unbound(store, slug: str) -> dict | None:
    """The `created` record on `slug`, or `None`. Never raises.

    Separate from `ever_bound`, which answers "was this ever bound" — a `created`
    record is not a binding and never was, so that answer is correctly no. But
    it is the only local pointer to a ticket that really exists, and deleting
    the item deletes the sidecar with it, leaving an open ticket in a shared
    tracker with nothing anywhere naming it. The gates that refuse to destroy a
    binding record ask this as well.
    """
    from tcw.store.base import Unbound
    try:
        binding, _revision = binding_of(store, slug)
    except Exception:                   # noqa: BLE001 — see the docstring
        return None
    return binding.created if isinstance(binding, Unbound) else None


def created_but_unbound_refusal(store, slug: str) -> str | None:
    """Why `slug` must not be destroyed, or `None`.

    Deliberately **not** gated on strict mode, unlike `ever_bound`'s refusal.
    Strict mode answers "may work proceed without a ticket"; this answers "is a
    real ticket about to lose the only thing that names it", and a project does
    not have to be strict to get into that state — `create.on-new` does not
    require strict, and under strict almost nothing reaches `tcw work new`
    anyway. Gating it on strict closed the rare case and left the common one.
    """
    made = created_but_unbound(store, slug)
    if made is None:
        return None
    return (f"{made['key']} was created for {slug} and never bound, and "
            f"destroying it would erase the only record of that ticket. Bind it "
            f"with `tcw work tracker create {slug}`, or forget the key with "
            f"`tcw work tracker unlink {slug} --reason \"<why>\"` and close "
            f"{made['key']} yourself.")


def without_pending_records(content: str) -> str:
    """`content` with any `created` and `owed` records removed.

    Both describe a ticket that is *not yet* bound, so both are spent the moment
    a binding is written — and both need clearing by hand when the ticket they
    name turns out to be gone. `unlink` is what clears them.
    """
    return _with_key(_with_key(content, "created", None), "owed", None)


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
    # The `pre-backlog` status the ticket was taken out of before the claim, or ""
    # when no such step ran. Set on success and on a refusal alike: either way the
    # ticket has left triage, and the caller has to say so (`moved_out`).
    left_status: str = ""


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


def moved_out(key: str, left_status: str) -> str:
    """The sentence every caller prints once a claim took a ticket out of triage,
    or `""` when it did not. Written once so the three callers cannot drift."""
    if not left_status:
        return ""
    return f"{key} was moved out of '{left_status}'. "


def _mapped_anywhere(statuses: dict, status: str) -> bool:
    from tcw.store.base import mapped_statuses
    from tcw.tracker.claim import _normalize
    return any(_normalize(name) == _normalize(status)
               for name in mapped_statuses(statuses))


def pre_backlog_hint(config, status: str, category: str) -> str:
    """The sentence naming `work.tracker.pre-backlog`, for a refusal on a ticket
    whose status nothing in the configuration accounts for — or `""`.

    Worded as a condition, because TCW cannot tell a status tickets wait in before
    the backlog from one the project simply forgot to map. Not said for a resolved
    ticket, a status already named under `pre-backlog`, or a mapped status."""
    from tcw.store.base import pre_backlog_entry
    if (category == "done" or pre_backlog_entry(config.pre_backlog, status)[0]
            or _mapped_anywhere(config.statuses, status)):
        return ""
    return (f" If '{status}' is where tickets wait before your backlog, name it and "
            f"the transition out of it under work.tracker.pre-backlog.")


def leave_pre_backlog(client, ticket: TicketRead
                      ) -> tuple[TicketRead, "ClaimOutcome | None", str]:
    """Take `ticket` out of a status named under `work.tracker.pre-backlog`, before
    it is claimed. Returns `(ticket to claim, refusal or None, status left)`.

    **Decided by the ticket's status alone**, never by whether a transition of the
    configured name happens to be offered. A resolved ticket, or one another
    account holds, is left for the claim's own rows 1a and 1b to refuse, so nothing
    is sent for either.

    The named transition must be offered exactly once and lead to
    `statuses.backlog`; anything else is refused before sending, because a
    transition cannot be taken back and a ticket landing elsewhere is somewhere no
    later run can reason about. After sending, the ticket is read again, and the
    claim works from that read — never from the one taken before the step, since
    somebody may have taken or closed the ticket in between.

    Rows, in the claim's own table style: `0a` refused before sending, `0b` landed
    somewhere else, `0d` the tracker refused the transition, `0e` the tracker
    accepted it but the ticket did not move, `0f` could not tell whether it applied
    and it did not arrive, `0-read` sent but not read back. `0f` and `0-read` are
    worth retrying; the others need somebody to act.
    """
    from tcw.store.base import pre_backlog_entry, target_status
    from tcw.tracker.claim import _normalize
    from tcw.tracker.jira import (TrackerAuthError, TrackerError, TrackerNotFound,
                                  TrackerPermissionError, TrackerRateLimited,
                                  TrackerRequestInvalid)

    status, name = pre_backlog_entry(client.config.pre_backlog, ticket.status)
    if (not status or ticket.category == "done"
            or ticket.assignee_id not in ("", None, ticket.me_id)):
        return ticket, None, ""
    key, where = ticket.key, f"work.tracker.pre-backlog.{status}"
    backlog = target_status(client.config.statuses, "backlog", None)

    def refused(row: str, message: str, left: str = "", detail: str = ""):
        return ticket, ClaimOutcome(row=row, claimed=False, message=message,
                                    detail=detail, issue_id=ticket.issue_id, key=key,
                                    url=ticket.url, summary=ticket.summary,
                                    status=ticket.status), left

    offers = ", ".join(f"'{t.name}' to '{t.to_status}'" for t in ticket.offered)
    matches = [t for t in ticket.offered if _normalize(t.name) == _normalize(name)]
    if not matches:
        return refused("0a", f"{key} in '{ticket.status}' offers no transition named "
                             f"'{name}'. It offers: {offers or 'nothing'}. Fix {where}.")
    if len(matches) > 1:
        ids = ", ".join(sorted(t.id for t in matches))
        return refused("0a", f"'{name}' matches more than one transition offered by "
                             f"{key} (ids {ids}); TCW will not guess which. Fix {where}.")
    if _normalize(matches[0].to_status) != _normalize(backlog):
        return refused("0a", f"{key}'s transition '{name}' leads to "
                             f"'{matches[0].to_status}', not '{backlog}', so nothing was "
                             f"sent. It offers: {offers}. Check {where} against "
                             f"work.tracker.statuses.backlog.")

    detail = ""
    try:
        client.apply_transition(ticket.issue_id, matches[0].id)
        result = "applied"
    except TrackerRequestInvalid as error:
        result, detail = "refused", str(error)
    except (TrackerAuthError, TrackerPermissionError, TrackerRateLimited,
            TrackerNotFound):
        raise
    except TrackerError as error:
        result, detail = "unknown", str(error)
    # The messages below give no recovery step: that depends on the command, and
    # each caller adds its own (`sync`, `start` again, or the same import).
    try:
        fresh = read_ticket(client, ticket.issue_id)
    except TrackerError as error:
        # Moved only if the tracker said the transition applied; an unanswered
        # request is reported as exactly that.
        if result == "applied":
            return refused("0-read", f"'{name}' applied, but {key} could not be read "
                                     f"back, so where it is now is unknown.", status,
                           str(error))
        return refused("0-read", f"'{name}' was sent; whether it applied is unknown, "
                                 f"and {key} could not be read back.", detail=str(error))
    if _normalize(fresh.status) == _normalize(backlog):
        return fresh, None, status
    if _normalize(fresh.status) == _normalize(ticket.status):
        if result == "refused":
            return refused("0d", f"the tracker refused '{name}', so {key} is still in "
                                 f"'{ticket.status}'.", detail=detail)
        if result == "applied":
            # A workflow rule can decline a transition without an error, so an
            # accepted request is not a move. Trying again would meet the same rule.
            return refused("0e", f"the tracker accepted '{name}', but {key} is still "
                                 f"in '{ticket.status}'.", detail=detail)
        return refused("0f", f"could not tell whether '{name}' applied, and {key} is "
                             f"still in '{ticket.status}'.", detail=detail)
    return refused("0b", f"{key} did not reach '{backlog}' through '{name}': it is in "
                         f"'{fresh.status}'.", status, detail)


def claim(client, ticket: TicketRead) -> ClaimOutcome:
    """Claim `ticket` for the signed-in account, first taking it out of a
    `work.tracker.pre-backlog` status when it is in one (`leave_pre_backlog`).

    Every outcome says, in `left_status`, whether the ticket left triage. So does a
    tracker error raised after the step, as an attribute of the same name: the
    ticket has moved even though the claim did not finish, and the caller has to
    say so. A bare `raise` keeps the error's type, so it is still sorted into
    pending or conflicting correctly.
    """
    from tcw.tracker.jira import TrackerError

    ticket, refusal, left = leave_pre_backlog(client, ticket)
    if refusal is not None:
        return replace(refusal, left_status=left)
    try:
        outcome = _claim_from(client, ticket)
    except TrackerError as error:
        if left:
            error.left_status = left
        raise
    return replace(outcome, left_status=left)


def _claim_from(client, ticket: TicketRead) -> ClaimOutcome:
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
    name = client.config.start_transition

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
                             f"offer {name!r}. It offers: {offers}."
                             + pre_backlog_hint(client.config, status, ticket.category))
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
