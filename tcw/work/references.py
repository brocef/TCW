"""Checks `tcw validate` runs over a project's items: references that point
nowhere, and items whose stage is ahead of the files their earlier stages
should have left."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from tcw.work.layout import Layout
from tcw.work.model import DOCUMENT, FLOW, ROUNDS, STAGES, Item, Slug, position, stage as table_stage

WARNING, UNRESOLVED, ERROR = "warning", "unresolved", "error"
FOUND, MISSING = "found", "missing"
# The project is on this machine but its work store could not be opened or
# read: a fault in that project, reported here as a warning so this project's
# run does not fail for it (TCW-73 plan choice 9).
BROKEN = "broken"


@dataclass(frozen=True)
class GraphError:
    """The answer for a reference whose project cannot be looked up: an ID
    nothing knows, or a problem in the project graph (TCW-110 Design 6.3).
    `message` says which."""
    message: str


@dataclass(frozen=True)
class Problem:
    level: str  # warning, error, or unresolved (neither a warning nor an error)
    slug: Slug  # the item the problem is reported against
    message: str


#: The `Item` attribute each work item reference field is read from.
_ATTRIBUTES = {"parent": "parent", "blocked-by": "blocked_by"}


def item_references(item: Item) -> list[tuple[Item, str, Slug]]:
    """`(item, field, reference)` for each reference `item` holds, in the
    fields the one table names for a work item (TCW-114 Design 6.1)."""
    from tcw.reference_fields import fields_of
    out = []
    for row in fields_of("work-item"):
        value = getattr(item, _ATTRIBUTES[row.name])
        for ref in (value if row.many else [value] if value else []):
            out.append((item, row.name, ref))
    return out


def reference_problems(items: Iterable[Item], current_project: str,
                       resolve: Callable[[Slug], "str | GraphError"],
                       more: Iterable[tuple[Item, str, Slug]] = ()) -> list[Problem]:
    """Every `parent` and `blocked-by` that points at nothing.

    Pass **every** item, finished ones included, or a reference to a completed
    blocker looks missing. A reference into another project goes through
    `resolve`, which answers `found`, `missing`, `unresolved` (that project
    cannot be reached from here), `broken` (it is here, and its work store
    cannot be read) or a `GraphError` (it cannot be looked up). `more` adds
    `(item, field, reference)` triples kept somewhere other than the items'
    own properties.
    """
    items = list(items)
    known = {item.slug for item in items}
    problems = []
    triples = [t for item in items for t in item_references(item)] + list(more)
    for item, field, ref in triples:
        if ref.project == current_project:
            answer = FOUND if ref in known else MISSING
        else:
            answer = resolve(ref)
        if isinstance(answer, GraphError):
            problems.append(Problem(ERROR, item.slug,
                                    f"{field} {ref} cannot be looked up: "
                                    f"{answer.message}"))
        elif answer == MISSING:
            problems.append(Problem(WARNING, item.slug,
                                    f"{field} references a missing item, {ref}"))
        elif answer == UNRESOLVED:
            problems.append(Problem(UNRESOLVED, item.slug,
                                    f"{field} {ref} is in a project that "
                                    f"cannot be reached from here"))
        elif answer == BROKEN:
            problems.append(Problem(WARNING, item.slug,
                                    f"{field} {ref} could not be checked, because "
                                    f"project '{ref.project}' cannot be read; run "
                                    f"`tcw validate` there"))
    return problems


def _has_artifact(layout: Layout, slug: Slug, name: str) -> bool:
    if table_stage(name).artifact == DOCUMENT:
        return layout.document(slug, name).is_file()
    return bool(layout.rounds(slug, name))


def stage_problems(items: Iterable[Item], layout: Layout) -> list[Problem]:
    """A warning for each enabled stage before an unfinished item's stage that
    should have left a document or rounds in the item folder and did not."""
    problems = []
    for item in items:
        if item.stage is None or table_stage(item.stage).kind != FLOW:
            continue
        here = position(item.stage)
        for row in STAGES[:here]:
            if row.kind != FLOW or row.artifact not in (DOCUMENT, ROUNDS) \
                    or row.name not in layout.enabled \
                    or row.name in layout.external:
                continue
            if not _has_artifact(layout, item.slug, row.name):
                problems.append(Problem(
                    WARNING, item.slug,
                    f"is at {item.stage} but has nothing from {row.name}; an "
                    f"item forced past a stage warns until it is finished"))
    return problems
