"""The Jira client: its single seam, and what every operation puts through it.

`_request` is the only function that touches `urllib.request`. It is the one
function a test replaces, so every operation is tested here through a recorded
stub: its method, path (with a key that needs quoting), query and body.

The timeout test is the one to keep. `urllib.request.urlopen` falls back to the
global socket default when no timeout is given, and that default is unset, so a
forgotten timeout is an indefinite hang rather than a slow call. The test walks the
operations rather than naming them individually, so an operation added without a
timeout fails it.
"""

from __future__ import annotations

import dataclasses
import io
import json
import socket
import time
import urllib.error

import pytest

from tcw.work.jira import client as jira
from tcw.work.jira.client import TrackerError, Transition


@dataclasses.dataclass(frozen=True)
class _Config:
    """The attributes the client reads from its configuration, and no more:
    it reads them only by name, so any object carrying them will do."""
    site: str
    email_env: str
    token_env: str
    timeout: float = 15


CONFIG = _Config(site="https://example.atlassian.net", email_env="TCW_PROBE_EMAIL",
                 token_env="TCW_PROBE_TOKEN", timeout=15)

#: A key holding characters that must be quoted in a path.
ODD = "A B/1"
QODD = "A%20B%2F1"


@pytest.fixture(autouse=True)
def _credentials(monkeypatch):
    monkeypatch.setenv("TCW_PROBE_EMAIL", "probe@example.test")
    monkeypatch.setenv("TCW_PROBE_TOKEN", "sentinel-token-value")


class Recorder:
    """Replaces `_request`; records every call and answers from `responses`,
    keyed by path, each a payload or a list of payloads given in turn."""

    def __init__(self, responses=None):
        self.calls = []
        self.responses = {k: (list(v) if isinstance(v, list) and v
                              and isinstance(v[0], Answer) else v)
                          for k, v in (responses or {}).items()}

    def __call__(self, method, path, body=None, *, timeout=None):
        self.calls.append({"method": method, "path": path, "body": body,
                           "timeout": timeout})
        answer = self.responses.get(path.split("?")[0] if path.split("?")[0]
                                    in self.responses else path, {})
        if isinstance(answer, list) and answer and isinstance(answer[0], Answer):
            answer = answer.pop(0).payload
        return 200, {}, json.dumps(answer).encode()

    @property
    def last(self):
        return self.calls[-1]


@dataclasses.dataclass
class Answer:
    payload: object


def _client(monkeypatch, recorder):
    client = jira.JiraClient(CONFIG)
    monkeypatch.setattr(client, "_request", recorder)
    return client


def call(rec):
    return rec.last["method"], rec.last["path"], rec.last["body"]


# ── reads ─────────────────────────────────────────────────────────────────────


def test_myself(monkeypatch):
    rec = Recorder({"/rest/api/3/myself": {"accountId": "a1"}})
    assert _client(monkeypatch, rec).myself() == {"accountId": "a1"}
    assert call(rec) == ("GET", "/rest/api/3/myself", None)


def test_issue_quotes_the_key_and_names_the_fields(monkeypatch):
    rec = Recorder()
    _client(monkeypatch, rec).issue(ODD, ("summary", "customfield_1"))
    assert call(rec) == ("GET", f"/rest/api/3/issue/{QODD}?fields=summary,customfield_1",
                         None)


def test_issue_with_no_fields_asks_for_the_default(monkeypatch):
    rec = Recorder()
    _client(monkeypatch, rec).issue("P-1")
    assert rec.last["path"] == "/rest/api/3/issue/P-1"


