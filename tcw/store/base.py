"""Abstract store interfaces — the portable spine the CLI depends on.

Per `docs/lifecycle/abstraction.md` (the litmus test) the model is storage-abstracted: a tree of
named entries with cross-links is implementable by any backend. The filesystem
adapters in `fs.py` are the only store adapters for taxonomy and capabilities.
The work axis has its own interface, `tcw.work.backend.WorkBackend`, with a
filesystem backend and a Jira backend.
"""

# Defer annotation evaluation (PEP 563): the store interfaces use forward refs
# (`"TermDetail" | None`) and self-referential dataclass fields that only resolve
# lazily. Without this, importing on Python 3.11–3.13 raises at class-definition
# time. Python 3.14 defers natively (PEP 649); this keeps <3.14 working too.
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any

from tcw.errors import NotFound, UsageError
from tcw.findings import Finding
from tcw.ids import FullId
from tcw.project_files import follows_naming_rule


class RefError(NotFound):
    """A reference could not be resolved cleanly."""


class AmbiguousRef(UsageError, RefError):
    """A bare reference matches more than one namespace — author must qualify.

    Carries its own message: callers print `str(e)`, and the bare ref alone
    ("x/thing") reads as noise rather than an explanation.
    """

    def __init__(self, ref: str, namespace: str):
        self.ref = ref
        super().__init__(f"ambiguous ref '{ref}': more than one project this one "
                         f"inherits from holds it; name it by its full identifier, "
                         f"<project>.{namespace}/{ref}")


class StaleRevision(Exception):
    """A write was rejected because the provided revision token no longer matches.

    The editable resource was modified (by another editor or CLI) since the caller
    last read it. The caller should re-read the current version and re-apply edits.
    """


class StoreLocationUnusable(ValueError):
    """A candidate location does not hold a usable store — it is absent, it is
    not a directory, or it lacks the component's layout.

    The distinction the resolution ladder needs, and could not make before it
    existed. Rules 1 and 2 try a location and fall through when it does not work
    out, which is right for "there is no store there" and wrong for every other
    reason a store fails to open: a federation error in a project that also declares
    a repository was reported as "not provisioned; run `tcw provision`", which
    then succeeded and left the store just as unopenable, because the real error
    had been swallowed two rules earlier.

    Storage-neutral: "the place I was told to look does not hold one of these"
    is a question any adapter answers — a missing table, a project id the tracker
    does not have — and it is categorically different from "the thing I found
    there is misconfigured".

    A `ValueError` for the same reason as its siblings: every existing
    `except ValueError` around a store `open()` keeps working unchanged.
    """


class StoreDeclarationError(ValueError):
    """A store's configured location is *wrong* — the configuration itself is
    the problem, and the message names the line to fix.

    Originally scoped to a wrongly declared home repository, and widened to what
    it always meant: any configured location the adapter can see is there and
    cannot use. A `work.path` naming a complete store outside any repository is
    the same kind of fact as a `repository` block missing its url — present, and
    unusable as written — and it must reach the reader for the same reason.

    A sibling of `StoreNotProvisioned`, and a `ValueError` for the same reason:
    every existing `except ValueError` around a store keeps working, including
    `_has_work_store`, which must answer False for a misconfigured *other* project
    rather than failing a whole topology listing.

    It exists because `find_component_project` cannot otherwise tell "this config is wrong"
    from "this is not a project", and flattening the first to the second is what
    answered a typo'd `repository` block with "run `tcw init`" — the one command
    that would scaffold a second, empty store beside the real one.
    """


class StoreNotProvisioned(ValueError):
    """A store is *declared* but not available here — nothing is wrong with the
    configuration, the store simply has not been obtained on this machine yet.

    A `ValueError` on purpose. Every existing `except ValueError` around a store
    `open()` keeps working unchanged, so this cannot silently break a caller; the
    sites that should now say more are the ones updated deliberately. What
    separates it from a misconfiguration is that it is *actionable* — the message
    carries what to run — and `str(e)` is the whole of it, so callers print it
    rather than composing their own.

    Not filesystem-specific: "declared but not available here" is a state a
    tracker-backed adapter reaches too, when credentials are absent or the
    service is unreachable.
    """


@dataclass(frozen=True)
class Project:
    """A registered TCW project.

    ``locator`` is deliberately opaque: filesystem adapters use a path while a
    remote adapter may use a tracker key, URL, or database handle.
    """

    id: str
    locator: Any


#: What a parent link can pass down (TCW-108 Design 1.2), in the order every
#: list of them is printed.
AXES = ("taxonomy", "capabilities", "config")


@dataclass(frozen=True)
class ParentLink:
    """One entry of a project's `parents:`: the parent's ID, and the axes the
    link passes down (a subset of `AXES`; all three for `inherit: all`)."""

    id: str
    inherit: frozenset = frozenset(AXES)


@dataclass(frozen=True)
class LoadOrder:
    """A project's load order (TCW-108 Design 4): the project and every
    ancestor, farthest first and the project itself last. `missing` holds the
    IDs in `ids` that are not on this machine and `unreadable` those whose own
    parent links could not be read; each is placed as a project with no
    parents (Design 6.4). `warning` is Design 4.5's text when C3 found no
    order and the depth-first order is used instead."""

    ids: tuple
    missing: tuple = ()
    unreadable: tuple = ()
    warning: str | None = None

    @property
    def complete(self) -> bool:
        return not self.missing and not self.unreadable


@dataclass(frozen=True)
class SourceEntry:
    """One project of a project's sources for an axis (TCW-109 Design 1.3):
    its ID, its `Project` when it is on this machine, and its state, `here`,
    `missing` (not on this machine) or `unreadable` (its own parent links, or
    its whole shared file, could not be read)."""

    id: str
    project: Project | None
    state: str


def _parents_of(project_id: str, links, absent: "set[str]") -> list[str]:
    if project_id in absent:
        return []
    return [link.id for link in links.get(project_id, ())]


def find_loop(links, read_order) -> list[str] | None:
    """A loop through the parent links, as Design 4.7 prints it: the list
    starts and ends with the loop's member that comes first in `read_order`,
    each next one a parent of the one before, parents tried in listing
    order. None when there is no loop."""
    order = [*read_order, *(pid for pid in links if pid not in read_order)]
    for start in order:
        path = _path_back(start, links)
        if path is not None:
            return path
    return None


def _path_back(start: str, links) -> list[str] | None:
    """The first path, depth-first in listing order, from `start` up its
    parent links back to `start`."""
    path = [start]
    visited: set[str] = set()

    def climb(pid: str) -> bool:
        for parent in _parents_of(pid, links, set()):
            if parent == start:
                path.append(start)
                return True
            if parent in visited:
                continue
            visited.add(parent)
            path.append(parent)
            if climb(parent):
                return True
            path.pop()
        return False

    return path if climb(start) else None


