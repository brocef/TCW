"""The filesystem work backend: every work item is a folder in the work path.

An item folder is `<date>-<title words>`, directly inside the work path, holding
`item.yaml` (the item's properties and stage), the stage folders TCW-69's
layout names, and `comments/`. The folder never moves when the item's stage
changes; only `rename` moves it, because a person asked.

Every write replaces a whole file in one step, and every file written, moved or
removed is reported through `report` (stderr by default). Nothing here changes
git state.

No stage is named in this module: the stage table in `model.py` is the only
place that does.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

from tcw.errors import BackendError, MovedWithoutNote, NotFound, Refused, UsageError
from tcw.findings import Finding
from tcw.store.base import normalize_tag
from tcw.work.backend import Comment, Query
from tcw.work.config import MIGRATION_GUIDE, WorkConfig
from tcw.work.layout import Layout
from tcw.work.model import (
    DEFAULT_PRIORITY, FLOW, FOLDER_LIMIT, PRIORITIES, SIZES, TERMINAL, Changes,
    Item, Slug, apply_changes, is_stage, stage as table_stage, start_stage,
    title_words as make_title_words, validate_changes,
)

ITEM_FILE = "item.yaml"
COMMENTS = "comments"
ITEM_FOLDER = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9]+(-[a-z0-9]+)*$")
WORDS = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DATED = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.*)$")
COMMENT_NAME = re.compile(r"^(\d{8}T\d{6}Z)\.md$")
COMMENT_STAMP = "%Y%m%dT%H%M%SZ"

# The keys of item.yaml, in the order they are written.
KEYS = ("title", "stage", "priority", "effort", "complexity", "tags",
        "assignee", "parent", "blocked-by")


def is_item_folder(path: Path) -> bool:
    """A directory whose name is `<real date>-<words>`, at most the folder
    limit, holding an `item.yaml`."""
    name = path.name
    if len(name) > FOLDER_LIMIT or not ITEM_FOLDER.match(name):
        return False
    try:
        date.fromisoformat(name[:10])
    except ValueError:
        return False
    return path.is_dir() and (path / ITEM_FILE).is_file()


# ---------------------------------------------------------------------------
# Reading and writing item.yaml


class _Unreadable(Exception):
    def __init__(self, path: Path, key: str | None, message: str):
        super().__init__(message)
        self.path, self.key, self.message = path, key, message

    def __str__(self) -> str:
        where = f"{self.path}" + (f" ({self.key})" if self.key else "")
        return f"{where}: {self.message}"


@dataclass(frozen=True)
class Unreadable:
    path: Path
    key: str | None
    message: str

    def __str__(self) -> str:
        return f"{self.path}" + (f" ({self.key})" if self.key else "") + \
            f": {self.message}"


def _reads_as_stage(raw: str, enabled: frozenset[str]) -> bool:
    """An enabled flow or terminal stage. Anything else (a misspelling, a
    disabled or side stage, a 2.x name) reads as no stage."""
    return is_stage(raw) and raw in enabled and \
        table_stage(raw).kind in (FLOW, TERMINAL)


def _load(folder: Path, project: str,
          enabled: frozenset[str]) -> tuple[Item, str]:
    """The item and the raw `stage` string as written. Strict: anything wrong
    raises `_Unreadable` naming the key."""
    path = folder / ITEM_FILE
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
        raise _Unreadable(path, None, f"cannot be read: {error}") from None
    if not isinstance(raw, dict):
        raise _Unreadable(path, None, "must be a mapping of the item's properties")
    for key in raw:
        if key not in KEYS:
            raise _Unreadable(path, str(key), f"unknown key; the keys are "
                                              f"{', '.join(KEYS)}")

    def text(key: str, required: bool = False) -> str | None:
        value = raw.get(key)
        if value is None:
            if required:
                raise _Unreadable(path, key, "is required")
            return None
        if not isinstance(value, str) or not value.strip():
            raise _Unreadable(path, key, "must be a non-empty string")
        return value

    def scale(key: str, values: tuple[str, ...]) -> str | None:
        value = raw.get(key)
        if value is None:
            return None
        if not isinstance(value, str) or value not in values:
            raise _Unreadable(path, key, f"must be one of {', '.join(values)}; "
                                         f"got {value!r}")
        return value

    def slug(key: str, value: Any) -> Slug:
        try:
            return Slug.parse(value, project)
        except UsageError as error:
            raise _Unreadable(path, key, str(error)) from None

    title = text("title", required=True)
    raw_stage = text("stage", required=True)
    priority = scale("priority", PRIORITIES) or DEFAULT_PRIORITY
    tags_raw = raw.get("tags") or []
    if not isinstance(tags_raw, list):
        raise _Unreadable(path, "tags", "must be a list of tags")
    tags: list[str] = []
    for value in tags_raw:
        try:
            tag = normalize_tag(value)
        except (ValueError, AttributeError):
            raise _Unreadable(path, "tags", f"{value!r} is not a tag") from None
        if tag not in tags:
            tags.append(tag)
    blocked_raw = raw.get("blocked-by") or []
    if not isinstance(blocked_raw, list):
        raise _Unreadable(path, "blocked-by", "must be a list of slugs")
    parent = raw.get("parent")
    item = Item(
        slug=Slug(project, folder.name),
        title=title,
        stage=raw_stage if _reads_as_stage(raw_stage, enabled) else None,
        created=date.fromisoformat(folder.name[:10]),
        priority=priority,
        effort=scale("effort", SIZES),
        complexity=scale("complexity", SIZES),
        tags=tuple(tags),
        assignee=text("assignee"),
        parent=None if parent is None else slug("parent", parent),
        blocked_by=tuple(slug("blocked-by", v) for v in blocked_raw),
    )
    return item, raw_stage


def _dump(item: Item, raw_stage: str) -> str:
    data: dict[str, Any] = {"title": item.title, "stage": raw_stage,
                            "priority": item.priority or DEFAULT_PRIORITY}
    if item.effort:
        data["effort"] = item.effort
    if item.complexity:
        data["complexity"] = item.complexity
    if item.tags:
        data["tags"] = list(item.tags)
    if item.assignee:
        data["assignee"] = item.assignee
    if item.parent:
        data["parent"] = str(item.parent)
    if item.blocked_by:
        data["blocked-by"] = [str(s) for s in item.blocked_by]
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def _replace_file(path: Path, text: str) -> None:
    """Write `text` to a temporary file beside `path`, then replace `path`
    with it in one step, so no reader ever sees half a file."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def read_all(work_path: Path, project: str,
             enabled: frozenset[str]) -> tuple[list[Item], list[Unreadable]]:
    """Every item folder directly inside the work path, in name order, read
    one by one. An unreadable one is set aside rather than failing the rest."""
    items: list[Item] = []
    bad: list[Unreadable] = []
    if not work_path.is_dir():
        return items, bad
    for entry in sorted(work_path.iterdir(), key=lambda p: p.name):
        if not is_item_folder(entry):
            continue
        try:
            items.append(_load(entry, project, enabled)[0])
        except _Unreadable as error:
            bad.append(Unreadable(error.path, error.key, error.message))
    return items, bad