def test_search_reads_every_page(monkeypatch):
    path = "/rest/api/3/search/jql"
    rec = Recorder({path: [
        Answer({"issues": [{"key": "P-1"}], "nextPageToken": "t1", "isLast": False}),
        Answer({"issues": [{"key": "P-2"}], "nextPageToken": "t2", "isLast": False}),
        Answer({"issues": [{"key": "P-3"}], "isLast": True})]})
    found = _client(monkeypatch, rec).search('project = "P"', ["summary"])
    assert [i["key"] for i in found] == ["P-1", "P-2", "P-3"]
    bodies = [c["body"] for c in rec.calls]
    assert [b.get("nextPageToken") for b in bodies] == [None, "t1", "t2"]
    assert all(c["method"] == "POST" and c["path"] == path for c in rec.calls)
    assert bodies[0] == {"jql": 'project = "P"', "fields": ["summary"], "maxResults": 100}


def test_a_search_answer_that_does_not_say_there_is_more_ends_the_walk(monkeypatch):
    rec = Recorder({"/rest/api/3/search/jql": {"issues": [], "nextPageToken": "t"}})
    assert _client(monkeypatch, rec).search("x", []) == []
    assert len(rec.calls) == 1


def test_transitions_expand_their_screen_fields(monkeypatch):
    rec = Recorder({f"/rest/api/3/issue/{QODD}/transitions": {"transitions": [
        {"id": "11", "name": "Plan", "to": {"name": "Planning", "id": "3"},
         "fields": {"comment": {"required": False}, "resolution": {"required": True}}},
        {"id": "12", "name": "Go", "to": {"name": "Done", "id": "4"}}]}})
    found = _client(monkeypatch, rec).transitions(ODD)
    assert rec.last["path"] == (f"/rest/api/3/issue/{QODD}/transitions"
                                "?expand=transitions.fields")
    assert found == [Transition("11", "Plan", "Planning", "3",
                                ("comment", "resolution"), ("resolution",)),
                     Transition("12", "Go", "Done", "4")]


def test_comments_page_newest_first_up_to_the_limit(monkeypatch):
    def page(start, count):
        return {"startAt": start, "total": 150, "comments": [
            {"author": {"accountId": f"a{n}", "displayName": f"N{n}"},
             "created": f"2026-10-0{1 + n % 9}T10:00:00.000+0000",
             "body": {"type": "doc", "content": []}}
            for n in range(start, start + count)]}
    base = f"/rest/api/3/issue/{QODD}/comment"
    rec = Recorder()
    answers = [page(0, 100), page(100, 50)]
    rec.responses = {}

    def answer(method, path, body=None, *, timeout=None):
        rec.calls.append({"method": method, "path": path, "body": body,
                          "timeout": timeout})
        return 200, {}, json.dumps(answers.pop(0)).encode()

    client = jira.JiraClient(CONFIG)
    monkeypatch.setattr(client, "_request", answer)
    found = client.comments(ODD, 150)
    assert len(found) == 150
    assert [c["path"] for c in rec.calls] == [
        f"{base}?orderBy=-created&startAt=0&maxResults=100",
        f"{base}?orderBy=-created&startAt=100&maxResults=50"]
    assert found[0].author_id == "a0" and found[0].author_name == "N0"


def test_comments_with_no_limit_read_every_page(monkeypatch):
    def page(start, count):
        return {"total": 230, "comments": [
            {"author": None, "created": "x", "body": None}] * count}
    answers = [page(0, 100), page(100, 100), page(200, 30)]
    paths = []

    def answer(method, path, body=None, *, timeout=None):
        paths.append(path)
        return 200, {}, json.dumps(answers.pop(0)).encode()

    client = jira.JiraClient(CONFIG)
    monkeypatch.setattr(client, "_request", answer)
    assert len(client.comments("P-1", None)) == 230
    assert [p.split("startAt=")[1] for p in paths] == [
        "0&maxResults=100", "100&maxResults=100", "200&maxResults=100"]


def test_comments_stop_at_the_limit(monkeypatch):
    rec = Recorder({"/rest/api/3/issue/P-1/comment": {"total": 500, "comments": [
        {"author": None, "created": "x", "body": None}] * 10}})
    found = _client(monkeypatch, rec).comments("P-1", 10)
    assert len(found) == 10 and len(rec.calls) == 1
    assert "maxResults=10" in rec.last["path"]
    assert found[0].author_id is None


