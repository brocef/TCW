"""The filesystem work backend: every work item is a folder in the work path.

An item folder is `<date>-<title words>`, directly inside the work path, holding
`tcw-work-item.yaml` (its state file: the item's properties and stage, after
its `tcw-version`), the stage folders TCW-69's layout names, and `comments/`. The folder never moves when the item's stage
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
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

from tcw.errors import BackendError, MovedWithoutNote, NotFound, Refused, UsageError
from tcw.findings import Finding
from tcw.object_folders import (STATE_FILES, existing_version_line, id_problem, is_object,
                                length_problems, shape_problems, state_text, walk)
from tcw.project_files import VERSION_KEY, version_problem
from tcw.output import shown
from tcw.store.base import normalize_tag
from tcw.store.fs import _atomic_write_all, _umask, exact_child
from tcw.work.backend import Comment, Query, nesting_parent
from tcw.work.config import WorkConfig
from tcw.work.layout import Layout
from tcw.work.model import (
    DEFAULT_PRIORITY, FLOW, FOLDER_LIMIT, PRIORITIES, SIZES, TERMINAL, Changes,
    UNSET, Item, Slug, _as_slug, apply_changes, check_encodable, fitted_words, is_stage, stage as table_stage, start_stage,
    title_words as make_title_words, validate_changes,
)

STATE_FILE = STATE_FILES["work"]
COMMENTS = "comments"
ITEM_FOLDER = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9]+(-[a-z0-9]+)*$")
WORDS = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DATED = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.*)$")
COMMENT_NAME = re.compile(r"^(\d{8}T\d{6}Z)\.md$")
COMMENT_STAMP = "%Y%m%dT%H%M%SZ"

# The keys of an item's state file, in the order they are written. `id` is
# never written by TCW, only kept where a person wrote it (Design 1.3).
KEYS = (VERSION_KEY, "id", "title", "stage", "priority", "effort", "complexity",
        "tags", "assignee", "parent", "blocked-by")


def item_named(name: str) -> bool:
    """Whether the folder name `name`, an id-path's last part, follows this
    backend's rule for an item: `<real date>-<words>`, at most the folder
    limit. Holding the state file is the walk's question (`is_object`)."""
    if not isinstance(name, str) or len(name) > FOLDER_LIMIT \
            or not ITEM_FOLDER.match(name):
        return False
    try:
        date.fromisoformat(name[:10])
    except ValueError:
        return False
    return True


def is_item_folder(work_path: Path, id_path: str) -> bool:
    """Whether `id_path` names an item of the work store at `work_path`: its
    last part follows `item_named`, and the walk's rule makes it an object,
    at any depth (TCW-111 Design 5, row 12)."""
    return item_named(id_path.rpartition("/")[2]) and is_object(work_path, "work", id_path)


#: Row h's message, at the state file of a folder named as an item that holds
#: none (TCW-111 Design 2.6). Decided by the implementing agent: the Jira
#: backend's message says what the file holds, and this one says the same.
UNMADE_MESSAGE = "is missing; it holds the item's properties and stage"


# ---------------------------------------------------------------------------
# Reading and writing an item's state file


class Unreadable(Exception):
    """A state file that cannot be read, naming the key at fault when there
    is one: raised by the reader, and returned as a value by `read_all`."""

    def __init__(self, path: Path, key: str | None, message: str):
        super().__init__(message)
        self.path, self.key, self.message = path, key, message

    def __str__(self) -> str:
        where = f"{self.path}" + (f" ({self.key})" if self.key else "")
        return f"{where}: {self.message}"


def _reads_as_stage(raw: str, enabled: frozenset[str]) -> bool:
    """An enabled flow or terminal stage. Anything else (a misspelling, a
    disabled or side stage, a 2.x name) reads as no stage."""
    return is_stage(raw) and raw in enabled and \
        table_stage(raw).kind in (FLOW, TERMINAL)