def loop_message(loop: list[str]) -> str:
    return "loop in parents: " + " -> ".join(loop)


def load_order_of(project_id: str, links, *, missing=frozenset(),
                  unreadable=frozenset()) -> LoadOrder:
    """`project_id`'s load order from its parent links (Design 4): C3 over
    the parent lists reversed, so that the last listed parent wins (4.1);
    when any merge made on the way fails, the depth-first order instead (4.4),
    with the warning of 4.5 naming the first merge to fail. A project in
    `missing` or `unreadable` is placed as one with no parents (6.4), and one
    `links` does not hold has none either.

    Store-neutral: given each project's links and which projects are not
    available, any registry can call it. Raises `ValueError` on a loop, which
    the caller reports with `find_loop` (Design 4.7)."""
    absent = set(missing) | set(unreadable)
    resolved: dict[str, list[str]] = {}
    in_progress: set[str] = set()
    failure: list[tuple[str, list[str]]] = []

    def resolve(pid: str) -> list[str] | None:
        """R(pid), the order with the winner first; None once a merge has
        failed. Each project's merge after all of its parents', the parents
        taken in listing order (Design 4.5)."""
        if pid in resolved:
            return resolved[pid]
        if pid in in_progress:
            raise ValueError(f"loop in parents through '{pid}'")
        in_progress.add(pid)
        parents = _parents_of(pid, links, absent)
        for parent in parents:
            if resolve(parent) is None:
                return None
        merged = _merge([list(resolved[p]) for p in reversed(parents)]
                        + [list(reversed(parents))])
        in_progress.discard(pid)
        if isinstance(merged, tuple):
            failure.append((pid, merged[1]))
            return None
        resolved[pid] = [pid, *merged]
        return resolved[pid]

    found = resolve(project_id)
    warning = None
    if found is None:
        where, heads = failure[0]
        ids = _depth_first(project_id, links, absent)
        named = ", ".join(f"'{head}'" for head in heads)
        warning = (f"load order: no order keeps every project's own order of parents "
                   f"(at '{where}': {named} cannot be placed); using depth-first order "
                   f"{', '.join(ids)}; to choose a value yourself, set it in "
                   f"'{project_id}'")
    else:
        ids = tuple(reversed(found))
    return LoadOrder(ids=ids,
                     missing=tuple(pid for pid in ids if pid in missing),
                     unreadable=tuple(pid for pid in ids if pid in unreadable),
                     warning=warning)


def _merge(lists: list[list[str]]):
    """C3's merge of `lists`: the merged list, or `(None, heads)` when no
    list's first project can be taken, `heads` being the distinct first
    projects left, in the order of the lists."""
    result: list[str] = []
    while any(lists):
        for candidate in (lst[0] for lst in lists if lst):
            if not any(candidate in lst[1:] for lst in lists):
                break
        else:
            heads: list[str] = []
            for lst in lists:
                if lst and lst[0] not in heads:
                    heads.append(lst[0])
            return None, heads
        result.append(candidate)
        lists = [[pid for pid in lst if pid != candidate] for lst in lists]
    return result


def _depth_first(project_id: str, links, absent: "set[str]") -> tuple[str, ...]:
    """Design 4.4: each parent in listing order, its own ancestors placed
    first, skipping a project already placed; the project last."""
    placed: list[str] = []

    def place(pid: str, depth: int) -> None:
        if depth > len(links) + 1:
            raise ValueError(f"loop in parents through '{pid}'")
        for parent in _parents_of(pid, links, absent):
            if parent not in placed:
                place(parent, depth + 1)
        if pid not in placed:
            placed.append(pid)

    place(project_id, 0)
    return tuple(placed)


def passing(axis: str, project_id: str, links, *, absent=frozenset()) -> set[str]:
    """The projects that pass `axis` to `project_id` (Design 5.1): the
    project itself, and every project some chain of parent links from it
    reaches with `axis` in the `inherit` of every link. Nothing is passed
    through a project in `absent`, whose own links are unknown."""
    found = {project_id}
    frontier = [project_id]
    while frontier:
        pid = frontier.pop()
        if pid in absent:
            continue
        for link in links.get(pid, ()):
            if axis in link.inherit and link.id not in found:
                found.add(link.id)
                frontier.append(link.id)
    return found


# ── Combining an object over its sources (TCW-112 Design 2) ─────────────────


@dataclass(frozen=True)
class Declaration:
    """One project's own declaration of an object at one id-path (TCW-112
    Design 2.2, 2.3): its fields, and its description, a text (possibly
    empty) or None when it declares none. A store keeps "declared empty"
    and "not declared" apart, because completeness tells them apart."""

    fields: dict
    description: str | None = None


@dataclass(frozen=True)
class Unused:
    """A declarer whose object the active project does not use (Design 2.5):
    `winner` is the chain member that took its place, and `warned` whether
    the clash is still warned about."""

    project: str
    winner: str
    warned: bool


@dataclass(frozen=True)
class Combined:
    """The object at one id-path as one project sees it (Design 2.1-2.5).

    `chain` holds the project IDs whose declarations make it, nearest first,
    so `chain[0]` owns it and `chain[1]`, when there is one, is the object it
    overrides. `declared_by` names, for each key in `fields` and for
    `description`, the project whose declaration supplied it, so a store can
    read what that key names (attached documents) from that project.
    `unreadable` is a chain member whose declaration could not be read, in
    which case nothing was combined."""

    chain: tuple
    fields: dict
    description: str | None = None
    declared_by: dict = field(default_factory=dict)
    unused: tuple = ()
    unreadable: str | None = None

    @property
    def owner(self) -> str:
        return self.chain[0]

    @property
    def overrides(self) -> str | None:
        return self.chain[1] if len(self.chain) > 1 else None


#: The keys of a state file that belong to the file, never combined.
_FILE_KEYS = frozenset({"tcw-version", "id"})


def missing_parts(declaration: Declaration, axis: str) -> list[str]:
    """What a declaration lacks to be complete on its own (Design 6.1):
    a `name`, for a capability a `Status`, and a declared description,
    possibly empty. Empty when it is complete."""
    missing = [key for key in ("name", *(("Status",) if axis == "capabilities" else ()))
               if declaration.fields.get(key) is None]
    if declaration.description is None:
        missing.append("description")
    return missing


