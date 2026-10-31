"""The Jira work backend (TCW-71): Jira owns each item's status, properties,
request and comments, and the work path holds one folder per item for the
technical record.

An item folder is `<KEY>-<title words>`; the key in its name is what ties it
to its ticket. Only `lookup` works without the network.

Every client call goes through `_jira()`, the one place a client error becomes
one of the classes in `tcw/errors.py` (Design 10). Nothing here changes git
state.
"""

from __future__ import annotations

import copy
import os
import re
import sys
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping

import yaml

from tcw.errors import (
    BackendError, MovedWithoutNote, NotFound, Refused, TcwError, Unreachable, UsageError,
)
from tcw.findings import Finding
from tcw.ids import IdError, id_part_problem, is_project_id, length_problem, looks_full
from tcw.output import shown
from tcw.store.base import normalize_tag
from tcw.store.fs import exact_child
from tcw.work.backend import Comment, Query, nesting_parent
from tcw.work.config import WorkConfig
from tcw.object_folders import (UNMADE, id_problem, is_object, length_problems,
                                move_object_folder, object_paths, objects_below, read_state,
                                shape_problems, state_text, walk)
from tcw.project_files import VERSION_KEY, version_line, version_problem
from tcw.rewrite import rewrite_own_id
from tcw.work.fs_backend import STATE_FILE, WORDS
from tcw.work.jira import jql
from tcw.work.jira.client import (
    KEPT_SEARCHES,
    JiraClient, Transition, TrackerAuthError, TrackerError, TrackerNotFound,
    TrackerPermissionError, TrackerRateLimited, TrackerRequestInvalid, TrackerSiteMissing,
    TrackerUnavailable,
)
from tcw.work.jira.config import JiraConfig
from tcw.work.jira.mapping import (
    BLOCKS, Props, block_link, blocker_links, create_fields, document_text,
    normalize_text, read_fields, read_props, scale_name, text_document, write_fields,
)
from tcw.work.layout import Layout
from tcw.work.model import (
    FOLDER_LIMIT, PREFIX_ALLOWANCE, UNSET, Changes, Item, Slug, _as_slug, check_encodable,
    completion_stage, fitted_words,
    discard_stage, stage as table_stage, start_stage, title_words as make_title_words,
    validate_changes,
)

#: A whole Jira key.
KEY = re.compile(r"^[A-Z][A-Z0-9_]*-[1-9][0-9]*$")
#: An item folder in Jira mode: the key, then title words (Design 2.1).
KEY_FOLDER = re.compile(r"^(?P<key>[A-Z][A-Z0-9_]*-[1-9][0-9]*)-[a-z0-9]+(-[a-z0-9]+)*$")

#: The stages whose record Jira keeps: the request is the ticket's description,
#: and QA is done and recorded in Jira (TCW-69 Design 4).
EXTERNAL_STAGES = frozenset(table_stage(name).name for name in ("request", "qa"))

#: How many matching people `Refused` lists for an ambiguous assignee.
SHOWN_MATCHES = 10
#: How many of the newest comments are searched for a note that may have
#: landed (Design 5).
NOTE_WINDOW = 10


def _warn(line: str) -> None:
    print(line, file=sys.stderr)


def three_x_item(value: Any) -> bool:
    """Whether a `TCW Item` value is the 3.x `<project>/<folder>` that
    `tcw migrate` converts (TCW-110 Design 5.2)."""
    if not isinstance(value, str) or looks_full(value):
        return False
    project, slash, folder = value.partition("/")
    return bool(slash) and is_project_id(project) and id_part_problem(folder) is None


def three_x_item_message(value: str) -> str:
    """What a 3.x `TCW Item` value is reported with by `validate --remote`."""
    return (f"TCW Item {value} is a TCW 3.x value; run 'tcw migrate' in this "
            f"project to convert it")


@contextmanager
def _jira() -> Iterator[None]:
    """Turn a client error into the `tcw/errors.py` class Design 10's table
    names. There is no retry, even on 429: exit 5 tells the caller to try again
    later."""
    try:
        yield
    except TrackerUnavailable as error:
        raise Unreachable(f"Jira could not be reached: {error}") from None
    except TrackerRateLimited as error:
        raise Unreachable(f"Jira is limiting requests: {error}") from None
    except TrackerAuthError as error:
        raise BackendError(str(error)) from None
    except TrackerPermissionError as error:
        raise BackendError(str(error)) from None
    except TrackerSiteMissing as error:
        raise BackendError(str(error)) from None
    except TrackerNotFound as error:
        raise NotFound(str(error)) from None
    except TrackerRequestInvalid as error:
        raise BackendError(str(error)) from None
    except TrackerError as error:
        raise BackendError(str(error)) from None


def folder_key(folder: str) -> str | None:
    """The key a Jira-mode item's folder name starts with, or None. Read from
    an id-path's last part, so a nested item's key is its own folder's
    (TCW-111 Design 6.1)."""
    name = folder.rpartition("/")[2] if isinstance(folder, str) else None
    match = KEY_FOLDER.fullmatch(name) if name is not None else None
    return match.group("key") if match else None


def link_exists(work_path: Path, folder: str) -> bool:
    """Whether the id-path `folder` is an item of a Jira-mode project: its
    last part is named for a key, and the walk's rule makes it an object,
    at any depth (TCW-111 Design 5, row 12). The key in the name is
    authoritative, so no read of the ticket is needed, and a work link stays
    offline (R20). A key-named folder with no state file is no item."""
    return folder_key(folder) is not None and is_object(Path(work_path), "work", folder)


#: Row h's message in Jira mode, at the state file: today's message for an
#: item folder whose 3.x state file was missing (TCW-111 Design 2.6).
UNMADE_MESSAGE = "is missing; it holds the ticket's link"


def _key_named(name: str) -> bool:
    return KEY_FOLDER.fullmatch(name) is not None


def jira_store_problems(work_path: Path, jira: JiraConfig, project: str) -> list[Finding]:
    """The offline checks of a Jira-mode work path (Design 9.1): each folder's
    name and state file, keys used twice, and record folders for stages Jira
    keeps. Reads no network."""
    findings: list[Finding] = []
    work_path = Path(work_path)
    if not work_path.is_dir():
        return findings
    # The walk once: the store's shape (rows a to h; a key-named folder with
    # no state file is row h, with today's message), then every item folder
    # at any depth (TCW-111 Design 6.1).
    found = walk(work_path, "work", item_named=_key_named)
    findings += shape_problems(found, work_path, "work", project,
                               unmade_message=UNMADE_MESSAGE)
    findings += length_problems(found.objects, work_path, "work", project)
    by_key: dict[str, list[str]] = {}
    for id_path in found.objects:
        entry = work_path / id_path
        key = folder_key(id_path)
        if key is None:
            # Row i: a folder holding the state file whose name breaks the rule.
            findings.append(Finding("error", str(entry),
                                    "is not a Jira item folder: its name must be the "
                                    "ticket's key, then title words, such as "
                                    "TCW-5-add-export"))
            continue
        by_key.setdefault(key, []).append(id_path)
        findings.extend(_item_file_problems(entry / STATE_FILE, key, jira.site))
        for stage in sorted(EXTERNAL_STAGES):
            if (entry / table_stage(stage).name).is_dir():
                findings.append(Finding("warning", str(entry / stage),
                                        f"Jira keeps the {stage} record, so this "
                                        f"folder is ignored"))
    for key, names in by_key.items():
        if len(names) > 1:
            findings.append(Finding("error", str(work_path),
                                    f"the key {key} names {len(names)} folders: "
                                    f"{', '.join(names)}"))
    return findings


#: The keys a Jira item's state file holds, and the ones it may hold (TCW-111
#: Design 1.2): `parent` and `blocked-by` while they hold a recorded
#: reference (TCW-114 Design 3.3).
STATE_KEYS = frozenset({VERSION_KEY, "ticket"})
OPTIONAL_STATE_KEYS = frozenset({"id", "parent", "blocked-by"})


