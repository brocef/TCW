"""A stateful fake Jira Cloud site, installed in place of `JiraClient._request`
(TCW-71 Design 15.1).

It holds projects, issue types with hierarchy levels, tickets, comments,
links, users and a workflow, applies writes, and answers each request from its
current state, raising the client's own error types exactly as `_request`
would. No socket is opened.

The account a request runs as is chosen by the value of the calling client's
email variable, so two clients configured with different variables are two
accounts.

**Switches** (each a method or attribute; `test_fake.py` checks each one does
something): workflow definitions answer 403; a transition carrying a comment
is refused; a transition's screen requires a field; the connection drops after
the next write is applied; a whole `key IN` search naming a missing key is
refused with 400; tickets written in the last N requests are left out of
searches; a field is left off an issue type's edit screen; every request is
unreachable, 401, or 429 with `Retry-After`; Priority is left off the create
screen.

Searches go through `fake_jql`, which parses exactly the shapes TCW builds.
"""

from __future__ import annotations

import json
import os
import re
import urllib.parse
from dataclasses import dataclass, field
from typing import Any

from tcw.work.jira import client as jira
from tests.work.jira import fake_jql

SITE = "https://acme.atlassian.net"

#: Custom field ids, by the display names a test configuration uses.
FIELDS = {"TCW Project": "customfield_10001", "TCW Item": "customfield_10002",
          "Effort": "customfield_10003", "Complexity": "customfield_10004"}
TEXT_FIELD = "com.atlassian.jira.plugin.system.customfieldtypes:textfield"
SELECT_FIELD = "com.atlassian.jira.plugin.system.customfieldtypes:select"
SIZES = ("low", "medium", "high", "very-high")
PRIORITIES = ("Highest", "High", "Medium", "Low", "Lowest")

#: The statuses `TCWTEST` is given (the TCW-71 checklist), in order.
STATUSES = ("To Do", "Triage", "Specifying", "Planning", "In Progress",
            "In Review", "In QA", "Done", "Won't Do")


@dataclass
class IssueType:
    id: str
    name: str
    level: int
    subtask: bool = False


ISSUE_TYPES = (IssueType("10001", "Epic", 1), IssueType("10002", "Task", 0),
               IssueType("10003", "Bug", 0),
               IssueType("10004", "Subtask", -1, subtask=True))


@dataclass
class Transition:
    id: str
    name: str
    to: str
    #: None for a global transition (offered from every status), else the
    #: statuses it is offered from.
    sources: tuple[str, ...] | None = None
    #: field id -> required, for the transition's screen; empty for no screen.
    screen: dict = field(default_factory=dict)


@dataclass
class Project:
    key: str
    id: str
    statuses: tuple[str, ...] = STATUSES
    issue_types: tuple[IssueType, ...] = ISSUE_TYPES
    initial_status: str = "To Do"
    priority: bool = True
    transitions: list[Transition] = field(default_factory=list)
    counter: int = 0

    def __post_init__(self):
        if not self.transitions:
            self.transitions = [Transition(str(31 + i), f"Move to {s}", s)
                                for i, s in enumerate(self.statuses)]

    def type_by(self, ref: dict | str | None) -> IssueType | None:
        for kind in self.issue_types:
            if isinstance(ref, dict) and (ref.get("id") == kind.id
                                          or ref.get("name") == kind.name):
                return kind
            if ref in (kind.id, kind.name):
                return kind
        return None


@dataclass
class Ticket:
    key: str
    id: str
    project: str
    issue_type: IssueType
    summary: str
    status: str
    created: str
    description: Any = None
    priority: str | None = "Medium"
    labels: list[str] = field(default_factory=list)
    assignee: str | None = None
    parent: str | None = None
    custom: dict = field(default_factory=dict)
    comments: list[dict] = field(default_factory=list)
    #: The request number of the last write through the API; None for a
    #: ticket made directly, which no search lag hides.
    written: int | None = None


@dataclass
class Link:
    id: str
    type: str
    inward: str
    outward: str


@dataclass
class Account:
    account_id: str
    name: str
    email: str
    locale: str = "en_US"


