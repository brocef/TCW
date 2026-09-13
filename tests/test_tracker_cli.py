"""`tcw work tracker list` and `show`.

Two properties this file exists to hold, beyond the obvious:

- **Each error cause produces its own message.** Six exception types that all print
  the same sentence would be six types nobody can act on. One test per cause.
- **No credential value reaches any output stream.** Every command and every error
  branch is exercised with a sentinel token, and the sentinel must appear nowhere.
"""

from __future__ import annotations

import json
import subprocess

import pytest
import yaml

from tcw.store.fs import init
from tcw.tracker import jira

SENTINEL = "sentinel-token-do-not-print"

TRACKER = {
    "provider": "jira-cloud",
    "base-url": "https://example.invalid",
    "candidate-query": "assignee = currentUser()",
    "credentials": {"email-env": "TCW_PROBE_EMAIL", "token-env": "TCW_PROBE_TOKEN"},
    "transitions": {"claim": "Start Progress"},
}

SEARCH_BODY = {
    "isLast": True,
    "issues": [
        {"key": "TCWCLAIM-1", "fields": {
            "summary": "A ticket that is ready", "status": {"name": "To Do"},
            "assignee": {"displayName": "Probe"}}},
        {"key": "TCWCLAIM-2", "fields": {
            "summary": "Another one", "status": {"name": "To Do"},
            "assignee": None}},
    ],
}

ISSUE_BODY = {
    "key": "TCWCLAIM-1",
    "fields": {"summary": "A ticket that is ready", "status": {"name": "To Do"},
               "assignee": {"displayName": "Probe"}, "description": None},
}

TRANSITIONS_BODY = {
    "transitions": [
        {"id": "21", "name": "Start Progress", "to": {"name": "In Progress", "id": "3"}},
    ],
}