def _item_file_problems(path: Path, key: str, site: str) -> list[Finding]:
    """The state file must hold exactly `tcw-version` and `ticket:
    <site>/browse/<KEY>`, and may hold `id` (Design 2.2; TCW-111 Design
    1.2). Its version is checked first: a file this TCW cannot read is
    reported for that alone (Design 1.5)."""
    where = str(path)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [Finding("error", where, "is missing; it holds the ticket's link")]
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
        return [Finding("error", where, f"cannot be read: {error}")]
    if isinstance(data, dict) and (problem := version_problem(data, state=True)) is not None:
        return [Finding("error", where, problem)]
    if not isinstance(data, dict) or not STATE_KEYS <= set(data) \
            or set(data) - STATE_KEYS - OPTIONAL_STATE_KEYS:
        extra = sorted(map(str, set(data) - STATE_KEYS - OPTIONAL_STATE_KEYS)) \
            if isinstance(data, dict) else []
        detail = f"; it also has {', '.join(extra)}" if extra else ""
        return [Finding("error", where, f"must hold exactly tcw-version and ticket "
                                        f"(and may hold id, parent and blocked-by)"
                                        f"{detail}")]
    if (problem := id_problem(data, path.parent.name)) is not None:
        return [Finding("error", where, problem)]
    if (problem := _recorded_problem(data)) is not None:
        return [Finding("error", where, problem)]
    url = data["ticket"]
    prefix = f"{site}/browse/"
    if not isinstance(url, str) or not url.startswith(prefix):
        return [Finding("error", where, f"ticket {url!r} is not on {site} "
                                        f"(work.jira.site)")]
    if url[len(prefix):] != key:
        return [Finding("error", where, f"ticket {url!r} names {url[len(prefix):]}, but "
                                        f"the folder's key is {key}")]
    return []


def _recorded_problem(data: dict) -> str | None:
    """What is wrong with the form of a state file's recorded references:
    `parent` one full identifier, `blocked-by` a list of them."""
    from tcw.ids import IdError, parse_stored
    values = []
    if "parent" in data:
        if not isinstance(data["parent"], str):
            return "parent must be one item's full identifier"
        values.append(("parent", data["parent"]))
    if "blocked-by" in data:
        listed = data["blocked-by"]
        if not isinstance(listed, list) or not all(isinstance(v, str) for v in listed):
            return "blocked-by must be a list of items' full identifiers"
        values += [("blocked-by", v) for v in listed]
    for key, value in values:
        try:
            parse_stored(value, "work")
        except IdError as error:
            return f"{key}: {error}"
    return None


def recorded_references(state_path: Path) -> tuple[Slug | None, tuple[Slug, ...]]:
    """The `parent` and `blocked-by` a Jira item's state file records
    (TCW-114 Design 3.3), read from the file alone; a value that is not a
    full identifier is left out, since `tcw validate` reports it."""
    try:
        data, _ = read_state(state_path)
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return None, ()
    if not isinstance(data, dict):
        return None, ()

    def slug(value: Any) -> Slug | None:
        try:
            return Slug.stored(value)
        except (IdError, TypeError, ValueError):
            return None
    parent = slug(data.get("parent")) if data.get("parent") is not None else None
    listed = data.get("blocked-by")
    blocked = tuple(s for v in (listed if isinstance(listed, list) else [])
                    if (s := slug(v)) is not None)
    return parent, blocked


def same_site(a: str, b: str) -> bool:
    """Whether two Jira sites are one: their hosts equal ignoring letter
    case, the scheme and the rest as written (TCW-114 Design 3.3)."""
    from urllib.parse import urlsplit
    one, two = urlsplit(str(a)), urlsplit(str(b))
    return (one.scheme, one.netloc.lower(), one.path.rstrip("/")) == \
        (two.scheme, two.netloc.lower(), two.path.rstrip("/"))


def recorded_problems(backend: "JiraBackend", resolve) -> list[Finding]:
    """`tcw validate`'s offline checks of the references Jira items' state
    files record (TCW-114 Design 3.3): that each names an item, through
    `reference_problems`, as for every work reference; and that it belongs
    in the state file, since a ticket on this site belongs on the ticket."""
    from types import SimpleNamespace
    from tcw.reference_fields import fields_of
    from tcw.work.references import reference_problems
    findings: list[Finding] = []
    triples = []
    places: dict[str, Path] = {}
    for id_path in backend._walked().objects:
        path = backend.work_path / id_path / STATE_FILE
        parent, blocked = recorded_references(path)
        holder = SimpleNamespace(slug=Slug(backend.project, id_path))
        places[str(holder.slug)] = path
        held = {"parent": [parent] if parent else [], "blocked-by": list(blocked)}
        for row in fields_of("jira-item"):
            for ref in held[row.name]:
                triples.append((holder, row.name, ref))
    for problem in reference_problems([], backend.project, resolve, more=[
            t for t in triples if t[2].project != backend.project]):
        findings.append(Finding(problem.level, str(places[str(problem.slug)]),
                                problem.message))
    # Row m (TCW-111 Design 3.2) for a recorded parent: it is in the state
    # file, so the check needs no network (TCW-114 Design 3.3).
    from tcw.object_folders import disagreement, folder_parent
    for holder, name, ref in triples:
        if name != "parent":
            continue
        above = folder_parent(backend.work_path, "work", holder.slug.folder)
        if above is not None and not backend.is_item_folder(above):
            above = None
        if (warning := disagreement(holder.slug, None if above is None
                                    else Slug(backend.project, above), ref)):
            findings.append(Finding("warning", str(places[str(holder.slug)]), warning))
    for holder, name, ref in triples:
        try:
            placed = backend._place(ref, name)
        except TcwError:
            continue                    # reported above, or by its own check
        if isinstance(placed, Linked):
            flag = "--parent" if name == "parent" else "--blocked-by"
            findings.append(Finding(
                "error", str(places[str(holder.slug)]),
                f"{name} {ref} is a ticket on {backend.jira.site}; run tcw work edit "
                f"{holder.slug} {flag} {ref} to make it a Jira link"))
    return findings


def _kept_search(backend: "JiraBackend", text: str, fields) -> list:
    """`list`'s search, made once per command for each search key (TCW-113
    Design 3.5): the site, the account and a digest of the token the
    credentials sign in with, the search text and the fields asked for. A
    later search with the same key in the same command is answered from what
    was kept, as a deep copy, so no caller changes what another is given.
    Outside a command nothing is kept, and a write drops what was
    (`forget_kept_searches`)."""
    from tcw.config import command_state
    state = command_state()
    if state is None:
        return backend.client.search(text, fields)
    key = (*backend.client.account_key(), text, tuple(fields))
    kept = state.setdefault(KEPT_SEARCHES, {})
    if key not in kept:
        kept[key] = backend.client.search(text, fields)
    return copy.deepcopy(kept[key])


def _field(issue: Mapping, field_id: str) -> Any:
    fields = issue.get("fields") if isinstance(issue, Mapping) else None
    return fields.get(field_id) if isinstance(fields, Mapping) else None


def _clash(error: TcwError) -> TcwError:
    """Mark a stop as the clash with another command moving the same item
    (TCW-114 Design 7.3), so its message advises waiting, not a re-run."""
    error.clash = True
    return error


@dataclass(frozen=True)
class Linked:
    """A parent or blocker that is a ticket on this site: a Jira link."""
    key: str


@dataclass(frozen=True)
class Recorded:
    """A parent or blocker Jira cannot link: kept in the state file."""
    full_id: Slug


def _unique(values: Iterable[str]) -> list[str]:
    seen: list[str] = []
    for value in values:
        if value not in seen:
            seen.append(value)
    return seen


def _chunks(values: list[str], size: int) -> Iterator[list[str]]:
    for start in range(0, len(values), size):
        yield values[start:start + size]


def parse_stamp(value: str) -> datetime | None:
    """A Jira timestamp as an aware UTC datetime, or None."""
    for form in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(value, form).astimezone(timezone.utc)
        except (TypeError, ValueError):
            continue
    return None


@dataclass(frozen=True)
class IssueType:
    id: str
    name: str
    level: int
    subtask: bool


@dataclass(frozen=True)
class Metadata:
    """What one command learns about the Jira project, read once (Design 11,
    12): its id, its issue types, the configured issue type, the custom field
    ids by role, whether Priority exists, and the option values of each
    estimate field by scale name."""
    project_id: str
    issue_types: tuple[IssueType, ...]
    issue_type: IssueType
    field_ids: Mapping[str, str]
    has_priority: bool
    options: Mapping[str, Mapping[str, str]]


