"""TCW 3.0's work model: what a work item is, and the stages it moves through.

This module is the only place a stage is named (see `STAGES`). Everything else
reads the table's columns, so a project that disables a stage, or a later
version that adds one, changes behavior here and nowhere else.

It imports nothing from the 2.x work store, which TCW-70 removes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import date
from typing import Any, Callable, Iterable

from tcw.errors import UsageError
from tcw.store.base import normalize_tag
from tcw.store.project import PROJECT_ID_PATTERN

# ---------------------------------------------------------------------------
# Identity

FOLDER_LIMIT = 128
# Room left for the prefix a backend puts before the title words: a date, or a
# Jira key such as `TCW-1234`, and the `-` that joins them.
PREFIX_ALLOWANCE = 20
FOLDER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*$")


@dataclass(frozen=True, order=True)
class Slug:
    """A work item's identity: the project it belongs to, and its folder name.

    The folder pattern allows upper case so that a Jira key can lead it
    (`TCW-67-…`); each backend narrows the pattern for the names it creates.
    """

    project: str
    folder: str

    @classmethod
    def parse(cls, text: str, current_project: str) -> Slug:
        """`project/folder`, or a bare `folder` in `current_project`.

        Anything else is a usage error. The 2.x reserved project names are not
        applied: they kept project ids apart from status folders, and 3.0 has
        none, so `backlog/f` is simply an unknown project.
        """
        if not isinstance(text, str):
            raise UsageError(f"{text!r} is not a work item slug")
        parts = text.split("/")
        if len(parts) == 1:
            project, folder = current_project, parts[0]
        elif len(parts) == 2:
            project, folder = parts
        else:
            raise UsageError(
                f"{text!r} is not a work item slug: use `project/folder` or a "
                f"bare folder name")
        if not PROJECT_ID_PATTERN.match(project):
            raise UsageError(
                f"{text!r} is not a work item slug: {project!r} is not a "
                f"project id (lowercase letters and digits joined by `-`)")
        if len(folder) > FOLDER_LIMIT or not FOLDER_PATTERN.match(folder):
            raise UsageError(
                f"{text!r} is not a work item slug: a folder name is letters, "
                f"digits and `-`, starts with a letter or digit, and is at "
                f"most {FOLDER_LIMIT} characters")
        return cls(project, folder)

    def __str__(self) -> str:
        return f"{self.project}/{self.folder}"


def title_words(title: str, limit: int = FOLDER_LIMIT - PREFIX_ALLOWANCE) -> str:
    """The part of a folder name that comes from the title.

    Lowercase; every run of characters outside `[a-z0-9]` becomes one `-`;
    ends trimmed; cut back to the last `-` within `limit` (or cut hard when a
    single word is longer than that). `untitled` when nothing is left. Each
    backend adds its own prefix.
    """
    words = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if len(words) > limit:
        cut = words[:limit + 1]
        boundary = cut.rfind("-")
        words = cut[:boundary] if boundary > 0 else words[:limit]
        words = words.strip("-")
    return words or "untitled"


# ---------------------------------------------------------------------------
# Properties

PRIORITIES = ("highest", "high", "medium", "low", "lowest")
SIZES = ("low", "medium", "high", "very-high")  # effort and complexity
DEFAULT_PRIORITY = "medium"


@dataclass(frozen=True)
class Item:
    """One work item as a backend reports it.

    `stage` is None when the backend reports no stage (a Jira ticket in a
    status no stage maps to). `priority` is None when the backend has none to
    report. `untracked` holds the backend names of linked records that have no
    item (in Jira, ticket keys); it is always empty in filesystem mode.
    """

    slug: Slug
    title: str
    stage: str | None
    created: date
    priority: str | None
    effort: str | None
    complexity: str | None
    tags: tuple[str, ...]
    assignee: str | None
    parent: Slug | None
    blocked_by: tuple[Slug, ...]
    untracked: tuple[str, ...] = ()


class _Unset:
    def __repr__(self) -> str:
        return "UNSET"


UNSET: Any = _Unset()


@dataclass(frozen=True)
class Changes:
    """A partial update. `UNSET` leaves a property alone and None clears it.

    Slugs may be given as `Slug` or as text; text is parsed against the item's
    project. There is no `stage`: only `advance` moves an item.
    """

    title: Any = UNSET
    priority: Any = UNSET
    effort: Any = UNSET
    complexity: Any = UNSET
    assignee: Any = UNSET
    parent: Any = UNSET
    add_tags: tuple[str, ...] = field(default=())
    remove_tags: tuple[str, ...] = field(default=())
    add_blocked_by: tuple[Any, ...] = field(default=())
    remove_blocked_by: tuple[Any, ...] = field(default=())


def _as_slug(value: Any, current_project: str, what: str) -> Slug:
    if isinstance(value, Slug):
        return value
    try:
        return Slug.parse(value, current_project)
    except UsageError as error:
        raise UsageError(f"{what}: {error}") from None


def _check_scale(value: Any, scale: tuple[str, ...], what: str) -> None:
    if value is UNSET or value is None:
        return
    if not isinstance(value, str) or value not in scale:
        raise UsageError(f"{what} must be one of {', '.join(scale)}; got {value!r}")


def _tag(value: str) -> str:
    try:
        return normalize_tag(value)
    except (ValueError, AttributeError):
        raise UsageError(f"{value!r} is not a tag") from None


def validate_changes(changes: Changes, *, item_slug: Slug | None,
                     registered_tags: Iterable[str], current_project: str,
                     parent_of: Callable[[Slug], Slug | None]) -> None:
    """Raise `UsageError` for anything both backends must refuse.

    `item_slug` is None for an item not created yet. `parent_of` answers an
    item's current parent from the caller's own reads; the cycle check follows
    it up from the proposed parent within this project only, and stops at a
    slug it has already seen, so a cycle already in the data cannot loop.
    """
    if changes.title is not UNSET and (
            not isinstance(changes.title, str) or not changes.title.strip()):
        raise UsageError("a title must not be empty")
    _check_scale(changes.priority, PRIORITIES, "priority")
    _check_scale(changes.effort, SIZES, "effort")
    _check_scale(changes.complexity, SIZES, "complexity")

    registered = {_tag(t) for t in registered_tags}
    for tag in changes.add_tags:
        if _tag(tag) not in registered:
            raise UsageError(f"tag {tag!r} is not registered for this project")

    for blocker in changes.add_blocked_by:
        if _as_slug(blocker, current_project, "blocked-by") == item_slug:
            raise UsageError(f"{item_slug} cannot block itself")
    for blocker in changes.remove_blocked_by:
        _as_slug(blocker, current_project, "blocked-by")

    if changes.parent is UNSET or changes.parent is None:
        return
    parent = _as_slug(changes.parent, current_project, "parent")
    if parent == item_slug:
        raise UsageError(f"{item_slug} cannot be its own parent")
    if item_slug is None:
        return
    seen: set[Slug] = set()
    ancestor: Slug | None = parent
    while ancestor is not None and ancestor.project == current_project \
            and ancestor not in seen:
        if ancestor == item_slug:
            raise UsageError(
                f"making {parent} the parent of {item_slug} would make a cycle")
        seen.add(ancestor)
        ancestor = parent_of(ancestor)


def _merged(current: tuple, add: Iterable, remove: Iterable) -> tuple:
    removed = set(remove)
    out = [v for v in current if v not in removed]
    for value in add:
        if value not in out and value not in removed:
            out.append(value)
    return tuple(out)


def apply_changes(item: Item, changes: Changes) -> Item:
    """The item with `changes` applied. Pure; validate the changes first."""
    project = item.slug.project
    updates: dict[str, Any] = {}
    for name in ("title", "priority", "effort", "complexity", "assignee"):
        value = getattr(changes, name)
        if value is not UNSET:
            updates[name] = value
    if changes.parent is not UNSET:
        updates["parent"] = (None if changes.parent is None
                             else _as_slug(changes.parent, project, "parent"))
    updates["tags"] = _merged(item.tags, map(_tag, changes.add_tags),
                              map(_tag, changes.remove_tags))
    updates["blocked_by"] = _merged(
        item.blocked_by,
        (_as_slug(s, project, "blocked-by") for s in changes.add_blocked_by),
        (_as_slug(s, project, "blocked-by") for s in changes.remove_blocked_by))
    return replace(item, **updates)


def blocks_of(slug: Slug, items: Iterable[Item]) -> list[Slug]:
    """The items `slug` blocks. Nothing stores this; it is read off blocked-by."""
    return [item.slug for item in items if slug in item.blocked_by]