def test_user_and_assignable_users(monkeypatch):
    rec = Recorder({"/rest/api/3/user/assignable/search": [{"accountId": "a"}]})
    client = _client(monkeypatch, rec)
    client.user("id:1/2")
    assert rec.last["path"] == "/rest/api/3/user?accountId=id%3A1%2F2"
    assert client.assignable_users("P", "ann b", 20) == [{"accountId": "a"}]
    assert rec.last["path"] == ("/rest/api/3/user/assignable/search?project=P"
                                "&query=ann%20b&maxResults=20")


def test_project_reads(monkeypatch):
    rec = Recorder({f"/rest/api/3/project/{QODD}": {"id": "1", "issueTypes": []},
                    f"/rest/api/3/project/{QODD}/statuses": [{"statuses": []}]})
    client = _client(monkeypatch, rec)
    assert client.project(ODD)["id"] == "1"
    assert client.project_statuses(ODD) == [{"statuses": []}]
    assert rec.last == {"method": "GET", "path": f"/rest/api/3/project/{QODD}/statuses",
                        "body": None, "timeout": 15}


def test_create_metadata_pages(monkeypatch):
    base = f"/rest/api/3/issue/createmeta/{QODD}/issuetypes/10001"
    answers = [{"total": 3, "fields": [{"fieldId": "a"}, {"fieldId": "b"}]},
               {"total": 3, "fields": [{"fieldId": "c"}]}]
    paths = []

    def answer(method, path, body=None, *, timeout=None):
        paths.append(path)
        return 200, {}, json.dumps(answers.pop(0)).encode()

    client = jira.JiraClient(CONFIG)
    monkeypatch.setattr(client, "_request", answer)
    assert [f["fieldId"] for f in client.create_metadata(ODD, "10001")] == ["a", "b", "c"]
    assert paths == [f"{base}?startAt=0&maxResults=100", f"{base}?startAt=2&maxResults=100"]


def test_edit_metadata_link_types_and_workflows(monkeypatch):
    rec = Recorder({f"/rest/api/3/issue/{QODD}/editmeta": {"fields": {"summary": {}}},
                    "/rest/api/3/issueLinkType": {"issueLinkTypes": [{"name": "Blocks"}]},
                    "/rest/api/3/workflows": {"workflows": [{"id": "w"}],
                                              "statuses": [{"name": "Done"}]}})
    client = _client(monkeypatch, rec)
    assert client.edit_metadata(ODD) == {"summary": {}}
    assert client.link_types() == [{"name": "Blocks"}]
    assert client.workflows("10000", "10001") == {"workflows": [{"id": "w"}],
                                                  "statuses": [{"name": "Done"}]}
    assert call(rec) == ("POST", "/rest/api/3/workflows", {"projectAndIssueTypes": [
        {"projectId": "10000", "issueTypeId": "10001"}]})


# ── writes ────────────────────────────────────────────────────────────────────


def test_create_issue_sends_the_whole_fields_mapping(monkeypatch):
    rec = Recorder({"/rest/api/3/issue": {"id": "1", "key": "P-1"}})
    fields = {"project": {"key": "P"}, "summary": "s", "labels": ["a"]}
    assert _client(monkeypatch, rec).create_issue(fields) == {"id": "1", "key": "P-1"}
    assert call(rec) == ("POST", "/rest/api/3/issue", {"fields": fields})


def test_edit_issue_sends_fields_and_update(monkeypatch):
    rec = Recorder()
    _client(monkeypatch, rec).edit_issue(ODD, {"summary": "t"},
                                         {"labels": [{"add": "x"}]})
    assert call(rec) == ("PUT", f"/rest/api/3/issue/{QODD}",
                         {"fields": {"summary": "t"}, "update": {"labels": [{"add": "x"}]}})