class JiraBackend:
    external_stages: frozenset[str] = EXTERNAL_STAGES
    inbox_items = False

    def __init__(self, project: str, work_path: Path, config: WorkConfig,
                 jira: JiraConfig, *, client: JiraClient | None = None,
                 report: Callable[[str], None] | None = None,
                 root: Path | None = None):
        self.project = project
        self.root = None if root is None else Path(root)
        self.work_path = Path(work_path)
        self.config = config
        self.jira = jira
        self.client = client or JiraClient(jira)
        self.report = report or _warn
        self.layout = Layout(self.work_path, config.enabled, self.external_stages, "Jira")
        self._metadata: Metadata | None = None
        self._me: Any = _UNREAD
        #: Display names of accounts seen in this command, for `user_name`.
        self.names: dict[str, str] = {}

    # -- configuration ---------------------------------------------------------

    @property
    def enabled(self) -> frozenset[str]:
        return self.config.enabled

    @property
    def statuses(self) -> dict[str, str]:
        """Each enabled stage that has a Jira status, and that status."""
        return {name: self.config.stage(name).status for name in self.enabled
                if self.config.stage(name).status}

    def metadata(self) -> Metadata:
        if self._metadata is None:
            self._metadata = self._read_metadata()
        return self._metadata

    def _read_metadata(self) -> Metadata:
        with _jira():
            try:
                project = self.client.project(self.jira.project)
            except TrackerNotFound:
                # A missing project and a host with no Jira both answer 404
                # here. `/myself` exists on every site, so asking it tells
                # them apart: it raises `TrackerSiteMissing` for the second,
                # and the project's own 404 stands for the first (Design 14).
                self.client.myself()
                raise
        types = tuple(
            IssueType(str(t.get("id")), str(t.get("name")),
                      int(t.get("hierarchyLevel") or 0), bool(t.get("subtask")))
            for t in project.get("issueTypes") or [] if isinstance(t, dict))
        chosen = [t for t in types if t.name == self.jira.issue_type]
        if not chosen:
            raise BackendError(
                f"work.jira.issue-type is {self.jira.issue_type!r}, which is not an "
                f"issue type of Jira project {self.jira.project}; it has "
                f"{', '.join(t.name for t in types) or 'none'}")
        with _jira():
            fields = self.client.create_metadata(self.jira.project, chosen[0].id)
        by_name: dict[str, list[dict]] = {}
        for entry in fields:
            if isinstance(entry, dict):
                by_name.setdefault(str(entry.get("name")), []).append(entry)
        wanted = {"project": self.jira.fields.project, "item": self.jira.fields.item,
                  "effort": self.jira.fields.effort,
                  "complexity": self.jira.fields.complexity}
        field_ids: dict[str, str] = {}
        options: dict[str, dict[str, str]] = {}
        for role, name in wanted.items():
            if name is None:
                continue
            found = by_name.get(name, [])
            if len(found) != 1:
                what = ("no field" if not found else
                        f"{len(found)} fields ({', '.join(str(f.get('fieldId')) for f in found)})")
                raise BackendError(
                    f"work.jira.fields.{role} is {name!r}, but Jira project "
                    f"{self.jira.project} has {what} of that name on the "
                    f"{chosen[0].name} create screen")
            field_ids[role] = field_id(found[0])
            if role in ("effort", "complexity"):
                options[role] = {
                    scale: value["value"]
                    for value in found[0].get("allowedValues") or []
                    if isinstance(value, dict) and isinstance(value.get("value"), str)
                    for scale in [scale_name(value)] if scale}
        has_priority = any(isinstance(f, dict) and field_id(f) == "priority"
                           for f in fields)
        return Metadata(project_id=str(project.get("id")), issue_types=types,
                        issue_type=chosen[0], field_ids=field_ids,
                        has_priority=has_priority, options=options)

    # -- folders ---------------------------------------------------------------

    def is_item_folder(self, folder: str) -> bool:
        return link_exists(self.work_path, folder)

    def _walked(self):
        """The walk of the work path, kept for this backend's life, so
        `resolve_keys`, which asks `lookup` once per key, walks the store once
        per command (TCW-111 spec Risks). Dropped by `_item_file` and `rename`,
        the two methods that make or move a folder."""
        if getattr(self, "_walk_cache", None) is None:
            self._walk_cache = walk(self.work_path, "work", item_named=_key_named)
        return self._walk_cache

    def _forget_walk(self) -> None:
        self._walk_cache = None

    def _key_index(self) -> dict[str, list[str]]:
        """`{key: [id-paths]}` of every item folder, at any depth."""
        index: dict[str, list[str]] = {}
        for id_path in self._walked().objects:
            key = folder_key(id_path)
            if key is not None:
                index.setdefault(key, []).append(id_path)
        return index

    def key_folders(self, key: str) -> list[str]:
        """Every folder the walk met whose last part is named for `key`, with
        a state file or without one (an item, or row h's folder), as
        id-paths, sorted. Only adopt asks this: it can finish a folder an
        interrupted run left without its state file (TCW-111 Design 6.4)."""
        walked = self._walked()
        found = [p for p in walked.objects if folder_key(p) == key]
        found += [p for p, kind, _ in walked.folders
                  if kind == UNMADE and folder_key(p) == key]
        return sorted(found)

    def lookup(self, name: str) -> str | None:
        if not isinstance(name, str):
            return None
        key = name.upper()
        if not KEY.fullmatch(key) or not self.work_path.is_dir():
            return None
        found = sorted(self._key_index().get(key, []))
        if len(found) > 1:
            raise BackendError(f"two folders in {self.work_path} carry the key {key}: "
                               f"{', '.join(found)}; rename or remove one")
        return found[0] if found else None

    def _key(self, folder: str) -> str:
        key = folder_key(folder)
        if key is None or not isinstance(folder, str):
            raise NotFound(f"no work item {Slug(self.project, folder)}")
        if not link_exists(self.work_path, folder):
            # A disk that ignores letter case finds a folder by another
            # spelling; an id-path is compared exactly (TCW-110 Design 1.1).
            spelled = exact_child(self.work_path, folder) if "/" not in folder else False
            if isinstance(spelled, str) and link_exists(self.work_path, spelled):
                raise NotFound(f"no work item {Slug(self.project, folder)} (the "
                               f"folder is spelled {spelled})")
            raise NotFound(f"no work item {Slug(self.project, folder)}")
        return key

    # -- reading -----------------------------------------------------------------

    def read(self, folder: str) -> Item:
        key = self._key(folder)
        issue = self._issue(key, folder, read_fields(self.metadata().field_ids))
        answered = str(issue.get("key") or key)
        if answered != key:
            _warn(f"warning: {Slug(self.project, folder)}: Jira answered for {key} with "
                  f"{answered}; the ticket was moved, so the folder's key is stale")
        return self._items([(Slug(self.project, folder), issue)])[0]

    def _issue(self, key: str, folder: str, fields: Iterable[str]) -> dict:
        try:
            with _jira():
                return self.client.issue(key, tuple(fields))
        except NotFound:
            raise NotFound(f"{Slug(self.project, folder)}: Jira has no ticket {key}, or "
                           f"this account cannot see it") from None

    def _props(self, issue: Mapping) -> Props:
        meta = self.metadata()
        props = read_props(issue, self.jira, meta.field_ids, self.config.tags,
                           self.statuses)
        if props.assignee and props.assignee_name:
            self.names[props.assignee] = props.assignee_name
        return props

    def _items(self, found: list[tuple[Slug, Mapping]]) -> list[Item]:
        """Items for `(slug, issue)` pairs, with every parent and blocker key
        among them resolved together (Design 3.1)."""
        props = [(slug, self._props(issue)) for slug, issue in found]
        keys = _unique(k for _, p in props
                       for k in ((p.parent_key,) if p.parent_key else ()) + p.blocker_keys)
        slugs = self.resolve_keys(keys)
        items = []
        for slug, p in props:
            if p.created is None:
                raise BackendError(f"Jira ticket {p.key} has no readable creation date")
            # The recorded references join the links (TCW-114 Design 3.3).
            noted_parent, noted_blockers = recorded_references(
                self.work_path / slug.folder / STATE_FILE)
            parent = slugs.get(p.parent_key) if p.parent_key else noted_parent
            blocked_by = tuple(_unique([*(slugs[k] for k in p.blocker_keys
                                          if slugs.get(k)), *noted_blockers]))
            untracked = _unique(
                ([p.parent_key] if p.parent_key and parent is None else [])
                + [k for k in p.blocker_keys if not slugs.get(k)])
            items.append(Item(slug=slug, title=p.title, stage=p.stage, created=p.created,
                              priority=p.priority, effort=p.effort,
                              complexity=p.complexity, tags=p.tags, assignee=p.assignee,
                              parent=parent, blocked_by=blocked_by,
                              untracked=tuple(untracked)))
        return items

    def _slug_of(self, value: Any) -> Slug | None:
        """The item a `TCW Item` value names, or None when it names none: a
        3.x or malformed value is never refused here (Design 5.2)."""
        try:
            return Slug.stored(value)
        except IdError:
            return None

    def resolve_keys(self, keys: Iterable[str]) -> dict[str, Slug | None]:
        """Each key's item slug, or None for a ticket with no item (Design
        3.1): a folder here first; then `key in` searches of at most 100; a
        search refused with 400, and any key a search did not return, read
        directly, since a search can lag behind writes."""
        out: dict[str, Slug | None] = {}
        rest = []
        for key in _unique(keys):
            folder = self.lookup(key)
            if folder:
                out[key] = Slug(self.project, folder)
            else:
                rest.append(key)
        if not rest:
            return out
        meta = self.metadata()
        fields = [meta.field_ids["project"], meta.field_ids["item"]]
        returned: dict[str, Mapping] = {}
        for chunk in _chunks(rest, jql.MAX_KEYS):
            with _jira():
                try:
                    found = self.client.search(jql.keys_query(chunk), fields)
                except TrackerRequestInvalid:
                    found = []           # each key is confirmed directly below
            for issue in found:
                returned[str(issue.get("key"))] = issue
        for key in rest:
            if key in returned:
                continue
            try:
                with _jira():
                    returned[key] = self.client.issue(key, tuple(fields))
            except NotFound:
                continue
        for key in rest:
            issue = returned.get(key)
            fields_of = issue.get("fields") if isinstance(issue, Mapping) else None
            value = fields_of.get(meta.field_ids["item"]) if isinstance(fields_of, Mapping) \
                else None
            out[key] = self._slug_of(value)
        return out

    def list(self, query: Query) -> list[Item]:
        labels = None
        if query.tags is not None:
            given = {normalize_tag(t) for t in query.tags}
            labels = sorted(t for t in given if t in self.config.tags)
            if not labels:
                return []
            query = replace(query, tags=frozenset(labels))
        statuses = not_statuses = None
        if query.stages is not None:
            missing = sorted(s for s in query.stages if s not in self.statuses)
            if missing:
                raise UsageError(f"{', '.join(missing)}: no Jira status is configured "
                                 f"for {'this stage' if len(missing) == 1 else 'these stages'}"
                                 f" (it is not enabled)")
            statuses = sorted(self.statuses[s] for s in query.stages)
        elif not query.all:
            not_statuses = [self.statuses[s] for s in (completion_stage(), discard_stage())
                            if s in self.statuses]
        parent = None
        if query.parent is not None:
            # A ticket on this site is asked of Jira; anything else is
            # recorded, so it is found among the search's items by
            # `query.matches` (TCW-114 Design 3.3).
            if query.parent.project == self.project:
                parent = folder_key(query.parent.folder)
                if parent is None:
                    return []
            else:
                placed = self._place(query.parent, "parent")
                parent = placed.key if isinstance(placed, Linked) else None
        assignee = None
        if query.assignee is not None:
            assignee = self.account(query.assignee)
            query = replace(query, assignee=assignee)
        meta = self.metadata()
        text = jql.item_query(self.jira.project, meta.field_ids["item"],
                              statuses=statuses, not_statuses=not_statuses,
                              parent=parent, assignee=assignee, labels=labels)
        with _jira():
            issues = _kept_search(self, text, read_fields(meta.field_ids))
        found = []
        three_x = []
        for issue in issues:
            fields = issue.get("fields") if isinstance(issue.get("fields"), dict) else {}
            if fields.get(meta.field_ids["project"]) != self.project:
                continue
            value = fields.get(meta.field_ids["item"])
            if three_x_item(value):
                three_x.append(str(issue.get("key")))
                continue
            slug = self._slug_of(value)
            if slug is None or slug.project != self.project \
                    or not self.is_item_folder(slug.folder):
                _warn(f"warning: Jira ticket {issue.get('key')} names the item "
                      f"{value!r}, whose folder is not in {self.work_path}; it is "
                      f"left out (it may exist in another copy of this "
                      f"repository)")
                continue
            found.append((slug, issue))
        if three_x:
            many = len(three_x) != 1
            _warn(f"warning: {len(three_x)} Jira ticket{'s' if many else ''} of this "
                  f"project {'hold' if many else 'holds'} a TCW 3.x TCW Item value and "
                  f"{'are' if many else 'is'} left out ({', '.join(three_x)}); run "
                  f"'tcw migrate' in this project to convert "
                  f"{'them' if many else 'it'}")
        return [item for item in self._items(found) if query.matches(item)]

    def read_request(self, folder: str) -> str | None:
        key = self._key(folder)
        issue = self._issue(key, folder, ("description",))
        fields = issue.get("fields") if isinstance(issue.get("fields"), dict) else {}
        text = document_text(fields.get("description"))
        return text if text.strip() else None

    def read_comments(self, folder: str, limit: int | None = None) -> list[Comment]:
        key = self._key(folder)
        try:
            with _jira():
                found = self.client.comments(key, limit)
        except NotFound:
            raise NotFound(f"{Slug(self.project, folder)}: Jira has no ticket {key}, or "
                           f"this account cannot see it") from None
        comments = []
        for entry in found:
            at = parse_stamp(entry.created)
            if at is None:
                raise BackendError(f"a comment on {key} has no readable time: "
                                   f"{entry.created!r}")
            if entry.author_id and entry.author_name:
                self.names[entry.author_id] = entry.author_name
            comments.append(Comment(at, entry.author_id, document_text(entry.body)))
        return comments

    # -- people ------------------------------------------------------------------

    def current_user(self) -> str | None:
        """The account the credentials belong to; None without a request when
        either variable is unset (R3). Jira failing to answer is not "no
        identity": it raises as for any other operation, `Unreachable` when
        Jira cannot be reached and `BackendError` with Jira's reason otherwise
        (TCW-72 review finding C5). Read at most once."""
        if self._me is not _UNREAD:
            return self._me
        unset = [name for name in (self.jira.email_env, self.jira.token_env)
                 if not os.environ.get(name, "").strip()]
        if unset:
            self._me = None
            return None
        with _jira():
            try:
                me = self.client.myself()
            except TrackerAuthError as error:
                raise BackendError(f"Jira rejected the credentials in "
                                   f"{self.jira.email_env} and "
                                   f"{self.jira.token_env}: {error}") from None
        account = me.get("accountId") if isinstance(me, dict) else None
        self._me = account if isinstance(account, str) and account else None
        if self._me and isinstance(me.get("displayName"), str):
            self.names[self._me] = me["displayName"]
        return self._me

    def account(self, value: str) -> str:
        """An assignee given as an account id or a name to search for, as an
        account id (Design 4.2): exactly one match is used."""
        with _jira():
            try:
                user = self.client.user(value)
            except (TrackerNotFound, TrackerRequestInvalid):
                user = None
        if isinstance(user, dict) and user.get("accountId") == value:
            if isinstance(user.get("displayName"), str):
                self.names[value] = user["displayName"]
            return value
        with _jira():
            found = self.client.assignable_users(self.jira.project, value,
                                                 SHOWN_MATCHES + 1)
        found = [u for u in found if isinstance(u, dict) and u.get("accountId")]
        if not found:
            raise NotFound(f"no one assignable in Jira project {self.jira.project} "
                           f"matches {value!r}")
        if len(found) > 1:
            listed = ", ".join(f"{u.get('displayName')} ({u['accountId']})"
                               for u in found[:SHOWN_MATCHES])
            more = " and more" if len(found) > SHOWN_MATCHES else ""
            raise Refused(f"{value!r} matches several people in Jira project "
                          f"{self.jira.project}: {listed}{more}; give one account id")
        if isinstance(found[0].get("displayName"), str):
            self.names[found[0]["accountId"]] = found[0]["displayName"]
        return str(found[0]["accountId"])

    # -- resolving what a write names --------------------------------------------

    def _other(self, project_id: str):
        """Another project's backend; None when this backend was built without
        a project root to find it from."""
        if self.root is None:
            return None
        from tcw.work.open import open_project
        return open_project(project_id, self.root)

    def _place(self, value: Any, what: str) -> "Linked | Recorded":
        """Where a parent or blocker goes (TCW-114 Design 3.3): a ticket on
        this site is a Jira link; anything else is recorded in the item's
        state file. Decided without the network: the named item's project
        is located and its configuration read. A project that cannot be
        located stops the write with that outcome (exit 5 or 1), and one
        whose `work.jira` is undecided with exit 7, before anything is
        written."""
        slug = _as_slug(value, self.project, what)
        if slug.project == self.project:
            if folder_key(slug.folder) is None:
                raise Refused(f"{what} {slug} is not a Jira ticket of this project: its "
                              f"folder name holds no ticket key")
            return Linked(self._key(slug.folder))
        if self.root is None:
            raise Refused(f"{what} {slug} cannot be placed: this backend was opened "
                          f"with no project to find '{slug.project}' from")
        other = self._other(slug.project)
        if isinstance(other, JiraBackend) and same_site(other.jira.site, self.jira.site) \
                and folder_key(slug.folder) is not None:
            return Linked(other._key(slug.folder))
        return Recorded(slug)

    def _recorded_note(self, item: Slug, what: str, value: Slug) -> str:
        noun = "parent" if what == "parent" else "blocker"
        return (f"{item}'s {noun} {value} is not a ticket on {self.jira.site}, so it "
                f"is recorded in {shown(self.work_path / item.folder / STATE_FILE)} "
                f"and Jira shows no link for it")

    def _type_of(self, issue: Mapping) -> tuple[int, str]:
        kind = issue.get("fields", {}).get("issuetype") if isinstance(
            issue.get("fields"), dict) else None
        if not isinstance(kind, dict) or not isinstance(kind.get("hierarchyLevel"), int):
            raise BackendError(f"Jira did not say where {issue.get('key')} sits in "
                               f"the issue hierarchy")
        return kind["hierarchyLevel"], str(kind.get("name"))

    def child_issue_type(self, parent_key: str, level: int, type_name: str) -> IssueType:
        """The issue type of a new child of a ticket at `level` (Design 11)."""
        meta = self.metadata()
        target = level - 1
        if target == 0:
            return meta.issue_type
        if target == -1:
            found = [t for t in meta.issue_types if t.subtask]
        elif target >= 1:
            found = [t for t in meta.issue_types if t.level == target]
        else:
            raise Refused(f"{parent_key} is a {type_name}; Jira gives that type no "
                          f"children")
        if len(found) != 1:
            raise Refused(f"{parent_key} is a {type_name}, and Jira project "
                          f"{self.jira.project} has no single issue type to put under "
                          f"it ({len(found)} found)")
        return found[0]

    def _parent_level(self, key: str) -> tuple[int, str]:
        """A parent ticket's hierarchy level and type name."""
        with _jira():
            issue = self.client.issue(key, ("issuetype",))
        return self._type_of(issue)

    def _validate(self, changes: Changes, item_slug: Slug | None) -> None:
        # Jira's hierarchy puts every parent one level above its child, so a
        # chain of parents cannot loop and there is no cycle to walk for.
        validate_changes(changes, item_slug=item_slug, registered_tags=self.config.tags,
                         current_project=self.project, parent_of=lambda slug: None)

    def _check_priority(self, changes: Changes) -> None:
        if changes.priority not in (UNSET, None) and not self.metadata().has_priority:
            raise Refused(f"Jira project {self.jira.project} has no Priority field, so "
                          f"an item there has no priority to set")

    @staticmethod
    def _normalized(changes: Changes) -> Changes:
        return replace(changes, add_tags=tuple(normalize_tag(t) for t in changes.add_tags),
                       remove_tags=tuple(normalize_tag(t) for t in changes.remove_tags))

    def _item_file(self, folder: str, key: str, *, resume: bool = False,
                   parent: Slug | None = None, blocked_by: Iterable[Slug] = ()) -> None:
        """Make the folder and its state file, with the recorded `parent`
        and `blocked-by` when given (TCW-114 Design 3.3). `resume` finishes
        a folder an interrupted run made, and refuses nothing when it
        exists."""
        path = self.work_path / folder
        self._forget_walk()
        if not (resume and path.is_dir()):
            path.mkdir(parents=True)
            self.report(f"created {shown(path)}/")
        document = path / STATE_FILE
        recorded = ({"parent": str(parent)} if parent is not None else {}) | \
            ({"blocked-by": [str(s) for s in blocked_by]} if blocked_by else {})
        text = f"{version_line()}ticket: {self.jira.site}/browse/{key}\n"
        if recorded:
            text += yaml.safe_dump(recorded, sort_keys=False, allow_unicode=True)
        document.write_text(text, encoding="utf-8")
        self.report(f"wrote {shown(document)}")

    def _record(self, folder: str, *, parent: Any = UNSET,
                add: Iterable[Slug] = (), remove: Iterable[Slug] = ()) -> None:
        """Change the recorded references in an existing item's state file,
        replacing only the keys that change: `parent` a full identifier, or
        None to remove it; `add` and `remove` change `blocked-by`."""
        document = self.work_path / folder / STATE_FILE
        data, problem = read_state(document)
        if problem is not None or not isinstance(data, dict):
            raise BackendError(f"{shown(document)} cannot be read: {problem}")
        changed = dict(data)
        if parent is None:
            changed.pop("parent", None)
        elif parent is not UNSET:
            changed["parent"] = str(parent)
        listed = [v for v in changed.get("blocked-by") or []
                  if v not in {str(s) for s in remove}]
        listed += [str(s) for s in add if str(s) not in listed]
        if listed:
            changed["blocked-by"] = listed
        else:
            changed.pop("blocked-by", None)
        if changed != data:
            document.write_text(state_text(document, changed), encoding="utf-8")
            self.report(f"wrote {shown(document)}")

    # -- create (Design 4.1) -------------------------------------------------------

    def create(self, title: str, props: Changes, *, stage: str,
               request: str | None, nest: bool = False) -> Item:
        if not isinstance(title, str) or not title.strip():
            raise UsageError("a title must not be empty")
        table_stage(stage)
        if stage != start_stage():
            raise UsageError(f"a Jira item is created at {start_stage()}, not {stage}")
        if request is not None:
            check_encodable(request, "the request")
        props = self._normalized(props)
        self._validate(replace(props, title=title), None)
        meta = self.metadata()
        # 1. Resolve, reading only.
        self._check_priority(props)
        issue_type, parent_key, under, note = meta.issue_type, None, None, None
        noted_parent: Slug | None = None
        if props.parent not in (UNSET, None):
            placed = self._place(props.parent, "parent")
            if isinstance(placed, Linked):
                parent_key = placed.key
                level, type_name = self._parent_level(parent_key)
                issue_type = self.child_issue_type(parent_key, level, type_name)
            else:
                # The project's default issue type, as with no parent: the
                # level a child needs is this site's (TCW-114 Design 3.3).
                noted_parent = placed.full_id
            under, note = nesting_parent(
                self, _as_slug(props.parent, self.project, "parent"), nest)
        # Before the ticket exists, at the longest key allowed for: refused
        # here, nothing has been made (TCW-111 Design 4.3).
        fitted_words(title, project=self.project, parent=under, prefix=PREFIX_ALLOWANCE)
        assignee = (self.account(props.assignee)
                    if props.assignee not in (UNSET, None) else None)
        placed_blockers = [self._place(b, "blocked-by") for b in props.add_blocked_by]
        blockers = _unique(p.key for p in placed_blockers if isinstance(p, Linked))
        noted_blockers = _unique(p.full_id for p in placed_blockers
                                 if isinstance(p, Recorded))
        # 2. Create the ticket.
        fields = create_fields(title, props, request, config=self.jira,
                               field_ids=meta.field_ids, project_id=self.project,
                               issue_type=issue_type.id, has_priority=meta.has_priority,
                               assignee=assignee, parent=parent_key, options=meta.options)
        with _jira():
            try:
                created = self.client.create_issue(fields)
            except TrackerRequestInvalid as error:
                hint = (" A parent in another Jira project may not be allowed by "
                        "this project's type." if parent_key and
                        not parent_key.startswith(self.jira.project + "-") else "")
                raise BackendError(f"Jira refused to create the ticket: {error}.{hint}") \
                    from None
        key = created.get("key") if isinstance(created, dict) else None
        if not isinstance(key, str) or not KEY.fullmatch(key):
            raise BackendError("Jira's answer to the create request names no ticket key; "
                               "a ticket may have been created: look for it in Jira")
        # After it exists, cut to the room this key leaves, never refused.
        words = fitted_words(title, project=self.project, parent=under,
                             prefix=len(key) + 1, refuse=False)
        if words is None:
            raise _named(BackendError(
                f"created Jira ticket {key}, but the key leaves no room for title "
                f"words under {Slug(self.project, under)}, since no full identifier is "
                f"longer than 255; finish with `tcw work tickets adopt {key}`"), key)
        name = f"{key}-{words}"
        folder = f"{under}/{name}" if under else name
        slug = Slug(self.project, folder)
        request_status = self.statuses[start_stage()]
        # 3. Check the route to the request status.
        try:
            chosen = self._route(key, request_status)
        except TcwError as error:
            error.name = key
            raise
        if isinstance(chosen, Refusal):
            raise Refused(f"created Jira ticket {key}, but {chosen.message}; it is left "
                          f"as an ordinary ticket with no item", name=key)
        # 4. Set TCW Item.
        try:
            with _jira():
                self.client.edit_issue(key, {meta.field_ids["item"]: str(slug)})
        except TcwError as error:
            raise _named(BackendError(
                f"created Jira ticket {key}, but could not set its TCW Item: {error}; "
                f"finish with `tcw work tickets adopt {key}`"), key) from None
        # 5. Write the folder and its state file.
        try:
            self._item_file(folder, key, parent=noted_parent, blocked_by=noted_blockers)
        except OSError as error:
            again = "".join([*([f" --parent {noted_parent}"] if noted_parent else []),
                             *(f" --blocked-by {b}" for b in noted_blockers)])
            then = (f", then set again what Jira cannot link with `tcw work edit "
                    f"{slug}{again}`" if again else "")
            raise _named(BackendError(
                f"created Jira ticket {key} naming {slug}, but could not write its "
                f"folder: {error}; finish with `tcw work tickets adopt {key}`{then}"),
                key) from None
        if note:
            # Once the folder is made, so it never names one that is not.
            self.report(note)
        for what, values in (("parent", [noted_parent] if noted_parent else []),
                             ("blocked-by", noted_blockers)):
            for value in values:
                self.report(self._recorded_note(slug, what, value))
        # 6. Apply the transition.
        if chosen is not None:
            self._enter_request(key, slug, chosen)
        # 7. Create the Blocks links.
        made, failed = self._add_links(key, blockers)
        if failed:
            raise _named(BackendError(
                f"created {slug} at {start_stage()}, but not all its blocked-by links: "
                f"{_link_report(made, failed)}; finish with `tcw work edit {slug} "
                f"--blocked-by …`"), str(slug))
        # The item exists by now, so a failed read-back still names it (Design
        # 1.8): without the name a retry would make a second ticket.
        try:
            return self.read(folder)
        except TcwError as error:
            raise _named(type(error)(f"created {slug}, but could not read it back: "
                                     f"{error}; check it with `tcw work show {slug}`"),
                         str(slug)) from None

    def _route(self, key: str, status: str) -> Transition | Refusal | None:
        """None when `key` is already at `status`; else the transition the
        choice rule picks, or why it picks none."""
        with _jira():
            if self._status(key) == status:
                return None
            return choose_transition(self.client.transitions(key), status)

    def _status(self, key: str) -> str | None:
        issue = self.client.issue(key, ("status",))
        status = issue.get("fields", {}).get("status") if isinstance(
            issue.get("fields"), dict) else None
        return status.get("name") if isinstance(status, dict) else None

    def _enter_request(self, key: str, slug: Slug, chosen: Transition) -> None:
        stage = start_stage()
        # The first status may map to no stage, and a move from no stage
        # needs --force and a reason (advance's direction check).
        finish = (f"`tcw work advance {slug} --to {stage} --force --reason "
                  f"\"<why>\"`")
        try:
            self.client.apply_transition(key, chosen.id)
        except TrackerRequestInvalid as error:
            raise _named(BackendError(
                f"created {slug}, but Jira refused to move it to {stage}: {error}; it "
                f"is at the workflow's first status. Fix the workflow, then run "
                f"{finish}"), str(slug)) from None
        except (TrackerUnavailable, TrackerRateLimited) as error:
            raise _named(Unreachable(
                f"created {slug}, but moving it to {stage} did not complete: {error}; "
                f"check it with `tcw work show {slug}`, then run {finish}"),
                str(slug)) from None
        except TrackerError as error:
            try:
                with _jira():
                    raise error
            except TcwError as mapped:
                raise _named(type(mapped)(
                    f"created {slug}, but could not move it to {stage}: {mapped}; "
                    f"then run {finish}"), str(slug)) from None
        try:
            with _jira():
                status = self._status(key)
        except TcwError as error:
            raise _named(type(error)(f"created {slug}, but its status cannot be read "
                                     f"back: {error}"), str(slug)) from None
        if status != self.statuses[stage]:
            raise _named(BackendError(
                f"created {slug}, but Jira reports it at {status!r}, not "
                f"{self.statuses[stage]!r}; run {finish}"), str(slug))

    # -- update (Design 4.2) -----------------------------------------------------------

    def update(self, folder: str, changes: Changes) -> Item:
        key = self._key(folder)
        slug = Slug(self.project, folder)
        changes = self._normalized(changes)
        self._validate(changes, slug)
        meta = self.metadata()
        self._check_priority(changes)
        issue = self._issue(key, folder, read_fields(meta.field_ids))
        # Each value to its place, Jira first (TCW-114 Design 3.3): `parent`
        # is the Jira field's change, `noted` the state file's.
        parent: Any = UNSET
        noted: Any = UNSET
        if changes.parent is None:
            parent = noted = None
        elif changes.parent is not UNSET:
            placed = self._place(changes.parent, "parent")
            if isinstance(placed, Linked):
                parent, noted = placed.key, None
                level, type_name = self._parent_level(parent)
                own_level, own_name = self._type_of(issue)
                if level != own_level + 1:
                    raise Refused(f"{key} is a {own_name}, which cannot sit under "
                                  f"{parent}, a {type_name}; Jira cannot change an "
                                  f"issue's type here")
            else:
                noted = placed.full_id
                if self._props(issue).parent_key:
                    parent = None          # the Jira parent goes first
        assignee: Any = UNSET
        if changes.assignee is None:
            assignee = None
        elif changes.assignee is not UNSET:
            assignee = self.account(changes.assignee)
        _, recorded_now = recorded_references(self.work_path / folder / STATE_FILE)
        adding = [self._place(b, "blocked-by") for b in changes.add_blocked_by]
        add = _unique(p.key for p in adding if isinstance(p, Linked))
        note_add = _unique(p.full_id for p in adding if isinstance(p, Recorded))
        # A recorded blocker is taken off the state file without being placed.
        dropping = [_as_slug(b, self.project, "blocked-by")
                    for b in changes.remove_blocked_by]
        note_remove = [s for s in dropping if s in recorded_now]
        remove = _unique(placed.key for s in dropping if s not in recorded_now
                         if isinstance(placed := self._place(s, "blocked-by"), Linked))
        fields, update = write_fields(changes, self.jira, meta.field_ids,
                                      assignee=assignee, parent=parent,
                                      options=meta.options)
        if fields or update:
            with _jira():
                try:
                    self.client.edit_issue(key, fields or None, update or None)
                except TrackerRequestInvalid as error:
                    hint = (" A parent in another Jira project may not be allowed by "
                            "this project's type." if isinstance(parent, str)
                            and not parent.startswith(self.jira.project + "-") else "")
                    raise BackendError(f"Jira refused the edit of {slug}: {error}."
                                       f"{hint}") from None
        current = blocker_links(issue.get("fields", {}).get("issuelinks"))
        made, failed = self._add_links(key, [k for k in add if k not in current])
        for blocker in remove:
            link = current.get(blocker)
            if link is None:
                continue
            try:
                self.client.delete_link(link)
                made.append(f"removed {blocker}")
            except TrackerError as error:
                failed.append(f"remove {blocker} ({error})")
        if failed:
            saved = "the fields were saved" if fields or update else "no field changed"
            raise BackendError(f"{slug}: {saved}, but not every blocked-by link: "
                               f"{_link_report(made, failed)}; running the same edit "
                               f"again is safe")
        # Then the state file, once Jira is written: a stop between the two
        # is finished by the same command again.
        if noted is not UNSET or note_add or note_remove:
            self._record(folder, parent=noted, add=note_add, remove=note_remove)
            for what, values in (("parent", [noted] if isinstance(noted, Slug) else []),
                                 ("blocked-by", note_add)):
                for value in values:
                    self.report(self._recorded_note(slug, what, value))
        return self.read(folder)

    def _add_links(self, key: str, blockers: Iterable[str]) -> tuple[list[str], list[str]]:
        made: list[str] = []
        failed: list[str] = []
        for blocker in blockers:
            try:
                self.client.add_link(BLOCKS, *block_link(blocker, key))
                made.append(f"added {blocker}")
            except TrackerError as error:
                failed.append(f"add {blocker} ({error})")
        return made, failed

    # -- comment and rename (Design 4.3, 4.4) ---------------------------------------------

    def comment(self, folder: str, text: str) -> None:
        key = self._key(folder)
        if not isinstance(text, str) or not text.strip():
            raise UsageError("a comment must not be empty")
        check_encodable(text, "the comment")
        with _jira():
            self.client.add_comment(key, text_document(text))

    def move(self, folder: str, new_folder: str,
             before_folder: Callable[[], object]) -> list[tuple[Slug, Slug]]:
        """Give the item, and every item nested in its folder, a new id-path
        (TCW-114 Design 7.3): every moved ticket is read, and the move
        refused before any change when one holds a value that is neither
        the old nor the new identifier; then each ticket's `TCW Item` is
        set, the item's first, each read again just before its edit; then
        the item's own `id`; then `before_folder`; the folder moves last.
        Nothing is set back: running the same command again finishes it."""
        key = self._key(folder)
        self._forget_walk()
        new_last = new_folder.rpartition("/")[2]
        if folder_key(new_folder) != key:
            raise UsageError(f"a move keeps the key {key}; {new_last!r} does not")
        moved = [folder, *(p for p in objects_below(self.work_path, "work", folder)
                           if folder_key(p))]
        pairs = [(Slug(self.project, p), Slug(self.project, new_folder + p[len(folder):]))
                 for p in moved]
        keys = [folder_key(p) for p in moved]
        item_field = self.metadata().field_ids["item"]
        # 1. Read every moved ticket, writing nothing.
        returned: dict[str, Mapping] = {}
        for chunk in _chunks(keys, jql.MAX_KEYS):
            with _jira():
                for issue in self.client.search(jql.keys_query(chunk), [item_field]):
                    returned[str(issue.get("key"))] = issue
        to_set: list[int] = []
        three_x: list[str] = []
        for index, (key_, (old, new)) in enumerate(zip(keys, pairs)):
            issue = returned.get(key_)
            if issue is None:
                raise NotFound(f"{old}: Jira has no ticket {key_}, or this account "
                               f"cannot see it")
            value = _field(issue, item_field)
            if value == str(old):
                to_set.append(index)
            elif value == str(new):
                self.report(f"{key_}'s TCW Item already names {new}")
            elif three_x_item(value):
                three_x.append(key_)
            else:
                raise Refused(f"{key_}'s TCW Item is {value!r}, not {old}; run "
                              f"`tcw validate --remote` to see what it names")
        if three_x:
            raise Refused(f"{', '.join(three_x)} still "
                          f"{'hold' if len(three_x) > 1 else 'holds'} a TCW 3.x TCW "
                          f"Item; run 'tcw migrate' in this project first")
        # 2. Set each, read again just before its edit.
        self._set_items(keys, pairs, to_set, item_field)
        # 3. The item's own `id`, then the repository, then the folder.
        old_last = folder.rpartition("/")[2]
        if new_last != old_last:
            document = self.work_path / folder / STATE_FILE
            text = document.read_text(encoding="utf-8")
            new_text, own = rewrite_own_id(text, old_last, new_last)
            if own == "changed":
                try:
                    document.write_text(new_text, encoding="utf-8")
                except OSError as error:
                    raise BackendError(f"could not write {shown(document)}: "
                                       f"{error}") from None
                self.report(f"wrote {shown(document)}: id {old_last} -> {new_last}")
        before_folder()
        old_path, new_path = self.work_path / folder, self.work_path / new_folder
        try:
            created = move_object_folder(self.work_path, folder, new_folder)
        except OSError as error:
            raise BackendError(f"could not move {shown(old_path)} to "
                               f"{shown(new_path)}: {error}") from None
        finally:
            self._forget_walk()
        for rel in created:
            self.report(f"created {shown(self.work_path / rel)}/")
        self.report(f"moved {shown(old_path)} to {shown(new_path)}")
        return pairs

    def _set_items(self, keys: list[str], pairs, to_set: list[int],
                   item_field: str) -> None:
        """Set each moved ticket's `TCW Item`, the item's first (Design 7.3
        step 2). A stop names, as `pending`, the tickets still to be set."""
        for done, index in enumerate(to_set):
            try:
                self._set_item(keys[index], *pairs[index], item_field)
            except TcwError as error:
                error.pending = [keys[i] for i in to_set[done:]]
                raise

    def _set_item(self, key_: str, old: Slug, new: Slug, item_field: str) -> None:
        """One ticket, read again just before its edit: set only while it
        still holds the old value."""
        try:
            with _jira():
                issue = self.client.issue(key_, (item_field,))
        except NotFound:
            raise NotFound(f"{old}: Jira has no ticket {key_}, or this account "
                           f"cannot see it") from None
        value = _field(issue, item_field)
        if value == str(new):
            self.report(f"{key_}'s TCW Item already names {new}")
            return
        if value != str(old):
            raise _clash(Refused(f"{key_}'s TCW Item is now {value}: another "
                                 f"command may be moving this item"))
        with _jira():
            self.client.edit_issue(key_, {item_field: str(new)})
        self.report(f"set {key_}'s TCW Item to {new}")

    # -- tcw migrate's two calls (TCW-116 Design 5.4) ---------------------------------

    def item_values(self) -> list[tuple[str, Any, Any]]:
        """Every ticket of the Jira project that carries a `TCW Item`, as
        `(key, TCW Project value, TCW Item value)`, by one paged search with
        no status filter. Used only by `tcw migrate`, while it plans; not one
        of the twelve operations. Reads only `self.jira`, `self.client` and
        the field ids `metadata()` finds, never `self.config` or
        `self.layout`, so the work section the backend was built with does
        not change what it finds."""
        ids = self.metadata().field_ids
        text = jql.item_query(self.jira.project, ids["item"])
        with _jira():
            issues = self.client.search(text, [ids["project"], ids["item"]])
        return [(str(issue.get("key")), _field(issue, ids["project"]),
                 _field(issue, ids["item"])) for issue in issues]

    def set_item_values(self, pairs: Iterable[tuple[str, str, str]], *,
                        edited: Callable[[str], None] | None = None) -> None:
        """For each `(key, old, new)`, set the ticket's `TCW Item` to `new`
        when it still holds `old`, by the edit `move` sends; one already
        holding `new` is done. Every ticket is tried; `edited` is told each
        key edited. Then, when any is left, raises `Unreachable` if any
        attempt could not reach Jira, else `BackendError`, each naming the
        tickets left as `pending`. Swapping each pair's values puts the old
        ones back. Used only by `tcw migrate`; not one of the twelve
        operations, and like `item_values` it never reads `self.config`."""
        pairs = list(pairs)
        if not pairs:
            return
        item_field = self.metadata().field_ids["item"]
        left: list[str] = []
        reasons: list[str] = []
        unreachable = False
        for key_, old, new in pairs:
            try:
                with _jira():
                    value = _field(self.client.issue(key_, (item_field,)), item_field)
                    if value == new:
                        continue
                    if value != old:
                        left.append(key_)
                        reasons.append(f"{key_}'s TCW Item is {value!r}, not {old}")
                        continue
                    self.client.edit_issue(key_, {item_field: new})
            except Unreachable as error:
                unreachable = True
                left.append(key_)
                reasons.append(f"{key_}: {error}")
                continue
            except TcwError as error:
                left.append(key_)
                reasons.append(f"{key_}: {error}")
                continue
            if edited is not None:
                edited(key_)
        if left:
            kind = Unreachable if unreachable else BackendError
            error = kind(f"the TCW Item of {', '.join(left)} was not set: "
                         f"{'; '.join(reasons)}")
            error.pending = left
            raise error

    # -- set_stage (Design 5) --------------------------------------------------------------

    def set_stage(self, folder: str, stage: str, note: str | None) -> str | None:
        key = self._key(folder)
        slug = Slug(self.project, folder)
        table_stage(stage)
        status = self.statuses.get(stage)
        if status is None:
            raise UsageError(f"stage {stage} has no Jira status in this project")
        with _jira():
            offered = self.client.transitions(key)
        chosen = choose_transition(offered, status)
        if isinstance(chosen, Refusal):
            raise Refused(f"cannot move {slug} to {stage}: {chosen.message}")
        document = text_document(note) if note is not None and note.strip() else None
        # Jira answers 204 to a comment sent with a transition that has no screen
        # and discards it, so there the note is posted after the move (Design 5
        # step 3, a live finding).
        separate = document is not None and not chosen.has_screen
        # The comments already there, so that after a dropped connection only a
        # comment that arrived since can count as this note: an older one with
        # the same words (the same move, made before) must not hide a lost note.
        before = self._comment_ids(key) if document is not None else frozenset()
        try:
            self.client.apply_transition(key, chosen.id, None if separate else document)
        except TrackerRequestInvalid as error:
            return self._after_refusal(key, slug, stage, status, chosen, note, document,
                                       error, before, separate=separate)
        except TrackerUnavailable as error:
            moved = self._after_drop(key, slug, stage, status,
                                     None if separate else note,
                                     None if separate else document, error, before)
            if separate:
                self._post_note(key, slug, stage, note, before)
            return moved
        except TrackerError:
            with _jira():
                raise
        if separate:
            self._post_note(key, slug, stage, note, before)
        return self._stage_now(key)

    def _stage_now(self, key: str) -> str | None:
        with _jira():
            status = self._status(key)
        return {name: stage for stage, name in self.statuses.items()}.get(status)

    def _comment_ids(self, key: str) -> frozenset[str]:
        with _jira():
            return frozenset(c.id for c in self.client.comments(key, NOTE_WINDOW)
                             if c.id is not None)

    def _note_found(self, key: str, note: str, before: frozenset[str]) -> bool:
        """Whether a comment with the note's text arrived since `before` was read."""
        wanted = normalize_text(note)
        return any(c.id is not None and c.id not in before
                   and normalize_text(document_text(c.body)) == wanted
                   for c in self.client.comments(key, NOTE_WINDOW))

    def _post_note(self, key: str, slug: Slug, stage: str, note: str,
                   before: frozenset[str]) -> None:
        try:
            self.client.add_comment(key, text_document(note))
        except TrackerUnavailable as error:
            # The connection failed, so Jira may have the comment already:
            # look before suggesting it be added again (Design 1).
            try:
                found = self._note_found(key, note, before)
            except TrackerError:
                raise MovedWithoutNote(
                    f"{slug} moved to {stage}, but the connection failed while "
                    f"posting the note ({error}) and its comments cannot be read "
                    f"now; the note may have been posted: read the comments with "
                    f"`tcw work show {slug}` before adding it",
                    uncertain=True) from None
            if not found:
                raise MovedWithoutNote(f"{slug} moved to {stage}, but posting the "
                                       f"note failed: {error}") from None
        except TrackerError as error:
            raise MovedWithoutNote(f"{slug} moved to {stage}, but posting the note "
                                   f"failed: {error}") from None

    def _after_refusal(self, key, slug, stage, status, chosen, note, document,
                       error, before, *, separate: bool = False) -> str | None:
        """Jira answered 400. Its text is never read to decide what happened;
        the status is (Design 5)."""
        with _jira():
            current = self._status(key)
        if current == status:
            # Someone else made the move first, or Jira refused only the comment.
            # A note meant to go separately was never sent, so a matching
            # comment can only be someone else's: post it without looking.
            if document is not None:
                try:
                    found = not separate and self._note_found(key, note, before)
                except TrackerError:
                    found = False
                if not found:
                    self._post_note(key, slug, stage, note, before)
            return stage
        if document is None:
            raise Refused(_refusal_text(slug, stage, chosen, error))
        try:
            self.client.apply_transition(key, chosen.id)
        except TrackerRequestInvalid as again:
            raise Refused(_refusal_text(slug, stage, chosen, again)) from None
        except TrackerUnavailable as again:
            # The retry carried no comment, so posting the note cannot repeat it.
            moved = self._after_drop(key, slug, stage, status, None, None, again,
                                     before)
            self._post_note(key, slug, stage, note, before)
            return moved
        except TrackerError:
            with _jira():
                raise
        self._post_note(key, slug, stage, note, before)
        return self._stage_now(key)

    def _after_drop(self, key, slug, stage, status, note, document, error,
                    before) -> str | None:
        """The connection failed mid-request, which may have landed."""
        try:
            current = self._status(key)
        except TrackerError:
            raise Unreachable(f"the connection to Jira failed while moving {slug} to "
                              f"{stage} ({error}), and its status cannot be read now; "
                              f"the move may have happened: check with "
                              f"`tcw work show {slug}`") from None
        if current != status:
            raise Unreachable(f"Jira could not be reached to move {slug} to {stage}; "
                              f"it was not moved: {error}")
        if document is not None:
            try:
                found = self._note_found(key, note, before)
            except TrackerError:
                raise MovedWithoutNote(
                    f"{slug} moved to {stage}, but the connection failed ({error}) "
                    f"and its comments cannot be read now; the note may have been "
                    f"posted: read the comments with `tcw work show {slug}` before "
                    f"adding it", uncertain=True) from None
            if not found:
                raise MovedWithoutNote(f"{slug} moved to {stage}, but the connection "
                                       f"failed and the note is not among its newest "
                                       f"{NOTE_WINDOW} comments")
        return stage