def _stderr(line: str) -> None:
    print(line, file=sys.stderr)


# ---------------------------------------------------------------------------
# The backend


class FsWorkBackend:
    external_stages: frozenset[str] = frozenset()
    inbox_items = True

    def __init__(self, project: str, work_path: Path, config: WorkConfig,
                 user_name: str | None = None, *,
                 report: Callable[[str], None] | None = None,
                 today: Callable[[], date] = date.today,
                 now: Callable[[], datetime] | None = None):
        self.project = project
        self.work_path = Path(work_path)
        self.config = config
        self.user_name = user_name
        self.report = report or _stderr
        self.today = today
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.layout = Layout(self.work_path, config.enabled, self.external_stages)

    # -- helpers ------------------------------------------------------------

    @property
    def enabled(self) -> frozenset[str]:
        return self.config.enabled

    def _folder(self, folder: str) -> Path:
        path = self.work_path / folder
        if "/" in folder or not is_item_folder(path):
            raise NotFound(f"no work item {self.project}/{folder}")
        return path

    def _load(self, folder: str) -> tuple[Item, str]:
        path = self._folder(folder)
        try:
            return _load(path, self.project, self.enabled)
        except _Unreadable as error:
            raise BackendError(str(error)) from None

    def _write(self, item: Item, raw_stage: str) -> None:
        path = self.work_path / item.slug.folder / ITEM_FILE
        _replace_file(path, _dump(item, raw_stage))
        self.report(f"wrote {path}")

    def _parent_of(self, slug: Slug) -> Slug | None:
        if slug.project != self.project:
            return None
        try:
            return self._load(slug.folder)[0].parent
        except (NotFound, BackendError):
            return None

    def _validate(self, changes: Changes, item_slug: Slug | None) -> None:
        validate_changes(changes, item_slug=item_slug,
                         registered_tags=self.config.tags,
                         current_project=self.project,
                         parent_of=self._parent_of)

    def _request_path(self, slug: Slug) -> Path:
        return self.layout.document(slug, start_stage())

    # -- the interface ------------------------------------------------------

    def create(self, title: str, props: Changes, *, stage: str,
               request: str | None) -> Item:
        if not isinstance(title, str) or not title.strip():
            raise UsageError("a title must not be empty")
        table_stage(stage)
        self._validate(props, None)
        folder = f"{self.today().isoformat()}-{make_title_words(title)}"
        path = self.work_path / folder
        if path.exists():
            raise Refused(f"{path} already exists; rename it, or choose another "
                          f"title")
        self.work_path.mkdir(parents=True, exist_ok=True)
        path.mkdir()
        self.report(f"created {path}")
        try:
            base = Item(slug=Slug(self.project, folder), title=title, stage=stage,
                        created=date.fromisoformat(folder[:10]),
                        priority=DEFAULT_PRIORITY, effort=None, complexity=None,
                        tags=(), assignee=None, parent=None, blocked_by=())
            item = apply_changes(base, props)
            self._write(item, stage)
            if request:
                document = self._request_path(item.slug)
                document.parent.mkdir(parents=True, exist_ok=True)
                _replace_file(document, request)
                self.report(f"wrote {document}")
        except BaseException:
            shutil.rmtree(path, ignore_errors=True)
            self.report(f"removed {path}")
            raise
        return self.read(folder)

    def read(self, folder: str) -> Item:
        return self._load(folder)[0]

    def list(self, query: Query) -> list[Item]:
        items, bad = read_all(self.work_path, self.project, self.enabled)
        if bad:
            raise BackendError("cannot list the work items; unreadable: " +
                               "; ".join(str(b) for b in bad))
        if query.tags is not None:
            query = replace(query, tags=frozenset(normalize_tag(t)
                                                  for t in query.tags))
        return [item for item in items if query.matches(item)]

    def update(self, folder: str, changes: Changes) -> Item:
        item, raw_stage = self._load(folder)
        self._validate(changes, item.slug)
        self._write(apply_changes(item, changes), raw_stage)
        return self.read(folder)

    def set_stage(self, folder: str, stage: str, note: str | None) -> str | None:
        item, _ = self._load(folder)
        table_stage(stage)
        self._write(item, stage)
        if note is not None:
            try:
                self._write_comment(folder, note)
            except OSError as error:
                raise MovedWithoutNote(str(error)) from None
        return self.read(folder).stage

    def _write_comment(self, folder: str, text: str) -> Path:
        directory = self.work_path / folder / COMMENTS
        directory.mkdir(exist_ok=True)
        when = self.now().astimezone(timezone.utc).replace(microsecond=0)
        while True:
            path = directory / f"{when.strftime(COMMENT_STAMP)}.md"
            try:
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            except FileExistsError:
                when += timedelta(seconds=1)
                continue
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(text)
            self.report(f"wrote {path}")
            return path

    def comment(self, folder: str, text: str) -> None:
        self._folder(folder)
        if not isinstance(text, str) or not text.strip():
            raise UsageError("a comment must not be empty")
        try:
            self._write_comment(folder, text)
        except OSError as error:
            raise BackendError(f"cannot write the comment: {error}") from None

    def rename(self, folder: str, title_words: str) -> Item:
        old_path = self._folder(folder)
        prefix = folder[:10]
        dated = DATED.match(title_words)
        words = title_words
        if dated:
            if dated.group(1) != prefix:
                raise UsageError(f"a rename keeps the date {prefix}; give the "
                                 f"words alone, or {prefix}-<words>")
            words = dated.group(2)
        if not WORDS.match(words):
            raise UsageError(f"{title_words!r} is not a folder name; did you "
                             f"mean {make_title_words(words)}?")
        new = f"{prefix}-{words}"
        new_path = self.work_path / new
        if len(new) > FOLDER_LIMIT:
            raise UsageError(f"{new} is longer than {FOLDER_LIMIT} characters")
        if new_path.exists():
            raise Refused(f"{new_path} already exists")

        items, bad = read_all(self.work_path, self.project, self.enabled)
        if bad:
            raise BackendError("not renaming, because an unreadable item might "
                               "name it: " + "; ".join(str(b) for b in bad))
        old_slug, new_slug = Slug(self.project, folder), Slug(self.project, new)
        referencing = [i.slug.folder for i in items
                       if i.parent == old_slug or old_slug in i.blocked_by]

        os.rename(old_path, new_path)
        self.report(f"moved {old_path} to {new_path}")

        failed: list[str] = []
        for name in referencing:
            name = new if name == folder else name
            try:
                item, raw_stage = _load(self.work_path / name, self.project,
                                        self.enabled)
                item = replace(
                    item,
                    parent=new_slug if item.parent == old_slug else item.parent,
                    blocked_by=tuple(new_slug if s == old_slug else s
                                     for s in item.blocked_by))
                self._write(item, raw_stage)
            except (OSError, _Unreadable) as error:
                failed.append(f"{name} ({error})")
        if failed:
            raise BackendError(f"moved {folder} to {new}, but these items still "
                               f"name the old slug: {', '.join(failed)}")

        self._report_mentions(folder)
        self.report(f"items in other projects that name {old_slug} are not "
                    f"rewritten; `tcw validate` there reports them")
        return self.read(new)

    def _report_mentions(self, old: str) -> None:
        for path in sorted(self.work_path.rglob("*")):
            if not path.is_file() or path.name == ITEM_FILE:
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            for number, line in enumerate(lines, start=1):
                if old in line:
                    self.report(f"{path}:{number}: names {old}, not rewritten")

    def lookup(self, name: str) -> str | None:
        return None

    def read_request(self, folder: str) -> str | None:
        self._folder(folder)
        path = self._request_path(Slug(self.project, folder))
        if not path.is_file():
            return None
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise BackendError(f"{path}: cannot be read: {error}") from None

    def read_comments(self, folder: str, limit: int | None = None) -> list[Comment]:
        directory = self._folder(folder) / COMMENTS
        if not directory.is_dir():
            return []
        found = []
        for entry in directory.iterdir():
            match = COMMENT_NAME.match(entry.name)
            if not match or not entry.is_file():
                continue
            at = datetime.strptime(match.group(1), COMMENT_STAMP).replace(
                tzinfo=timezone.utc)
            found.append((at, entry))
        found.sort(key=lambda pair: pair[1].name, reverse=True)
        if limit is not None:
            found = found[:limit]
        comments = []
        for at, entry in found:
            try:
                text = entry.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as error:
                raise BackendError(f"{entry}: cannot be read: {error}") from None
            comments.append(Comment(at, None, text))
        return comments

    def current_user(self) -> str | None:
        return self.user_name


