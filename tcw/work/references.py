"""Checks `tcw validate` runs over a project's items: references that point
nowhere, and items whose stage is ahead of the files their earlier stages
should have left."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from tcw.work.layout import Layout
from tcw.work.model import DOCUMENT, FLOW, ROUNDS, STAGES, Item, Slug, position, stage as table_stage

WARNING, UNRESOLVED = "warning", "unresolved"
FOUND, MISSING = "found", "missing"


@dataclass(frozen=True)
class Problem:
    level: str  # warning, or unresolved (neither a warning nor an error)
    slug: Slug  # the item the problem is reported against
    message: str


def reference_problems(items: Iterable[Item], current_project: str,
                       resolve: Callable[[Slug], str]) -> list[Problem]:
    """Every `parent` and `blocked-by` that points at nothing.

    Pass **every** item, finished ones included, or a reference to a completed
    blocker looks missing. A reference into another project goes through
    `resolve`, which answers `found`, `missing` or `unresolved` (that project
    cannot be reached from here).
    """
    items = list(items)
    known = {item.slug for item in items}
    problems = []
    for item in items:
        refs = ([("parent", item.parent)] if item.parent else []) + \
               [("blocked-by", ref) for ref in item.blocked_by]
        for field, ref in refs:
            if ref.project == current_project:
                answer = FOUND if ref in known else MISSING
            else:
                answer = resolve(ref)
            if answer == MISSING:
                problems.append(Problem(WARNING, item.slug,
                                        f"{field} references a missing item, {ref}"))
            elif answer == UNRESOLVED:
                problems.append(Problem(UNRESOLVED, item.slug,
                                        f"{field} {ref} is in a project that "
                                        f"cannot be reached from here"))
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