def combine(declarers, passes, *, axis: str, unreadable=frozenset()) -> Combined | None:
    """The object at one id-path in the active project's view (Design 2.1-2.5).

    `declarers` is `(project ID, Declaration)` for every source of the
    active project that has an object of its own at the id-path, in the
    active project's load order; `passes(a, b)` says whether project `a`
    passes the axis to project `b`. `unreadable` holds declarers whose
    declaration could not be read: the chain is still found, since only who
    declares is needed for it. None when nothing declares the path.

    Reads no file and knows no folder, so every kind of store combines by
    this one rule (Design 2.6)."""
    declarers = list(declarers)
    if not declarers:
        return None
    order = [pid for pid, _ in declarers]
    position = {pid: i for i, pid in enumerate(order)}
    declared = dict(declarers)
    chain = [order[-1]]
    while True:
        current = chain[-1]
        nearer = next((pid for pid in reversed(order[:position[current]])
                       if passes(pid, current)), None)
        if nearer is None:
            break
        chain.append(nearer)
    in_chain = set(chain)
    unused = []
    for pid in order:
        if pid in in_chain:
            continue
        winner = min((m for m in chain if position[m] > position[pid]),
                     key=position.__getitem__)
        decided = any(position[m] > position[winner] and passes(pid, m)
                      and m not in unreadable and not missing_parts(declared[m], axis)
                      for m in chain)
        unused.append(Unused(pid, winner, not decided))
    blocked = next((pid for pid in chain if pid in unreadable), None)
    if blocked is not None:
        return Combined(tuple(chain), {}, None, {}, tuple(unused), blocked)
    fields: dict = {}
    declared_by: dict = {}
    for pid in reversed(chain):
        for key, value in declared[pid].fields.items():
            if key in _FILE_KEYS:
                continue
            if value is None:
                fields.pop(key, None)
                declared_by.pop(key, None)
            else:
                fields[key] = value
                declared_by[key] = pid
    description = None
    for pid in chain:
        text = declared[pid].description
        if text is not None and text.strip():
            description = text
            declared_by["description"] = pid
            break
    return Combined(tuple(chain), fields, description, declared_by, tuple(unused))


_COMPLETE = {"capabilities": "a name, a Status and a description",
             "taxonomy": "a name and a description"}


def clash_warning(axis: str, id_path: str, unused: str, winner: str, project: str) -> str:
    """Design 2.5's warning for an unused declarer."""
    return (f"{axis} {id_path}: '{unused}' and '{winner}' each have an object at this "
            f"path, and neither inherits it from the other; '{project}' uses the one "
            f"from '{winner}', which comes later in its load order, and nothing from "
            f"'{unused}''s; to choose for yourself, give '{project}' a complete object "
            f"of its own at {id_path} ({_COMPLETE[axis]}), holding every field you want")


@dataclass(frozen=True)
class UnreachableProject:
    """A connected project that is declared here but not available here.

    **Not a configuration error.** The declaration is well formed and names a
    project this store simply cannot reach from this machine — a repository that
    was never cloned, a tracker project the caller has no access to. Telling that
    apart from a malformed declaration is the whole reason this type exists:
    fail-closed is right for a declaration that is wrong, and wrong for one that
    is merely unanswerable here.

    ``locator`` is opaque exactly as ``Project.locator`` is, and ``declared_in``
    names the configuration that carried the declaration. Both are presentation
    only — nothing above the adapter may parse them.
    """

    id: str
    locator: Any
    declared_in: Any = ""
    # The rendered "not on this machine" message (TCW-107 Design 6.2), the
    # manifest holding the entry that decided where the project is (None when
    # no entry decided), and the repository that entry gives. Presentation
    # only, like `declared_in`. `remedy` is the message's part after its first
    # colon, kept on its own so a message quoting it (TCW-108 Design 6.2)
    # never parses `message`.
    message: str = ""
    decided_by: Any = None
    repository: str | None = None
    remedy: str = ""


@dataclass(frozen=True)
class ProjectOverride:
    """A locator the caller supplied, standing in place of the declared one.

    **Not a defect and not a declaration.** It is a third thing: a statement
    made by the machine running the command, about where a project sits *here*,
    that no file another machine reads can carry. The declared locator is a fact
    about one machine written into a file every machine shares, which is exactly
    the case it cannot express.

    ``source`` names whatever supplied the value — an environment variable, for
    the filesystem adapter — so a message can say where to go and change it.
    ``locator`` is opaque exactly as ``Project.locator`` is: a path here, a
    tracker key elsewhere, and nothing above the adapter may parse either.

    Reported rather than silent, always. An override that resolves a graph
    nobody else can resolve is the inverse of works-on-my-machine, and the only
    thing standing between it and a debugging trap is that every command that
    reports graph state says which overrides are in effect.

    ``problem`` is ``None`` when the override did what it said — the project it
    names is in the graph, under the right id, where it pointed. Anything else
    fills it in: the location is not a project at all, or is a different one.
    Carried on the record rather than in a second structure beside it, because
    the two failures are discovered at different moments — one when the override
    is resolved, one only after the target's configuration is read — and a caller
    that has to consult two places to learn "did this work" will consult one.
    """

    id: str
    source: str
    locator: Any
    problem: str | None = None
    # It worked, and still may not be what was meant: set when the project it
    # delivered disagrees with where the rest of the graph was read from. Never
    # a problem, and never fatal — the override is followed as stated.
    warning: str | None = None


