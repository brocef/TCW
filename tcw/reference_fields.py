"""The fields that hold a reference to another object, in one table (TCW-114
Design 6.1).

Every reader that looks for references in a record reads which fields to
look at from `FIELDS`: `tcw validate`'s checkers, the stores' refusals to
remove an object something names, and the rewrite a move or rename makes
(`tcw/rewrite.py`). Each keeps its own rule about a value (Design 6.3); only
the list of fields is shared, so a field added here is checked, refused on
and rewritten everywhere at once.

The table is TCW-110 Design 5.1's, with the `parent` of a term and a
capability (TCW-111 Design 3.1) and the two references a Jira item's state
file records (TCW-114 Design 3.3). `TCW Item` is the Jira ticket field that
names the item a ticket is; only the Jira backend reads and writes it.

Records:

- `work-item`: a files-backend item's state file.
- `jira-item`: a Jira-backend item's state file.
- `jira-ticket`: a Jira ticket's fields.
- `capabilities-yaml`: an item's `capabilities.yaml`; a dotted name is a key
  inside a mapping (`taxonomy.new` is `new` under `taxonomy:`).
- `term`, `capability`: a term's or capability's state file.
- `markdown`: a `tcw://` link in a document (`link`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Field:
    """One field that holds references. `many`: a list (or, in a
    capability, a comma list) rather than one value. `namespace`: what it
    names, None for anything. `group`: the first id-path part every value
    must have (`roles/` for `Roles`). `negatable`: a value may start with
    `!`, kept outside the reference."""

    record: str
    name: str
    many: bool
    namespace: str | None
    group: str | None = None
    negatable: bool = False


FIELDS: tuple[Field, ...] = (
    Field("work-item", "parent", False, "work"),
    Field("work-item", "blocked-by", True, "work"),
    Field("jira-item", "parent", False, "work"),
    Field("jira-item", "blocked-by", True, "work"),
    Field("jira-ticket", "TCW Item", False, "work"),
    Field("capabilities-yaml", "new", True, "capabilities"),
    Field("capabilities-yaml", "changed", True, "capabilities"),
    Field("capabilities-yaml", "removed", True, "capabilities"),
    Field("capabilities-yaml", "taxonomy.new", True, "taxonomy"),
    Field("capabilities-yaml", "taxonomy.changed", True, "taxonomy"),
    Field("capabilities-yaml", "taxonomy.removed", True, "taxonomy"),
    Field("term", "relatesTo", True, "taxonomy"),
    Field("term", "vocabulary", True, "taxonomy"),
    Field("term", "parent", False, "taxonomy"),
    Field("capability", "Subject", True, "taxonomy"),
    Field("capability", "Feature", False, "taxonomy"),
    Field("capability", "Superseded by", False, "capabilities"),
    Field("capability", "Blocked by", False, "capabilities"),
    Field("capability", "Roles", True, "capabilities", "roles", True),
    Field("capability", "When", True, "capabilities", "conditions", True),
    Field("capability", "parent", False, "capabilities"),
    Field("markdown", "link", True, None),
)


def fields_of(record: str, *, namespace: str | None = None,
              parent: bool = True) -> tuple[Field, ...]:
    """The rows of `record`, in table order; with `namespace`, only those
    naming it; `parent=False` leaves out the `parent` row."""
    return tuple(f for f in FIELDS if f.record == record
                 and (namespace is None or f.namespace == namespace)
                 and (parent or f.name != "parent"))


def names(record: str, **kw) -> tuple[str, ...]:
    """The field names of `fields_of(record, **kw)`."""
    return tuple(f.name for f in fields_of(record, **kw))


def field(record: str, name: str) -> Field:
    """The row of `record` named `name`."""
    for f in FIELDS:
        if f.record == record and f.name == name:
            return f
    raise KeyError(f"{record} {name}")


def _lookup(data: dict, dotted: str) -> Any:
    value: Any = data
    for part in dotted.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def tokens(row: Field, raw: Any) -> list[str]:
    """The values a field holds, as text, empty ones left out: one value for
    a single field; a list's items, or a comma list split, for a many."""
    if raw is None:
        return []
    if not row.many:
        text = str(raw).strip()
        return [text] if text else []
    items = raw if isinstance(raw, list) else str(raw).split(",")
    return [str(t).strip() for t in items if str(t).strip()]


def values(record: str, data: Any, **kw) -> list[tuple[Field, str, bool]]:
    """`(field, value, negated)` for every reference in `data`, a parsed
    record of kind `record`, in table order. `!` is taken off a negatable
    field's value and reported as `negated`. Not for `markdown`, whose
    links are found in text (`tcw.validate.links_outside_code`)."""
    if not isinstance(data, dict):
        return []
    out = []
    for row in fields_of(record, **kw):
        for token in tokens(row, _lookup(data, row.name)):
            negated = row.negatable and token.startswith("!")
            out.append((row, token[1:] if negated else token, negated))
    return out
