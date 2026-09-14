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
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import yaml

from tcw.store.base import RESOLVED_STATUSES

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


@dataclass(frozen=True)
class Unbound:
    """No `tracker.yaml`, or one whose binding was removed by `unlink`."""


@dataclass(frozen=True)
class Malformed:
    """A `tracker.yaml` that does not describe a binding it is safe to act on."""
    reason: str


@dataclass(frozen=True)
class Bound:
    provider: str
    project: str
    part: str
    ticket_id: str
    ticket_key: str
    ticket_url: str

    def key(self) -> tuple[str, str, str, str]:
        return (self.project, self.provider, self.ticket_id, self.part)


def _text(value) -> str:
    return value if isinstance(value, str) else ""


def read_binding(content: str | None) -> Unbound | Malformed | Bound:
    """Classify one item's `tracker.yaml` content (`None` when there is no file).

    The rules, in order: no file is unbound; content that is not a mapping is
    malformed; a mapping with no `ticket` is unbound, which is what `unlink`
    leaves; a `ticket` mapping with a non-empty `id` and `key`, beside non-empty
    `provider`, `project` and `part`, is bound; a `ticket` in any other shape is
    malformed.
    """
    if content is None:
        return Unbound()
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as error:
        return Malformed(f"not valid YAML ({error.__class__.__name__})")
    if not isinstance(data, dict):
        return Malformed("not a YAML mapping")
    if "ticket" not in data:
        return Unbound()
    ticket = data["ticket"]
    if not isinstance(ticket, dict):
        return Malformed("'ticket' is not a mapping")
    fields = {
        "ticket.id": _text(ticket.get("id")),
        "ticket.key": _text(ticket.get("key")),
        "provider": _text(data.get("provider")),
        "project": _text(data.get("project")),
        "part": _text(data.get("part")),
    }
    missing = [name for name, value in fields.items() if not value]
    if missing:
        return Malformed(f"missing or empty: {', '.join(missing)}")
    return Bound(provider=fields["provider"], project=fields["project"],
                 part=fields["part"], ticket_id=fields["ticket.id"],
                 ticket_key=fields["ticket.key"],
                 ticket_url=_text(ticket.get("url")))


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

    Resolved items are not consulted: a ticket whose item was discarded may be
    taken again, and a resolved item's binding cannot be repaired from here.
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
                     ticket_key: str, ticket_url: str, account_id: str,
                     account_name: str, bound: str, unlinked: list) -> str:
    """The `tracker.yaml` text for a new binding. No credential goes in it."""
    return yaml.safe_dump({
        "schema": 1,
        "provider": provider,
        "project": project,
        "part": part,
        "ticket": {"id": ticket_id, "key": ticket_key, "url": ticket_url},
        "claimed-by": {"account-id": account_id, "name": account_name},
        "bound": bound,
        "unlinked": list(unlinked),
    }, sort_keys=False, allow_unicode=True)


_BINDING_KEYS = ("provider", "project", "part", "ticket", "claimed-by", "bound")


def unlinked_history(content: str | None) -> list:
    """The `unlinked` entries an existing document carries, for a new binding."""
    if content is None:
        return []
    data = yaml.safe_load(content)
    history = data.get("unlinked") if isinstance(data, dict) else None
    return list(history) if isinstance(history, list) else []


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