class ProjectRegistry(ABC):
    """Storage-neutral connected-project graph."""

    @property
    @abstractmethod
    def current(self) -> Project:
        """The project from which this registry was opened."""

    @abstractmethod
    def parents(self, project_id: str | None = None) -> list[ParentLink]:
        """The project's declared parent links, in listing order, whether or
        not each parent is on this machine (TCW-108 Design 1, 3.2). Empty for
        a project with none, for one whose own links could not be read, and
        for one not on this machine."""

    def link_state(self, project_id: str) -> str:
        """`here`, `missing` (not on this machine) or `unreadable` (on this
        machine, its own parent links could not be read, Design 6.6). The
        default is right for a store with no unreadable state."""
        return "here" if self.get(project_id) is not None else "missing"

    def load_order(self, project_id: str | None = None, *,
                   root: Any = None) -> LoadOrder:
        """The project's load order (Design 4), computed from the declared
        links alone by `load_order_of`, so every store orders a family the
        same way. Raises `ProjectGraphError` on a loop (Design 4.7). `root`
        is where the caller holds a project outside the family, for a store
        that finds projects by folder; this default does not need it."""
        from tcw.errors import ProjectGraphError
        start = project_id or self.current.id
        links: dict[str, list[ParentLink]] = {}
        missing: set[str] = set()
        unreadable: set[str] = set()
        pending = [start]
        while pending:
            pid = pending.pop()
            if pid in links or pid in missing or pid in unreadable:
                continue
            state = self.link_state(pid)
            if state == "missing":
                missing.add(pid)
            elif state == "unreadable":
                unreadable.add(pid)
            else:
                links[pid] = self.parents(pid)
                pending.extend(link.id for link in reversed(links[pid]))
        try:
            return load_order_of(start, links, missing=missing, unreadable=unreadable)
        except ValueError:
            raise ProjectGraphError(loop_message(find_loop(links, [start]))) from None

    def sources(self, axis: str, project_id: str | None = None) -> list[Project]:
        """The projects whose `axis` reaches the project (Design 5.2): its load
        order keeping only those that pass `axis` to it (Design 5.1), in the
        same order, ending with the project itself.

        Raises `InheritedUnavailable` (Design 6.2) for the first project in
        the load order that would pass `axis` and is not on this machine, or
        whose own parent links could not be read, since what reaches the
        project is then unknown. A project that passes nothing for `axis`
        never stops it, whatever its state."""
        entries = self.source_entries(axis, project_id)
        for entry in entries:
            if entry.state != "here":
                raise self.unavailable(entries[-1].id, entry.id, axis)
        return [entry.project for entry in entries]

    def source_entries(self, axis: str, project_id: str | None = None, *,
                       root: Any = None) -> list[SourceEntry]:
        """`sources` without raising (TCW-109 Design 1.3): every project of
        the load order that passes `axis`, in order and ending with the
        project, each with its state, so a caller that needs to know what a
        gap could have set can carry on past it."""
        order = (self.load_order(project_id) if root is None
                 else self.load_order(project_id, root=root))
        passes = self.passing_in(order, axis)
        entries: list[SourceEntry] = []
        for pid in order.ids:
            if pid not in passes:
                continue
            if pid in order.missing:
                entries.append(SourceEntry(pid, None, "missing"))
            elif pid in order.unreadable:
                entries.append(SourceEntry(pid, None, "unreadable"))
            else:
                entries.append(SourceEntry(pid, self.order_project(pid), "here"))
        return entries

    def passing_in(self, order: LoadOrder, axis: str) -> set[str]:
        """The IDs of `order` that pass `axis` to its project (Design 5.1),
        nothing being passed through a project missing or unreadable."""
        absent = frozenset({*order.missing, *order.unreadable})
        links = {pid: self.parents(pid) for pid in order.ids if pid not in absent}
        return passing(axis, order.ids[-1], links, absent=absent)

    def inherited_unavailable(self, order: LoadOrder, axis: str, project_id: str):
        """Design 6.2's error for `project_id`, missing or unreadable, which
        would pass `axis` to the project of `order`."""
        return self.unavailable(order.ids[-1], project_id, axis,
                                missing=project_id in order.missing)

    def unavailable(self, project_id: str, gap_id: str, axis: str, *,
                    subject: str | None = None, missing: bool | None = None,
                    store_message: str | None = None):
        """Design 6.2's error: `gap_id`, missing or unreadable, would pass
        `axis` to `project_id`. The one place its messages are built.
        `subject` stands for the axis in the message (TCW-109 passes
        `configuration (work.tags)`); `missing` says which of the two it is
        when the caller knows, else `link_state` does. `store_message`, when
        given, is the third case (TCW-112 Design 1.3): `gap_id` is here and
        readable, but its store for `axis` cannot be opened, and this is
        that store's own message."""
        from tcw.errors import InheritedUnavailable
        words = subject or axis
        if store_message is not None:
            return InheritedUnavailable(
                f"'{project_id}' inherits its {words} from project '{gap_id}', whose "
                f"{words} store cannot be read here: {store_message}",
                project=gap_id, axis=axis, reason="store", detail=store_message)
        if missing is None:
            missing = self.link_state(gap_id) == "missing"
        if missing:
            return InheritedUnavailable(
                f"'{project_id}' inherits its {words} from project '{gap_id}', which "
                f"is not on this machine: {self.absent_note(gap_id)}",
                project=gap_id, axis=axis, reason="missing")
        return InheritedUnavailable(
            f"'{project_id}' inherits its {words} through project '{gap_id}', whose "
            f"parents could not be read: {self.link_problem(gap_id)}",
            project=gap_id, axis=axis, reason="unreadable")

    def order_project(self, project_id: str) -> Project:
        """The `Project` for an ID of a load order that is available here. A
        store whose load orders reach projects outside the family overrides
        this; the default answers for the family."""
        project = self.get(project_id)
        if project is None:
            raise KeyError(project_id)
        return project

    def absent_note(self, project_id: str) -> str:
        """What to do about a project not on this machine, for Design 6.2's
        first message, after its colon."""
        return f"project '{project_id}' is not available here"

    def link_problem(self, project_id: str) -> str | None:
        """The problem that left a project's own parent links unknown (Design
        6.6), naming its file and key, or None."""
        return None

    def declared_child_ids(self, project_id: str | None = None) -> list[str]:
        """The IDs of the declared children, on this machine or not: the
        committed list, then the personal list's additions (Design 2.1)."""
        return [child.id for child in self.children(project_id)]

    def read_only_reason(self, project_id: str,
                         from_id: str | None = None) -> str | None:
        """Why `from_id` (default: the current project) may not write to
        `project_id`, or None when it may.

        **The one place the write rule lives** until TCW-114 (Design 7.1). A
        project is writable only when reached across links both sides
        declare: up to a parent that lists the child, or down to a listed
        child. A project reached across a parent link the parent does not
        list is read-only. A registry whose links are always declared both
        ways has nothing read-only."""
        return None

    def warnings(self) -> list[str]:
        """Graph facts worth saying that are neither defects nor unreachable
        projects — printed by `tcw validate`, never fatal."""
        return []

    def overrides(self) -> list["ProjectOverride"]:
        """The locators the caller supplied for this graph, in place of declared ones.

        Empty by default, and concrete rather than abstract on purpose: a store
        with no override mechanism has none to report, and that is a correct
        answer rather than a gap. Every existing adapter is right without
        changing, so a caller may always ask.

        Storage-neutral despite the filesystem adapter's answer being a path.
        The question — *did the caller say where this project is, rather than
        the configuration?* — is one a tracker-backed registry answers too, by
        reading the same environment for a project key instead of a directory.
        Only the value is a filesystem particular, and it stays opaque here for
        the same reason ``Project.locator`` does.

        Only overrides that took **effect** belong here. One naming a project
        this graph never consults is not in force, and listing it would say the
        graph depends on something it does not.

        Includes the ones that took effect and *failed* — an override that
        stopped the ladder and produced nothing is in force in the way that
        matters, and it is the entry a caller has to see. Its ``problem`` says
        which.
        """
        return []

    @abstractmethod
    def get(self, project_id: str) -> Project | None:
        """Return a connected project by canonical ID."""

    @abstractmethod
    def children(self, project_id: str | None = None) -> list[Project]:
        """Return the direct children of a project."""

    @abstractmethod
    def ancestors(self, project_id: str | None = None) -> list[Project]:
        """The project's load order without the project itself, farthest
        first, keeping those on this machine."""

    @abstractmethod
    def descendants(self, project_id: str | None = None) -> list[Project]:
        """The projects below this one through listed children, breadth
        first, those on this machine."""

    @abstractmethod
    def projects(self) -> list["Project"]:
        """The family: the current project, its ancestors and its
        descendants (Design 3.3). Never a sibling, nor a project read only
        to answer a lookup or another project's load order."""

    @abstractmethod
    def check(self) -> "list[Finding]":
        """Return graph/configuration problems as error findings, each
        `where` the config file that holds it; empty means valid.

        Problems only. A project that is declared but not reachable here is not
        one — see ``unreachable``.
        """

    @abstractmethod
    def unreachable(self) -> list["UnreachableProject"]:
        """Return the declared projects this store cannot reach from here.

        Deliberately separate from ``check``: these are not defects to fix, and a
        caller that treats them as such refuses to run in exactly the checkouts
        this distinction exists to serve. Callers that need the graph complete
        report them; callers that do not, ignore them.
        """


