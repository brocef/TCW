"""The spec's Jira-mode fixture: TCW-69's in-memory backend playing a backend
that keeps the request and qa records itself, served with stubs for TCW-71's
Jira-only helpers.

Its project is a real Jira-mode `tcw-config.yaml` (TCW-71's test
configuration), so the server reads the same configuration it would read in
Jira mode, and its item folders carry Jira keys, so `validate`'s offline Jira
check reads them as items. No request leaves the process.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from tcw.serve.services import Services
from tcw.work.backend import Comment
from tcw.work.jira.backend import EXTERNAL_STAGES
from tcw.work.model import DEFAULT_PRIORITY, Item, Slug, start_stage
from tcw.work.open import work_path
from tests.work.jira.conftest import jira_config
from tests.work.memory_backend import MemoryBackend
from tests.work.projects import commit_all, make_project

ME = "acc-me"
SITE = "https://example.atlassian.net"
NAMES = {ME: "Me Myself", "acc-ann": "Ann Author", "acc-bob": "Bob Builder"}
# The stages this backend keeps itself, as the Jira backend does.
EXTERNAL = EXTERNAL_STAGES
READS = ("read", "list", "read_request", "read_comments", "current_user", "lookup")


class RecordingBackend(MemoryBackend):
    """Records every call, reads included, with its arguments. `fail[name]`
    is an exception the named read raises instead of answering."""

    def __init__(self, work_root: Path, project: str):
        super().__init__(work_root, project, external_stages=EXTERNAL,
                         inbox_items=False, user=ME)
        self.fail: dict[str, Exception] = {}

    def __getattribute__(self, name: str):
        value = super().__getattribute__(name)
        if name in READS:
            def recorded(*args, **kwargs):
                self.calls.append((name, *args, *kwargs.values()))
                failure = self.fail.get(name)
                if failure is not None:
                    raise failure
                return value(*args, **kwargs)
            return recorded
        return value

    def seed(self, folder: str, title: str, *, stage: str | None = None,
             request: str | None = None, comments: tuple = (), **props) -> Item:
        """An item that already exists, made without recording a call."""
        (self.work_root / folder).mkdir(parents=True, exist_ok=True)
        values: dict[str, Any] = dict(
            slug=Slug(self.project, folder), title=title,
            stage=stage or start_stage(), created=date(2026, 10, 1),
            priority=DEFAULT_PRIORITY, effort=None, complexity=None, tags=(),
            assignee=None, parent=None, blocked_by=(), untracked=())
        values.update(props)
        item = Item(**values)
        self.items[folder] = item
        if request is not None:
            self.requests[folder] = request
        for at, author, text in comments:
            self.comments.setdefault(folder, []).append(Comment(at, author, text))
        return item

    def named(self, name: str) -> list[tuple]:
        return [c for c in self.calls if c[0] == name]


@dataclass
class JiraStubs:
    """TCW-71's Jira-only helpers, as the spec's fixture describes them."""

    calls: list[tuple] = field(default_factory=list)
    users: list[tuple[str, str]] = field(default_factory=lambda: [
        ("acc-ann", "Ann Author"), ("acc-alf", "Alf Alpha")])
    tickets: list[dict] = field(default_factory=list)
    create_fields_answer: tuple = ("priority",)

    def ticket_link(self, backend, folder: str):
        key = "-".join(folder.split("-")[:2])
        return "Jira", f"{SITE}/browse/{key}"

    def user_name(self, backend, account_id: str):
        self.calls.append(("user_name", account_id))
        return NAMES.get(account_id)

    def assignable_users(self, backend, query: str, limit: int):
        self.calls.append(("assignable_users", query, limit))
        return [u for u in self.users if query.lower() in u[1].lower()][:limit]

    def inbox(self, backend):
        self.calls.append(("inbox",))
        return list(self.tickets), "project = TCW"

    def adopt(self, backend, key: str, root: Path):
        self.calls.append(("adopt", key))
        folder = f"{key}-adopted"
        backend.seed(folder, f"Adopted {key}")
        return f"{backend.project}/{folder}", 0

    def create_fields(self, backend):
        self.calls.append(("create_fields",))
        return self.create_fields_answer


@dataclass
class JiraMode:
    root: Path
    backend: RecordingBackend
    stubs: JiraStubs
    served: Any = None

    def services(self) -> Services:
        stubs = self.stubs
        return Services(open_backend=lambda root: self.backend,
                        ticket_link=stubs.ticket_link, user_name=stubs.user_name,
                        assignable_users=stubs.assignable_users, inbox=stubs.inbox,
                        adopt=stubs.adopt, create_fields=stubs.create_fields)


AT = datetime(2026, 10, 2, 9, 0, tzinfo=timezone.utc)


def jira_mode(tmp_path: Path, project_id: str = "tcw") -> JiraMode:
    """A Jira-mode project with two items: `TCW-1-first`, whose request and
    two comments the backend keeps, and `TCW-2-second`."""
    root = make_project(tmp_path, project_id, config=jira_config(project_id))
    commit_all(root)
    backend = RecordingBackend(work_path(root), project_id)
    backend.seed("TCW-1-first", "First", request="Please do the first thing.",
                 assignee="acc-ann", tags=("ui",),
                 comments=((AT, "acc-ann", "first comment"),
                           (AT.replace(hour=10), "acc-bob", "second comment")))
    backend.seed("TCW-2-second", "Second", assignee=ME)
    return JiraMode(root, backend, JiraStubs())
