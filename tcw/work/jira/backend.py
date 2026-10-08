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

from tcw.errors import BackendError, NotFound, Refused, Unreachable, UsageError
from tcw.store.base import normalize_tag
from tcw.work.backend import Comment, Query
from tcw.work.config import WorkConfig
from tcw.work.jira import jql
from tcw.work.jira.client import (
    JiraClient, TrackerAuthError, TrackerError, TrackerNotFound, TrackerPermissionError,
    TrackerRateLimited, TrackerRequestInvalid, TrackerUnavailable,
)
from tcw.work.jira.config import JiraConfig
from tcw.work.jira.mapping import (
    Props, document_text, read_fields, read_props, scale_name,
)
from tcw.work.layout import Layout
from tcw.work.model import (
    Changes, Item, Slug, completion_stage, discard_stage, stage as table_stage,
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
                 report: Callable[[str], None] | None = None):
        self.project = project
        self.work_path = Path(work_path)
        self.config = config
        self.jira = jira
        self.client = client or JiraClient(jira)
        self.report = report or _warn
        self.layout = Layout(self.work_path, config.enabled, self.external_stages)
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
            field_ids[role] = str(found[0].get("fieldId") or found[0].get("key"))
            if role in ("effort", "complexity"):
                options[role] = {
                    scale: value["value"]
                    for value in found[0].get("allowedValues") or []
                    if isinstance(value, dict) and isinstance(value.get("value"), str)
                    for scale in [scale_name(value)] if scale}
        has_priority = any(isinstance(f, dict) and f.get("fieldId") == "priority"
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
                      f"left out (it may have been created on another branch)")
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
            shown = ", ".join(f"{u.get('displayName')} ({u['accountId']})"
                              for u in found[:SHOWN_MATCHES])
            more = " and more" if len(found) > SHOWN_MATCHES else ""
            raise Refused(f"{value!r} matches several people in Jira project "
                          f"{self.jira.project}: {shown}{more}; give one account id")
        if isinstance(found[0].get("displayName"), str):
            self.names[found[0]["accountId"]] = found[0]["displayName"]
        return str(found[0]["accountId"])

    # -- writing: TCW-71 task 8 --------------------------------------------------

    def create(self, title: str, props: Changes, *, stage: str,
               request: str | None) -> Item:
        raise NotImplementedError

    def update(self, folder: str, changes: Changes) -> Item:
        raise NotImplementedError

    def set_stage(self, folder: str, stage: str, note: str | None) -> str | None:
        raise NotImplementedError

    def comment(self, folder: str, text: str) -> None:
        raise NotImplementedError

    def rename(self, folder: str, title_words: str) -> Item:
        raise NotImplementedError


class _Unread:
    def __repr__(self) -> str:
        return "UNREAD"


_UNREAD = _Unread()