# Sentinel to distinguish "field not provided" from "set to None" in
# partial-update operations.  Omitted → unchanged; None → clear nullable.
_UNSET = object()


@dataclass
class Term:
    """A taxonomy entry: a vocabulary term or feature addressed by its path.

    `slug` is the identity (path from the taxonomy root, e.g. `admin/permission`).
    `owner` is the ID of the project whose store holds it, and `full_id` its
    full identifier (TCW-110 Design 1.4). `origin` is `"local"` or the
    `extends` ID the term was resolved through; it is the stores' own field,
    never printed.
    """
    slug: str
    name: str
    description: str = ""
    kind: str = "Vocabulary"
    relates_to: list[str] = field(default_factory=list)
    vocabulary: list[str] = field(default_factory=list)
    attachments: list[str] = field(default_factory=list)
    origin: str = "local"
    modified: str = ""
    owner: str = ""
    # The object this one belongs under (TCW-111 Design 3.1): a full
    # identifier, or the text as written when it is not one, which `check`
    # reports; None when the state file names no parent.
    parent: "FullId | str | None" = None

    @property
    def full_id(self) -> FullId:
        return FullId(self.owner, "taxonomy", self.slug)


class TaxonomyStore(ABC):
    """The taxonomy axis: a forest of terms, optionally federated via `extends`.

    Errors, by the class `tcw` turns into its exit code (TCW-73 Design 4):
    `NotFound` (4) when the entry or `extends` ID named does not exist;
    `UsageError` (2) when the input itself is wrong (a bad ID or path, a kind,
    Status or field outside the list, a reference that does not resolve or is
    ambiguous, a project nothing registers); `Refused` (3) when the input is
    fine but the store's state forbids it (the name is taken, the entry is
    inherited, has nested entries or is still referenced, the `extends` entry
    already exists); `BackendError` (1) for a fault reading back what was
    written. An adapter for another kind of store raises the same classes.
    """

    @abstractmethod
    def list_all(self, local_only: bool = False) -> list[Term]:
        """All terms (local + inherited), each flagged by `origin`."""

    @abstractmethod
    def get_local(self, slug: str) -> Term | None:
        """This store's own project's entry at the id-path `slug`, every
        folder spelled exactly as given, or None."""

    @abstractmethod
    def get_inherited(self, owner: str, slug: str) -> Term | None:
        """The entry at id-path `slug` in project `owner`, one this store
        inherits from, as this project sees it, or None."""

    @abstractmethod
    def get_view(self, slug: str) -> Term | None:
        """An id-path read as the active project sees it (TCW-110 Design 3.1
        form d): the local entry first, else the one inherited entry at that
        path. Raises `AmbiguousRef` when two inherited projects both hold it."""

    @abstractmethod
    def add(self, name: str, slug: str | None = None, parent: str | None = None,
            description: str = "", kind: str = "Vocabulary",
            vocabulary: list[str] | None = None) -> Term:
        """Create a local term with `parent` (TCW-111 Design 3.3): command
        input naming a term, written as its full identifier; the folder is
        made inside the parent's when it is a term of this project's own
        store, else at the root. Refuse a collision."""

    @abstractmethod
    def remove(self, ref: "FullId | str") -> None:
        """Remove a local term, writing nothing when refused. `ref` is a full
        identifier, or text read as command input is (TCW-110 Design 3.1). Raise `ValueError`
        when nothing resolves, the term is inherited, another term is nested under
        it, another local term's `relatesTo` or `vocabulary` still resolves to it,
        or a local capability's `Subject` or `Feature` does — including when the
        project's capabilities cannot be read, since that cannot then be known.
        Refusing rather than cascading is the contract, as for capabilities.
        Never reports success for a term that still exists afterwards."""

    @abstractmethod
    def search(self, query: str) -> list[Term]:
        """Substring search over names + descriptions, local + inherited."""

    @abstractmethod
    def check(self, identifier: str | None = None) -> "list[Finding]":
        """Validate the taxonomy, optionally limited to one object."""

    @abstractmethod
    def extends_add(self, project_id: str) -> None:
        """Explicitly inherit the taxonomy of a connected project."""

    @abstractmethod
    def extends_remove(self, project_id: str) -> None:
        """Drop an inherited project ID. Refuse if it isn't present."""

    @abstractmethod
    def get_term_detail(self, ref: "FullId | str") -> "TermDetail" | None:
        """The term `ref` names (a full identifier, or command input) plus a
        core revision token. Returns ``None`` when it names nothing.
        """

    @abstractmethod
    def update_term(self, ref: "FullId | str", *,
                    name: Any = _UNSET,
                    description: Any = _UNSET,
                    relates_to: Any = _UNSET,
                    vocabulary: Any = _UNSET,
                    kind: Any = _UNSET,
                    core_revision: str | None = None) -> "TermDetail":
        """Partial-merge update for an existing local term.

        Only keys that are *not* ``_UNSET`` are changed.  Passing ``None``
        clears a field to its default (empty string / empty list).  Empty
        strings are explicit values and are preserved.  Refers to
        ``TAXONOMY_EDITABLE_FIELDS`` for the allowed set.

        ``core_revision`` (when provided) must match the current token; a
        stale token raises ``StaleRevision`` and performs no write.

        Returns the updated ``TermDetail`` with a fresh revision.
        """


# ── Revision-bearing resource types ──────────────────────────────────────────


@dataclass
class TermDetail:
    """A taxonomy term with its core revision token."""
    term: Term
    core_revision: str = ""


@dataclass
class CapabilityDetail:
    """A single capability entry with its core revision token."""
    capability: Capability
    core_revision: str = ""


# ── Capabilities (Phase 3) ───────────────────────────────────────────────────