@pytest.fixture()
def node(tmp_path, monkeypatch):
    root = tmp_path / "node"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    init(["work"], root, project_id="probe")
    monkeypatch.chdir(root)
    monkeypatch.setenv("TCW_PROBE_EMAIL", "probe@example.test")
    monkeypatch.setenv("TCW_PROBE_TOKEN", SENTINEL)

    def configure(tracker=TRACKER):
        config = {"id": "probe"}
        if tracker is not None:
            config["work"] = {"tracker": tracker}
        (root / "tcw-config.yaml").write_text(
            yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    return root, configure


def _run(argv):
    """Run the CLI in-process and capture streams plus exit code."""
    import contextlib
    import io

    from tcw.cli import main
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(argv)
        except SystemExit as exit_:
            code = exit_.code or 0
    return code, out.getvalue(), err.getvalue()


def _responses(monkeypatch, mapping):
    """Replace the transport with canned per-path responses."""
    def fake(self, method, path, body=None, *, timeout=None):
        for fragment, response in mapping.items():
            if fragment in path:
                if isinstance(response, Exception):
                    raise response
                return response
        return (200, {}, b"{}")
    monkeypatch.setattr(jira.JiraClient, "_request", fake)


OK_RESPONSES = {
    "/search": (200, {}, json.dumps(SEARCH_BODY).encode()),
    "/transitions": (200, {}, json.dumps(TRANSITIONS_BODY).encode()),
    "/issue/": (200, {}, json.dumps(ISSUE_BODY).encode()),
    "/myself": (200, {}, json.dumps({"accountId": "a"}).encode()),
}


# ── no tracker configured ────────────────────────────────────────────────────


@pytest.mark.parametrize("argv", [
    ["work", "tracker", "list"],
    ["work", "tracker", "show", "X-1"],
])
def test_with_no_tracker_configured_both_refuse_and_name_the_key(node, argv):
    root, configure = node
    configure(tracker=None)
    code, out, err = _run(argv)
    assert code != 0
    assert "work.tracker" in (out + err)


def test_a_malformed_tracker_refuses_rather_than_guessing(node):
    root, configure = node
    configure(tracker={"provider": "jira-cloud"})
    code, out, err = _run(["work", "tracker", "list"])
    assert code != 0
    assert "work.tracker" in (out + err)


# ── the happy paths ──────────────────────────────────────────────────────────


def test_list_prints_one_row_per_ticket(node, monkeypatch):
    root, configure = node
    configure()
    _responses(monkeypatch, OK_RESPONSES)
    code, out, err = _run(["work", "tracker", "list"])
    assert code == 0, err
    assert "TCWCLAIM-1" in out and "TCWCLAIM-2" in out
    assert "A ticket that is ready" in out
    assert "Probe" in out


def test_list_says_so_when_there_are_more_pages(node, monkeypatch):
    """No total is printed, because the endpoint does not report one. Printing a
    number that looks authoritative and is not would be worse than saying "more"."""
    root, configure = node
    configure()
    body = {"isLast": False, "nextPageToken": "abc", "issues": SEARCH_BODY["issues"]}
    _responses(monkeypatch, {**OK_RESPONSES,
                             "/search": (200, {}, json.dumps(body).encode())})
    code, out, err = _run(["work", "tracker", "list"])
    assert code == 0, err
    assert "more" in (out + err).lower()


def test_list_with_no_matching_tickets_is_not_an_error(node, monkeypatch):
    root, configure = node
    configure()
    body = {"isLast": True, "issues": []}
    _responses(monkeypatch, {**OK_RESPONSES,
                             "/search": (200, {}, json.dumps(body).encode())})
    code, out, err = _run(["work", "tracker", "list"])
    assert code == 0, err


def test_show_prints_the_ticket_and_its_claimability(node, monkeypatch):
    root, configure = node
    configure()
    _responses(monkeypatch, OK_RESPONSES)
    code, out, err = _run(["work", "tracker", "show", "TCWCLAIM-1"])
    assert code == 0, err
    assert "TCWCLAIM-1" in out
    assert "To Do" in out
    assert "claimable" in out.lower()


def test_show_uses_distinct_words_for_the_ticket_and_the_workflow(node, monkeypatch):
    """"claimable" is about this ticket; "exclusive" is about the workflow. One word
    for both would be true and misleading at once."""
    root, configure = node
    configure()
    _responses(monkeypatch, OK_RESPONSES)
    code, out, err = _run(["work", "tracker", "show", "TCWCLAIM-1"])
    assert code == 0, err
    lowered = out.lower()
    assert "claimable" in lowered
    assert "exclusiv" in lowered or "not determined" in lowered


# ── one message per cause ────────────────────────────────────────────────────


CAUSES = [
    (jira.TrackerAuthError("the tracker rejected the credentials; check "
                           "work.tracker.credentials"), "credentials"),
    (jira.TrackerPermissionError("the account is not permitted to see this"),
     "permitted"),
    (jira.TrackerNotFound("the tracker has no such resource"), "no such"),
    (jira.TrackerRequestInvalid("the tracker refused the request"), "refused"),
    (jira.TrackerRateLimited("the tracker is rate limiting requests", "30"),
     "rate limit"),
    (jira.TrackerUnavailable("could not reach the tracker"), "reach"),
]


@pytest.mark.parametrize("error,fragment", CAUSES)
def test_each_cause_produces_its_own_message(node, monkeypatch, error, fragment):
    root, configure = node
    configure()
    _responses(monkeypatch, {"/search": error, "/issue/": error,
                             "/transitions": error})
    code, out, err = _run(["work", "tracker", "list"])
    assert code != 0
    assert fragment in (out + err).lower(), (fragment, out, err)


def test_the_six_causes_produce_six_different_messages(node, monkeypatch):
    """Six types printing one sentence would be six types nobody can act on."""
    root, configure = node
    configure()
    messages = set()
    for error, _fragment in CAUSES:
        _responses(monkeypatch, {"/search": error})
        _code, out, err = _run(["work", "tracker", "list"])
        messages.add((out + err).strip())
    assert len(messages) == len(CAUSES), messages


# ── the sentinel must never appear ───────────────────────────────────────────


def test_no_command_or_error_path_prints_the_token(node, monkeypatch):
    root, configure = node
    configure()
    streams = []

    for argv in (["work", "tracker", "list"], ["work", "tracker", "show", "TCWCLAIM-1"]):
        _responses(monkeypatch, OK_RESPONSES)
        _code, out, err = _run(argv)
        streams.append(out + err)
        for error, _fragment in CAUSES:
            _responses(monkeypatch, {"/search": error, "/issue/": error,
                                     "/transitions": error})
            _code, out, err = _run(argv)
            streams.append(out + err)

    for captured in streams:
        assert SENTINEL not in captured, captured

    for path in root.rglob("*"):
        if path.is_file():
            assert SENTINEL not in path.read_text(encoding="utf-8", errors="ignore"), path
