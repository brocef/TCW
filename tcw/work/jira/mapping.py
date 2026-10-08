"""Item properties to and from ticket fields, and text to and from the
Atlassian Document Format (ADF), the JSON tree Jira's version 3 API uses for
rich text (TCW-71 Design 3, 4, 14).

Nothing here reads the network: the backend passes in what it read.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Iterable, Mapping

from tcw.work.jira.config import JiraConfig
from tcw.work.model import DEFAULT_PRIORITY, SIZES, UNSET, Changes

BLOCKS = "Blocks"

#: ADF node types that sit inside a line of text rather than forming a block.
INLINE = frozenset({"text", "hardBreak", "mention", "emoji", "inlineCard", "date",
                    "status"})


# ---------------------------------------------------------------------------
# Text and ADF, as a pair that round-trips (Design 14)


def _lines(text: str) -> list[str]:
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def text_document(text: str) -> dict:
    """`text` as an ADF document. Paragraphs are split at each run of blank
    lines; inside a paragraph each line break is a `hardBreak`. Nothing inside a
    line is stripped or escaped: ADF has no markup, so `[`, `]` and `*` are
    literal text."""
    paragraphs: list[list[str]] = [[]]
    for line in _lines(text):
        if line.strip():
            paragraphs[-1].append(line)
        elif paragraphs[-1]:
            paragraphs.append([])
    content = []
    for lines in paragraphs:
        if not lines:
            continue
        nodes: list[dict] = []
        for index, line in enumerate(lines):
            if index:
                nodes.append({"type": "hardBreak"})
            nodes.append({"type": "text", "text": line})
        content.append({"type": "paragraph", "content": nodes})
    return {"type": "doc", "version": 1, "content": content}


def _children(node: dict) -> list:
    content = node.get("content")
    return [c for c in content if isinstance(c, dict)] if isinstance(content, list) else []


def _inline_text(node: dict) -> str:
    kind = node.get("type")
    if kind == "text":
        return str(node.get("text", ""))
    if kind == "hardBreak":
        return "\n"
    attrs = node.get("attrs") if isinstance(node.get("attrs"), dict) else {}
    for key in ("text", "shortName", "url"):
        if isinstance(attrs.get(key), str):
            return attrs[key]
    return ""


def _block_text(node: dict) -> str:
    children = _children(node)
    if all(c.get("type") in INLINE for c in children):
        return "".join(_inline_text(c) for c in children)
    # Blocks nested in a block (list items, table cells) read one per line.
    return "\n".join(_block_text(c) if c.get("type") not in INLINE
                     else _inline_text(c) for c in children)


def document_text(node: Any) -> str:
    """The text of an ADF document: top-level blocks joined by a blank line, a
    `hardBreak` as a line break, nested blocks one per line. Anything not in a
    document's shape reads as no text."""
    if not isinstance(node, dict):
        return ""
    return "\n\n".join(_block_text(block) for block in _children(node))


def normalize_text(text: str) -> str:
    """For comparing text that went through Jira: line endings unified,
    trailing spaces removed, runs of blank lines collapsed to one, ends
    stripped. Stored text is never rewritten with it."""
    out: list[str] = []
    for line in _lines(text):
        line = line.rstrip()
        if line or (out and out[-1]):
            out.append(line)
    return "\n".join(out).strip()


# ---------------------------------------------------------------------------
# Reading a ticket (Design 3)


@dataclass(frozen=True)
class Props:
    """What a ticket says about its item, before parent and blocker keys are
    turned into slugs (Design 3.1)."""
    key: str
    title: str
    status: str | None
    stage: str | None
    created: date | None
    priority: str | None
    effort: str | None
    complexity: str | None
    tags: tuple[str, ...]
    assignee: str | None
    assignee_name: str | None
    parent_key: str | None
    blocker_keys: tuple[str, ...]
    tcw_project: str | None
    tcw_item: str | None
    issue_type: str | None


def _get(mapping: Any, *path: str) -> Any:
    for key in path:
        if not isinstance(mapping, dict):
            return None
        mapping = mapping.get(key)
    return mapping


def _string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def parse_created(value: Any) -> date | None:
    """The date part of `created` once converted to UTC, so two people whose
    profiles are in different time zones read the same date."""
    if not isinstance(value, str):
        return None
    for form in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(value, form).astimezone(timezone.utc).date()
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc).date()


def scale_name(option: Any) -> str | None:
    """A single-choice option's value as a scale name (`Very High` →
    `very-high`), or `None` when it is not one."""
    value = _get(option, "value") if isinstance(option, dict) else option
    if not isinstance(value, str):
        return None
    name = re.sub(r"\s+", "-", value.strip().lower())
    return name if name in SIZES else None


def blocker_links(links: Any) -> dict[str, str | None]:
    """Each ticket that blocks this one, by key, with the id of its link, in
    Jira's order. As read on the blocked ticket, a `Blocks` link names the
    blocker as `inwardIssue`. The direction is a live-check question (Design
    15.4); it lives here and in `block_link` only."""
    found: dict[str, str | None] = {}
    for link in links if isinstance(links, list) else ():
        if _get(link, "type", "name") != BLOCKS:
            continue
        key = _string(_get(link, "inwardIssue", "key"))
        if key and key not in found:
            found[key] = _string(_get(link, "id"))
    return found