def test_apply_transition_with_and_without_a_comment(monkeypatch):
    rec = Recorder()
    client = _client(monkeypatch, rec)
    client.apply_transition(ODD, "21")
    assert call(rec) == ("POST", f"/rest/api/3/issue/{QODD}/transitions",
                         {"transition": {"id": "21"}})
    doc = {"type": "doc", "version": 1, "content": []}
    client.apply_transition(ODD, "21", doc)
    assert rec.last["body"] == {"transition": {"id": "21"}, "update": {
        "comment": [{"add": {"body": doc}}]}}


def test_add_comment_posts_a_document(monkeypatch):
    rec = Recorder()
    doc = {"type": "doc", "version": 1, "content": []}
    _client(monkeypatch, rec).add_comment(ODD, doc)
    assert call(rec) == ("POST", f"/rest/api/3/issue/{QODD}/comment", {"body": doc})


def test_links(monkeypatch):
    rec = Recorder()
    client = _client(monkeypatch, rec)
    client.add_link("Blocks", "P-2", "P-1")
    assert call(rec) == ("POST", "/rest/api/3/issueLink", {
        "type": {"name": "Blocks"}, "inwardIssue": {"key": "P-2"},
        "outwardIssue": {"key": "P-1"}})
    client.delete_link("10/1")
    assert call(rec) == ("DELETE", "/rest/api/3/issueLink/10%2F1", None)


def test_a_write_answered_with_no_content_succeeds(monkeypatch):
    client = jira.JiraClient(CONFIG)
    monkeypatch.setattr(client, "_request",
                        lambda *a, **k: (204, {}, b""))
    client.edit_issue("P-1", {"summary": "s"})


# ── every operation passes a timeout ─────────────────────────────────────────

OPERATIONS = {
    "myself": (), "issue": ("P-1",), "search": ("x", ()), "transitions": ("P-1",),
    "comments": ("P-1", 5), "user": ("a",), "assignable_users": ("P", "q", 5),
    "project": ("P",), "project_statuses": ("P",), "create_metadata": ("P", "1"),
    "edit_metadata": ("P-1",), "link_types": (), "workflows": ("1", "2"),
    "create_issue": ({},), "edit_issue": ("P-1", {"summary": "s"}),
    "apply_transition": ("P-1", "1"), "add_comment": ("P-1", {}),
    "add_link": ("Blocks", "P-1", "P-2"), "delete_link": ("1",),
}


def test_every_operation_is_accounted_for_here():
    """If an operation is added and not listed above, the timeout test below would
    silently stop covering it. This is what makes that impossible."""
    public = {name for name in vars(jira.JiraClient)
              if not name.startswith("_") and callable(getattr(jira.JiraClient, name))}
    assert public == set(OPERATIONS), public ^ set(OPERATIONS)


@pytest.mark.parametrize("name", sorted(OPERATIONS))
def test_every_operation_passes_an_explicit_timeout(monkeypatch, name):
    rec = Recorder({"/rest/api/3/user/assignable/search": [],
                    "/rest/api/3/project/P/statuses": []})
    client = jira.JiraClient(CONFIG)
    monkeypatch.setattr(client, "_request", rec)
    getattr(client, name)(*OPERATIONS[name])
    assert rec.calls and all(c["timeout"] == CONFIG.timeout for c in rec.calls), (
        f"{name} did not pass a timeout; urlopen would block forever")


# ── the seam itself ──────────────────────────────────────────────────────────


def test_the_authorization_header_is_built_from_the_named_variables(monkeypatch):
    """The only place credentials are read. Asserted on the header rather than on
    an attribute, because the config must never hold the value."""
    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["headers"] = dict(request.headers)
        captured["timeout"] = timeout
        captured["url"] = request.full_url

        class R:
            status = 200
            headers = {}

            def read(self):
                return b"{}"

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        return R()

    monkeypatch.setattr(jira.urllib.request, "urlopen", fake_urlopen)
    jira.JiraClient(CONFIG).myself()
    auth = next(v for k, v in captured["headers"].items() if k.lower() == "authorization")
    assert auth.startswith("Basic ")
    import base64
    decoded = base64.b64decode(auth.split(" ", 1)[1]).decode()
    assert decoded == "probe@example.test:sentinel-token-value"
    assert captured["timeout"] == 15
    assert captured["url"].startswith("https://example.atlassian.net/")