class FakeJira:
    def __init__(self, site: str = SITE):
        self.site = site
        self.projects: dict[str, Project] = {}
        self.tickets: dict[str, Ticket] = {}
        self.links: list[Link] = []
        self.accounts: dict[str, Account] = {}
        self.log: list[tuple[str, str, Any]] = []
        self.clock = 0
        self.link_counter = 0
        self.comment_counter = 0
        self.page_size = 100
        # switches
        self.workflows_forbidden = False
        self.refuse_commented_transitions = False
        self.refuse_missing_key_search = False
        self.search_lag = 0
        self.ignore_label_case = False
        self.off_edit_screen: set[tuple[str, str]] = set()   # (type name, field id)
        self.down: Exception | None = None
        self.refuse_cross_project_parent = False
        self._drop_after_write = False
        self._down_after_drop = False
        self._drop_before_write = False
        self.add_project("TCW")

    # -- setup -------------------------------------------------------------------

    def add_project(self, key: str, **values) -> Project:
        project = Project(key, str(10000 + len(self.projects)), **values)
        self.projects[key] = project
        return project

    def account(self, email: str, account_id: str, name: str, **values) -> Account:
        self.accounts[email] = Account(account_id, name, email, **values)
        return self.accounts[email]

    def ticket(self, summary: str = "A ticket", *, project: str = "TCW",
               issue_type: str = "Task", status: str | None = None, **values) -> Ticket:
        """A ticket made directly, as a person would in Jira."""
        proj = self.projects[project]
        proj.counter += 1
        self.clock += 1
        kind = proj.type_by(issue_type)
        ticket = Ticket(key=f"{project}-{proj.counter}", id=str(20000 + len(self.tickets)),
                        project=project, issue_type=kind, summary=summary,
                        status=status or proj.initial_status,
                        created=self._stamp(), **values)
        self.tickets[ticket.key] = ticket
        return ticket

    def custom(self, key: str, name: str) -> Any:
        return self.tickets[key].custom.get(FIELDS[name])

    def require_screen_field(self, transition_id: str, field_id: str,
                             project: str = "TCW") -> None:
        for transition in self.projects[project].transitions:
            if transition.id == transition_id:
                transition.screen[field_id] = True
                return
        raise KeyError(transition_id)

    def drop_after_next_write(self, *, then_unreachable: bool = False) -> None:
        """The next write is applied, then its connection drops; with
        `then_unreachable`, every request after it is unreachable too."""
        self._drop_after_write = True
        self._down_after_drop = then_unreachable

    def drop_before_next_write(self) -> None:
        """The next write's connection drops before Jira applies it."""
        self._drop_before_write = True

    def unreachable(self) -> None:
        self.down = jira.TrackerUnavailable(f"could not reach the tracker at {self.site}")

    def unauthorized(self) -> None:
        self.down = jira._for_status(401, {}, "", "/")

    def rate_limited(self, retry_after: str | None = "30") -> None:
        headers = {"Retry-After": retry_after} if retry_after else {}
        self.down = jira._for_status(429, headers, "", "/")

    # -- installing ------------------------------------------------------------

    def install(self, monkeypatch) -> "FakeJira":
        install_sites(monkeypatch, self)
        return self

    def writes(self) -> list[tuple[str, str]]:
        """Every write request, as (method, path), in order."""
        return [(m, p) for m, p, _ in self.log if _is_write(m, p)]

    def requests(self, method: str | None = None, fragment: str = "") -> list:
        return [(m, p, b) for m, p, b in self.log
                if (method is None or m == method) and fragment in p]

    # -- answering ---------------------------------------------------------------

    def answer(self, client, method: str, path: str, body: Any):
        self.log.append((method, path, body))
        if self.down is not None:
            raise self.down
        email = os.environ.get(client.config.email_env, "")
        if email not in self.accounts:
            self.account(email, f"acct-{len(self.accounts) + 1}", email or "anonymous")
        me = self.accounts[email]
        route, query = _split(path)
        if _is_write(method, path) and self._drop_before_write:
            self._drop_before_write = False
            raise jira.TrackerUnavailable(
                f"could not reach the tracker at {self.site} (connection reset)")
        payload = self._route(me, method, route, query, body)
        if _is_write(method, path):
            if self._drop_after_write:
                self._drop_after_write = False
                if self._down_after_drop:
                    self.unreachable()
                raise jira.TrackerUnavailable(
                    f"the connection to the tracker at {self.site} was lost before "
                    f"it answered (RemoteDisconnected)")
        return 200 if payload is not None else 204, {}, (
            b"" if payload is None else json.dumps(payload).encode())

    def _error(self, status: int, path: str, detail: str = ""):
        return jira._for_status(status, {}, json.dumps({"errorMessages": [detail]})
                                if detail else "", path)

    def _route(self, me: Account, method: str, route: str, query: dict, body: Any):
        parts = route.strip("/").split("/")[3:]        # after rest/api/3
        match parts, method:
            case ["myself"], "GET":
                return self._user(me)
            case ["search", "jql"], "POST":
                return self._search(body, route)
            case ["issue"], "POST":
                return self._create(body, route)
            case ["issue", "createmeta", project, "issuetypes", type_id], "GET":
                return self._createmeta(project, type_id, query, route)
            case ["issue", key], "GET":
                return self._issue(self._find(key, route), query.get("fields"))
            case ["issue", key], "PUT":
                return self._edit(self._find(key, route), body, route)
            case ["issue", key, "editmeta"], "GET":
                return self._editmeta(self._find(key, route))
            case ["issue", key, "transitions"], "GET":
                return self._transitions(self._find(key, route))
            case ["issue", key, "transitions"], "POST":
                return self._transition(self._find(key, route), body, route)
            case ["issue", key, "comment"], "GET":
                return self._comments(self._find(key, route), query)
            case ["issue", key, "comment"], "POST":
                return self._comment(self._find(key, route), me, body["body"])
            case ["issueLink"], "POST":
                return self._link(body, route)
            case ["issueLink", link_id], "DELETE":
                return self._unlink(link_id, route)
            case ["issueLinkType"], "GET":
                return {"issueLinkTypes": [
                    {"id": "1", "name": "Blocks", "inward": "is blocked by",
                     "outward": "blocks"},
                    {"id": "2", "name": "Relates", "inward": "relates to",
                     "outward": "relates to"}]}
            case ["user"], "GET":
                for account in self.accounts.values():
                    if account.account_id == query.get("accountId"):
                        return self._user(account)
                raise self._error(404, route)
            case ["user", "assignable", "search"], "GET":
                text = query.get("query", "").lower()
                found = [self._user(a) for a in self.accounts.values()
                         if text in a.name.lower() or text in a.email.lower()
                         or text == a.account_id.lower()]
                return found[:int(query.get("maxResults", 50))]
            case ["project", key], "GET":
                return self._project(self._project_of(key, route))
            case ["project", key, "statuses"], "GET":
                project = self._project_of(key, route)
                return [{"id": t.id, "name": t.name, "subtask": t.subtask,
                         "statuses": [{"id": str(100 + i), "name": s}
                                      for i, s in enumerate(project.statuses)]}
                        for t in project.issue_types]
            case ["workflows"], "POST":
                return self._workflows(body, route)
        raise self._error(404, route, f"the fake does not answer {method} {route}")

    # -- reads -----------------------------------------------------------------

    def _user(self, account: Account) -> dict:
        return {"accountId": account.account_id, "displayName": account.name,
                "emailAddress": account.email, "locale": account.locale,
                "active": True}

    def _find(self, key: str, route: str) -> Ticket:
        ticket = self.tickets.get(urllib.parse.unquote(key))
        if ticket is None:
            raise self._error(404, route, "Issue does not exist or you do not have "
                                          "permission to see it.")
        return ticket

    def _project_of(self, key: str, route: str) -> Project:
        project = self.projects.get(urllib.parse.unquote(key))
        if project is None:
            raise self._error(404, route, "No project could be found")
        return project

    def _issue(self, ticket: Ticket, fields: str | None = None) -> dict:
        project = self.projects[ticket.project]
        names = {self._account_name(ticket.assignee)}
        values = {
            "summary": ticket.summary,
            "status": {"name": ticket.status,
                       "id": str(100 + project.statuses.index(ticket.status))
                       if ticket.status in project.statuses else "999",
                       "statusCategory": {"key": "done" if ticket.status in
                                          ("Done", "Won't Do") else "indeterminate"}},
            "created": ticket.created,
            "priority": {"name": ticket.priority} if ticket.priority else None,
            "labels": list(ticket.labels),
            "assignee": None if ticket.assignee is None else {
                "accountId": ticket.assignee, "displayName": names.pop()},
            "parent": None if ticket.parent is None else {
                "key": ticket.parent, "id": self.tickets[ticket.parent].id,
                "fields": {"issuetype": self._type(self.tickets[ticket.parent].issue_type)}},
            "issuelinks": self._issuelinks(ticket.key),
            "issuetype": self._type(ticket.issue_type),
            "project": {"key": ticket.project, "id": project.id},
            "description": ticket.description,
            **{f: v for f, v in ticket.custom.items()},
        }
        if fields:
            wanted = fields.split(",")
            values = {k: v for k, v in values.items() if k in wanted}
        return {"id": ticket.id, "key": ticket.key,
                "self": f"{self.site}/rest/api/3/issue/{ticket.id}", "fields": values}

    def _account_name(self, account_id: str | None) -> str | None:
        for account in self.accounts.values():
            if account.account_id == account_id:
                return account.name
        return None

    @staticmethod
    def _type(kind: IssueType) -> dict:
        return {"id": kind.id, "name": kind.name, "hierarchyLevel": kind.level,
                "subtask": kind.subtask}

    def _issuelinks(self, key: str) -> list[dict]:
        out = []
        for link in self.links:
            if link.outward == key:
                out.append({"id": link.id, "type": self._link_type(link.type),
                            "inwardIssue": {"key": link.inward}})
            elif link.inward == key:
                out.append({"id": link.id, "type": self._link_type(link.type),
                            "outwardIssue": {"key": link.outward}})
        return out

    @staticmethod
    def _link_type(name: str) -> dict:
        return {"name": name, "inward": "is blocked by", "outward": "blocks"}

    def _value(self, ticket: Ticket, name: str) -> Any:
        if name.startswith("customfield_"):
            value = ticket.custom.get(name)
            return value.get("value") if isinstance(value, dict) else value
        return {"project": ticket.project, "status": ticket.status, "key": ticket.key,
                "labels": ticket.labels, "parent": ticket.parent,
                "assignee": ticket.assignee, "issuetype": ticket.issue_type.name,
                "created": ticket.created}.get(name)

    def _search(self, body: dict, route: str) -> dict:
        query = body["jql"]
        try:
            keys = re.fullmatch(r'key IN \((.*)\)', query)
            if keys and self.refuse_missing_key_search:
                named = [k.strip().strip('"') for k in keys.group(1).split(",")]
                if any(k not in self.tickets for k in named):
                    raise self._error(400, route, "An issue with key does not exist")
            visible = [t for t in self.tickets.values()
                       if not self.search_lag or t.written is None
                       or t.written <= len(self.log) - self.search_lag - 1]
            known = {s for p in self.projects.values() for s in p.statuses}
            found = fake_jql.select(query, visible, self._value,
                                    ignore_label_case=self.ignore_label_case,
                                    statuses=known)
        except fake_jql.JqlError as error:
            raise self._error(400, route, str(error)) from None
        start = int(body.get("nextPageToken") or 0)
        size = min(int(body.get("maxResults", 50)), self.page_size)
        page = found[start:start + size]
        fields = ",".join(body.get("fields") or [])
        answer: dict = {"issues": [self._issue(t, fields or None) for t in page],
                        "isLast": start + size >= len(found)}
        if not answer["isLast"]:
            answer["nextPageToken"] = str(start + size)
        return answer

    def _transitions(self, ticket: Ticket) -> dict:
        offered = []
        for transition in self._offered(ticket):
            entry = {"id": transition.id, "name": transition.name,
                     "to": {"name": transition.to, "id": str(
                         100 + self.projects[ticket.project].statuses.index(transition.to))}}
            if transition.screen:
                entry["fields"] = {f: {"required": required, "name": f}
                                   for f, required in transition.screen.items()}
            offered.append(entry)
        return {"transitions": offered}

    def _offered(self, ticket: Ticket) -> list[Transition]:
        return [t for t in self.projects[ticket.project].transitions
                if t.sources is None or ticket.status in t.sources]

    def _comments(self, ticket: Ticket, query: dict) -> dict:
        ordered = sorted(ticket.comments, key=lambda c: c["created"],
                         reverse=query.get("orderBy") == "-created")
        start = int(query.get("startAt", 0))
        size = int(query.get("maxResults", 50))
        return {"startAt": start, "maxResults": size, "total": len(ordered),
                "comments": ordered[start:start + size]}

    def _fields_for(self, project: Project, kind: IssueType) -> list[dict]:
        fields = [
            {"fieldId": "summary", "name": "Summary", "required": True,
             "schema": {"type": "string", "system": "summary"}},
            {"fieldId": "issuetype", "name": "Issue Type", "required": True,
             "schema": {"type": "issuetype", "system": "issuetype"}},
            {"fieldId": "project", "name": "Project", "required": True,
             "schema": {"type": "project", "system": "project"}},
            {"fieldId": "description", "name": "Description", "required": False,
             "schema": {"type": "string", "system": "description"}},
            {"fieldId": "labels", "name": "Labels", "required": False,
             "schema": {"type": "array", "items": "string", "system": "labels"}},
            {"fieldId": "assignee", "name": "Assignee", "required": False,
             "schema": {"type": "user", "system": "assignee"}},
            {"fieldId": "parent", "name": "Parent", "required": kind.subtask,
             "schema": {"type": "issuelink", "system": "parent"}},
        ]
        if project.priority:
            fields.append({"fieldId": "priority", "name": "Priority", "required": False,
                           "schema": {"type": "priority", "system": "priority"},
                           "allowedValues": [{"name": p, "id": str(i + 1)}
                                             for i, p in enumerate(PRIORITIES)]})
        for name, field_id in FIELDS.items():
            if name in ("TCW Project", "TCW Item"):
                fields.append({"fieldId": field_id, "name": name, "required": False,
                               "schema": {"type": "string", "custom": TEXT_FIELD}})
            else:
                fields.append({"fieldId": field_id, "name": name, "required": False,
                               "schema": {"type": "option", "custom": SELECT_FIELD},
                               "allowedValues": [{"value": v, "id": str(300 + i)}
                                                 for i, v in enumerate(SIZES)]})
        return fields

    def _createmeta(self, key: str, type_id: str, query: dict, route: str) -> dict:
        project = self._project_of(key, route)
        kind = project.type_by(type_id)
        if kind is None:
            raise self._error(404, route, "issue type not found")
        fields = self._fields_for(project, kind)
        start = int(query.get("startAt", 0))
        size = int(query.get("maxResults", 50))
        return {"startAt": start, "maxResults": size, "total": len(fields),
                "fields": fields[start:start + size]}

    def _editmeta(self, ticket: Ticket) -> dict:
        project = self.projects[ticket.project]
        fields = self._fields_for(project, ticket.issue_type)
        return {"fields": {f["fieldId"]: {k: v for k, v in f.items() if k != "fieldId"}
                           for f in fields if f["fieldId"] not in ("issuetype", "project")
                           and (ticket.issue_type.name, f["fieldId"])
                           not in self.off_edit_screen}}

    def _project(self, project: Project) -> dict:
        return {"id": project.id, "key": project.key, "name": f"{project.key} project",
                "issueTypes": [self._type(t) for t in project.issue_types]}

    def _workflows(self, body: dict, route: str) -> dict:
        if self.workflows_forbidden:
            raise self._error(403, route, "You don't have permission")
        wanted = body["projectAndIssueTypes"][0]
        project = next(p for p in self.projects.values() if p.id == wanted["projectId"])
        refs = {s: f"ref-{i}" for i, s in enumerate(project.statuses)}
        # Real answers carry the create transition too, typed INITIAL, with no
        # links; it is offered from no status.
        transitions = [{"id": "1", "name": "Create", "type": "INITIAL", "links": [],
                        "toStatusReference": refs[project.statuses[0]]}]
        for t in project.transitions:
            entry = {"id": t.id, "name": t.name, "toStatusReference": refs[t.to],
                     "type": "GLOBAL" if t.sources is None else "DIRECTED",
                     "links": [] if t.sources is None else [
                         {"fromStatusReference": refs[s]} for s in t.sources]}
            transitions.append(entry)
        return {"statuses": [{"name": s, "statusReference": r} for s, r in refs.items()],
                "workflows": [{"id": "wf-1", "name": f"{project.key} workflow",
                               "statuses": [{"statusReference": r} for r in refs.values()],
                               "transitions": transitions}]}

    # -- writes ----------------------------------------------------------------

    def _stamp(self) -> str:
        minutes = self.clock
        return f"2026-10-01T{10 + minutes // 60:02d}:{minutes % 60:02d}:00.000+0000"

    def _touch(self, ticket: Ticket) -> None:
        ticket.written = len(self.log)

    def _check_field_value(self, field_id: str, value: Any, route: str) -> None:
        if field_id in (FIELDS["Effort"], FIELDS["Complexity"]) and value is not None:
            if not isinstance(value, dict) or value.get("value") not in SIZES:
                raise self._error(400, route, f"Option value '{value}' is not valid")

    def _create(self, body: dict, route: str) -> dict:
        fields = dict(body["fields"])
        project = self.projects.get((fields.get("project") or {}).get("key"))
        if project is None:
            raise self._error(400, route, "project is required")
        kind = project.type_by(fields.get("issuetype"))
        if kind is None:
            raise self._error(400, route, "Specify a valid issue type")
        if not fields.get("summary"):
            raise self._error(400, route, "You must specify a summary of the issue.")
        on_screen = {f["fieldId"] for f in self._fields_for(project, kind)}
        for name in fields:
            if name not in on_screen:
                raise self._error(400, route, f"Field '{name}' cannot be set. It is "
                                              f"not on the appropriate screen")
        parent = (fields.get("parent") or {}).get("key")
        if parent:
            self._check_parent(parent, kind, project, route)
        if kind.subtask and not parent:
            raise self._error(400, route, "Sub-tasks must have a parent")
        custom = {}
        for name, value in fields.items():
            if name.startswith("customfield_"):
                self._check_field_value(name, value, route)
                custom[name] = value
        ticket = self.ticket(fields["summary"], project=project.key, issue_type=kind.name,
                             description=fields.get("description"),
                             priority=(fields.get("priority") or {}).get("name")
                             if project.priority else None,
                             labels=list(fields.get("labels") or []),
                             assignee=(fields.get("assignee") or {}).get("accountId"),
                             parent=parent, custom=custom)
        if project.priority and "priority" not in fields:
            ticket.priority = "Medium"
        self._touch(ticket)
        return {"id": ticket.id, "key": ticket.key,
                "self": f"{self.site}/rest/api/3/issue/{ticket.id}"}

    def _check_parent(self, parent_key: str, kind: IssueType, project: Project,
                      route: str) -> None:
        parent = self.tickets.get(parent_key)
        if parent is None:
            raise self._error(400, route, f"Issue '{parent_key}' does not exist")
        if parent.project != project.key and self.refuse_cross_project_parent:
            raise self._error(400, route, "The parent must be in the same project")
        if parent.issue_type.level != kind.level + 1:
            raise self._error(400, route, "Given parent work item does not belong to "
                                          "appropriate hierarchy.")

    def _edit(self, ticket: Ticket, body: dict, route: str) -> None:
        project = self.projects[ticket.project]
        editable = set(self._editmeta(ticket)["fields"])
        fields = body.get("fields") or {}
        update = body.get("update") or {}
        for name in list(fields) + list(update):
            if name not in editable:
                raise self._error(400, route, f"Field '{name}' cannot be set. It is "
                                              f"not on the appropriate screen")
        for name, value in fields.items():
            if name.startswith("customfield_"):
                self._check_field_value(name, value, route)
        if "parent" in fields and fields["parent"] is not None:
            self._check_parent(fields["parent"]["key"], ticket.issue_type, project, route)
        if "priority" in fields and fields["priority"] is not None \
                and fields["priority"].get("name") not in PRIORITIES:
            raise self._error(400, route, "The priority selected is invalid.")
        for name, value in fields.items():
            if name == "summary":
                ticket.summary = value
            elif name == "priority":
                ticket.priority = None if value is None else value["name"]
            elif name == "assignee":
                ticket.assignee = None if value is None else value["accountId"]
            elif name == "parent":
                ticket.parent = None if value is None else value["key"]
            elif name == "labels":
                ticket.labels = list(value)
            elif name == "description":
                ticket.description = value
            elif name.startswith("customfield_"):
                ticket.custom[name] = value
        for operation in update.get("labels", []):
            if "add" in operation and operation["add"] not in ticket.labels:
                ticket.labels.append(operation["add"])
            if "remove" in operation and operation["remove"] in ticket.labels:
                ticket.labels.remove(operation["remove"])
        self._touch(ticket)
        return None

    def _transition(self, ticket: Ticket, body: dict, route: str) -> None:
        wanted = body["transition"]["id"]
        chosen = next((t for t in self._offered(ticket) if t.id == wanted), None)
        if chosen is None:
            raise self._error(400, route, f"Transition id '{wanted}' is not valid for "
                                          f"this issue.")
        comments = (body.get("update") or {}).get("comment") or []
        if comments and self.refuse_commented_transitions:
            raise self._error(400, route, "Field 'comment' cannot be set. It is not on "
                                          "the appropriate screen")
        given = set((body.get("fields") or {}))
        missing = [f for f, required in chosen.screen.items()
                   if required and f != "comment" and f not in given]
        if missing:
            raise self._error(400, route, f"{missing[0]} is required.")
        ticket.status = chosen.to
        for entry in comments:
            self._comment(ticket, None, entry["add"]["body"])
        self._touch(ticket)
        return None

    def _comment(self, ticket: Ticket, me: Account | None, document: Any) -> dict:
        self.clock += 1
        self.comment_counter += 1
        author = me or next(iter(self.accounts.values()), None)
        comment = {"id": str(self.comment_counter),
                   "author": None if author is None else {
                       "accountId": author.account_id, "displayName": author.name},
                   "created": self._stamp(), "body": document}
        ticket.comments.append(comment)
        self._touch(ticket)
        return comment

    def _link(self, body: dict, route: str) -> None:
        name = body["type"]["name"]
        if name not in ("Blocks", "Relates"):
            raise self._error(404, route, f"No issue link type with name '{name}' found.")
        inward, outward = body["inwardIssue"]["key"], body["outwardIssue"]["key"]
        for key in (inward, outward):
            self._find(key, route)
        self.link_counter += 1
        self.links.append(Link(str(self.link_counter), name, inward, outward))
        for key in (inward, outward):
            self._touch(self.tickets[key])
        return None

    def _unlink(self, link_id: str, route: str) -> None:
        for link in self.links:
            if link.id == link_id:
                self.links.remove(link)
                return None
        raise self._error(404, route, "No issue link with id exists")