def blocker_keys(links: Any) -> tuple[str, ...]:
    """The keys of the tickets that block this one."""
    return tuple(blocker_links(links))


def block_link(blocker: str, blocked: str) -> tuple[str, str]:
    """`(inward_key, outward_key)` for the client's `add_link` so that
    `blocker` blocks `blocked`."""
    return blocker, blocked


def read_props(issue: Mapping, config: JiraConfig, field_ids: Mapping[str, str],
               registered_tags: Iterable[str],
               stage_statuses: Mapping[str, str]) -> Props:
    """A ticket's fields as item properties. `field_ids` maps `project`,
    `item`, `effort` and `complexity` to Jira field ids (those configured);
    `stage_statuses` maps each enabled stage to its status name."""
    fields = issue.get("fields") if isinstance(issue.get("fields"), dict) else {}
    status = _string(_get(fields, "status", "name"))
    by_status = {name: stage for stage, name in stage_statuses.items()}
    priorities = {name: model for model, name in config.priorities.items()}
    registered = set(registered_tags)
    labels = fields.get("labels") if isinstance(fields.get("labels"), list) else []

    def custom(name: str) -> Any:
        field_id = field_ids.get(name)
        return fields.get(field_id) if field_id else None

    return Props(
        key=str(issue.get("key", "")),
        title=str(fields.get("summary") or ""),
        status=status,
        stage=by_status.get(status) if status else None,
        created=parse_created(fields.get("created")),
        priority=priorities.get(_get(fields, "priority", "name")),
        effort=scale_name(custom("effort")),
        complexity=scale_name(custom("complexity")),
        tags=tuple(label for label in labels
                   if isinstance(label, str) and label in registered),
        assignee=_string(_get(fields, "assignee", "accountId")),
        assignee_name=_string(_get(fields, "assignee", "displayName")),
        parent_key=_string(_get(fields, "parent", "key")),
        blocker_keys=blocker_keys(fields.get("issuelinks")),
        tcw_project=_string(custom("project")),
        tcw_item=_string(custom("item")),
        issue_type=_string(_get(fields, "issuetype", "name")),
    )


def read_fields(field_ids: Mapping[str, str]) -> tuple[str, ...]:
    """The fields `read` asks for (Design 3)."""
    return ("summary", "status", "created", "priority", "labels", "assignee",
            "parent", "issuelinks", "issuetype", *field_ids.values())


# ---------------------------------------------------------------------------
# Writing (Design 4)


def _option(name: str, options: Mapping[str, str] | None) -> dict:
    return {"value": (options or {}).get(name, name)}


def label_updates(added: Iterable[str], removed: Iterable[str]) -> list[dict]:
    """Label operations for an edit's `update` section, one per label, so
    labels the edit does not name are left alone."""
    return ([{"add": tag} for tag in added] + [{"remove": tag} for tag in removed])


def write_fields(changes: Changes, config: JiraConfig, field_ids: Mapping[str, str],
                 *, assignee: Any = UNSET, parent: Any = UNSET,
                 options: Mapping[str, Mapping[str, str]] | None = None
                 ) -> tuple[dict, dict]:
    """The `fields` and `update` sections of one edit. `assignee` (an account
    id or `None`) and `parent` (a ticket key or `None`) are passed already
    resolved; `options` maps each estimate field's scale names to the option
    values its Jira field offers."""
    fields: dict = {}
    if changes.title is not UNSET:
        fields["summary"] = changes.title
    if changes.priority is not UNSET:
        fields["priority"] = (None if changes.priority is None
                              else {"name": config.priorities[changes.priority]})
    for name in ("effort", "complexity"):
        value = getattr(changes, name)
        if value is UNSET or name not in field_ids:
            continue
        fields[field_ids[name]] = (None if value is None
                                   else _option(value, (options or {}).get(name)))
    if assignee is not UNSET:
        fields["assignee"] = None if assignee is None else {"accountId": assignee}
    if parent is not UNSET:
        fields["parent"] = None if parent is None else {"key": parent}
    update: dict = {}
    labels = label_updates(changes.add_tags, changes.remove_tags)
    if labels:
        update["labels"] = labels
    return fields, update


def create_fields(title: str, props: Changes, request: str | None, *,
                  config: JiraConfig, field_ids: Mapping[str, str], project_id: str,
                  issue_type: str, has_priority: bool, assignee: str | None = None,
                  parent: str | None = None,
                  options: Mapping[str, Mapping[str, str]] | None = None) -> dict:
    """The `fields` of the one create request (Design 4.1 step 2). TCW Item is
    not set here; it is set once the ticket exists (step 4)."""
    fields: dict = {
        "project": {"key": config.project},
        "issuetype": {"id": issue_type},
        "summary": title,
        field_ids["project"]: project_id,
    }
    if request is not None:
        fields["description"] = text_document(request)
    if has_priority:
        priority = DEFAULT_PRIORITY if props.priority in (UNSET, None) else props.priority
        fields["priority"] = {"name": config.priorities[priority]}
    if props.add_tags:
        fields["labels"] = list(props.add_tags)
    if assignee is not None:
        fields["assignee"] = {"accountId": assignee}
    if parent is not None:
        fields["parent"] = {"key": parent}
    for name in ("effort", "complexity"):
        value = getattr(props, name)
        if value not in (UNSET, None) and name in field_ids:
            fields[field_ids[name]] = _option(value, (options or {}).get(name))
    return fields