def test_a_missing_credential_variable_is_a_clear_error(monkeypatch):
    monkeypatch.delenv("TCW_PROBE_TOKEN", raising=False)
    with pytest.raises(jira.TrackerError) as excinfo:
        jira.JiraClient(CONFIG).myself()
    assert "TCW_PROBE_TOKEN" in str(excinfo.value)


# ── the error taxonomy ───────────────────────────────────────────────────────
#
# Six causes, each its own type. The justification is that all six are reachable
# from this item alone: a wrong token (401), a query selecting a project the
# account cannot browse (403), `tracker show` on a bad key (404), a malformed
# candidate query (400), a tight loop of list calls (429), and an unreachable
# tracker (5xx or a timeout).


def _raise_http(monkeypatch, status, headers=None, body=b"{}"):
    """Make urlopen raise HTTPError with a given status."""
    def fake_urlopen(request, timeout=None):
        raise urllib.error.HTTPError(
            request.full_url, status, "boom", headers or {}, io.BytesIO(body))
    monkeypatch.setattr(jira.urllib.request, "urlopen", fake_urlopen)


@pytest.mark.parametrize("status,expected", [
    (401, jira.TrackerAuthError),
    (403, jira.TrackerPermissionError),
    (404, jira.TrackerNotFound),
    (400, jira.TrackerRequestInvalid),
    (429, jira.TrackerRateLimited),
    (500, jira.TrackerUnavailable),
    (503, jira.TrackerUnavailable),
])
def test_each_status_raises_its_own_cause(monkeypatch, status, expected):
    _raise_http(monkeypatch, status)
    with pytest.raises(expected):
        jira.JiraClient(CONFIG).myself()


def test_every_cause_is_a_tracker_error(monkeypatch):
    """So a caller that wants to handle all of them can, with one except."""
    for status in (400, 401, 403, 404, 429, 500):
        _raise_http(monkeypatch, status)
        with pytest.raises(jira.TrackerError):
            jira.JiraClient(CONFIG).myself()


def test_rate_limiting_carries_retry_after_when_given(monkeypatch):
    _raise_http(monkeypatch, 429, headers={"Retry-After": "30"})
    with pytest.raises(jira.TrackerRateLimited) as excinfo:
        jira.JiraClient(CONFIG).myself()
    assert excinfo.value.retry_after == "30"
    assert "30" in str(excinfo.value)


def test_rate_limiting_without_retry_after_still_raises_cleanly(monkeypatch):
    _raise_http(monkeypatch, 429)
    with pytest.raises(jira.TrackerRateLimited) as excinfo:
        jira.JiraClient(CONFIG).myself()
    assert excinfo.value.retry_after is None


def test_an_auth_failure_names_the_variable_to_fix(monkeypatch):
    """A user who sees "rejected" needs to know which variable to look at."""
    _raise_http(monkeypatch, 401)
    with pytest.raises(jira.TrackerAuthError) as excinfo:
        jira.JiraClient(CONFIG).myself()
    assert "work.jira.credentials" in str(excinfo.value)


def test_an_unavailable_tracker_names_the_timeout(monkeypatch):
    _raise_http(monkeypatch, 503)
    with pytest.raises(jira.TrackerUnavailable):
        jira.JiraClient(CONFIG).myself()