# ---------------------------------------------------------------------------
# What `tcw validate` checks in the work path


def work_store_problems(work_path: Path, project: str,
                        config: WorkConfig) -> list[Finding]:
    """The checks that read only the files in the work path: unreadable
    items, items with no stage, folders and files that are not items, and
    unregistered tags."""
    findings: list[Finding] = []
    if not work_path.is_dir():
        return findings
    registered = set(config.tags)
    guide = f"see {MIGRATION_GUIDE} for the work store layout"
    for entry in sorted(work_path.iterdir(), key=lambda p: p.name):
        if entry.name.startswith("."):
            continue
        if entry.is_file():
            findings.append(Finding("warning", str(entry),
                                    f"is not part of a work store; {guide}"))
            continue
        if not is_item_folder(entry):
            findings.append(Finding("error", str(entry),
                                    f"is not an item folder, so it is not part "
                                    f"of a work store; {guide}"))
            continue
        try:
            item, raw_stage = _load(entry, project, config.enabled)
        except _Unreadable as error:
            key = f" ({error.key})" if error.key else ""
            findings.append(Finding("error", str(error.path),
                                    f"unreadable{key}: {error.message}"))
            continue
        if item.stage is None:
            findings.append(Finding("error", str(entry / ITEM_FILE),
                                    f"stage {raw_stage!r} is not an enabled stage, "
                                    f"so the item has no stage; move it with "
                                    f"`tcw work advance --to <stage> --force`"))
        for tag in item.tags:
            if tag not in registered:
                findings.append(Finding("warning", str(entry / ITEM_FILE),
                                        f"tag {tag!r} is not in the tag registry"))
    return findings
