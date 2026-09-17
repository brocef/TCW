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


# ── `tcw work inbox list`, `show` and `accept` with an inbox-query ───────────


INBOX_TRACKER = {**TRACKER, "inbox-query": "status = Triage"}

TRIAGE_BODY = {
    "isLast": True,
    "issues": [
        {"key": "EX-482", "fields": {
            "summary": "Login retries twice on a 502", "status": {"name": "Triage"},
            "assignee": None}},
    ],
}


def _recording(monkeypatch, mapping):
    """`_responses`, also keeping every request as (method, path, body)."""
    sent = []

    def fake(self, method, path, body=None, *, timeout=None):
        sent.append((method, path, body))
        for fragment, response in mapping.items():
            if fragment in path:
                if isinstance(response, Exception):
                    raise response
                return response
        return (200, {}, b"{}")
    monkeypatch.setattr(jira.JiraClient, "_request", fake)
    return sent


def _inbox_entry(root, name="2026-09-14-serve-accepts-writes.md", text="# Serve\n"):
    inbox = root / "docs/work/inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / name).write_text(text, encoding="utf-8")


TODAY = "2026-09-14-serve-accepts-writes.md | file | 2026-09-14-serve-accepts-writes\n"


@pytest.mark.parametrize("tracker", [None, TRACKER], ids=["no-tracker", "no-inbox-query"])
def test_inbox_list_without_an_inbox_query_is_unchanged(node, monkeypatch, tracker):
    root, configure = node
    configure(tracker=tracker)
    _inbox_entry(root)
    sent = _recording(monkeypatch, OK_RESPONSES)
    code, out, err = _run(["work", "inbox", "list"])
    assert (code, out, err) == (0, TODAY, "")
    assert sent == []


def test_inbox_list_with_a_broken_tracker_is_unchanged_but_says_so(node, monkeypatch):
    root, configure = node
    configure(tracker={**INBOX_TRACKER, "timeout-seconds": -1})
    _inbox_entry(root)
    sent = _recording(monkeypatch, OK_RESPONSES)
    code, out, err = _run(["work", "inbox", "list"])
    assert (code, out) == (0, TODAY)
    assert len(err.strip().splitlines()) == 1 and "tcw validate" in err
    assert sent == []


def test_inbox_list_prints_two_sections_from_the_inbox_query(node, monkeypatch):
    root, configure = node
    configure(tracker=INBOX_TRACKER)
    _inbox_entry(root)
    sent = _recording(monkeypatch, {"/search": (200, {}, json.dumps(TRIAGE_BODY).encode())})
    code, out, err = _run(["work", "inbox", "list"])
    assert (code, err) == (0, "")
    assert out == ("raw intake:\n  " + TODAY + "\ntracker tickets:\n"
                   "  EX-482 | Triage | unassigned | Login retries twice on a 502\n")
    [(_method, _path, body)] = sent
    assert body["jql"] == "status = Triage"


def test_inbox_list_marks_both_empty_sections(node, monkeypatch):
    root, configure = node
    configure(tracker=INBOX_TRACKER)
    _recording(monkeypatch, {"/search": (200, {}, b'{"isLast": true, "issues": []}')})
    code, out, err = _run(["work", "inbox", "list"])
    assert (code, err) == (0, "")
    assert out == "raw intake:\n  (none)\n\ntracker tickets:\n  (none)\n"


def test_inbox_list_says_there_are_more_naming_the_inbox_query(node, monkeypatch):
    root, configure = node
    configure(tracker=INBOX_TRACKER)
    body = {**TRIAGE_BODY, "isLast": False}
    _recording(monkeypatch, {"/search": (200, {}, json.dumps(body).encode())})
    code, out, err = _run(["work", "inbox", "list"])
    assert code == 0
    assert "work.tracker.inbox-query" in err and "candidate-query" not in err
    assert "EX-482" in out


def test_inbox_list_keeps_raw_intake_when_the_tracker_fails(node, monkeypatch):
    root, configure = node
    configure(tracker=INBOX_TRACKER)
    _inbox_entry(root)
    _recording(monkeypatch, {"/search": jira.TrackerUnavailable("the tracker is down")})
    code, out, err = _run(["work", "inbox", "list"])
    assert code != 0
    assert out == "raw intake:\n  " + TODAY + "\ntracker tickets:\n  (not listed)\n"
    assert "the tracker is down" in err
    assert SENTINEL not in out + err


