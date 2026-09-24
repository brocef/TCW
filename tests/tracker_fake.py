"""A stateful fake Jira, installed in place of `JiraClient._request`.

The claim's correctness is in *sequences* — two accounts reading, transitioning,
assigning and reading back in different orders — and no single captured response
shows a sequence. So this fake holds tickets and a workflow, applies writes, and
answers each request from its current state.

**Accounts** are chosen per request from the value of the calling client's
configured email variable, so two clients configured with different
`credentials.email-env` names are two accounts, exactly as two developers are.

**Hooks** make orderings deterministic without threads. `before(...)` runs a
function just before a matching request is answered — which is how a test puts
account B's whole claim inside account A's, between A's transition and A's
assign. `fail(...)` raises instead of answering, optionally after applying the
write, which is what a timeout on a request that did land looks like.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

from tcw.tracker import jira

BASE_URL = "https://example.invalid"

# name, destination status
DIRECTED = {
    "To Do": [("21", "Start Progress", "In Progress")],
    "In Progress": [("31", "Finish", "Done")],
    "Done": [],
}
GLOBAL = {status: [("11", "Back to To Do", "To Do"),
                   ("21", "Start Progress", "In Progress"),
                   ("31", "Finish", "Done")]
          for status in ("To Do", "In Progress", "In Review", "Done", "Won't Do",
                         "Duplicate")}
# The lifecycle-synchronization workflow: directed, with a review status and two
# discard statuses reachable from every open status.
_DISCARDS = [("51", "Won't Do", "Won't Do"), ("52", "Mark Duplicate", "Duplicate")]
SYNC = {
    "To Do": [("21", "Start Progress", "In Progress"), *_DISCARDS],
    "In Progress": [("41", "Ready for Review", "In Review"),
                    ("31", "Finish", "Done"), *_DISCARDS],
    "In Review": [("42", "Back to Progress", "In Progress"),
                  ("31", "Finish", "Done"), *_DISCARDS],
    "Done": [], "Won't Do": [], "Duplicate": [],
}
# `SYNC` with a second route out of the backlog status into `In Progress`. Two routes
# into `statuses.active` is what makes a configured `transitions.start` load-bearing:
# on `SYNC` the named transition and the one derived from the target status are the
# same id, so a test there cannot tell the two rules apart.
TWO_ROUTES_IN = {
    **SYNC,
    "To Do": [("21", "Start Progress", "In Progress"),
              ("22", "Fast Track", "In Progress"), *_DISCARDS],
}
# `SYNC` with a second route into `In Progress` that is still offered once the ticket
# is there. `Start Progress` excludes a second claimant and `Pick Up` does not, so this
# is the fixture on which `transitions.start` and `exclusive-claim-transition` can be
# told apart: name one in each key, and which key an exclusivity verdict came from
# shows in whether it refuses.
ONE_MUTEX_ONE_NOT = {
    **SYNC,
    "To Do": [("21", "Start Progress", "In Progress"),
              ("23", "Pick Up", "In Progress"), *_DISCARDS],
    "In Progress": [("23", "Pick Up", "In Progress"), *SYNC["In Progress"]],
}
# Two routes out of one status into `Done` — a "finished" one and an "abandoned" one —
# plus a pair sharing a name. Which transition ran cannot be read back from the status,
# which is the whole reason a project has to be able to name it.
_SAME_NAME = [("33", "Same Name", "Done"), ("34", "Same Name", "Done")]
AMBIGUOUS = {
    "To Do": [("21", "Start Progress", "In Progress")],
    "In Progress": [("31", "Finish", "Done"), ("32", "Abandon", "Done"),
                    ("41", "Ready for Review", "In Review"), *_SAME_NAME],
    "In Review": [("31", "Finish", "Done"), ("32", "Abandon", "Done"), *_SAME_NAME],
    "Done": [],
}
# A workflow with no shortcut: reaching `Done` means passing through `In Review`, so a
# ticket several rungs behind its item needs more than one transition to catch up.
STRICT_LADDER = {
    "To Do": [("21", "Start Progress", "In Progress")],
    "In Progress": [("41", "Ready for Review", "In Review")],
    "In Review": [("31", "Finish", "Done")],
    "Done": [],
}
# The same, with the last rung unreachable: a walk that gets part of the way.
BROKEN_LADDER = {**STRICT_LADDER, "In Review": []}
CATEGORY = {"To Do": "new", "In Progress": "indeterminate", "Done": "done",
            "Triage": "new", "In Review": "indeterminate", "Won't Do": "done",
            "Duplicate": "done"}


@dataclass
class Ticket:
    id: str
    key: str
    summary: str
    status: str = "To Do"
    assignee: str | None = None           # account id
    description: str | None = "The ticket's product text."
    comments: list = field(default_factory=list)      # (author account id, document)


@dataclass
class _Hook:
    method: str
    fragment: str
    account: str | None
    run: object = None
    error: Exception | None = None
    apply_first: bool = False
    used: bool = False


@dataclass
class FakeJira:
    workflow: dict = field(default_factory=lambda: DIRECTED)
    accounts: dict = field(default_factory=dict)      # email → (account id, name)
    tickets: dict = field(default_factory=dict)       # id → Ticket
    requests: list = field(default_factory=list)      # (method, path, account id)
    hooks: list = field(default_factory=list)
    down: bool = False                                # every request unreachable
    site: str | None = None                           # the base URL it answers for
    applied: list = field(default_factory=list)       # transition ids actually applied

    # -- setup --

    def account(self, email: str, account_id: str, name: str) -> None:
        self.accounts[email] = (account_id, name)

    def ticket(self, **values) -> Ticket:
        ticket = Ticket(**values)
        self.tickets[ticket.id] = ticket
        return ticket

    def before(self, method: str, fragment: str, run, *, account: str | None = None):
        self.hooks.append(_Hook(method, fragment, account, run=run))

    def fail(self, method: str, fragment: str, error: Exception, *,
             account: str | None = None, apply_first: bool = False):
        self.hooks.append(_Hook(method, fragment, account, error=error,
                                apply_first=apply_first))

    def install(self, monkeypatch) -> "FakeJira":
        fake = self

        def request(client, method, path, body=None, *, timeout=None):
            return fake.answer(client, method, path, body)

        monkeypatch.setattr(jira.JiraClient, "_request", request)
        return self

    # -- what tests read --

    def writes(self, account: str | None = None) -> list[tuple[str, str]]:
        return [(m, p) for m, p, a in self.requests
                if m in ("POST", "PUT") and (account is None or a == account)]

    # -- answering --

    def _find(self, ref: str) -> Ticket:
        for ticket in self.tickets.values():
            if ref in (ticket.id, ticket.key, ticket.key.lower()):
                return ticket
        raise jira._for_status(404, {}, "Issue does not exist", ref)

    def _offered(self, ticket: Ticket) -> list[tuple[str, str, str]]:
        return self.workflow.get(ticket.status, [])

    def answer(self, client, method: str, path: str, body):
        if self.down:
            raise jira.TrackerUnavailable(f"the tracker at {client.config.base_url} "
                                          f"could not be reached (fake: down)")
        email = os.environ.get(client.config.email_env, "")
        me = self.accounts.get(email)
        if me is None:
            raise jira._for_status(401, {}, "unknown account", path)
        self.requests.append((method, path, me[0]))
        for hook in self.hooks:
            if (not hook.used and hook.method == method and hook.fragment in path
                    and hook.account in (None, me[0])):
                hook.used = True
                if hook.run is not None:
                    hook.run()
                if hook.error is not None:
                    if hook.apply_first:
                        self._apply(me, method, path, body)
                    raise hook.error
        return self._apply(me, method, path, body)

    def _apply(self, me, method: str, path: str, body):
        if method == "GET" and path == "/rest/api/3/myself":
            return self._json({"accountId": me[0], "displayName": me[1]})
        if match := re.fullmatch(r"/rest/api/2/issue/([^/?]+)\?fields=description", path):
            return self._json({"fields": {"description": self._find(match[1]).description}})
        if match := re.fullmatch(r"/rest/api/3/issue/([^/?]+)/transitions", path):
            ticket = self._find(match[1])
            offered = self._offered(ticket)
            if method == "GET":
                return self._json({"transitions": [
                    {"id": tid, "name": name, "to": {"name": to, "id": to}}
                    for tid, name, to in offered]})
            wanted = body["transition"]["id"]
            for tid, _name, to in offered:
                if tid == wanted:
                    ticket.status = to
                    self.applied.append(tid)
                    return (204, {}, b"")
            raise jira._for_status(400, {}, f"Action {wanted} is invalid", path)
        if match := re.fullmatch(r"/rest/api/3/issue/([^/?]+)/comment", path):
            self._find(match[1]).comments.append((me[0], body["body"]))
            return self._json({"id": str(len(self._find(match[1]).comments))})
        if match := re.fullmatch(
                r"/rest/api/3/issue/([^/?]+)/comment\?orderBy=-created&maxResults=(\d+)",
                path):
            newest = list(reversed(self._find(match[1]).comments))[:int(match[2])]
            return self._json({"comments": [
                {"author": {"accountId": author}, "body": document}
                for author, document in newest]})
        if match := re.fullmatch(r"/rest/api/3/issue/([^/?]+)/assignee", path):
            # Only `None` or an account id this fake was told about. Real Jira
            # answers anything else with 400, and accepting it here once meant an
            # unassignment sent as `""` passed every test and would have failed in
            # production: `_issue` below reads `""` as unassigned, so the ticket
            # even looked right afterwards.
            account = body["accountId"]
            assert account is None or account in {
                aid for aid, _name in self.accounts.values()
            }, f"not an account this fake knows: {account!r}"
            self._find(match[1]).assignee = account
            return (204, {}, b"")
        if match := re.fullmatch(r"/rest/api/3/issue/([^/?]+)\?fields=.*", path):
            ticket = self._find(match[1].replace("%2F", "/"))
            return self._json(self._issue(ticket))
        raise AssertionError(f"the fake does not answer {method} {path}")

    def _issue(self, ticket: Ticket) -> dict:
        assignee = None
        if ticket.assignee:
            name = next((n for aid, n in self.accounts.values() if aid == ticket.assignee),
                        ticket.assignee)
            assignee = {"accountId": ticket.assignee, "displayName": name}
        return {"id": ticket.id, "key": ticket.key, "fields": {
            "summary": ticket.summary,
            "status": {"name": ticket.status,
                       "statusCategory": {"key": CATEGORY[ticket.status]}},
            "assignee": assignee,
            "description": None,
        }}

    @staticmethod
    def _json(payload: dict):
        return (200, {}, json.dumps(payload).encode("utf-8"))


def install_sites(monkeypatch, *fakes: FakeJira) -> None:
    """Route each request to the fake whose `site` is the calling client's base URL.

    `FakeJira.install` replaces `JiraClient._request` for the whole class, so two
    fakes installed that way overwrite each other and neither looks at the URL. A
    test about bindings from two Jira sites needs both, and needs a request to the
    wrong site to fail loudly rather than be answered.
    """
    by_site = {fake.site: fake for fake in fakes}

    def request(client, method, path, body=None, *, timeout=None):
        fake = by_site.get(client.config.base_url)
        if fake is None:
            raise AssertionError(f"no fake answers for {client.config.base_url}")
        return fake.answer(client, method, path, body)

    monkeypatch.setattr(jira.JiraClient, "_request", request)
