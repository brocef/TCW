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
from tcw.output import shown
from tcw.store.base import normalize_tag
from tcw.work.backend import Comment, Query
from tcw.work.config import WorkConfig
from tcw.work.fs_backend import ITEM_FILE, WORDS, report_mentions
from tcw.work.jira import jql
from tcw.work.jira.client import (
    JiraClient, Transition, TrackerAuthError, TrackerError, TrackerNotFound,
    TrackerPermissionError, TrackerRateLimited, TrackerRequestInvalid, TrackerUnavailable,
)
from tcw.work.jira.config import JiraConfig
from tcw.work.jira.mapping import (
    BLOCKS, Props, block_link, blocker_links, create_fields, document_text,
    normalize_text, read_fields, read_props, scale_name, text_document, write_fields,
)
from tcw.work.layout import Layout
from tcw.work.model import (
    FOLDER_LIMIT, UNSET, Changes, Item, Slug, check_encodable, completion_stage,
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
    except TrackerNotFound as error:
        raise NotFound(str(error)) from None
    except TrackerRequestInvalid as error:
        raise BackendError(str(error)) from None
    except TrackerError as error:
        raise BackendError(str(error)) from None


def folder_key(folder: str) -> str | None:
    """The key a Jira-mode folder name starts with, or None."""
    match = KEY_FOLDER.fullmatch(folder) if isinstance(folder, str) else None
    return match.group("key") if match else None


def link_exists(work_path: Path, folder: str) -> bool:
    """Whether `folder` is an item of a Jira-mode project, by the folder scan
    `lookup` uses: the key in the name is authoritative, so no read of the
    ticket is needed, and a work link stays offline (R20)."""
    return folder_key(folder) is not None and "/" not in folder \
        and (Path(work_path) / folder).is_dir()


def jira_store_problems(work_path: Path, jira: JiraConfig) -> list[Finding]:
    """The offline checks of a Jira-mode work path (Design 9.1): each folder's
    name and `item.yaml`, keys used twice, and record folders for stages Jira
    keeps. Reads no network."""
    findings: list[Finding] = []
    work_path = Path(work_path)
    if not work_path.is_dir():
        return findings
    by_key: dict[str, list[str]] = {}
    for entry in sorted(work_path.iterdir(), key=lambda p: p.name):
        if entry.name.startswith(".") or not entry.is_dir():
            continue
        key = folder_key(entry.name)
        if key is None:
            findings.append(Finding("error", str(entry),
                                    "is not a Jira item folder: its name must be the "
                                    "ticket's key, then title words, such as "
                                    "TCW-5-add-export"))
            continue
        by_key.setdefault(key, []).append(entry.name)
        findings.extend(_item_file_problems(entry / ITEM_FILE, key, jira.site))
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


def _item_file_problems(path: Path, key: str, site: str) -> list[Finding]:
    """`item.yaml` must be exactly `ticket: <site>/browse/<KEY>` (Design 2.2)."""
    where = str(path)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [Finding("error", where, "is missing; it holds the ticket's link")]
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
        return [Finding("error", where, f"cannot be read: {error}")]
    if not isinstance(data, dict) or set(data) != {"ticket"}:
        extra = sorted(map(str, set(data) - {"ticket"})) if isinstance(data, dict) else []
        detail = f"; it also has {', '.join(extra)}" if extra else ""
        return [Finding("error", where, f"must hold exactly one key, ticket{detail}")]
    url = data["ticket"]
    prefix = f"{site}/browse/"
    if not isinstance(url, str) or not url.startswith(prefix):
        return [Finding("error", where, f"ticket {url!r} is not on {site} "
                                        f"(work.jira.site)")]
    if url[len(prefix):] != key:
        return [Finding("error", where, f"ticket {url!r} names {url[len(prefix):]}, but "
                                        f"the folder's key is {key}")]
    return []


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
            project = self.client.project(self.jira.project)
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

    def lookup(self, name: str) -> str | None:
        if not isinstance(name, str):
            return None
        key = name.upper()
        if not KEY.fullmatch(key) or not self.work_path.is_dir():
            return None
        found = sorted(entry.name for entry in self.work_path.iterdir()
                       if entry.is_dir() and folder_key(entry.name) == key)
        if len(found) > 1:
            raise BackendError(f"two folders in {self.work_path} carry the key {key}: "
                               f"{', '.join(found)}; rename or remove one")
        return found[0] if found else None

    def _key(self, folder: str) -> str:
        key = folder_key(folder)
        if key is None or "/" in folder or not (self.work_path / folder).is_dir():
            raise NotFound(f"no work item {self.project}/{folder}")
        return key

    # -- reading -----------------------------------------------------------------

    def read(self, folder: str) -> Item:
        key = self._key(folder)
        issue = self._issue(key, folder, read_fields(self.metadata().field_ids))
        answered = str(issue.get("key") or key)
        if answered != key:
            _warn(f"warning: {self.project}/{folder}: Jira answered for {key} with "
                  f"{answered}; the ticket was moved, so the folder's key is stale")
        return self._items([(Slug(self.project, folder), issue)])[0]

    def _issue(self, key: str, folder: str, fields: Iterable[str]) -> dict:
        try:
            with _jira():
                return self.client.issue(key, tuple(fields))
        except NotFound:
            raise NotFound(f"{self.project}/{folder}: Jira has no ticket {key}, or "
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
            parent = slugs.get(p.parent_key) if p.parent_key else None
            blocked_by = tuple(_unique(slugs[k] for k in p.blocker_keys if slugs.get(k)))
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
        if not isinstance(value, str):
            return None
        try:
            return Slug.parse(value, self.project)
        except UsageError:
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
            parent = folder_key(query.parent.folder)
            if parent is None:
                return []
        assignee = None
        if query.assignee is not None:
            assignee = self.account(query.assignee)
            query = replace(query, assignee=assignee)
        meta = self.metadata()
        text = jql.item_query(self.jira.project, meta.field_ids["item"],
                              statuses=statuses, not_statuses=not_statuses,
                              parent=parent, assignee=assignee, labels=labels)
        with _jira():
            issues = self.client.search(text, read_fields(meta.field_ids))
        found = []
        for issue in issues:
            fields = issue.get("fields") if isinstance(issue.get("fields"), dict) else {}
            if fields.get(meta.field_ids["project"]) != self.project:
                continue
            value = fields.get(meta.field_ids["item"])
            slug = self._slug_of(value)
            if slug is None or slug.project != self.project \
                    or folder_key(slug.folder) is None \
                    or not (self.work_path / slug.folder).is_dir():
                _warn(f"warning: Jira ticket {issue.get('key')} names the item "
                      f"{value!r}, whose folder is not in {self.work_path}; it is "
                      f"left out (it may exist in another copy of this "
                      f"repository)")
                continue
            found.append((slug, issue))
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
            raise NotFound(f"{self.project}/{folder}: Jira has no ticket {key}, or "
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
        either variable is unset, and None with one stderr line naming the
        cause when Jira cannot say (R3). Read at most once."""
        if self._me is not _UNREAD:
            return self._me
        unset = [name for name in (self.jira.email_env, self.jira.token_env)
                 if not os.environ.get(name, "").strip()]
        if unset:
            self._me = None
            return None
        try:
            me = self.client.myself()
        except TrackerUnavailable as error:
            _warn(f"Jira could not be reached to say who you are: {error}")
            me = None
        except TrackerAuthError:
            _warn(f"Jira rejected the credentials in {self.jira.email_env} and "
                  f"{self.jira.token_env}")
            me = None
        except TrackerError as error:
            _warn(f"Jira could not say who you are: {error}")
            me = None
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

    def ticket_key(self, value: Any, what: str) -> str:
        """The Jira key of the item a parent or blocker names. An item that is
        not a ticket on this site is refused before any request (Design 4.1
        step 1, 11.4)."""
        slug = value if isinstance(value, Slug) else Slug.parse(value, self.project)
        backend = self if slug.project == self.project else self._other(slug.project)
        if not isinstance(backend, JiraBackend) or backend.jira.site != self.jira.site \
                or folder_key(slug.folder) is None:
            raise Refused(f"{what} {slug} is not a Jira ticket on {self.jira.site}; "
                          f"Jira links only tickets on one site")
        return backend._key(slug.folder)

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

    def _parent(self, value: Any) -> tuple[str, int, str]:
        """A parent's key, hierarchy level and type name."""
        key = self.ticket_key(value, "parent")
        with _jira():
            issue = self.client.issue(key, ("issuetype",))
        level, name = self._type_of(issue)
        return key, level, name

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

    def _item_file(self, folder: str, key: str, *, resume: bool = False) -> None:
        """Make the folder and its item.yaml. `resume` finishes a folder an
        interrupted run made, and refuses nothing when it exists."""
        path = self.work_path / folder
        if not (resume and path.is_dir()):
            path.mkdir(parents=True)
            self.report(f"created {shown(path)}/")
        document = path / ITEM_FILE
        document.write_text(f"ticket: {self.jira.site}/browse/{key}\n", encoding="utf-8")
        self.report(f"wrote {shown(document)}")

    # -- create (Design 4.1) -------------------------------------------------------

    def create(self, title: str, props: Changes, *, stage: str,
               request: str | None) -> Item:
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
        issue_type, parent_key = meta.issue_type, None
        if props.parent not in (UNSET, None):
            parent_key, level, type_name = self._parent(props.parent)
            issue_type = self.child_issue_type(parent_key, level, type_name)
        assignee = (self.account(props.assignee)
                    if props.assignee not in (UNSET, None) else None)
        blockers = _unique(self.ticket_key(b, "blocked-by") for b in props.add_blocked_by)
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
        folder = f"{key}-{make_title_words(title)}"
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
        # 5. Write the folder and item.yaml.
        try:
            self._item_file(folder, key)
        except OSError as error:
            raise _named(BackendError(
                f"created Jira ticket {key} naming {slug}, but could not write its "
                f"folder: {error}; finish with `tcw work tickets adopt {key}`"), key) \
                from None
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
        return self.read(folder)

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
        parent: Any = UNSET
        if changes.parent is None:
            parent = None
        elif changes.parent is not UNSET:
            parent, level, type_name = self._parent(changes.parent)
            own_level, own_name = self._type_of(issue)
            if level != own_level + 1:
                raise Refused(f"{key} is a {own_name}, which cannot sit under {parent}, "
                              f"a {type_name}; Jira cannot change an issue's type here")
        assignee: Any = UNSET
        if changes.assignee is None:
            assignee = None
        elif changes.assignee is not UNSET:
            assignee = self.account(changes.assignee)
        add = _unique(self.ticket_key(b, "blocked-by") for b in changes.add_blocked_by)
        remove = _unique(self.ticket_key(b, "blocked-by")
                         for b in changes.remove_blocked_by)
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

    def rename(self, folder: str, title_words: str) -> Item:
        key = self._key(folder)
        words = title_words
        keyed = KEY_FOLDER.fullmatch(title_words) if isinstance(title_words, str) else None
        if keyed:
            if keyed.group("key") != key:
                raise UsageError(f"a rename keeps the key {key}; give the words alone, "
                                 f"or {key}-<words>")
            words = title_words[len(key) + 1:]
        if not isinstance(words, str) or not WORDS.fullmatch(words):
            raise UsageError(f"{title_words!r} is not a folder name; did you mean "
                             f"{make_title_words(str(title_words))}?")
        new = f"{key}-{words}"
        if len(new) > FOLDER_LIMIT:
            raise UsageError(f"{new} is longer than {FOLDER_LIMIT} characters")
        if new == folder:
            raise Refused(f"{folder} already has that name")
        old_path, new_path = self.work_path / folder, self.work_path / new
        if new_path.exists():
            raise Refused(f"{new_path} already exists")
        item_field = self.metadata().field_ids["item"]
        old_slug, new_slug = Slug(self.project, folder), Slug(self.project, new)
        with _jira():
            self.client.edit_issue(key, {item_field: str(new_slug)})
        try:
            os.rename(old_path, new_path)
        except OSError as error:
            try:
                self.client.edit_issue(key, {item_field: str(old_slug)})
                restored = f"TCW Item is set back to {old_slug}"
            except TrackerError as again:
                restored = (f"TCW Item still says {new_slug} and could not be set back "
                            f"to {old_slug} ({again})")
            raise BackendError(f"could not move {old_path} to {new_path}: {error}; "
                               f"{restored}") from None
        self.report(f"moved {shown(old_path)} to {shown(new_path)}")
        report_mentions(self.work_path, folder, self.report)
        return self.read(new)

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
        try:
            self.client.apply_transition(key, chosen.id, None if separate else document)
        except TrackerRequestInvalid as error:
            return self._after_refusal(key, slug, stage, status, chosen, note, document,
                                       error, separate=separate)
        except TrackerUnavailable as error:
            moved = self._after_drop(key, slug, stage, status,
                                     None if separate else note,
                                     None if separate else document, error)
            if separate:
                self._post_note(key, slug, stage, note)
            return moved
        except TrackerError:
            with _jira():
                raise
        if separate:
            self._post_note(key, slug, stage, note)
        return self._stage_now(key)

    def _stage_now(self, key: str) -> str | None:
        with _jira():
            status = self._status(key)
        return {name: stage for stage, name in self.statuses.items()}.get(status)

    def _note_found(self, key: str, note: str) -> bool:
        wanted = normalize_text(note)
        return any(normalize_text(document_text(c.body)) == wanted
                   for c in self.client.comments(key, NOTE_WINDOW))

    def _post_note(self, key: str, slug: Slug, stage: str, note: str) -> None:
        try:
            self.client.add_comment(key, text_document(note))
        except TrackerError as error:
            raise MovedWithoutNote(f"{slug} moved to {stage}, but posting the note "
                                   f"failed: {error}") from None

    def _after_refusal(self, key, slug, stage, status, chosen, note, document,
                       error, *, separate: bool = False) -> str | None:
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
                    found = not separate and self._note_found(key, note)
                except TrackerError:
                    found = False
                if not found:
                    self._post_note(key, slug, stage, note)
            return stage
        if document is None:
            raise Refused(_refusal_text(slug, stage, chosen, error))
        try:
            self.client.apply_transition(key, chosen.id)
        except TrackerRequestInvalid as again:
            raise Refused(_refusal_text(slug, stage, chosen, again)) from None
        except TrackerUnavailable as again:
            # The retry carried no comment, so posting the note cannot repeat it.
            moved = self._after_drop(key, slug, stage, status, None, None, again)
            self._post_note(key, slug, stage, note)
            return moved
        except TrackerError:
            with _jira():
                raise
        self._post_note(key, slug, stage, note)
        return self._stage_now(key)

    def _after_drop(self, key, slug, stage, status, note, document, error) -> str | None:
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
                found = self._note_found(key, note)
            except TrackerError:
                found = False
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