def test_a_raw_entry_resolves_without_asking_the_tracker(node, monkeypatch):
    root, configure = node
    configure(tracker=INBOX_TRACKER)
    _inbox_entry(root)
    sent = _recording(monkeypatch, OK_RESPONSES)
    code, out, err = _run(["work", "inbox", "show", "2026-09-14-serve-accepts-writes"])
    assert code == 0, err
    assert "body:" in out and sent == []
    code, out, err = _run(["work", "inbox", "accept", "2026-09-14-serve-accepts-writes"])
    assert code == 0, err
    assert sent == []


def test_inbox_show_reads_an_unknown_ref_as_a_ticket(node, monkeypatch):
    root, configure = node
    configure(tracker=INBOX_TRACKER)
    issue = {**ISSUE_BODY, "fields": {**ISSUE_BODY["fields"],
                                      "description": "The words triage reads."}}
    _recording(monkeypatch, {**OK_RESPONSES,
                             "/issue/": (200, {}, json.dumps(issue).encode())})
    code, out, err = _run(["work", "inbox", "show", "TCWCLAIM-1"])
    assert code == 0, err
    for line in ("TCWCLAIM-1  [To Do]", "summary: A ticket that is ready",
                 "assignee: Probe", "claimable: ", "workflow: ",
                 "description:", "The words triage reads."):
        assert line in out, (line, out)
    assert "tracker show" not in err


def test_a_raw_entry_shadows_a_ticket_of_the_same_name_unless_ticket_is_given(
        node, monkeypatch):
    root, configure = node
    configure(tracker=INBOX_TRACKER)
    _inbox_entry(root, name="TCWCLAIM-1.md", text="# The local one\n")
    sent = _recording(monkeypatch, OK_RESPONSES)
    code, out, _err = _run(["work", "inbox", "show", "TCWCLAIM-1"])
    assert code == 0 and "The local one" in out and sent == []
    code, out, err = _run(["work", "inbox", "show", "--ticket", "TCWCLAIM-1"])
    assert code == 0, err
    assert "The local one" not in out and "summary: A ticket that is ready" in out


def test_an_ambiguous_ref_is_not_tried_as_a_ticket(node, monkeypatch):
    root, configure = node
    configure(tracker=INBOX_TRACKER)
    _inbox_entry(root, name="EX-9.txt", text="one\n")
    _inbox_entry(root, name="EX-9.rst", text="two\n")
    sent = _recording(monkeypatch, OK_RESPONSES)
    for verb in ("show", "accept"):
        code, _out, err = _run(["work", "inbox", verb, "EX-9"])
        assert code == 1 and "ambiguous inbox entry" in err
    assert sent == []


def test_a_ref_that_is_neither_names_both(node, monkeypatch):
    root, configure = node
    configure(tracker=INBOX_TRACKER)
    _recording(monkeypatch, {"/issue/": jira.TrackerNotFound("Issue does not exist")})
    for verb in ("show", "accept"):
        code, out, err = _run(["work", "inbox", verb, "EX-404"])
        assert (code, out) == (1, "")
        assert err == (f"tcw work inbox {verb}: no such inbox entry: EX-404, and the "
                       f"tracker has no ticket EX-404\n")


@pytest.mark.parametrize("tracker", [None, TRACKER], ids=["no-tracker", "no-inbox-query"])
def test_a_ref_that_is_nothing_without_an_inbox_query_says_what_it_said(
        node, monkeypatch, tracker):
    root, configure = node
    configure(tracker=tracker)
    sent = _recording(monkeypatch, OK_RESPONSES)
    for verb in ("show", "accept"):
        code, out, err = _run(["work", "inbox", verb, "EX-404"])
        assert (code, out, err) == (1, "", f"tcw work inbox {verb}: no such inbox entry: EX-404\n")
    assert sent == []


def test_no_inbox_path_prints_the_token(node, monkeypatch):
    root, configure = node
    configure(tracker=INBOX_TRACKER)
    _inbox_entry(root)
    outputs = []
    _recording(monkeypatch, OK_RESPONSES)
    outputs += _run(["work", "inbox", "list"])[1:]
    outputs += _run(["work", "inbox", "show", "TCWCLAIM-1"])[1:]
    for error in (jira.TrackerAuthError(f"rejected"), jira.TrackerNotFound("gone"),
                  jira.TrackerUnavailable("down")):
        _recording(monkeypatch, {"/search": error, "/issue/": error})
        outputs += _run(["work", "inbox", "list"])[1:]
        outputs += _run(["work", "inbox", "show", "EX-1"])[1:]
        outputs += _run(["work", "inbox", "accept", "EX-1"])[1:]
    assert all(SENTINEL not in text for text in outputs)