def _load(folder: Path, project: str,
          enabled: frozenset[str], id_path: str | None = None) -> tuple[Item, str]:
    """The item at the id-path `id_path` (the folder's name when not given)
    and the raw `stage` string as written. Strict: anything wrong raises
    `Unreadable` naming the key."""
    id_path = folder.name if id_path is None else id_path
    name = id_path.rpartition("/")[2]
    path = folder / STATE_FILE
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
        raise Unreadable(path, None, f"cannot be read: {error}") from None
    if not isinstance(raw, dict):
        raise Unreadable(path, None, "must be a mapping of the item's properties")
    # The version first: a file this TCW cannot read is never interpreted, so
    # a newer one's keys are not reported as unknown (Design 1.5).
    problem = version_problem(raw)
    if problem is not None:
        raise Unreadable(path, VERSION_KEY, problem)
    for key in raw:
        if key not in KEYS:
            raise Unreadable(path, str(key), f"unknown key; the keys are "
                                              f"{', '.join(KEYS)}")

    def text(key: str, required: bool = False) -> str | None:
        value = raw.get(key)
        if value is None:
            if required:
                raise Unreadable(path, key, "is required")
            return None
        if not isinstance(value, str) or not value.strip():
            raise Unreadable(path, key, "must be a non-empty string")
        return value

    def scale(key: str, values: tuple[str, ...]) -> str | None:
        value = raw.get(key)
        if value is None:
            return None
        if not isinstance(value, str) or value not in values:
            raise Unreadable(path, key, f"must be one of {', '.join(values)}; "
                                         f"got {value!r}")
        return value

    def slug(key: str, value: Any) -> Slug:
        try:
            return Slug.stored(value)
        except UsageError as error:
            raise Unreadable(path, key, str(error)) from None

    title = text("title", required=True)
    raw_stage = text("stage", required=True)
    priority = scale("priority", PRIORITIES) or DEFAULT_PRIORITY
    tags_raw = raw.get("tags") or []
    if not isinstance(tags_raw, list):
        raise Unreadable(path, "tags", "must be a list of tags")
    tags: list[str] = []
    for value in tags_raw:
        try:
            tag = normalize_tag(value)
        except (ValueError, AttributeError):
            raise Unreadable(path, "tags", f"{value!r} is not a tag") from None
        if tag not in tags:
            tags.append(tag)
    blocked_raw = raw.get("blocked-by") or []
    if not isinstance(blocked_raw, list):
        raise Unreadable(path, "blocked-by", "must be a list of slugs")
    parent = raw.get("parent")
    item = Item(
        slug=Slug(project, id_path),
        title=title,
        stage=raw_stage if _reads_as_stage(raw_stage, enabled) else None,
        created=date.fromisoformat(name[:10]),
        priority=priority,
        effort=scale("effort", SIZES),
        complexity=scale("complexity", SIZES),
        tags=tuple(tags),
        assignee=text("assignee"),
        parent=None if parent is None else slug("parent", parent),
        blocked_by=tuple(slug("blocked-by", v) for v in blocked_raw),
    )
    return item, raw_stage


def _dump(item: Item, raw_stage: str) -> dict[str, Any]:
    """The state file's mapping for `item`, without `tcw-version`."""
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
    return data


def _state_text(path: Path, item: Item, raw_stage: str) -> str:
    """What `path` is rewritten with: its `tcw-version` line as written (or
    this TCW's, for a new file), the `id` a person wrote, kept, and the
    item's properties (Design 1.3, 1.4)."""
    data = _dump(item, raw_stage)
    if existing_version_line(path) is not None:
        try:
            old = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError):
            old = None
        if isinstance(old, dict) and "id" in old:
            data = {"id": old["id"], **data}
    return state_text(path, data)


def _replace_file(path: Path, text: str) -> None:
    """Replace `path` with `text` in one step, so no reader ever sees half a
    file, with the mode an ordinary write would give."""
    _atomic_write_all([(path, text)])


def read_all(work_path: Path, project: str,
             enabled: frozenset[str]) -> tuple[list[Item], list[Unreadable]]:
    """Every item the walk finds in the work path, at any depth, in name
    order, read one by one. An unreadable one is set aside rather than
    failing the rest."""
    items: list[Item] = []
    bad: list[Unreadable] = []
    for id_path in Layout.objects(work_path):
        if not item_named(id_path.rpartition("/")[2]):
            continue
        try:
            items.append(_load(work_path / id_path, project, enabled, id_path)[0])
        except Unreadable as error:
            bad.append(error)
    return items, bad


