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

from tcw.errors import InheritedUnavailable, ProjectGraphError, Unreachable
from tcw.ids import FullId, IdError, parse_stored
from tcw.locate import FOUND, MISSING as MISSING_OBJECT, UNRESOLVED
from tcw.store.base import RefError
from tcw.store.fs import FsCapabilitiesStore, FsTaxonomyStore
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


@dataclass(frozen=True)
class Invalid:
    """The entry itself is wrong, and says why: a TCW 3.x or malformed entry,
    or a project ID TCW cannot locate (TCW-110 Design 6.1). Reported at any
    point, not only once the work is finished."""

    reason: str


class _Answer:
    def __init__(self, name: str):
        self.name = name

    def __repr__(self) -> str:
        return self.name


ABSENT = _Answer("ABSENT")
# For a removal: the owner has no object of its own left at the path, or it
# still has one (TCW-112 Design 7.1). A full identifier never names an
# inherited copy, so there is no third answer.
REMOVED = _Answer("REMOVED")
STILL_LOCAL = _Answer("STILL_LOCAL")

MISSING = "Missing"


class RecordsReader(Protocol):
    def capability(self, path: str) -> Present | _Answer | Unchecked | Invalid: ...

    def removal(self, path: str) -> _Answer | Unchecked | Invalid: ...

    def term(self, term: str) -> Present | _Answer | Unchecked | Invalid: ...


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
        if isinstance(answer, Invalid):
            return f"{path}: {answer.reason}"
        if isinstance(answer, Unchecked):
            return _unchecked(path, answer)
        if answer is STILL_LOCAL and finished:
            return (f"{path}: declared removed but still in the ledger (delete "
                    f"it with `tcw capabilities rm`)")
        return None
    answer = reader.capability(path)
    if isinstance(answer, Invalid):
        return f"{path}: {answer.reason}"
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
    if isinstance(answer, Invalid):
        return f"term {term}: {answer.reason}"
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


class DriftProblem(NamedTuple):
    """One drift finding: `kind` is `drift`, `ambiguous` or `unchecked`;
    `where` the capability path, `term <name>`, or an item's slug; its `str()`
    is the line `tcw capabilities drift` prints (TCW-73 Design 7.3)."""
    kind: str
    where: str
    message: str

    def __str__(self) -> str:
        return f"{self.kind}: {self.where}: {self.message}"


def drift_problems(layout: Layout, items: Iterable[Item],
                   reader: RecordsReader) -> list[DriftProblem]:
    """Finished items' declarations checked against today's records.

    For each path or term the newest declaration wins (by the item's creation
    date), so a later item that declares it differently supersedes an earlier
    one. Two newest declarations that disagree are reported as ambiguous.
    """
    problems: list[DriftProblem] = []
    # (what, name) -> [(created, kind, slug)]; `what` is capability or term
    seen: dict[tuple[str, str], list[tuple]] = defaultdict(list)
    for item in items:
        declared = parse_declarations(layout.capabilities_file(item.slug))
        if isinstance(declared, str):
            problems.append(DriftProblem("unchecked", str(item.slug),
                                         f"capabilities.yaml {declared}"))
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
        by = ", ".join(sorted({str(slug) for _, slug in latest}))
        if "removed" in kinds and kinds & _PRESENT_KINDS:
            who = (f"items created the same day ({by}) declare"
                   if len({slug for _, slug in latest}) > 1 else f"{by} declares")
            problems.append(DriftProblem("ambiguous", label,
                                         f"{who} it both kept and removed"))
            continue
        # A `new` among the newest declarations keeps the Missing check.
        kind = "removed" if "removed" in kinds else (
            "new" if "new" in kinds else "changed")
        if what == "capability":
            problem = _capability_problem(kind, name, reader, finished=True)
        else:
            problem = _term_problem(kind, name, reader, finished=True)
        if problem is None:
            continue
        # Each problem text starts with its label, which is `where` here.
        message = problem[len(label) + 2:] if problem.startswith(f"{label}: ") else problem
        problems.append(DriftProblem(
            "unchecked" if isinstance(problem, _UncheckedProblem) else "drift",
            label, f"{message} (declared by {by})"))
    return problems


# ---------------------------------------------------------------------------
# The filesystem reader, and the routing rule it shares with 2.x


class Route(NamedTuple):
    """Which ledger answers for a declared capability: its owner's."""
    full_id: FullId
    store: FsCapabilitiesStore


