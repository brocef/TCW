"""An in-memory `WorkBackend` for the work model's tests. Not shipped.

Items live in a dict, but each one still gets a real folder under the work root
so the layout has somewhere to put files. Every write is recorded in `calls`;
reads are not, so a test can assert that a read changed nothing.

The knobs on `set_stage` let a test play a backend that refuses a move, loses
the note after moving, or reports a stage other than the one asked for.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from tcw.errors import MovedWithoutNote, NotFound, Refused
from tcw.work.backend import Comment, Query
from tcw.work.model import (
    DEFAULT_PRIORITY, Changes, Item, Slug, apply_changes, title_words,
)

_EPOCH = datetime(2026, 10, 1, tzinfo=timezone.utc)


class MemoryBackend:
    def __init__(self, work_root: Path, project: str = "tcw", *,
                 external_stages: frozenset[str] = frozenset(),
                 inbox_items: bool = True, user: str | None = None,
                 today: date = date(2026, 10, 1)):
        self.work_root = Path(work_root)
        self.project = project
        self.external_stages = frozenset(external_stages)
        self.inbox_items = inbox_items
        self.user = user
        self.today = today
        self.items: dict[str, Item] = {}
        self.requests: dict[str, str] = {}
        self.comments: dict[str, list[Comment]] = {}
        self.calls: list[tuple] = []
        self._counter = 0
        self._clock = 0
        # set_stage behaviour a test can switch on
        self.refuse_moves = False
        self.lose_notes = False
        self.report_stage: str | None = None

    # -- helpers for tests --------------------------------------------------

    def _get(self, folder: str) -> Item:
        try:
            return self.items[folder]
        except KeyError:
            raise NotFound(f"no work item {self.project}/{folder}") from None

    def _put(self, item: Item) -> Item:
        self.items[item.slug.folder] = item
        return item

    def _now(self) -> datetime:
        self._clock += 1
        return _EPOCH + timedelta(seconds=self._clock)

    def _add_comment(self, folder: str, text: str) -> None:
        self.comments.setdefault(folder, []).append(
            Comment(self._now(), self.user, text))

    def set_reported_stage(self, folder: str, stage: str | None) -> None:
        """Put an item at any stage, or at none, without recording a call."""
        self._put(replace(self._get(folder), stage=stage))

    def stage_of(self, folder: str) -> str | None:
        return self._get(folder).stage

    # -- the interface ------------------------------------------------------

    def create(self, title: str, props: Changes, *, stage: str,
               request: str | None) -> Item:
        self.calls.append(("create", title, props, stage, request))
        self._counter += 1
        folder = f"{self._counter}-{title_words(title)}"
        (self.work_root / folder).mkdir(parents=True)
        base = Item(slug=Slug(self.project, folder), title=title, stage=stage,
                    created=self.today, priority=DEFAULT_PRIORITY, effort=None,
                    complexity=None, tags=(), assignee=None, parent=None,
                    blocked_by=())
        if request is not None:
            self.requests[folder] = request
        return self._put(apply_changes(base, props))

    def read(self, folder: str) -> Item:
        return self._get(folder)

    def list(self, query: Query) -> list[Item]:
        return [item for item in self.items.values() if query.matches(item)]

    def update(self, folder: str, changes: Changes) -> Item:
        item = self._get(folder)
        self.calls.append(("update", folder, changes))
        return self._put(apply_changes(item, changes))

    def set_stage(self, folder: str, stage: str, note: str | None) -> str | None:
        item = self._get(folder)
        self.calls.append(("set_stage", folder, stage, note))
        if self.refuse_moves:
            raise Refused(f"the backend offers no move to {stage}")
        reported = self.report_stage or stage
        self._put(replace(item, stage=reported))
        if note is not None:
            if self.lose_notes:
                raise MovedWithoutNote("the note could not be recorded")
            self._add_comment(folder, note)
        return reported

    def comment(self, folder: str, text: str) -> None:
        self._get(folder)
        self.calls.append(("comment", folder, text))
        self._add_comment(folder, text)

    def rename(self, folder: str, title_words_: str) -> Item:
        item = self._get(folder)
        self.calls.append(("rename", folder, title_words_))
        prefix = folder.split("-", 1)[0]
        new = f"{prefix}-{title_words_}"
        (self.work_root / folder).rename(self.work_root / new)
        del self.items[folder]
        for store in (self.requests, self.comments):
            if folder in store:
                store[new] = store.pop(folder)
        return self._put(replace(item, slug=Slug(self.project, new)))

    def lookup(self, name: str) -> str | None:
        return next((f for f in self.items if f.startswith(f"{name}-")), None)

    def read_request(self, folder: str) -> str | None:
        self._get(folder)
        return self.requests.get(folder)

    def read_comments(self, folder: str, limit: int | None = None) -> list[Comment]:
        self._get(folder)
        newest_first = sorted(self.comments.get(folder, []),
                              key=lambda c: c.at, reverse=True)
        return newest_first if limit is None else newest_first[:limit]

    def current_user(self) -> str | None:
        return self.user