# The locked vocabulary `check` validates (phase-3-capabilities A.4). `Planning
# doc` is included: A.8 / the work spec use it as the capability→work forward
# pointer, so it must be recognized (reconciles the A.4 table omission).
CAP_STATUSES = {"Supported", "Partial", "Missing", "Blocked", "Omitted"}
CAP_PRIORITIES = {"P0", "P1", "P2", "P3"}
CAP_LIFECYCLES = {"Experimental", "Stable", "Deprecated"}
CAP_FIELDS = {
    "Status", "Priority", "Lifecycle", "Superseded by", "Subject",
    "Feature", "Roles", "When", "Gaps", "Blocked by",
}
# Fields 2.x accepted that 3.0 retired (TCW-73 Design 8.6): both pointed from
# the ledger into the work axis, which now links the other way, through each
# work item's `capabilities.yaml`. A record still carrying one is a check error
# naming the migration guide.
RETIRED_CAP_FIELDS = {"Planning doc", "Tracker"}
# The 2.x name of the 3.x `projects` key in `tcw-config.yaml` (TCW-73 Design
# 9.3): refused before every command, never read.
RETIRED_PROJECTS_KEY = "connected-projects"
# The keys that once named other projects, which TCW 4.0 refuses (TCW-108
# Design 3.5): parent links are `parents:` and `children:`.
REMOVED_LINK_KEYS = ("projects", RETIRED_PROJECTS_KEY)
MIGRATION_GUIDE = "docs/migration-guide-2.8-to-3.0.0.md"  # removed keys and fields


def retired_key_problem(config: object,
                        keys: tuple[str, ...] = REMOVED_LINK_KEYS) -> str | None:
    """The problem for a `tcw-config.yaml` mapping that still holds a key that
    once named other projects (the 3.x `projects`, the 2.x
    `connected-projects`), or None (TCW-108 Design 3.5). One wording wherever
    it is reported."""
    if not isinstance(config, dict):
        return None
    for key in keys:
        if key in config:
            return (f"'{key}' is not a TCW 4.0 key: name parents under 'parents:' "
                    f"and children under 'children:', by ID, and say where projects "
                    f"are in .tcw/tcw-manifest.yaml")
    return None


@dataclass
class Capability:
    """A single user-story capability, addressed by its folder path.

    `path` is the identity (path from the capabilities root, e.g.
    `auth/providers/github`). `id` is an opaque, immutable stable id — the
    durable key an override points at (a `tcw://` link names the full
    identifier instead). `owner` is the
    ID of the project whose store holds it, and `full_id` its full identifier
    (TCW-110 Design 1.4). `origin` is `"local"` or the `extends` ID the
    capability was resolved through; it is the stores' own field, never
    printed.
    `fields` holds the locked metadata vocabulary (`CAP_FIELDS`); `Subject` may
    be a list of taxonomy slugs.
    """
    path: str
    name: str
    id: str = ""
    fields: dict[str, Any] = field(default_factory=dict)
    body: str = ""
    origin: str = "local"
    modified: str = ""
    owner: str = ""
    # As `Term.parent` (TCW-111 Design 3.1).
    parent: "FullId | str | None" = None

    @property
    def status(self) -> str | None:
        return self.fields.get("Status")

    @property
    def full_id(self) -> FullId:
        return FullId(self.owner, "capabilities", self.path)


class CapabilitiesStore(ABC):
    """The capabilities axis: a bounded tree of user-story entries, optionally
    federated via `extends`.

    Deliberately near-identical to `TaxonomyStore` — both are bounded trees of
    body + named-fields + named-attachments entries on the shared tree-store core.

    Errors, by the class `tcw` turns into its exit code (TCW-73 Design 4):
    `NotFound` (4) when the entry or `extends` ID named does not exist;
    `UsageError` (2) when the input itself is wrong (a bad ID or path, a kind,
    Status or field outside the list, a reference that does not resolve or is
    ambiguous, a project nothing registers); `Refused` (3) when the input is
    fine but the store's state forbids it (the name is taken, the entry is
    inherited, has nested entries or is still referenced, the `extends` entry
    already exists); `BackendError` (1) for a fault reading back what was
    written. An adapter for another kind of store raises the same classes.
    """

    @abstractmethod
    def list_all(self, status: str | None = None, namespace: str | None = None,
                 local_only: bool = False) -> list[Capability]:
        """All capabilities (local + inherited), each flagged by `origin`."""

    @abstractmethod
    def get_local(self, path: str) -> Capability | None:
        """This store's own project's capability at the id-path `path`, every
        folder spelled exactly as given, or None."""

    @abstractmethod
    def get_inherited(self, owner: str, path: str) -> Capability | None:
        """The capability at id-path `path` in project `owner`, one this store
        extends, as this project sees it (its local override applied), or
        None."""

    @abstractmethod
    def get_view(self, path: str) -> Capability | None:
        """An id-path read as the active project sees it (TCW-110 Design 3.1
        form d): the local capability first, else the one inherited at that
        path. Raises `AmbiguousRef` when two extended projects both hold it."""

    @abstractmethod
    def add(self, identifier: str, name: str | None = None, status: str = "Missing",
            body: str = "", fields: dict[str, Any] | None = None,
            parent: str | None = None) -> Capability:
        """Create a local capability folder at `identifier` (a path), with
        `parent` (command input naming a capability) written as its full
        identifier when given. Refuse a collision. `fields` are validated as `set` validates them, before
        anything is written, so a create carrying a bad field writes nothing."""

    @abstractmethod
    def remove(self, identifier: "FullId | str") -> None:
        """Delete the local capability `identifier` names (a full identifier,
        or text read as command input is, TCW-110 Design 3.1), writing nothing
        when refused. Raise `AmbiguousRef` when an id-path matches multiple
        extended stores, and `ValueError` when:

        - nothing resolves;
        - the capability is inherited, overridden locally or not (an override
          is dropped with `reset`, never with `remove`);
        - another capability or override is nested under its path;
        - another local capability or override still references it through
          `Superseded by`, `Blocked by`, `Roles` or `When`.

        Refusing rather than cascading is the contract: a delete never takes a
        second capability with it or leaves a reference pointing at nothing.
        Never mutates an extended store."""

    @abstractmethod
    def reset(self, identifier: "FullId | str") -> None:
        """Drop the local override at `identifier`, re-inheriting the upstream
        capability verbatim. Raise `ValueError` when there is no override (a
        standalone local capability is not an override — the `remove` operation,
        driven by `tcw capabilities rm`, deletes it; a bare
        inherited path has nothing to drop), or `AmbiguousRef` when an id-path
        matches multiple extended stores. Never mutates an extended store."""

    @abstractmethod
    def set(self, identifier: "FullId | str", fields: dict[str, Any],
            parent: str | None = None) -> Capability:
        """Update/insert metadata fields on the capability at `identifier`;
        return it. `parent`, when given, is command input naming a capability,
        or `''` to clear it; it is refused for an inherited capability before
        anything is written (TCW-111 Design 3.4). Keys must be in CAP_FIELDS; a Status value must be in
        CAP_STATUSES. `Subject` accepts a list (or a comma string). Other
        field-value semantics are `check`'s job (Spec 3)."""

    @abstractmethod
    def search(self, query: str) -> list[Capability]:
        ...

    @abstractmethod
    def unreviewed_inherited(self) -> list["Capability"]:
        """Inherited capabilities whose Status is the master's default — never
        locally ruled on (no local override that sets Status). The 'unreviewed'
        half of drift: distinguishes an echoed master default from a local
        decision. Empty when nothing is federated."""

    @abstractmethod
    def check(self, taxonomy: "TaxonomyStore | None" = None,
              identifier: str | None = None) -> "list[Finding]":
        """Validate identifiers, metadata vocabulary, federation, and
        (cross-component) Subject/Feature refs, as error findings."""

    @abstractmethod
    def get_capability_detail(self, identifier: "FullId | str") -> "CapabilityDetail" | None:
        """The capability `identifier` names plus a revision token.
        Returns ``None`` when it names nothing."""

    @abstractmethod
    def update_capability(self, identifier: "FullId | str", *,
                          body: Any = _UNSET,
                          fields: Any = _UNSET,
                          core_revision: str | None = None) -> "CapabilityDetail":
        """Partial-merge update for an existing capability.

        ``body``: ``None`` clears to empty string; any string sets it.
        ``fields``: a dict of ``{key: value}`` pairs to merge into the
        capability's metadata (keys validated against ``CAP_FIELDS``).
        ``core_revision`` enforces stale-write rejection.

        Returns the updated ``CapabilityDetail`` with a fresh revision.
        """

    @abstractmethod
    def extends_add(self, project_id: str) -> None:
        """Explicitly inherit capabilities from a connected project."""

    @abstractmethod
    def extends_remove(self, project_id: str) -> None:
        """Drop an inherited project ID. Refuse if it isn't present."""


