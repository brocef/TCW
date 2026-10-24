"""References within the project, rewritten to full identifiers (TCW-116
Design 4.1, C16; plan Step 8).

Each 3.x value gets the owner 3.x gives it. In part 1 of the build, with no
related project, that is the project itself: a bare taxonomy or capability
path is its own, a `capabilities.yaml` entry is routed as 3.x's
`route_capability_path` routes it with no source and no child, and a work
slug `<project>/<folder>` names the project when the ID is its own. A value
already written as a full identifier is left. A work slug naming another
project, and a link to one, are B5 until part 2 converts them.

Every owner given is kept in the plan (Design 2.7), so the progress record
says why each byte it writes is what it is.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from tcw.ids import FullId, id_path_problem, looks_full
from tcw.migrate.legacy import links_3x
from tcw.migrate.model import Blocker, not_yet
from tcw.reference_fields import Field, fields_of
from tcw.rewrite import Replace

#: The record kind of each namespace's state file, by work backend.
RECORDS = {"taxonomy": "term", "capabilities": "capability"}
_AXES = {"T": "taxonomy", "C": "capabilities", "W": "work"}


def record_of(namespace: str, work_backend: str) -> str:
    if namespace == "work":
        return "jira-item" if work_backend == "jira" else "work-item"
    return RECORDS[namespace]


def state_fields(namespace: str, work_backend: str) -> tuple[Field, ...]:
    """The reference fields of a 3.x state file; `parent` of a term or
    capability is TCW 4's, written whole by C11, and so left out."""
    record = record_of(namespace, work_backend)
    return fields_of(record, parent=namespace == "work")


CAPABILITIES_YAML = fields_of("capabilities-yaml")


@dataclass
class Owners:
    """The owner of every reference one project's run converts."""

    project: str
    has_ledger: bool
    blockers: list[Blocker] = field(default_factory=list)
    given: dict[str, str] = field(default_factory=dict)
    #: Each of the project's capabilities an override's move (C14) puts at
    #: a new id-path: the 3.x id-path to the new one.
    moved: dict[str, str] = field(default_factory=dict)

    def owner_of(self, value: str, row: Field, where: str) -> str | None:
        """The full identifier `value` names, or None to leave it."""
        if not value or looks_full(value):
            return None
        if row.namespace == "work":
            project, _, folder = value.partition("/")
            if not folder:
                return None
            if project != self.project:
                self.blockers.append(not_yet(where, row.name,
                                             "a reference to another project's work item"))
                return None
            new = str(FullId(self.project, "work", folder))
        else:
            if row.record == "capabilities-yaml" and row.namespace == "capabilities" \
                    and not self.has_ledger:
                self.blockers.append(Blocker(
                    "B10", where, f"{value}: this project ('{self.project}') keeps no "
                                  f"capabilities ledger; qualify the path with a child "
                                  f"project id (it declares no child projects)",
                    "remove the entry, or keep a capabilities store, then run "
                    "'tcw migrate' again"))
                return None
            if id_path_problem(value):
                return None
            now = self.moved.get(value, value) if row.namespace == "capabilities" else value
            new = str(FullId(self.project, row.namespace, now))
        self.given[f"{where} {row.name} {value}"] = new
        return new

    def replace(self, where: str, rows: tuple[Field, ...]) -> Replace:
        """`rewrite_yaml`'s function for one file."""
        def replace(row: Field, value: str) -> str | None:
            return self.owner_of(value, row, where) if row in rows else None
        return replace

    def links(self, text: str, where: str) -> str:
        """Every 3.x `tcw://` link outside code made to hold `tcw://` and the
        full identifier, by position; a link already in TCW 4 form is left."""
        edits = []
        for link in links_3x(text):
            body = link.uri[len("tcw://"):]
            if link.parsed is None or looks_full(body):
                continue
            namespace = _AXES[link.parsed.axis]
            prefix, ref = link.parsed.namespace or None, link.parsed.ref
            if namespace == "work":
                if prefix is None and "/" in ref:
                    prefix, ref = ref.split("/", 1)
                if prefix is not None and prefix != self.project:
                    self.blockers.append(not_yet(where, link.uri,
                                                 "a link to another project's work item"))
                    continue
            elif prefix:
                ref = f"{prefix}/{ref}"
            if id_path_problem(ref):
                continue
            if namespace == "capabilities":
                ref = self.moved.get(ref, ref)
            new = FullId(self.project, namespace, ref).address()
            self.given[f"{where} link {link.uri}"] = new
            edits.append((link.start, link.end, new))
        for start, end, new in sorted(edits, reverse=True):
            text = text[:start] + new + text[end:]
        return text


def applied(data: dict, rows: tuple[Field, ...], replace: Replace) -> dict:
    """`data` as `rewrite_yaml` with `replace` leaves it: what the final check
    of a converted file compares with (Decided 9)."""
    out = copy.deepcopy(data)
    for row in rows:
        keys = row.name.split(".") if row.record == "capabilities-yaml" else [row.name]
        holder: Any = out
        for key in keys[:-1]:
            holder = holder.get(key) if isinstance(holder, dict) else None
        if not isinstance(holder, dict) or keys[-1] not in holder:
            continue
        holder[keys[-1]] = _value(holder[keys[-1]], row, replace)
    return out


def _piece(piece: str, row: Field, replace: Replace) -> str:
    token = piece.strip()
    negated = row.negatable and token.startswith("!")
    body = token[1:] if negated else token
    new = replace(row, body) if body else None
    if new is None or new == body:
        return piece
    lead = piece[:len(piece) - len(piece.lstrip())]
    trail = piece[len(piece.rstrip()):]
    return lead + ("!" if negated else "") + new + trail


def _value(value: Any, row: Field, replace: Replace) -> Any:
    if isinstance(value, list) and row.many:
        return [_piece(v, row, replace) if isinstance(v, str) else v for v in value]
    if isinstance(value, str):
        pieces = value.split(",") if row.many else [value]
        return ",".join(_piece(p, row, replace) for p in pieces)
    return value
