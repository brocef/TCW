"""The Jira client: its single seam, and what every operation puts through it.

`_request` is the only function that touches `urllib.request`. That is a design
decision rather than an implementation detail, because it is the one function a
test replaces, and four of this item's acceptance criteria depend on replacing it.

The timeout test is the one to keep. `urllib.request.urlopen` falls back to the
global socket default when no timeout is given, and that default is unset, so a
forgotten timeout is an indefinite hang rather than a slow call. The test walks the
operations rather than naming them individually, so a sixth operation added without
a timeout fails it.
"""

from __future__ import annotations

import dataclasses
import io
import json
import pathlib
import socket
import time
import urllib.error

import pytest

from tcw.store.base import TrackerConfig
from tcw.tracker import jira

CONFIG = TrackerConfig(
    provider="jira-cloud",
    base_url="https://example.atlassian.net",
    candidate_query='assignee = currentUser() AND status = "To Do"',
    email_env="TCW_PROBE_EMAIL",
    token_env="TCW_PROBE_TOKEN",
    start_transition="Start Progress",
    timeout_seconds=15,
)


@pytest.fixture(autouse=True)
def _credentials(monkeypatch):
    monkeypatch.setenv("TCW_PROBE_EMAIL", "probe@example.test")
    monkeypatch.setenv("TCW_PROBE_TOKEN", "sentinel-token-value")


class Recorder:
    """Replaces `_request`; records every call and returns canned responses."""

    def __init__(self, responses=None):
        self.calls = []
        self.responses = responses or {}

    def __call__(self, method, path, body=None, *, timeout=None):
        self.calls.append({"method": method, "path": path, "body": body,
                           "timeout": timeout})
        return self.responses.get(path, (200, {}, b"{}"))

    @property
    def last(self):
        return self.calls[-1]


def _client(monkeypatch, recorder):
    client = jira.JiraClient(CONFIG)
    monkeypatch.setattr(client, "_request", recorder)
    return client


# ── each operation's shape ───────────────────────────────────────────────────


def test_myself_gets_the_current_user(monkeypatch):
    rec = Recorder({"/rest/api/3/myself": (200, {}, json.dumps(
        {"accountId": "abc", "displayName": "Probe",
         "emailAddress": "probe@example.test"}).encode())})
    who = _client(monkeypatch, rec).myself()
    assert rec.last["method"] == "GET"
    assert rec.last["path"] == "/rest/api/3/myself"
    assert who["accountId"] == "abc"


def test_search_posts_the_configured_query(monkeypatch):
    rec = Recorder()
    _client(monkeypatch, rec).search(CONFIG.candidate_query)
    assert rec.last["method"] == "POST"
    assert CONFIG.candidate_query == rec.last["body"]["jql"]


def test_search_sends_a_default_limit(monkeypatch):
    rec = Recorder()
    _client(monkeypatch, rec).search("project = X")
    assert rec.last["body"]["maxResults"] == jira.DEFAULT_SEARCH_LIMIT


def test_search_uses_the_endpoint_that_still_exists(monkeypatch):
    """`/rest/api/3/search` has been removed by Atlassian. A live call returns 400
    naming `/rest/api/3/search/jql` as the replacement. Found by running against a
    real site, which is why this assertion is on the path."""
    rec = Recorder()
    _client(monkeypatch, rec).search("project = X")
    assert rec.last["path"] == "/rest/api/3/search/jql"


def test_search_reports_truncation_rather_than_hiding_it(monkeypatch):
    """Silently returning a short list would make a user believe they have no
    other assigned tickets. The endpoint reports `isLast`, not a count."""
    payload = {"issues": [{"key": f"X-{n}"} for n in range(3)],
               "isLast": False, "nextPageToken": "abc"}

    def respond(method, path, body=None, *, timeout=None):
        return (200, {}, json.dumps(payload).encode())

    client = jira.JiraClient(CONFIG)
    monkeypatch.setattr(client, "_request", respond)
    result = client.search("project = X", limit=3)
    assert len(result.issues) == 3
    assert result.truncated is True


