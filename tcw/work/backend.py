"""The interface every work backend implements.

A backend owns the facts about an item that people outside engineering read and
change: its properties, its stage, its request and its comments. The technical
record (specs, plans, rounds) is files in the item folder in every mode, so
paths and artifacts are not part of this interface; see `layout.py`.

Eleven operations, small enough that the filesystem backend (TCW-70) and the
Jira backend (TCW-71) can each implement every one of them for real.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

from tcw.errors import UsageError
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
               request: str | None) -> Item:
        """Make the item and its folder."""

    def read(self, folder: str) -> Item:
        """Raises `NotFound` for an unknown folder."""

    def list(self, query: Query) -> list[Item]: ...

    def update(self, folder: str, changes: Changes) -> Item: ...

    def set_stage(self, folder: str, stage: str, note: str | None) -> str | None:
        """Move the item, recording `note` as a comment as part of the same
        move where the store allows it. Returns the stage the backend reports
        afterwards. Raises `Refused` having changed nothing, or
        `MovedWithoutNote` when the stage changed but the note was not kept.
        Runs no checks and no hooks: that is `advance`'s job."""

    def comment(self, folder: str, text: str) -> None: ...

    def rename(self, folder: str, title_words: str) -> Item: ...

    def lookup(self, name: str) -> str | None:
        """A backend-specific name (a Jira key) as a folder, or None."""

    def read_request(self, folder: str) -> str | None: ...

    def read_comments(self, folder: str, limit: int | None = None) -> list[Comment]:
        """Newest first, at most `limit` (all when None)."""

    def current_user(self) -> str | None:
        """The user in the same form the backend uses for `Item.assignee`."""
