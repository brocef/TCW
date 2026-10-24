"""The interface every work backend implements.

A backend owns the facts about an item that people outside engineering read and
change: its properties, its stage, its request and its comments. The technical
record (specs, plans, rounds) is files in the item folder in every mode, so
paths and artifacts are not part of this interface; see `layout.py`.

Twelve operations, small enough that the filesystem backend (TCW-70) and the
Jira backend (TCW-71) can each implement every one of them for real.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Protocol, runtime_checkable

from tcw.errors import UsageError
from tcw.ids import FullId
from tcw.work.model import TERMINAL, Changes, Item, Slug, stage as table_stage


def default_includes(item_stage: str | None) -> bool:
    """What `list` shows by default: unfinished items, and items with no stage.

    An item with no stage is a Jira ticket in a status no stage maps to. It
    needs attention, so it is never hidden.
    """
    return item_stage is None or table_stage(item_stage).kind != TERMINAL


@dataclass(frozen=True)
class Query:
    """What `list` returns. `stages` and `all` cannot be given together; with
    neither, the default applies (`default_includes`). `tags` matches an item
    carrying any of them."""

    stages: frozenset[str] | None = None
    parent: Slug | None = None
    assignee: str | None = None
    tags: frozenset[str] | None = None
    all: bool = False

    def __post_init__(self) -> None:
        if self.stages is not None and self.all:
            raise UsageError("choose stages or all, not both")

    def matches(self, item: Item) -> bool:
        if self.stages is not None:
            if item.stage not in self.stages:
                return False
        elif not self.all and not default_includes(item.stage):
            return False
        if self.parent is not None and item.parent != self.parent:
            return False
        if self.assignee is not None and item.assignee != self.assignee:
            return False
        if self.tags is not None and not self.tags.intersection(item.tags):
            return False
        return True


@dataclass(frozen=True)
class Comment:
    at: datetime  # UTC
    author: str | None
    text: str


@runtime_checkable
class WorkBackend(Protocol):
    project: str  # this project's id
    external_stages: frozenset[str]  # stages whose record the backend keeps
    inbox_items: bool  # may an item sit at the inbox stage

    def create(self, title: str, props: Changes, *, stage: str,
               request: str | None, nest: bool = False) -> Item:
        """Make the item and its folder: inside its parent's folder when
        `nest` is true and the parent is one of this backend's items
        (`nesting_parent`), else directly under the work path."""

    # Every other operation's `id_path` is an item's id-path: its folder's
    # path in the work store, at any depth (TCW-111 Design 5).

    def read(self, id_path: str) -> Item:
        """Raises `NotFound` for an id-path naming no item."""

    def list(self, query: Query) -> list[Item]: ...

    def update(self, id_path: str, changes: Changes) -> Item: ...

    def set_stage(self, id_path: str, stage: str, note: str | None) -> str | None:
        """Move the item, recording `note` as a comment as part of the same
        move where the store allows it. Returns the stage the backend reports
        afterwards. Raises `Refused` having changed nothing, or
        `MovedWithoutNote` when the stage changed but the note was not kept.
        Runs no checks and no hooks: that is `advance`'s job."""

    def comment(self, id_path: str, text: str) -> None: ...

    def move(self, id_path: str, new_id_path: str,
             before_folder: Callable[[], object]) -> list[tuple[FullId, FullId]]:
        """Give the item, and every item nested in its folder, a new id-path
        (TCW-114 Design 7.1), keeping its last part's date or key
        (`UsageError` otherwise): write what the backend owns that names a
        moved item, call `before_folder`, then move the folder or records.
        Returns the pairs of full identifiers, the item first."""

    def lookup(self, name: str) -> str | None:
        """A backend-specific name (a Jira key) as an id-path, or None."""

    def read_request(self, id_path: str) -> str | None: ...

    def read_comments(self, id_path: str, limit: int | None = None) -> list[Comment]:
        """Newest first, at most `limit` (all when None)."""

    def current_user(self) -> str | None:
        """The user in the same form the backend uses for `Item.assignee`."""

    def is_item_folder(self, id_path: str) -> bool:
        """Whether `id_path`, a folder at any depth under the work path, is one
        of this backend's item folders, by its own rule for naming and keeping
        them. Reads only the work path, never the network, so it answers
        while the backend cannot; a folder anything else left there is not
        an item."""


def nesting_parent(backend: WorkBackend, parent: Slug | None,
                   nest: bool) -> tuple[str | None, str | None]:
    """Where a new item's folder goes (TCW-111 Design 5): the parent's
    id-path when `nest` is true and the parent is one of `backend`'s items,
    else None for the top of the work path; and a note to report when `nest`
    was asked for but the parent belongs to another project."""
    if not nest or parent is None:
        return None, None
    if parent.project != backend.project:
        return None, (f"not nested: {parent} belongs to project {parent.project!r}, "
                      f"so the item's folder is made at the top of this project's "
                      f"work folder")
    if not backend.is_item_folder(parent.folder):
        return None, None
    return parent.folder, None


def folder_disagreement(backend: WorkBackend, item: Item) -> str | None:
    """Design 3.2's warning when `item`'s folder sits directly in another item's
    folder that its `parent` does not name, or None (TCW-111 row m). Reads only
    the work path; the parent is the one `item` carries, read by its backend."""
    from tcw.object_folders import disagreement, folder_parent
    work_path = getattr(backend, "work_path", None)
    if work_path is None:              # a backend with no work path has no folders
        return None
    above = folder_parent(work_path, "work", item.slug.folder)
    if above is not None and not backend.is_item_folder(above):
        above = None
    return disagreement(item.slug, None if above is None else Slug(backend.project, above),
                        item.parent)