def test_search_is_not_truncated_when_everything_fits(monkeypatch):
    payload = {"issues": [{"key": "X-1"}], "isLast": True}

    def respond(method, path, body=None, *, timeout=None):
        return (200, {}, json.dumps(payload).encode())

    client = jira.JiraClient(CONFIG)
    monkeypatch.setattr(client, "_request", respond)
    assert client.search("project = X", limit=50).truncated is False


def test_a_response_that_does_not_say_there_is_more_is_not_truncated(monkeypatch):
    """`isLast` absent must not read as truncated. Claiming there is more when the
    response never said so would send a user hunting for tickets that do not exist."""
    def respond(method, path, body=None, *, timeout=None):
        return (200, {}, json.dumps({"issues": [{"key": "X-1"}]}).encode())

    client = jira.JiraClient(CONFIG)
    monkeypatch.setattr(client, "_request", respond)
    assert client.search("project = X").truncated is False


def test_issue_gets_one_ticket_by_key(monkeypatch):
    rec = Recorder()
    _client(monkeypatch, rec).issue("TCWCLAIM-1")
    assert rec.last["method"] == "GET"
    assert "TCWCLAIM-1" in rec.last["path"]


def test_transitions_reads_what_the_issue_offers_now(monkeypatch):
    rec = Recorder()
    rec.responses = {}
    payload = {"transitions": [
        {"id": "21", "name": "Start Progress", "to": {"name": "In Progress", "id": "3"}}]}

    def respond(method, path, body=None, *, timeout=None):
        rec.calls.append({"method": method, "path": path, "body": body,
                          "timeout": timeout})
        return (200, {}, json.dumps(payload).encode())

    client = jira.JiraClient(CONFIG)
    monkeypatch.setattr(client, "_request", respond)
    offered = client.transitions("TCWCLAIM-1")
    assert rec.last["method"] == "GET"
    assert rec.last["path"].endswith("/transitions")
    assert offered[0].name == "Start Progress"
    assert offered[0].to_status == "In Progress"


def test_issue_quotes_the_key_it_puts_in_the_path(monkeypatch):
    """The key is whatever the user typed. A slash in it must not reach a
    different resource."""
    rec = Recorder()
    _client(monkeypatch, rec).issue("a/b")
    assert rec.last["path"].startswith("/rest/api/3/issue/a%2Fb?")


def test_apply_transition_posts_the_transition_id_by_issue_id(monkeypatch):
    rec = Recorder()
    assert _client(monkeypatch, rec).apply_transition("10052", "21") is None
    assert rec.last["method"] == "POST"
    assert rec.last["path"] == "/rest/api/3/issue/10052/transitions"
    assert rec.last["body"] == {"transition": {"id": "21"}}


def test_assign_puts_the_account_id_by_issue_id(monkeypatch):
    rec = Recorder()
    assert _client(monkeypatch, rec).assign("10052", "acct-a") is None
    assert rec.last["method"] == "PUT"
    assert rec.last["path"] == "/rest/api/3/issue/10052/assignee"
    assert rec.last["body"] == {"accountId": "acct-a"}


def test_assign_unassigns_with_a_null_account_id(monkeypatch):
    """`None` is Jira's documented way to unassign, and the only one that works.

    An empty string is not an account id and the real endpoint answers it with 400;
    the fake tracker used to accept it, which is how a release could have gone green
    here and failed in production.
    """
    rec = Recorder()
    assert _client(monkeypatch, rec).assign("10052", None) is None
    assert rec.last["body"] == {"accountId": None}


def test_a_write_answered_with_no_content_succeeds(monkeypatch):
    """Jira answers both writes with 204 and an empty body."""
    rec = Recorder({"/rest/api/3/issue/10052/transitions": (204, {}, b""),
                    "/rest/api/3/issue/10052/assignee": (204, {}, b"")})
    client = _client(monkeypatch, rec)
    client.apply_transition("10052", "21")
    client.assign("10052", "acct-a")