def test_a_refused_connection_is_unavailable_not_invalid(monkeypatch):
    def fake_urlopen(request, timeout=None):
        raise urllib.error.URLError(ConnectionRefusedError("refused"))
    monkeypatch.setattr(jira.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(jira.TrackerUnavailable):
        jira.JiraClient(CONFIG).myself()


def test_no_cause_is_named_for_contention(monkeypatch):
    """The standing guard. A live experiment recorded three different 400 bodies
    for one condition — a rejected transition, a bad transition id, and a lost
    race — one of which blames permissions. Inferring "already claimed" from a
    status or a body would encode a guess as a fact. Deciding that needs a re-read
    of the issue, which is the next child's job, not the transport's.
    """
    names = [n for n in vars(jira) if n.startswith("Tracker")]
    assert names, "no exception types found; this test would pass vacuously"
    for name in names:
        assert "conflict" not in name.lower(), name
        assert "claimed" not in name.lower(), name

    # And the behavioural half, which a name check cannot give: the same status
    # with different bodies must produce the same type. If anything ever branches
    # on the body — the thing the experiment proved unsafe — this fails.
    bodies = [
        "Action 21 is invalid",
        "Transition id '999' is not valid for this issue.",
        "Can't move (X-1). You might not have permission, or the work item is "
        "missing required information.",
        "",
    ]
    kinds = {type(jira._for_status(400, {}, body, "/p")) for body in bodies}
    assert kinds == {jira.TrackerRequestInvalid}, kinds


def test_a_400_body_is_carried_but_not_interpreted(monkeypatch):
    """The body reaches the message so a human can read it; nothing branches on it."""
    _raise_http(monkeypatch, 400, body=b'{"errorMessages":["Action 21 is invalid"]}')
    with pytest.raises(jira.TrackerRequestInvalid) as excinfo:
        jira.JiraClient(CONFIG).myself()
    assert "Action 21 is invalid" in str(excinfo.value)


# ── the real socket: the one place a urllib mistake cannot hide ──────────────


def test_a_server_that_never_answers_times_out_rather_than_hanging():
    """The riskiest behaviour in the item, and the only test here that uses a real
    socket. Every other test replaces the transport, so none of them would notice
    a missing or ignored timeout in the actual `urlopen` call. This one binds a
    listening socket that accepts a connection and never writes a byte.
    """
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    try:
        config = dataclasses.replace(
            CONFIG, site=f"http://127.0.0.1:{port}", timeout=1)
        started = time.monotonic()
        with pytest.raises(jira.TrackerUnavailable):
            jira.JiraClient(config).myself()
        elapsed = time.monotonic() - started
        assert elapsed < 10, f"took {elapsed:.1f}s; the timeout was not honoured"
    finally:
        listener.close()


def test_a_server_that_drops_the_connection_is_unavailable_not_a_crash():
    """A connection closed after the request was sent raises
    `http.client.RemoteDisconnected`, which is not a `URLError`. Uncaught, it
    escaped every command as a traceback — and for a claim, a write that may or may
    not have landed has to reach the caller as "unavailable" so the ticket is read
    back rather than the command dying."""
    import threading

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]

    def accept_read_and_close():
        connection, _ = listener.accept()
        connection.recv(65536)
        connection.close()

    thread = threading.Thread(target=accept_read_and_close, daemon=True)
    thread.start()
    try:
        config = dataclasses.replace(
            CONFIG, site=f"http://127.0.0.1:{port}", timeout=5)
        with pytest.raises(jira.TrackerUnavailable, match="connection"):
            jira.JiraClient(config).apply_transition("TCW-1", "21")
    finally:
        thread.join(timeout=5)
        listener.close()


# ── each read refuses a response of the wrong shape ──────────────────────────


def respond(path: str, payload) -> Recorder:
    return Recorder({path: payload})