def _split(path: str) -> tuple[str, dict]:
    route, _, query = path.partition("?")
    return route, dict(urllib.parse.parse_qsl(query, keep_blank_values=True))


def _is_write(method: str, path: str) -> bool:
    route = path.split("?")[0]
    return method in ("PUT", "DELETE") or (
        method == "POST" and not route.endswith(("/search/jql", "/workflows")))


def install_sites(monkeypatch, *fakes: FakeJira) -> None:
    """Answer every client by its configured site; a site no fake serves is
    unreachable, as an unknown host would be."""
    by_site = {fake.site: fake for fake in fakes}

    def request(client, method, path, body=None, *, timeout=None):
        assert timeout, "every request passes a timeout"
        missing = [name for name in (client.config.email_env, client.config.token_env)
                   if not os.environ.get(name, "").strip()]
        if missing:
            raise jira.TrackerAuthError(
                f"Jira credentials are not set: {', '.join(missing)}. "
                f"Export them, or correct work.jira.credentials in tcw-config.yaml.")
        fake = by_site.get(client.config.site)
        if fake is None:
            raise jira.TrackerUnavailable(f"could not reach the tracker at "
                                          f"{client.config.site}")
        return fake.answer(client, method, path, body)

    monkeypatch.setattr(jira.JiraClient, "_request", request)