def test_description_reads_the_plain_text_form(monkeypatch):
    """The v2 endpoint returns the description as a wiki-markup string; v3 returns
    a document tree this module would otherwise have to convert."""
    path = "/rest/api/2/issue/10052?fields=description"
    rec = Recorder({path: (200, {}, json.dumps(
        {"fields": {"description": "h2. Problem\n\nIt is broken."}}).encode())})
    assert _client(monkeypatch, rec).description("10052") == "h2. Problem\n\nIt is broken."
    assert (rec.last["method"], rec.last["path"]) == ("GET", path)


@pytest.mark.parametrize("value", [None, {"type": "doc"}])
def test_a_missing_or_unexpected_description_is_empty(monkeypatch, value):
    path = "/rest/api/2/issue/10052?fields=description"
    rec = Recorder({path: (200, {}, json.dumps({"fields": {"description": value}}).encode())})
    assert _client(monkeypatch, rec).description("10052") == ""


def test_add_comment_posts_a_document(monkeypatch):
    rec = Recorder()
    doc = {"type": "doc", "version": 1, "content": []}
    _client(monkeypatch, rec).add_comment("10052", doc)
    assert (rec.last["method"], rec.last["path"], rec.last["body"]) == (
        "POST", "/rest/api/3/issue/10052/comment", {"body": doc})


def test_recent_comments_are_newest_first_with_their_text(monkeypatch):
    path = "/rest/api/3/issue/10052/comment?orderBy=-created&maxResults=100"
    body = {"type": "doc", "version": 1, "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "TCW: "},
                                          {"type": "text", "text": "done."}]},
        {"type": "paragraph", "content": [{"type": "text", "text": "tcw-event: x-1"}]}]}
    rec = Recorder({path: (200, {}, json.dumps({"comments": [
        {"author": {"accountId": "acct-a"}, "body": body},
        {"author": None, "body": "not a document"},
    ]}).encode())})
    assert _client(monkeypatch, rec).recent_comments("10052") == [
        ("acct-a", "TCW: done.\ntcw-event: x-1"), ("", "")]
    assert (rec.last["method"], rec.last["path"]) == ("GET", path)


# ── the timeout, on every operation ──────────────────────────────────────────


OPERATIONS = [
    ("myself", ()),
    ("search", ("project = X",)),
    ("issue", ("X-1",)),
    ("transitions", ("X-1",)),
    ("apply_transition", ("10052", "21")),
    ("assign", ("10052", "acct-a")),
    ("description", ("10052",)),
    ("add_comment", ("10052", {"type": "doc", "version": 1, "content": []})),
    ("recent_comments", ("10052",)),
]


def test_every_operation_is_accounted_for_here():
    """If an operation is added and not listed above, the timeout test below would
    silently stop covering it. This is what makes that impossible."""
    public = {name for name in vars(jira.JiraClient)
              if not name.startswith("_") and callable(getattr(jira.JiraClient, name))}
    assert public == {name for name, _ in OPERATIONS}, public


@pytest.mark.parametrize("name,args", OPERATIONS)
def test_every_operation_passes_an_explicit_timeout(monkeypatch, name, args):
    rec = Recorder()
    client = jira.JiraClient(CONFIG)
    monkeypatch.setattr(client, "_request", rec)
    getattr(client, name)(*args)
    assert rec.last["timeout"] == CONFIG.timeout_seconds, (
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
    assert "work.tracker.credentials" in str(excinfo.value)


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
            CONFIG, base_url=f"http://127.0.0.1:{port}", timeout_seconds=1)
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
            CONFIG, base_url=f"http://127.0.0.1:{port}", timeout_seconds=5)
        with pytest.raises(jira.TrackerUnavailable, match="connection"):
            jira.JiraClient(config).apply_transition("10052", "21")
    finally:
        thread.join(timeout=5)
        listener.close()
