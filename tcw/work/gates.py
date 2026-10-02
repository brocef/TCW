"""The two gates TCW builds in, and the drift check that reuses the first.

**The records gate** checks that the capability and taxonomy changes an item
declares in `<item>/capabilities.yaml` are actually in the records. It runs on
the move after implementation (`model.records_gate_stage`), so the records are
checked while the code that changed them is still being looked at.

**The completion gate** checks that every verdict stage TCW can read accepted
the latest implementation.

**Drift** re-checks finished items' declarations against today's records.

None of these opens a ledger itself: each asks a `RecordsReader`, so a second
capabilities store would supply its own. `ledger_reader` is the filesystem one.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, NamedTuple, Protocol

import yaml

from tcw.store.base import RefError
from tcw.store.fs import FsCapabilitiesStore
from tcw.work.layout import ACCEPTED, Layout
from tcw.work.model import STAGES, Item, Slug

# ---------------------------------------------------------------------------
# What a reader answers


@dataclass(frozen=True)
class Present:
    status: str | None = None  # a capability's status; None for a term


@dataclass(frozen=True)
class Unchecked:
    """The reader could not find out, and says why. Every gate treats this as
    a failure: a check that could not run has not passed."""

    reason: str


class _Answer:
    def __init__(self, name: str):
        self.name = name

    def __repr__(self) -> str:
        return self.name


ABSENT = _Answer("ABSENT")
# For a removal: nothing local is left at the path; a local capability is still
# there; or the path names a capability inherited from an extended ledger, which
# no local removal can ever satisfy.
REMOVED = _Answer("REMOVED")
STILL_LOCAL = _Answer("STILL_LOCAL")
INHERITED = _Answer("INHERITED")

MISSING = "Missing"


class RecordsReader(Protocol):
    def capability(self, path: str) -> Present | _Answer | Unchecked: ...

    def removal(self, path: str) -> _Answer | Unchecked: ...

    def term(self, term: str) -> Present | _Answer | Unchecked: ...


# ---------------------------------------------------------------------------
# The declaration file

_KINDS = ("new", "changed", "removed")
_TAXONOMY = "taxonomy"


@dataclass(frozen=True)
class Declared:
    new: tuple[str, ...] = ()
    changed: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()
    term_new: tuple[str, ...] = ()
    term_changed: tuple[str, ...] = ()
    term_removed: tuple[str, ...] = ()

    def capabilities(self) -> Iterable[tuple[str, str]]:
        for kind in _KINDS:
            for path in getattr(self, kind):
                yield kind, path

    def terms(self) -> Iterable[tuple[str, str]]:
        for kind in _KINDS:
            for term in getattr(self, f"term_{kind}"):
                yield kind, term


def _names(raw: object, where: str) -> tuple[str, ...] | str:
    if not isinstance(raw, list) or not all(
            isinstance(v, str) and v.strip() for v in raw):
        return f"'{where}' must be a list of non-empty strings"
    return tuple(v.strip() for v in raw)


def parse_declarations(path: Path) -> Declared | str:
    """The declared changes, or a string saying what is wrong with the file.
    A missing file declares nothing."""
    if not path.exists():
        return Declared()
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
        return f"cannot be read: {error}"
    if raw is None:
        return Declared()
    if not isinstance(raw, dict):
        return "must be a mapping of new, changed, removed and taxonomy"
    unknown = sorted(map(str, set(raw) - {*_KINDS, _TAXONOMY}))
    if unknown:
        return (f"unknown key(s) {', '.join(unknown)}; expected "
                f"{', '.join(_KINDS)} or {_TAXONOMY}")
    fields: dict[str, tuple[str, ...]] = {}
    for kind in _KINDS:
        if kind in raw:
            names = _names(raw[kind], kind)
            if isinstance(names, str):
                return names
            fields[kind] = names
    if _TAXONOMY in raw:
        taxonomy = raw[_TAXONOMY]
        if not isinstance(taxonomy, dict):
            return f"'{_TAXONOMY}' must be a mapping of new, changed and removed"
        unknown = sorted(map(str, set(taxonomy) - set(_KINDS)))
        if unknown:
            return (f"unknown key(s) under {_TAXONOMY}: {', '.join(unknown)}; "
                    f"expected {', '.join(_KINDS)}")
        for kind in _KINDS:
            if kind in taxonomy:
                names = _names(taxonomy[kind], f"{_TAXONOMY}.{kind}")
                if isinstance(names, str):
                    return names
                fields[f"term_{kind}"] = names
    return Declared(**fields)


# ---------------------------------------------------------------------------
# The records gate


class _UncheckedProblem(str):
    """A problem line saying a check could not run, rather than that it failed."""


def _unchecked(label: str, answer: Unchecked) -> str:
    return _UncheckedProblem(f"{label}: could not be checked: {answer.reason}")


def _capability_problem(kind: str, path: str, reader: RecordsReader,
                        finished: bool) -> str | None:
    if kind == "removed":
        answer = reader.removal(path)
        if isinstance(answer, Unchecked):
            return _unchecked(path, answer)
        if answer is INHERITED:
            return (f"{path}: declared removed, but it is inherited from an "
                    f"extended ledger, and only a local capability can be removed")
        if answer is STILL_LOCAL and finished:
            return (f"{path}: declared removed but still in the ledger (delete "
                    f"it with `tcw capabilities rm`)")
        return None
    answer = reader.capability(path)
    if isinstance(answer, Unchecked):
        return _unchecked(path, answer)
    if not finished:
        return None
    if answer is ABSENT:
        return f"{path}: declared {kind} but not in the ledger"
    if kind == "new" and isinstance(answer, Present) and answer.status == MISSING:
        return (f"{path}: declared new but its status is still {MISSING}; set "
                f"the status it now has")
    return None


def _term_problem(kind: str, term: str, reader: RecordsReader,
                  finished: bool) -> str | None:
    answer = reader.term(term)
    if isinstance(answer, Unchecked):
        return _unchecked(f"term {term}", answer)
    if not finished:
        return None
    if kind == "removed" and isinstance(answer, Present):
        return f"term {term}: declared removed but still in the taxonomy"
    if kind != "removed" and answer is ABSENT:
        return f"term {term}: declared {kind} but not in the taxonomy"
    return None


def records_problems(layout: Layout, slug: Slug, reader: RecordsReader, *,
                     finished: bool) -> list[str]:
    """What is wrong with the item's declared record changes.

    With `finished=False` (mid-work, for `tcw validate`) only what is wrong at
    any point is reported: an unreadable or malformed file, an answer that
    could not be checked, and a removal no local change can satisfy. A change
    simply not made yet is not reported until `finished`.
    """
    path = layout.capabilities_file(slug)
    declared = parse_declarations(path)
    if isinstance(declared, str):
        return [f"{path.name}: {declared}"]
    problems = [p for kind, name in declared.capabilities()
                if (p := _capability_problem(kind, name, reader, finished))]
    problems += [p for kind, name in declared.terms()
                 if (p := _term_problem(kind, name, reader, finished))]
    return problems


def records_gate(layout: Layout, slug: Slug, reader: RecordsReader) -> list[str]:
    return records_problems(layout, slug, reader, finished=True)


# ---------------------------------------------------------------------------
# The completion gate


def completion_gate(layout: Layout, slug: Slug) -> list[str]:
    """Each enabled verdict stage the layout can read must currently be
    accepted. A stage the backend keeps (`layout.external`) records its
    verdict as the move itself, so there is nothing here to read."""
    problems = []
    for row in STAGES:
        if not row.verdict or row.name not in layout.enabled \
                or row.name in layout.external:
            continue
        state = layout.current_verdict(slug, row.name)
        if state != ACCEPTED:
            problems.append(
                f"{row.name}: the current verdict is {state}; it must be "
                f"{ACCEPTED} for the latest implementation (write "
                f"{layout.next_round(slug, row.name)})")
    return problems


# ---------------------------------------------------------------------------
# Drift

_PRESENT_KINDS = {"new", "changed"}


def drift_problems(layout: Layout, items: Iterable[Item],
                   reader: RecordsReader) -> list[str]:
    """Finished items' declarations checked against today's records.

    For each path or term the newest declaration wins (by the item's creation
    date), so a later item that declares it differently supersedes an earlier
    one. Two newest declarations that disagree are reported as ambiguous.
    """
    problems: list[str] = []
    # (what, name) -> [(created, kind, slug)]; `what` is capability or term
    seen: dict[tuple[str, str], list[tuple]] = defaultdict(list)
    for item in items:
        declared = parse_declarations(layout.capabilities_file(item.slug))
        if isinstance(declared, str):
            problems.append(f"{item.slug}: capabilities.yaml {declared}")
            continue
        for kind, name in declared.capabilities():
            seen[("capability", name)].append((item.created, kind, item.slug))
        for kind, name in declared.terms():
            seen[("term", name)].append((item.created, kind, item.slug))

    for (what, name), declarations in seen.items():
        newest = max(created for created, _, _ in declarations)
        latest = [(kind, slug) for created, kind, slug in declarations
                  if created == newest]
        kinds = {kind for kind, _ in latest}
        label = name if what == "capability" else f"term {name}"
        by = ", ".join(sorted(str(slug) for _, slug in latest))
        if "removed" in kinds and kinds & _PRESENT_KINDS:
            problems.append(f"{label}: ambiguous — items created the same day "
                            f"({by}) declare it both kept and removed")
            continue
        kind = "removed" if "removed" in kinds else (
            "new" if kinds == {"new"} else "changed")
        if what == "capability":
            problem = _capability_problem(kind, name, reader, finished=True)
        else:
            problem = _term_problem(kind, name, reader, finished=True)
        if problem is None:
            continue
        if isinstance(problem, _UncheckedProblem):
            problems.append(f"unchecked ({by}): {problem}")
        else:
            problems.append(f"drift ({by}): {problem}")
    return problems


# ---------------------------------------------------------------------------
# The filesystem reader, and the routing rule it shares with 2.x


class Route(NamedTuple):
    """Which ledger answers for a declared capability path, and the path
    within it. `owner` is the child project's id, or None for the item's own
    node."""
    owner: str | None
    store: FsCapabilitiesStore
    path: str


def route_capability_path(path: str, *, own: "FsCapabilitiesStore | None",
                          registry, node_id: str,
                          open_child) -> "Route | str":
    """Route one declared `capabilities.yaml` path to the ledger that answers
    for it, or return a problem line.

    The one place this rule lives. `own` is the item's node's ledger (None when
    the node keeps none); `open_child(project_id)` returns a child's ledger or
    the reason it has none. In order:

    1. A first segment naming a project `own` extends is today's inheritance
       reading, even when that project is also a declared child — every
       existing sidecar keeps its meaning.
    2. A first segment naming a declared child (reachable here or not) routes
       the rest of the path to that child's own ledger, read the way the child
       reads it — unless `own` already shows capabilities under that same
       namespace, which is refused as ambiguous rather than guessed at.
    3. Anything else is the node's own path; with no ledger of its own, nothing
       can check it.

    Uses only the registry's declared children and the stores it is handed, so
    a non-filesystem store could answer every question it asks."""
    head, _, rest = path.partition("/")
    if own is not None and head in own.extends:
        return Route(None, own, path)
    child_ids = registry.declared_child_ids()
    if head in child_ids:
        if not rest:
            return f"{path}: names project '{head}' but no capability"
        if own is not None:
            # Judged over the node's resolved view — its own capabilities and
            # the inherited ones `get` falls through to — so a `kid/...` path
            # that resolved through inheritance before `kid` was declared a
            # child is refused, not quietly sent to the child's ledger.
            clash = [c.path for c in own.list_all(namespace=head)]
            if clash:
                more = ", …" if len(clash) > 1 else ""
                return (f"{path}: ambiguous — '{head}' is both a child project of "
                        f"this node and a namespace in this node's capabilities "
                        f"ledger ({clash[0]}{more}); rename one of them, or "
                        f"complete with --force")
        store = open_child(head)
        if isinstance(store, str):
            return f"{path}: {store}"
        return Route(head, store, rest)
    if own is not None:
        return Route(None, own, path)
    qualifiers = ", ".join(child_ids) or "it declares no child projects"
    return (f"{path}: this node ('{node_id}') keeps no capabilities ledger; "
            f"qualify the path with a child project id ({qualifiers})")


_READ_ERRORS = (RefError, ValueError, yaml.YAMLError)


class _LedgerReader:
    def __init__(self, own, registry, project_id, open_child, taxonomy):
        self.own = own
        self.registry = registry
        self.project_id = project_id
        self.open_child = open_child
        self.taxonomy = taxonomy

    def _route(self, path: str) -> Route | Unchecked:
        try:
            route = route_capability_path(path, own=self.own,
                                          registry=self.registry,
                                          node_id=self.project_id,
                                          open_child=self.open_child)
        except _READ_ERRORS as error:
            return Unchecked(str(error))
        return Unchecked(route) if isinstance(route, str) else route

    def capability(self, path: str):
        route = self._route(path)
        if isinstance(route, Unchecked):
            return route
        try:
            found = route.store.get(route.path)
        except _READ_ERRORS as error:
            return Unchecked(str(error))
        return ABSENT if found is None else Present(found.status)

    def removal(self, path: str):
        # After a local capability is removed its path may fall through to an
        # inherited one, and that still counts as removed: only a local hit is
        # STILL_LOCAL. A path qualified by an extended ledger can never be
        # removed locally at all.
        route = self._route(path)
        if isinstance(route, Unchecked):
            return route
        try:
            if route.path.partition("/")[0] in route.store.extends:
                return INHERITED
            local = route.store.get_local(route.path)
        except _READ_ERRORS as error:
            return Unchecked(str(error))
        return REMOVED if local is None else STILL_LOCAL

    def term(self, term: str):
        if self.taxonomy is None:
            return Unchecked(f"project '{self.project_id}' keeps no taxonomy")
        try:
            found = self.taxonomy.get(term)
        except _READ_ERRORS as error:
            return Unchecked(str(error))
        return ABSENT if found is None else Present()


def ledger_reader(own: FsCapabilitiesStore | None, registry, project_id: str,
                  open_child: Callable[[str], "FsCapabilitiesStore | str"],
                  taxonomy) -> RecordsReader:
    """The production `RecordsReader` over this project's capabilities ledger
    (`own`, None when it keeps none), its child projects' ledgers
    (`open_child`) and its taxonomy store (None when it keeps none)."""
    return _LedgerReader(own, registry, project_id, open_child, taxonomy)