# ── Work (Phase 5) ───────────────────────────────────────────────────────────


def normalize_tag(value: str) -> str:
    """Canonicalize a work tag: lowercase-hyphenated slug (mirrors
    ``fs.slugify``), with a non-empty guard. Registration and application both
    run inputs through this so ``Bug`` and ``bug`` never diverge."""
    tag = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not tag:
        raise ValueError(f"invalid tag {value!r}: empty after normalization")
    return tag


# ── Lifecycle policy (stage/transition bindings) ─────────────────────────────
#
# Two ladders. A **stage** produces one lifecycle artifact; a **transition** moves
# status. Nothing is both. These ids are **public API**: a user's
# `tcw-config.yaml` keys on them, so renaming one silently breaks their
# configuration. Insertions are safe; renames are not.


# Procedures: instruction text TCW ships that is not a lifecycle stage, which a
# project may replace under `work.procedures`. Public API like `STAGE_IDS`, and
# deliberately **not** skill names, so renaming a skill never breaks a
# project's configuration. Removing an id does break it: TCW 3.0 deleted
# `post-mortem`, `decompose`, `delegation` and `consolidate-plans`, and a
# project still configuring one gets a config error saying where its text went
# (`_REMOVED_PROCEDURES` in `tcw/work/config.py`). A project replaces a
# procedure's text; it cannot add a procedure.
PROCEDURE_IDS = ("unattended-work", "triage-issues", "documentation-sync",
                 "create-work", "audit-backlog", "search", "pause-work")


# Bound on a `generate` hook's stdout, in **raw bytes before decoding**.
# Enforced while reading rather than after, so a runaway script cannot exhaust
# memory before the check fires. Also the cap on the item `body` a hook gets.
DEFAULT_OUTPUT_CAP = 64 * 1024


@dataclass(frozen=True)
class DocEntry:
    """One `work.documentation` entry: a document, when it must be updated, and
    what to write in it.

    Project configuration, not store content — a tracker-backed project has these
    exactly as a filesystem project does, the same way `work.tags` and
    `work.lifecycle` already do.
    """
    path: str
    trigger: str
    description: str


@dataclass(frozen=True)
class RepositoryDeclaration:
    """Where a component store comes from, as the project records it.

    Project configuration and an **adapter locator**, exactly as a store path is —
    the project registry already states the rule that canonical IDs are identity
    and filesystem locations are locators only. A tracker-backed adapter would
    read a different locator from the same slot; nothing above the adapter is
    entitled to read these fields.

    `path` is the store's location *within* the declared repository, and stays a
    POSIX-style relative string here rather than becoming a `Path`: this object
    is parsed from YAML and compared in tests, and the adapter that joins it is
    the only code that needs it to be a path at all.
    """
    url: str
    ref: str | None = None
    path: str = ""
    checkout: str | None = None


@dataclass(frozen=True)
class ProvisionResult:
    """What one provisioning attempt did.

    `location` is a short human-readable handle: presentation only, do not
    parse it. `action` is the closed vocabulary a
    caller may branch on.
    """
    action: str                 # one of PROVISION_ACTIONS
    available: bool
    location: str = ""
    detail: str = ""


PROVISION_ACTIONS = (
    "undeclared",        # nothing declared; there was nothing to do
    "available",         # already usable here; nothing was contacted
    "obtained",          # newly made available
    "planned",           # dry run: this is what would have happened
)


class StoreProvisioner(ABC):
    """Making a declared store usable *here*.

    The abstract verb is "make yourself usable", not "clone": a tracker-backed
    adapter answers `is_available` by checking credentials and reachability, and
    an adapter that needs nothing implements `ensure_available` as a no-op —
    which is a legitimate implementation, not a stub.

    No signature names a URL, a ref, or a directory. Those are the filesystem
    adapter's private business, and a store-interface method that mentioned one
    would have moved the seam into the wrong layer.
    """

    @abstractmethod
    def describe(self) -> str:
        """A short, human-readable account of where the store is declared to come
        from. Presentation only — do not parse it."""

    @abstractmethod
    def is_available(self) -> bool:
        """Whether the store can be used here right now, without contacting
        anything."""

    @abstractmethod
    def ensure_available(self, *, dry_run: bool = False) -> ProvisionResult:
        """Make the store usable here, and report what that took.

        Idempotent: an already-usable store returns `available` and contacts
        nothing, which is what lets a caller run this unconditionally. Keeping
        an available store up to date is the project's own business, not
        TCW's (TCW-73 Design 8.4). `dry_run` reports the plan and contacts
        nothing.
        """


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")


def is_slug(text: str) -> bool:
    """Whether `text` is already in the form `slugify` produces: lowercase
    letters and digits in words joined by single hyphens, with no `/`."""
    return bool(text) and slugify(text) == text