KEY = "SYNC-1"
CALLS = {
    "myself": ("/rest/api/3/myself", lambda c: c.myself()),
    "issue": (f"/rest/api/3/issue/{KEY}", lambda c: c.issue(KEY)),
    "search": ("/rest/api/3/search/jql", lambda c: c.search("x", ())),
    "transitions": (f"/rest/api/3/issue/{KEY}/transitions", lambda c: c.transitions(KEY)),
    "comments": (f"/rest/api/3/issue/{KEY}/comment", lambda c: c.comments(KEY, 5)),
    "project": ("/rest/api/3/project/P", lambda c: c.project("P")),
    "project_statuses": ("/rest/api/3/project/P/statuses",
                         lambda c: c.project_statuses("P")),
    "create_metadata": ("/rest/api/3/issue/createmeta/P/issuetypes/1",
                        lambda c: c.create_metadata("P", "1")),
    "edit_metadata": (f"/rest/api/3/issue/{KEY}/editmeta", lambda c: c.edit_metadata(KEY)),
    "link_types": ("/rest/api/3/issueLinkType", lambda c: c.link_types()),
    "workflows": ("/rest/api/3/workflows", lambda c: c.workflows("1", "2")),
    "assignable_users": ("/rest/api/3/user/assignable/search",
                         lambda c: c.assignable_users("P", "q", 5)),
}

BAD = [
    ("myself", []),
    ("issue", ["not", "a", "mapping"]),
    ("issue", {"fields": []}),
    ("issue", {"fields": {"status": "Done"}}),
    ("issue", {"fields": {"status": {"statusCategory": 3}}}),
    ("issue", {"fields": {"assignee": ["a"]}}),
    ("issue", {"fields": {"status": {"name": 5}}}),
    ("issue", {"key": 1, "fields": {}}),
    ("issue", {"fields": {"summary": ["s"]}}),
    ("issue", {"fields": {"assignee": {"displayName": {"x": 1}}}}),
    ("search", {"issues": {"a": 1}}),
    ("search", {"issues": ["TCW-1"]}),
    ("search", {"issues": [{"fields": {"status": 1}}]}),
    ("search", {"issues": [{"fields": {"status": {"statusCategory": {"key": 2}}}}]}),
    ("transitions", {"transitions": "all"}),
    ("transitions", {"transitions": [7]}),
    ("transitions", {"transitions": [{"id": "1", "to": "Done"}]}),
    ("transitions", {"transitions": [{"id": "1", "fields": ["comment"]}]}),
    ("comments", {"comments": {"x": 1}}),
    ("comments", {"comments": ["hi"]}),
    ("comments", {"comments": [{"author": {"accountId": 5}}]}),
    ("project", {"issueTypes": "Task"}),
    ("project_statuses", {"not": "a list"}),
    ("project_statuses", [{"statuses": "Done"}]),
    ("create_metadata", {"fields": "x"}),
    ("edit_metadata", {"fields": []}),
    ("link_types", {"issueLinkTypes": "Blocks"}),
    ("workflows", {"workflows": {"a": 1}}),
    ("workflows", {"workflows": [], "statuses": "Done"}),
    ("assignable_users", {"accountId": "a"}),
    # `create_issue` is deliberately absent: its answer is returned as it came,
    # since the request may have made the ticket whatever the answer looks like.
]


@pytest.mark.parametrize("operation, payload", BAD,
                         ids=[f"{op}-{i}" for i, (op, _) in enumerate(BAD)])
def test_a_response_of_the_wrong_shape_is_a_tracker_error(monkeypatch, operation, payload):
    path, run = CALLS[operation]
    client = _client(monkeypatch, respond(path, payload))
    with pytest.raises(TrackerError, match="unexpected shape"):
        run(client)


def test_nulls_the_code_already_treats_as_absent_still_read(monkeypatch):
    payload = {"id": "1", "key": KEY,
               "fields": {"summary": "s", "status": {"name": "To Do", "statusCategory": None},
                          "assignee": None, "description": None}}
    assert _client(monkeypatch, respond(f"/rest/api/3/issue/{KEY}", payload)).issue(
        KEY)["key"] == KEY
    comments = {"comments": [{"author": None, "body": {"content": "not a list"}}]}
    found = _client(monkeypatch, respond(f"/rest/api/3/issue/{KEY}/comment",
                                         comments)).comments(KEY, 5)
    assert (found[0].author_id, found[0].body) == (None, {"content": "not a list"})
