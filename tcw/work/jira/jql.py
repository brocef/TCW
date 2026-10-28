"""Every Jira Query Language (JQL) string TCW sends (TCW-71 Design 6, 7.1).

Each string placed in a query goes through `quote`, and custom fields are
addressed by id (`cf[10042]`), never by display name. No builder uses `~`:
on a text field it is a word search, not equality (Design 6), so TCW Project
is matched after the search instead.

The test fake parses exactly the shapes built here (`tests/work/jira/fake_jql.py`),
and a test builds every shape, so a new clause cannot slip past the fake.

Within one command the same item search, with the same account and fields, is
sent once and its answer kept, until a write (TCW-113 Design 3.5,
`tcw.work.jira.backend._kept_search`).
"""

from __future__ import annotations

from typing import Iterable

#: Jira's limit on keys in one `key IN (...)` search.
MAX_KEYS = 100
ORDER = " ORDER BY created ASC"


def quote(text: str) -> str:
    """A JQL string literal: wrapped in `"`, with `\\` and `"` escaped."""
    return '"' + str(text).replace("\\", "\\\\").replace('"', '\\"') + '"'


def field(field_id: str) -> str:
    """A custom field by id: `customfield_10042` → `cf[10042]`."""
    prefix = "customfield_"
    if not field_id.startswith(prefix) or not field_id[len(prefix):].isdigit():
        raise ValueError(f"not a custom field id: {field_id!r}")
    return f"cf[{field_id[len(prefix):]}]"


def _values(values: Iterable[str]) -> str:
    return "(" + ", ".join(quote(v) for v in values) + ")"


def _narrowed(clauses: list[str], statuses: Iterable[str] | None,
              not_statuses: Iterable[str] | None, parent: str | None,
              assignee: str | None, labels: Iterable[str] | None) -> str:
    if statuses is not None:
        clauses.append(f"status IN {_values(statuses)}")
    if not_statuses is not None:
        clauses.append(f"status NOT IN {_values(not_statuses)}")
    if parent is not None:
        clauses.append(f"parent = {quote(parent)}")
    if assignee is not None:
        clauses.append(f"assignee = {quote(assignee)}")
    if labels is not None:
        clauses.append(f"labels IN {_values(labels)}")
    return " AND ".join(clauses) + ORDER


def item_query(project: str, item_field: str, *,
               statuses: Iterable[str] | None = None,
               not_statuses: Iterable[str] | None = None,
               parent: str | None = None, assignee: str | None = None,
               labels: Iterable[str] | None = None) -> str:
    """The items of one Jira project (Design 6): tickets with a TCW Item,
    narrowed by status, parent key, assignee account and labels."""
    return _narrowed([f"project = {quote(project)}", f"{field(item_field)} IS NOT EMPTY"],
                     statuses, not_statuses, parent, assignee, labels)


def item_keys_query(project: str, keys: Iterable[str], *,
                    statuses: Iterable[str] | None = None,
                    not_statuses: Iterable[str] | None = None,
                    parent: str | None = None, assignee: str | None = None,
                    labels: Iterable[str] | None = None) -> str:
    """The items of a project without the TCW fields: the tickets its item
    folders name, at most `MAX_KEYS`, narrowed as `item_query` narrows."""
    keys = list(keys)
    if not keys or len(keys) > MAX_KEYS:
        raise ValueError(f"a key search takes 1 to {MAX_KEYS} keys, not {len(keys)}")
    return _narrowed([f"project = {quote(project)}", f"key IN {_values(keys)}"],
                     statuses, not_statuses, parent, assignee, labels)


def inbox_query(project: str, item_field: str | None, inbox_status: str,
                extra: str | None = None) -> str:
    """The Jira inbox (Design 7.1): tickets at the inbox status with no TCW
    Item, or, without the TCW fields, every ticket at the inbox status; with
    `inbox-query`, the union of the two."""
    default = f"project = {quote(project)} AND status = {quote(inbox_status)}"
    if item_field is not None:
        default += f" AND {field(item_field)} IS EMPTY"
    if extra:
        return f"({default}) OR ({extra})" + ORDER
    return default + ORDER


def keys_query(keys: Iterable[str]) -> str:
    """The tickets with these keys; at most `MAX_KEYS`."""
    keys = list(keys)
    if not keys or len(keys) > MAX_KEYS:
        raise ValueError(f"a key search takes 1 to {MAX_KEYS} keys, not {len(keys)}")
    return f"key IN {_values(keys)}"


def sample_query(project: str, issue_type: str, status: str) -> str:
    """One ticket of a type at a status, for `validate --remote` to sample."""
    return (f"project = {quote(project)} AND issuetype = {quote(issue_type)} "
            f"AND status = {quote(status)}" + ORDER)


def type_query(project: str, issue_type: str) -> str:
    """Tickets of one issue type, for `validate --remote` to sample an edit
    screen."""
    return f"project = {quote(project)} AND issuetype = {quote(issue_type)}" + ORDER