class NotASlug(UsageError):
    """A slug given by the caller that `is_slug` refuses. The message names no
    flag, since the viewer returns it too; the CLI adds `--slug`."""


def parse_repository_declaration(
    raw: Any, where: str
) -> tuple["RepositoryDeclaration | None", list[str]]:
    """Parse a `<component>.repository` mapping into a declaration plus problems.

    Mirrors `parse_lifecycle_policy` and `parse_documentation_entries`: pure,
    touches no filesystem, never raises. `where` is the config path to quote in
    problems (`work.repository`), so one implementation serves every component
    rather than three that drift.

    Returns `(None, problems)` when the declaration cannot be trusted — unlike
    the documentation parser, which keeps the entries that parsed. The difference
    is what a half-read value would do: a mistyped documentation entry costs one
    row in a table, while a mistyped repository would send a fetch somewhere
    nobody asked for. This one fails closed.
    """
    problems: list[str] = []
    if raw is None:
        return None, problems
    if not isinstance(raw, dict):
        return None, [f"{where}: expected a mapping, got {type(raw).__name__}"]

    known = {"url", "ref", "path", "checkout"}
    unknown = {k for k in set(raw) - known if follows_naming_rule(k)}
    if unknown:
        problems.append(f"{where}: unknown key(s) {', '.join(sorted(map(str, unknown)))}; "
                        f"expected {', '.join(repr(k) for k in sorted(known))}")

    url = raw.get("url")
    if not isinstance(url, str) or not url.strip():
        problems.append(f"{where}.url: expected a non-empty string")

    def _optional_string(key: str) -> str | None:
        value = raw.get(key)
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            problems.append(f"{where}.{key}: expected a non-empty string")
            return None
        return value.strip()

    ref = _optional_string("ref")
    checkout = _optional_string("checkout")

    # `path` is bounded rather than merely typed: it is joined onto a directory
    # this code created, so the containment rule the stores already enforce for
    # their own identifiers applies here too — syntactically, before any join.
    store_path = ""
    raw_path = raw.get("path")
    if raw_path is not None:
        if not isinstance(raw_path, str) or not raw_path.strip():
            problems.append(f"{where}.path: expected a non-empty string")
        else:
            candidate = raw_path.strip()
            parts = PurePosixPath(candidate).parts
            if candidate.startswith("/") or (len(candidate) > 1 and candidate[1] == ":"):
                problems.append(f"{where}.path: must be relative to the repository root, "
                                f"got {candidate!r}")
            elif ".." in parts:
                problems.append(f"{where}.path: must not leave the repository root, "
                                f"got {candidate!r}")
            else:
                store_path = PurePosixPath(candidate).as_posix().strip("/")

    if problems:
        return None, problems
    return RepositoryDeclaration(url=url.strip(), ref=ref, path=store_path,
                                 checkout=checkout), problems


def parse_documentation_entries(raw: Any) -> tuple[list["DocEntry"], list[str]]:
    """Parse a `work.documentation` list into entries plus a problem list.

    Mirrors `parse_lifecycle_policy`: pure, touches no filesystem, never raises,
    and returns problems advisorily so `tcw validate` can report them while the
    adapter discards them. A typo in one entry must not blank a project's whole
    documentation gate, so entries that parse are kept alongside the problems.

    **Shape only, deliberately.** The trigger vocabulary is explicitly open —
    `skills/documentation-sync/SKILL.md` says "Treat any such project-defined
    trigger as authoritative for that project" — so a trigger is checked for
    whitespace (which catches `Public API` and a dropped bracket) and nothing
    else. `path` is likewise **not** required to exist: an entry routinely names
    a file the project intends to create, and this repository's own entry is the
    pattern `skills/<component>/SKILL.md`, which resolves to no file at all.

    **Identity is `(path, trigger)`, not the path alone** — the same call
    `_parse_bindings` makes for `(kind, value, when)`. One file large enough
    that its sections answer to different triggers needs one entry per trigger:
    a CLI-surface change fires the first, a validation-rule change touching no
    CLI surface fires only the second. Keying on the path alone made the config
    form less expressive than the Markdown section it replaced.
    """
    entries: list[DocEntry] = []
    problems: list[str] = []
    if raw is None:
        return entries, problems
    if not isinstance(raw, list):
        return entries, [f"work.documentation: expected a list, "
                         f"got {type(raw).__name__}"]

    seen: dict[tuple[str, str], int] = {}
    for index, item in enumerate(raw):
        where = f"work.documentation entry {index}"
        if not isinstance(item, dict):
            problems.append(f"{where}: expected a mapping, "
                            f"got {type(item).__name__}")
            continue

        unknown = {k for k in set(item) - {"path", "trigger", "description"}
                   if follows_naming_rule(k)}
        if unknown:
            problems.append(f"{where}: unknown key(s) {', '.join(sorted(map(str, unknown)))}; "
                            f"expected 'path', 'trigger', 'description'")

        values: dict[str, str] = {}
        for key in ("path", "trigger", "description"):
            value = item.get(key)
            if not isinstance(value, str) or not value.strip():
                problems.append(f"{where}: '{key}' is required and must be a "
                                f"non-empty string")
            else:
                values[key] = value.strip()
        if len(values) != 3:
            continue

        path, trigger = values["path"], values["trigger"]
        if "\n" in path:
            problems.append(f"{where}: 'path' must not contain a newline")
            continue
        if "\n" in trigger:
            problems.append(f"{where}: 'trigger' must not contain a newline")
            continue
        if PurePosixPath(path).is_absolute() or path.startswith("/"):
            problems.append(f"{where}: 'path' must be relative to the project, "
                            f"got an absolute path")
            continue
        if any(part == ".." for part in PurePosixPath(path).parts):
            problems.append(f"{where}: 'path' must not escape the project")
            continue
        if any(character.isspace() for character in trigger):
            problems.append(f"{where}: 'trigger' must not contain whitespace "
                            f"(got {trigger!r}) — a trigger is one bracketed name")
            continue

        if (path, trigger) in seen:
            problems.append(f"{where}: duplicate 'path' {path!r} under trigger "
                            f"{trigger!r}, already declared by entry "
                            f"{seen[(path, trigger)]}")
            continue
        seen[(path, trigger)] = index
        entries.append(DocEntry(path=path, trigger=trigger,
                                description=values["description"]))

    return entries, problems


# Taxonomy term fields that the abstract ``update_term`` operation may modify.
TAXONOMY_EDITABLE_FIELDS = frozenset({"name", "description", "kind", "relates_to", "vocabulary"})


class IllegalTransition(Exception):
    """A status transition not in the legal graph (the enforcement — B.3)."""


class MultipleMatch(Exception):
    """A slug resolves to more than one item folder (slug integrity broken)."""


