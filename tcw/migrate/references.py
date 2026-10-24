"""References rewritten to full identifiers (TCW-116 Design 4.1, C16;
plan Steps 8 and 22).

Each 3.x value gets the owner 3.x gives it. A work slug `<project>/<folder>`
names that project's item. A taxonomy or capability path prefixed with an
`extends` project's ID is that project's; a bare one is read as the store's
3.x `get` read it (`legacy.bare_owner_3x`): the project's own when it has
the object, else the one inherited source that has it, ambiguous B10. A
`capabilities.yaml` entry under `new:`, `changed:` or `removed:` is routed
as 3.x's `route_capability_path` routes it (`legacy.route_entry_3x`), and
one under `taxonomy:` read as a term is. A value already written as a full
identifier is left. A reference to an object an override's move put at a new
id-path names the new one: this run's moves for the project's own objects,
and a migrated source's record (`moved:`) for its own.

Every owner given is kept in the plan (Design 2.7), so the progress record
says why each byte it writes is what it is.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from tcw.ids import FullId, id_part_problem, id_path_problem, looks_full
from tcw.migrate.legacy import Ambiguous3, bare_owner_3x, links_3x, route_entry_3x
from tcw.migrate.model import Blocker
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
class View:
    """What 3.x's readers resolved a bare reference against, for each axis
    (`taxonomy`, `capabilities`): the project's own id-paths; each source's
    (a project the axis's `extends` names) id-paths, by its ID; and the
    project's listed children, which a `capabilities.yaml` entry may be
    routed to. `moved` is each source's record's `moved:`."""

    own: dict[str, set[str]] = field(default_factory=dict)
    sources: dict[str, dict[str, set[str]]] = field(default_factory=dict)
    children: list[str] = field(default_factory=list)
    moved: dict[str, dict[str, str]] = field(default_factory=dict)

    def sources_of(self, axis: str) -> dict[str, set[str]]:
        return {pid: paths[axis] for pid, paths in self.sources.items() if axis in paths}


B10_FIX = "qualify the reference with the project that owns it, then run 'tcw migrate' again"


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
    view: View = field(default_factory=View)

    def _ambiguous(self, where: str, row: Field, value: str) -> None:
        owners = sorted(pid for pid, paths in self.view.sources_of(row.namespace).items()
                        if value in paths)
        self.blockers.append(Blocker(
            "B10", where, f"{row.name}: {value} is in more than one project this one "
                          f"inherits from ({', '.join(owners)}), and TCW 3 refused it",
            B10_FIX))

    def _full(self, owner: str | None, namespace: str, path: str) -> str:
        if owner is None:
            if namespace == "capabilities":
                path = self.moved.get(path, path)
            return str(FullId(self.project, namespace, path))
        if namespace == "capabilities":
            path = self.view.moved.get(owner, {}).get(path, path)
        return str(FullId(owner, namespace, path))

    def owner_of(self, value: str, row: Field, where: str) -> str | None:
        """The full identifier `value` names, or None to leave it."""
        if not value or looks_full(value):
            return None
        if row.namespace == "work":
            project, _, folder = value.partition("/")
            if not folder or id_part_problem(project) or id_path_problem(folder):
                return None
            new = str(FullId(project, "work", folder))
        else:
            if id_path_problem(value):
                return None
            sources = self.view.sources_of(row.namespace)
            own = self.view.own.get(row.namespace, set())
            owner, path = None, value
            try:
                if row.record == "capabilities-yaml" and row.namespace == "capabilities":
                    routed = route_entry_3x(
                        value, extends=set(sources), children=self.view.children,
                        has_ledger=self.has_ledger,
                        own_namespaces={p.split("/", 1)[0]
                                        for p in own.union(*sources.values())},
                        project_id=self.project)
                    if isinstance(routed, str):
                        self.blockers.append(Blocker(
                            "B10", where, routed, "remove the entry, or keep a "
                                                  "capabilities store, then run "
                                                  "'tcw migrate' again"))
                        return None
                    owner, path = routed
                    if owner is None:
                        owner, path = bare_owner_3x(path, own, sources)
                else:
                    owner, path = bare_owner_3x(value, own, sources)
            except Ambiguous3:
                self._ambiguous(where, row, value)
                return None
            if not path or id_path_problem(path):
                return None
            new = self._full(owner, row.namespace, path)
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
        from tcw.migrate.legacy import link_owner_3x
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
                if id_path_problem(ref) or (prefix and id_part_problem(prefix)):
                    continue
                new = FullId(prefix or self.project, "work", ref).address()
            else:
                try:
                    owner, path = link_owner_3x(
                        link.parsed, self.view.own,
                        {pid: paths for pid, paths in self.view.sources.items()
                         if namespace in paths})
                except Ambiguous3:
                    self.blockers.append(Blocker(
                        "B10", where, f"{link.uri}: is in more than one project this "
                                      f"one inherits from, and TCW 3 refused it", B10_FIX))
                    continue
                if not path or id_path_problem(path):
                    continue
                new = f"tcw://{self._full(owner, namespace, path)}"
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