def field_id(entry: dict) -> str:
    """A create-metadata entry's field id; older answers carry only `key`."""
    return str(entry.get("fieldId") or entry.get("key"))


@dataclass(frozen=True)
class Refusal:
    """Why the choice rule picked no transition."""
    message: str


def _describe(transition: Transition) -> str:
    screen = f" (screen: {', '.join(transition.fields)})" if transition.fields else ""
    return f"{transition.name} → {transition.to_status}{screen}"


def choose_transition(transitions: Iterable[Transition],
                      status: str) -> Transition | Refusal:
    """The choice rule (Design 5 step 2): the one transition into `status`;
    of several, the one whose screen asks for nothing but a comment; else a
    refusal listing them. It never walks through other statuses."""
    offered = list(transitions)
    candidates = [t for t in offered if t.to_status == status]
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        listed = "; ".join(_describe(t) for t in offered) or "none"
        return Refusal(f"no transition leads to {status!r}; the ticket offers: {listed}")
    plain = [t for t in candidates if set(t.fields) <= {"comment"}]
    if len(plain) == 1:
        return plain[0]
    listed = "; ".join(_describe(t) for t in (plain or candidates))
    return Refusal(f"several transitions lead to {status!r}, and TCW will not choose "
                   f"between them: {listed}")


def _refusal_text(slug: Slug, stage: str, chosen: Transition, error: Exception) -> str:
    return (f"Jira refused moving {slug} to {stage} through {chosen.name!r}: {error}. "
            f"If that transition's screen requires a field such as a resolution, set "
            f"it in a workflow post function instead; TCW fills in only the comment")


def _link_report(made: list[str], failed: list[str]) -> str:
    return (f"made: {', '.join(made) or 'none'}; not made: {', '.join(failed)}")


def _named(error: TcwError, name: str) -> TcwError:
    error.name = name
    return error


class _Unread:
    def __repr__(self) -> str:
        return "UNREAD"


_UNREAD = _Unread()