def route_capability_path(path: str, *, own: "FsCapabilitiesStore | None",
                          project_id: str, locator, project_root: Path
                          ) -> "Route | Unchecked | Invalid":
    """Route one declared `capabilities.yaml` entry to the ledger that answers
    for it, or say why none can (TCW-110 Design 6.2).

    The one place this rule lives. The entry is a full identifier, and its
    project is the ledger's (TCW-112 Design 7.1): `own` (the item's project's
    ledger, None when it keeps none) for the item's own project; any other
    project's own ledger, found through the command's `locator`, whether or
    not the item's project inherits from it. A 3.x or malformed entry, and a
    project TCW cannot locate, are `Invalid`; a project not on this machine,
    or one that keeps no ledger, `Unchecked`.

    Uses only the locator and the stores it is handed, so a non-filesystem
    store could answer every question it asks."""
    try:
        full_id = parse_stored(path, "capabilities")
    except IdError as error:
        return Invalid(str(error))
    if full_id.project == project_id:
        if own is None:
            return Unchecked(f"this project ('{project_id}') keeps no capabilities "
                             f"ledger; name the ledger's project in the entry "
                             f"(<project>.capabilities/{full_id.id_path})")
        return Route(full_id, own)
    try:
        store = locator.owner_store(full_id.project, "capabilities", project_root)
    except Unreachable as error:
        return Unchecked(str(error))
    except ProjectGraphError as error:
        return Invalid(str(error))
    except _READ_ERRORS as error:
        return Unchecked(str(error))
    if not store.root.is_dir():
        return Unchecked(f"project '{full_id.project}' keeps no capabilities ledger")
    return Route(full_id, store)


# An entry whose owner's view cannot be built here is unchecked, like one
# that cannot be read (TCW-112 Design 7.1).
_READ_ERRORS = (RefError, ValueError, yaml.YAMLError, InheritedUnavailable)


class _LedgerReader:
    def __init__(self, own, project_id, locator, project_root, taxonomy):
        self.own = own
        self.project_id = project_id
        self.locator = locator
        self.project_root = project_root
        self.taxonomy = taxonomy

    def _route(self, path: str) -> "Route | Unchecked | Invalid":
        try:
            return route_capability_path(path, own=self.own, project_id=self.project_id,
                                         locator=self.locator,
                                         project_root=self.project_root)
        except _READ_ERRORS as error:
            return Unchecked(str(error))

    def capability(self, path: str):
        route = self._route(path)
        if not isinstance(route, Route):
            return route
        full_id = route.full_id
        try:
            # The owner's own object, as its owner sees it, with its combined
            # Status; ABSENT when the owner has none of its own there, even
            # where it inherits one (TCW-112 Design 7.1).
            found = route.store.get_local(full_id.id_path)
        except _READ_ERRORS as error:
            return Unchecked(str(error))
        return ABSENT if found is None else Present(found.status)

    def removal(self, path: str):
        # After a capability is removed its path may still show an inherited
        # one, and that counts as removed: only the owner's own object left
        # there is STILL_LOCAL. Existence alone, so no view is needed.
        route = self._route(path)
        if not isinstance(route, Route):
            return route
        try:
            own = route.store.has_own(route.full_id.id_path)
        except _READ_ERRORS as error:
            return Unchecked(str(error))
        return STILL_LOCAL if own else REMOVED

    def term(self, term: str):
        try:
            full_id = parse_stored(term, "taxonomy")
        except IdError as error:
            return Invalid(str(error))
        if full_id.project == self.project_id and self.taxonomy is None:
            return Unchecked(f"project '{self.project_id}' keeps no taxonomy")
        try:
            found = self.locator.exists(full_id, named_by=self.project_root)
        except _READ_ERRORS as error:
            return Unchecked(str(error))
        if found.kind == FOUND:
            return Present()
        if found.kind == MISSING_OBJECT:
            return ABSENT
        return Unchecked(found.message) if found.kind == UNRESOLVED \
            else Invalid(found.message)


def ledger_reader(own: FsCapabilitiesStore | None, project_id: str, locator,
                  project_root: Path, taxonomy) -> RecordsReader:
    """The production `RecordsReader` over this project's capabilities ledger
    (`own`, None when it keeps none) and taxonomy store (None when it keeps
    none), and every other project's ledger and taxonomy, found through the
    command's `locator`."""
    return _LedgerReader(own, project_id, locator, Path(project_root), taxonomy)


def _open_or_reason(store_cls, root: Path):
    """A project's store: `(store, None)`, `(None, None)` when it keeps none,
    or `(None, reason)` when it cannot be opened."""
    try:
        store = store_cls.open(root)
    except (ValueError, yaml.YAMLError) as error:
        return None, str(error)
    return (store, None) if store.root.is_dir() else (None, None)


def project_reader(project_root: Path, registry) -> RecordsReader:
    """`ledger_reader` for the project at `project_root`: its own capabilities
    ledger and taxonomy, and other projects' found through the command's one
    `Locator`. A store that cannot be opened turns every question routed to
    it into an `Unchecked` answer naming why, never an exception."""
    from tcw.locate import Locator
    own, _ = _open_or_reason(FsCapabilitiesStore, Path(project_root))
    taxonomy, _ = _open_or_reason(FsTaxonomyStore, Path(project_root))
    return ledger_reader(own, registry.current.id, Locator.of(Path(project_root)),
                         Path(project_root), taxonomy)