def report_mentions(work_path: Path, old: str, report: Callable[[str], None]) -> None:
    """After a rename, every line of the work path's files, other than the
    state files, that still names the old folder. None is rewritten."""
    for path in sorted(work_path.rglob("*")):
        if not path.is_file() or path.name == STATE_FILE:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for number, line in enumerate(lines, start=1):
            if old in line:
                report(f"{path}:{number}: names {old}, not rewritten")


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
        """The folder of the item at the id-path `folder`, at any depth."""
        path = self.work_path / folder
        if not isinstance(folder, str) or not is_item_folder(self.work_path, folder):
            # A disk that ignores letter case finds a folder by another
            # spelling; an id-path is compared exactly (TCW-110 Design 1.1),
            # and the spelling found is said when there is one.
            spelled = exact_child(self.work_path, folder) \
                if isinstance(folder, str) and "/" not in folder else False
            if isinstance(spelled, str) and is_item_folder(self.work_path, spelled):
                raise NotFound(f"no work item {Slug(self.project, folder)} (the "
                               f"folder is spelled {spelled})")
            raise NotFound(f"no work item {Slug(self.project, folder)}")
        return path

    def _load(self, folder: str) -> tuple[Item, str]:
        path = self._folder(folder)
        try:
            return _load(path, self.project, self.enabled, folder)
        except Unreadable as error:
            raise BackendError(str(error)) from None

    def _write(self, item: Item, raw_stage: str) -> None:
        path = self.work_path / item.slug.folder / STATE_FILE
        _replace_file(path, _state_text(path, item, raw_stage))
        self.report(f"wrote {shown(path)}")

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
               request: str | None, nest: bool = False) -> Item:
        if not isinstance(title, str) or not title.strip():
            raise UsageError("a title must not be empty")
        table_stage(stage)
        self._validate(replace(props, title=title), None)
        parent = (None if props.parent in (UNSET, None)
                  else _as_slug(props.parent, self.project, "parent"))
        under, note = nesting_parent(self, parent, nest)
        if note:
            self.report(note)
        # Fitted under the 255-character limit (TCW-111 Design 4.3): a date
        # and its `-` lead the name.
        words = fitted_words(title, project=self.project, parent=under, prefix=11)
        name = f"{self.today().isoformat()}-{words}"
        folder = f"{under}/{name}" if under else name
        path = self.work_path / folder
        if path.exists():
            raise Refused(f"{path} already exists; rename it, or choose another "
                          f"title")
        self.work_path.mkdir(parents=True, exist_ok=True)
        path.mkdir()
        self.report(f"created {shown(path)}/")
        try:
            # The date of the last part: `folder` is the whole id-path.
            base = Item(slug=Slug(self.project, folder), title=title, stage=stage,
                        created=date.fromisoformat(name[:10]),
                        priority=DEFAULT_PRIORITY, effort=None, complexity=None,
                        tags=(), assignee=None, parent=None, blocked_by=())
            item = apply_changes(base, props)
            self._write(item, stage)
            if request:
                document = self._request_path(item.slug)
                document.parent.mkdir(parents=True, exist_ok=True)
                _replace_file(document, request)
                self.report(f"wrote {shown(document)}")
        except BaseException:
            # One line per file removed and none for the folder (Design 1.2),
            # read back from the disk so only what actually went is named.
            files = sorted(f for f in path.rglob("*") if f.is_file() or f.is_symlink())
            shutil.rmtree(path, ignore_errors=True)
            for f in files:
                if not (f.exists() or f.is_symlink()):
                    self.report(f"removed {shown(f)}")
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
        if note is not None:
            check_encodable(note, "the reason")
        self._write(item, stage)
        if note is not None:
            try:
                self._write_comment(folder, note)
            except (OSError, ValueError) as error:
                raise MovedWithoutNote(str(error)) from None
        return self.read(folder).stage

    def _write_comment(self, folder: str, text: str) -> Path:
        directory = self.work_path / folder / COMMENTS
        directory.mkdir(exist_ok=True)
        when = self.now().astimezone(timezone.utc).replace(microsecond=0)
        # Written whole to a temporary file first, then linked to the first
        # free name: `link` takes a name in one step and never replaces one, so
        # two comments in the same second cannot overwrite each other and a
        # failed write leaves no comment file behind.
        fd, tmp = tempfile.mkstemp(dir=directory, prefix=".comment.")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(text)
            os.chmod(tmp, 0o666 & ~_umask())
            while True:
                path = directory / f"{when.strftime(COMMENT_STAMP)}.md"
                try:
                    os.link(tmp, path)
                except FileExistsError:
                    when += timedelta(seconds=1)
                    continue
                except OSError:
                    # FAT and exFAT volumes and SMB mounts have no hard links.
                    path = self._create_comment(directory, when, text)
                break
        finally:
            os.unlink(tmp)
        self.report(f"wrote {shown(path)}")
        return path

    @staticmethod
    def _create_comment(directory: Path, when: datetime, text: str) -> Path:
        """The fallback without hard links: take the first free name with an
        exclusive create, which also never replaces a file, and remove the
        file again if writing it fails."""
        while True:
            path = directory / f"{when.strftime(COMMENT_STAMP)}.md"
            try:
                # `open` applies the umask itself.
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
            except FileExistsError:
                when += timedelta(seconds=1)
                continue
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(text)
            except BaseException:
                path.unlink(missing_ok=True)
                raise
            return path

    def comment(self, folder: str, text: str) -> None:
        self._folder(folder)
        if not isinstance(text, str) or not text.strip():
            raise UsageError("a comment must not be empty")
        check_encodable(text, "the comment")
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
        self.report(f"moved {shown(old_path)} to {shown(new_path)}")

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
            except (OSError, Unreadable) as error:
                failed.append(f"{name} ({error})")
        if failed:
            raise BackendError(f"moved {folder} to {new}, but these items still "
                               f"name the old slug: {', '.join(failed)}",
                               name=str(new_slug))

        report_mentions(self.work_path, folder, self.report)
        self.report(f"items in other projects that name {old_slug} are not "
                    f"rewritten; `tcw validate` there reports them")
        return self.read(new)


    def lookup(self, name: str) -> str | None:
        return None

    def is_item_folder(self, folder: str) -> bool:
        return isinstance(folder, str) and is_item_folder(self.work_path, folder)

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
    """The checks that read only the files in the work path: the store's
    shape (TCW-111 Design 2.6 rows a to i), then, for every item the walk
    finds at any depth, an unreadable state file, an id that is not its
    folder's name, no stage, and unregistered tags."""
    findings: list[Finding] = []
    if not work_path.is_dir():
        return findings
    registered = set(config.tags)
    found = walk(work_path, "work", item_named=item_named)
    findings += shape_problems(found, work_path, "work", project,
                               unmade_message=UNMADE_MESSAGE)
    findings += length_problems(found.objects, work_path, "work", project)
    for id_path in found.objects:
        entry = work_path / id_path
        if not item_named(id_path.rpartition("/")[2]):
            # Row i: the state file makes it an object, but its name is not
            # one this backend gives an item, so it is no item.
            findings.append(Finding("error", str(entry),
                                    "is not an item folder: its name must be a "
                                    "date, then title words"))
            continue
        try:
            item, raw_stage = _load(entry, project, config.enabled, id_path)
        except Unreadable as error:
            key = f" ({error.key})" if error.key else ""
            findings.append(Finding("error", str(error.path),
                                    f"unreadable{key}: {error.message}"))
            continue
        problem = id_problem(_raw(entry / STATE_FILE), entry.name)
        if problem is not None:
            findings.append(Finding("error", str(entry / STATE_FILE), problem))
        if item.stage is None:
            findings.append(Finding("error", str(entry / STATE_FILE),
                                    f"stage {raw_stage!r} is not an enabled stage, "
                                    f"so the item has no stage; move it with "
                                    f"`tcw work advance --to <stage> --force`"))
        for tag in item.tags:
            if tag not in registered:
                findings.append(Finding("warning", str(entry / STATE_FILE),
                                        f"tag {tag!r} is not in the tag registry"))
    return findings


def _raw(path: Path) -> Any:
    """A state file's mapping as written, or None when it cannot be read
    (its reader has reported why)."""
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return None
