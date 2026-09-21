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
    "transitions": {"start": "Start Progress"},
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


def test_ticket_with_a_broken_tracker_names_the_problem_not_the_missing_query(
        node, monkeypatch):
    root, configure = node
    configure(tracker={**INBOX_TRACKER, "timeout-seconds": -1})
    code, _out, err = _run(["work", "inbox", "show", "--ticket", "EX-1"])
    assert code == 1 and "tcw validate" in err
    assert "--ticket needs" not in err


# ── `tcw work tracker create` ───────────────────────────────────────────────

CREATE_TRACKER = {
    **TRACKER,
    "statuses": {"backlog": "To Do", "active": "In Progress"},
    "create": {"project": "PROBE", "issue-type": "Task",
               "issue-types": {"epic": "Epic", "bug": "Bug"}},
}

# A just-created issue sits in the entry status, and the hop out of it is named
# for the transition, not the destination — the shape the 2026-09-20 backfill met.
CREATE_RESPONSES = {
    "/transitions": (200, {}, json.dumps({"transitions": [
        {"id": "11", "name": "Accept", "to": {"name": "To Do", "id": "2"}}]}).encode()),
    # The status read `_place` does before and after its hop. "To Do" here means
    # the CLI fixture exercises the *already placed* shape; the transition path
    # is covered in `tests/test_tracker_create.py`, where the status can change.
    "/myself": (200, {}, json.dumps({"accountId": "a"}).encode()),
    # For a `PROBE-1` a test seeds itself rather than one the stub minted — the
    # resumption record is written by hand, so no create call ever names it.
    "/issue/PROBE-1": (200, {}, json.dumps(
        {"id": "10001", "key": "PROBE-1",
         "fields": {"summary": "Thing", "status": {"name": "To Do"},
                    "assignee": None, "description": None}}).encode()),
}


def _issue_read(key: str) -> tuple:
    """What a GET of one issue returns. Built per key rather than held as a single
    literal, because `--all` creates several tickets in one run and a fixture that
    answers every read with `PROBE-1` would hide a key mixed up between items."""
    return (200, {}, json.dumps(
        {"id": "1000" + key.rsplit("-", 1)[1], "key": key,
         "fields": {"summary": "Thing", "status": {"name": "To Do"},
                    "assignee": None, "description": None}}).encode())


def _created_node(node, monkeypatch, *, status, tracker=CREATE_TRACKER, title="Thing"):
    """A node holding one item, in `status`.

    `status` has **no default** on purpose. `create` branches on it in three
    places — the closed-item refusal, the holder check, and whether the follow-on
    `link` has anything to deliver — and a fixture's default is always whichever
    value makes setup easiest, which here would be `backlog`, the one value that
    takes none of those branches (`docs/lifecycle/implementation.md`).
    """
    root, configure = node
    configure(tracker)
    code, _out, err = _run(["work", "new", title])
    assert code == 0, err
    from tcw.store.fs import FsWorkStore
    st = FsWorkStore.open(root)
    items = st.query()
    assert len(items) == 1, items
    slug = items[0].slug
    for hop in _ROUTE_TO[status]:
        st.transition(slug, hop)
    assert FsWorkStore.open(root)._require(slug).status == status
    return root, slug


#: How to walk a freshly filed item to each status, since `transition` only
#: accepts legal hops.
_ROUTE_TO = {
    "backlog": (),
    "active": ("active",),
    "review": ("active", "review"),
    "completed": ("active", "review", "completed"),
    "discarded": ("discarded",),
}


def _create_responses(monkeypatch, **overrides):
    mapping = {**CREATE_RESPONSES, **overrides}
    posted: list[tuple] = []
    minted: list[str] = []

    def fake(self, method, path, body=None, *, timeout=None):
        posted.append((method, path, body))
        # The create POST goes to `/rest/api/3/issue`, which is a prefix of every
        # other issue path, so it is matched on method and exact path rather than
        # by substring — otherwise `/issue/PROBE-1` would answer it.
        if method == "POST" and path.rstrip("/").endswith("/issue"):
            created = mapping.get("__create__")
            if isinstance(created, Exception):
                raise created
            if created:
                return created
            # Jira numbers each new issue, so the stub does too. Returning one
            # fixed key would let a sweep bind two items to the same ticket and
            # still look correct.
            minted.append(f"PROBE-{len(minted) + 1}")
            return (200, {}, json.dumps(
                {"id": "1000" + str(len(minted)), "key": minted[-1]}).encode())
        for fragment, response in mapping.items():
            if fragment != "__create__" and fragment in path:
                if isinstance(response, Exception):
                    raise response
                return response
        for key in minted:
            if f"/issue/{key}" in path:
                return _issue_read(key)
        return (200, {}, b"{}")
    monkeypatch.setattr(jira.JiraClient, "_request", fake)
    return posted


def test_create_makes_a_ticket_places_it_and_binds_it(node, monkeypatch):
    """Spec criterion 1, end to end through the CLI."""
    root, slug = _created_node(node, monkeypatch, status="backlog")
    posted = _create_responses(monkeypatch)

    code, _out, err = _run(["work", "tracker", "create", slug])
    assert code == 0, err
    assert "created PROBE-1" in err
    assert "To Do" in err

    creates = [p for p in posted if p[0] == "POST" and p[1].endswith("/issue")]
    assert len(creates) == 1, posted
    assert creates[0][2]["fields"]["project"] == {"key": "PROBE"}
    assert creates[0][2]["fields"]["issuetype"] == {"name": "Task"}
    # The status is read back rather than assumed: Jira accepting a transition is
    # not the transition applying, and this fixture's project needs no hop at all.
    assert any(p[0] == "GET" and "/issue/PROBE-1" in p[1] for p in posted), posted

    from tcw.store.fs import FsWorkStore
    from tcw.tracker.intake import Bound, binding_of
    bound, _ = binding_of(FsWorkStore.open(root), slug)
    assert isinstance(bound, Bound) and bound.ticket_key == "PROBE-1"


def test_create_refuses_before_creating_when_backlog_is_unmapped(node, monkeypatch):
    """Spec criterion 3. The refusal must reach the tracker's create endpoint
    never — a ticket made and then declined is the worst outcome available."""
    tracker = {**CREATE_TRACKER, "statuses": {"active": "In Progress"}}
    root, slug = _created_node(node, monkeypatch, status="backlog", tracker=tracker)
    posted = _create_responses(monkeypatch)

    code, _out, err = _run(["work", "tracker", "create", slug])
    assert code == 1
    assert "work.tracker.statuses.backlog" in err
    assert [p for p in posted if p[0] == "POST"] == [], posted


def test_create_is_idempotent(node, monkeypatch):
    """Spec criterion 5: a second run creates nothing and exits zero."""
    root, slug = _created_node(node, monkeypatch, status="backlog")
    _create_responses(monkeypatch)
    assert _run(["work", "tracker", "create", slug])[0] == 0

    posted = _create_responses(monkeypatch)
    code, _out, err = _run(["work", "tracker", "create", slug])
    assert code == 0, err
    assert "already bound to PROBE-1" in err
    assert [p for p in posted if p[0] == "POST"] == [], posted


def test_dry_run_writes_nothing_anywhere(node, monkeypatch):
    """Spec criterion 7 — asserted against the tracker as well as the tree."""
    root, slug = _created_node(node, monkeypatch, status="backlog")
    posted = _create_responses(monkeypatch)

    code, _out, err = _run(["work", "tracker", "create", slug, "--dry-run"])
    assert code == 0, err
    assert "would create a Task in PROBE" in err
    assert "'To Do'" in err
    assert [p for p in posted if p[0] == "POST"] == [], posted

    from tcw.store.fs import FsWorkStore
    from tcw.tracker.intake import Bound, binding_of
    bound, _ = binding_of(FsWorkStore.open(root), slug)
    assert not isinstance(bound, Bound)


def test_create_does_not_mention_a_command_nobody_ran(node, monkeypatch):
    """`create` binds through `link`'s implementation, so every message must
    still name the verb the user typed.

    **This test used to pass without running the refactored code.** It
    configured no `statuses.backlog`, so the command returned at
    `_tracker_create`'s own `unplaceable` refusal — a message with the verb
    hard-coded — and both assertions held with the whole `verb` parameter
    reverted. Found by an adversarial review. It now fails the binding *inside*
    `_tracker_link`, which is the only way to reach one of the ten rewritten
    message sites.
    """
    root, slug = _created_node(node, monkeypatch, status="backlog")
    posted = _create_responses(monkeypatch)

    from tcw.store.fs import FsWorkStore

    real = FsWorkStore.write_sidecar

    def refuse_the_binding(self, slug_, name, content, *a, **kw):
        # Only the binding. The `created` record goes through the same method and
        # is written first; failing that too would stop the run before it ever
        # reached `_tracker_link`, which is the whole point of this test.
        if "ticket:" in content:
            raise OSError("disk is full")
        return real(self, slug_, name, content, *a, **kw)

    monkeypatch.setattr(FsWorkStore, "write_sidecar", refuse_the_binding)

    code, _out, err = _run(["work", "tracker", "create", slug])
    assert code == 1
    # The message `_tracker_link` owns, reached only after the ticket was made.
    assert "the binding could not be written" in err, err
    assert "tcw work tracker create:" in err
    assert "tracker link" not in err
    assert [p for p in posted if p[0] == "POST"], "the ticket should have been made"


def test_an_invalid_part_is_refused_before_any_ticket_exists(node, monkeypatch):
    """`link` can check `--part` after reading its ticket, because that ticket
    already existed. `create` cannot: the same order would leave a real ticket in
    a shared tracker bound to nothing, and TCW has no way to delete it."""
    root, slug = _created_node(node, monkeypatch, status="backlog")
    posted = _create_responses(monkeypatch)

    code, _out, err = _run(["work", "tracker", "create", slug, "--part", "Not A Part"])
    assert code == 1
    assert [p for p in posted if p[0] == "POST"] == [], posted
    assert "tracker create" in err


@pytest.mark.parametrize("status", ["completed", "discarded"])
def test_a_closed_item_is_refused_before_anything_reaches_the_tracker(
        node, monkeypatch, status):
    """A spec non-goal: "a ticket created only to be closed is noise". Placement
    is what makes it concrete — every created ticket lands in the *backlog*
    status, so a ticket for finished work would be created open and then have to
    be walked forward and resolved, and a failure part-way leaves an open ticket
    for work that is done."""
    root, slug = _created_node(node, monkeypatch, status=status)
    posted = _create_responses(monkeypatch)
    code, _out, err = _run(["work", "tracker", "create", slug])
    assert code == 1
    assert f"{slug} is {status}" in err, err
    assert "noise" in err
    assert posted == [], f"the tracker was called anyway: {posted}"


def _sidecar(root, slug: str) -> str:
    from tcw.store.fs import FsWorkStore
    from tcw.tracker.intake import BINDING_SIDECAR
    found = FsWorkStore.open(root).read_sidecar(slug, BINDING_SIDECAR)
    return found.content if found else ""


def test_the_created_key_is_on_disk_before_the_binding_is_attempted(node, monkeypatch):
    """Spec criterion 6, first half. The window between "the ticket exists" and
    "the binding is written" is the only place this command can cost something it
    cannot undo, because TCW never deletes a ticket. So the key is written to disk
    inside that window, not merely held in memory.

    Asserted by failing the binding write and then reading the tree: the record
    has to have survived the failure."""
    root, slug = _created_node(node, monkeypatch, status="backlog")
    _create_responses(monkeypatch)

    from tcw.store.fs import FsWorkStore
    real = FsWorkStore.write_sidecar

    def refuse_the_binding(self, slug_, name, content, *a, **kw):
        # The `created` record goes through the same method, so only the binding
        # itself is failed — otherwise this would prove nothing about ordering.
        if "ticket:" in content:
            raise OSError("disk is full")
        return real(self, slug_, name, content, *a, **kw)

    monkeypatch.setattr(FsWorkStore, "write_sidecar", refuse_the_binding)
    code, _out, _err = _run(["work", "tracker", "create", slug])
    assert code == 1
    assert "created:" in _sidecar(root, slug), _sidecar(root, slug)
    from tcw.tracker.intake import created_record
    assert created_record(_sidecar(root, slug)) == {"key": "PROBE-1", "id": "10001"}


def test_an_interrupted_run_binds_the_recorded_key_instead_of_creating_another(
        node, monkeypatch):
    """Spec criterion 6. Starting from a recorded key with no binding, `create`
    must reach a binding **without** asking the tracker for a second ticket."""
    root, slug = _created_node(node, monkeypatch, status="backlog")
    from tcw.store.fs import FsWorkStore
    from tcw.tracker.intake import BINDING_SIDECAR, with_created_record
    FsWorkStore.open(root).write_sidecar(
        slug, BINDING_SIDECAR,
        with_created_record(None, {"key": "PROBE-1", "id": "10001"}), revision="")

    posted = _create_responses(monkeypatch)
    code, _out, err = _run(["work", "tracker", "create", slug])
    assert code == 0, err
    assert "did not finish" in err, err
    assert [p for p in posted if p[0] == "POST" and p[1].rstrip("/").endswith("/issue")] == [], \
        f"a second ticket was created: {posted}"

    from tcw.tracker.intake import binding_of, created_record
    bound, _rev = binding_of(FsWorkStore.open(root), slug)
    assert getattr(bound, "ticket_key", "") == "PROBE-1", bound
    # The record is spent once the binding exists, or the next run would think a
    # bound item still owed a ticket.
    assert created_record(_sidecar(root, slug)) is None, _sidecar(root, slug)


def test_a_ticket_made_but_not_recorded_still_names_its_key(node, monkeypatch):
    """The worst state this command can reach: the tracker made a ticket and the
    record of it could not be written. The user cannot be left to find it by
    hand, and the message must not be a traceback."""
    root, slug = _created_node(node, monkeypatch, status="backlog")
    _create_responses(monkeypatch)
    from tcw.store.fs import FsWorkStore

    def refuse(self, *a, **kw):
        raise OSError("disk is full")

    monkeypatch.setattr(FsWorkStore, "write_sidecar", refuse)
    code, _out, err = _run(["work", "tracker", "create", slug])
    assert code == 1
    assert "PROBE-1 was created" in err, err
    assert "tracker link" in err, err
    assert "Traceback" not in err


def test_a_recorded_key_sends_the_user_back_to_create_not_link(node, monkeypatch):
    """The failure message after a ticket is created and placement fails used to
    say that running `create` again "would make a second ticket". With the key
    recorded it would not — `create` resumes from it, which is the entire point
    of recording it — so the message steered the user away from the recovery
    path this feature was built for.

    Placement is what fails here: the ticket is made, the key is written, and
    then the tracker offers no way out of the status it was created in.
    """
    root, slug = _created_node(node, monkeypatch, status="backlog")
    _create_responses(monkeypatch, **{
        # Created in the triage column, with nothing offered that leads out.
        "/transitions": (200, {}, json.dumps({"transitions": []}).encode()),
        "/issue/PROBE-1": (200, {}, json.dumps(
            {"id": "10001", "key": "PROBE-1",
             "fields": {"summary": "Thing", "status": {"name": "Triage"},
                        "assignee": None, "description": None}}).encode()),
    })

    code, _out, err = _run(["work", "tracker", "create", slug])
    assert code == 1
    assert "PROBE-1 was created" in err, err
    assert f"tracker create {slug}" in err, err
    # The wording this replaces. Both halves matter: the old message named
    # `link`, and named it as the alternative to making a second ticket.
    assert "would make a second ticket" not in err, err
    assert "tracker link" not in err, err
    # And the key really is on disk, which is what makes the advice true.
    from tcw.tracker.intake import created_record
    assert created_record(_sidecar(root, slug)) == {"key": "PROBE-1", "id": "10001"}


def test_a_dry_run_reports_a_resumption_rather_than_a_creation(node, monkeypatch):
    """`--dry-run` read the resumption record and then reported "would create"
    anyway, because it returned before the notice. Wrong in exactly the case
    somebody is checking before touching a shared tracker, and `--all --dry-run`
    — which the help tells you to run first — overstated the number of new
    tickets it was about to make."""
    root, slug = _created_node(node, monkeypatch, status="backlog")
    from tcw.store.fs import FsWorkStore
    from tcw.tracker.intake import BINDING_SIDECAR, with_created_record
    FsWorkStore.open(root).write_sidecar(
        slug, BINDING_SIDECAR,
        with_created_record(None, {"key": "PROBE-1", "id": "10001"}), revision="")

    posted = _create_responses(monkeypatch)
    code, _out, err = _run(["work", "tracker", "create", slug, "--dry-run"])
    assert code == 0, err
    assert "PROBE-1" in err and "would bind" in err, err
    assert "would create" not in err, err
    assert posted == [], posted


def test_a_sweep_stops_once_a_created_key_cannot_be_recorded(node, monkeypatch):
    """A ticket made whose key cannot be written down is unfindable: no record
    survives, so a re-run makes another. Carrying on would produce one of those
    per remaining item, and a re-run once the disk is fixed would duplicate
    every one. The tracker is fine; this machine is not, so the sweep stops."""
    root, slugs = _board(node, monkeypatch,
                         [("Alpha", "task", "backlog"), ("Beta", "task", "backlog"),
                          ("Gamma", "task", "backlog")])
    posted = _create_responses(monkeypatch)
    from tcw.store.fs import FsWorkStore

    def refuse(self, *a, **kw):
        raise OSError("disk is full")

    monkeypatch.setattr(FsWorkStore, "write_sidecar", refuse)
    code, _out, err = _run(["work", "tracker", "create", "--all"])
    assert code == 1
    creates = [p for p in posted
               if p[0] == "POST" and p[1].rstrip("/").endswith("/issue")]
    assert len(creates) == 1, f"the sweep kept creating tickets it could not record: {creates}"
    assert "stopping the sweep" in err, err


def _board(node, monkeypatch, items, tracker=CREATE_TRACKER):
    """A node holding several items, so `--all` has something to sweep.

    Each entry is `(title, kind, status)`, and **`status` carries no default**,
    for the reason `_created_node` gives: `_sweep_order` branches on it, and an
    all-`backlog` board is the one shape that takes none of those branches. The
    first version of this helper filed every item with `tcw work new` and took
    no status at all — with the result that the status filter, the unbound
    filter and the held-by-someone-else skip could each be deleted outright with
    every test in this file still passing.
    """
    root, configure = node
    configure(tracker)
    from tcw.store.fs import FsWorkStore
    st = FsWorkStore.open(root)
    slugs = {}
    for title, kind, status in items:
        argv = ["work", "new", title]
        if kind == "epic":
            argv.append("--epic")
        code, out, err = _run(argv)
        assert code == 0, err
        slug = out.strip().splitlines()[0]
        for hop in _ROUTE_TO[status]:
            st.transition(slug, hop)
        assert FsWorkStore.open(root)._require(slug).status == status
        slugs[title] = slug
    return root, slugs


def test_all_sweeps_every_unbound_open_item_and_skips_bound_ones(node, monkeypatch):
    """Spec criterion 8. The bound item must be passed over entirely: a sweep
    that re-creates for an item that already has a ticket is how one mistake
    becomes one mistake per item."""
    root, slugs = _board(node, monkeypatch,
                          [("Alpha", "task", "backlog"), ("Beta", "task", "backlog")])
    from tcw.store.fs import FsWorkStore
    from tcw.tracker.intake import BINDING_SIDECAR, binding_document
    FsWorkStore.open(root).write_sidecar(
        slugs["Alpha"], BINDING_SIDECAR,
        binding_document(provider="jira-cloud", project="probe", part="default",
                         ticket_id="9", ticket_key="PROBE-9",
                         ticket_url="https://example.invalid/browse/PROBE-9",
                         bound="2026-09-20", unlinked=[]), revision="")

    posted = _create_responses(monkeypatch)
    code, _out, err = _run(["work", "tracker", "create", "--all"])
    assert code == 0, err
    creates = [p for p in posted
               if p[0] == "POST" and p[1].rstrip("/").endswith("/issue")]
    assert len(creates) == 1, creates
    assert creates[0][2]["fields"]["summary"] == "Beta"
    # The slug, not the title: every message this command prints names the slug,
    # so `"Alpha" not in err` could never have failed, and the whole unbound
    # filter could be deleted with this test still green.
    assert slugs["Alpha"] not in err, err


def test_the_created_ticket_links_back_to_the_item(node, monkeypatch):
    """`work.tracker.link` says where a project's items can be read, and progress
    comments have carried it since they existed. `item_url` was threaded through
    `create_and_place` to `description_document` with no caller passing it, so
    the created ticket — the first place anyone looks — was the one thing that
    never linked back."""
    root, slug = _created_node(
        node, monkeypatch, status="backlog",
        tracker={**CREATE_TRACKER,
                 "link": "https://example.invalid/{project}/work/{slug}"})
    posted = _create_responses(monkeypatch)
    code, _out, err = _run(["work", "tracker", "create", slug])
    assert code == 0, err

    create = next(p for p in posted
                  if p[0] == "POST" and p[1].rstrip("/").endswith("/issue"))
    text = json.dumps(create[2]["fields"]["description"])
    assert f"https://example.invalid/probe/work/{slug}" in text, text


def test_all_sweeps_an_item_whose_binding_was_unlinked(node, monkeypatch):
    """`unlink` leaves the former binding under `unlinked:`, and that history
    still contains the text `ticket:`. The sweep decided "already bound" with a
    substring search over the raw sidecar, so the one item a user most likely
    unlinked *in order to* re-create was the one it silently walked past."""
    root, slugs = _board(node, monkeypatch, [("Alpha", "task", "backlog")])
    from tcw.store.fs import FsWorkStore
    from tcw.tracker.intake import BINDING_SIDECAR, binding_document
    FsWorkStore.open(root).write_sidecar(
        slugs["Alpha"], BINDING_SIDECAR,
        binding_document(provider="jira-cloud", project="probe", part="default",
                         ticket_id="9", ticket_key="PROBE-9",
                         ticket_url="https://example.invalid/browse/PROBE-9",
                         bound="2026-09-20", unlinked=[]), revision="")
    _create_responses(monkeypatch)
    code, _out, err = _run(["work", "tracker", "unlink", slugs["Alpha"],
                            "--reason", "bound to the wrong ticket"])
    assert code == 0, err
    sidecar = FsWorkStore.open(root).read_sidecar(slugs["Alpha"], BINDING_SIDECAR)
    assert "ticket:" in sidecar.content, sidecar.content   # the history remains

    posted = _create_responses(monkeypatch)
    code, _out, err = _run(["work", "tracker", "create", "--all"])
    assert code == 0, err
    creates = [p for p in posted
               if p[0] == "POST" and p[1].rstrip("/").endswith("/issue")]
    assert len(creates) == 1, creates
    assert creates[0][2]["fields"]["summary"] == "Alpha"


def test_all_passes_over_closed_items(node, monkeypatch):
    """A ticket made only to be closed is noise — the spec's non-goal. Enforced
    for one named item already; this is the sweep, where nobody typed the slug."""
    root, slugs = _board(node, monkeypatch,
                         [("Done", "task", "completed"),
                          ("Dropped", "task", "discarded"),
                          ("Open", "task", "backlog")])
    posted = _create_responses(monkeypatch)
    code, _out, err = _run(["work", "tracker", "create", "--all"])
    assert code == 0, err
    summaries = [p[2]["fields"]["summary"] for p in posted
                 if p[0] == "POST" and p[1].rstrip("/").endswith("/issue")]
    assert summaries == ["Open"], summaries


def test_all_skips_an_item_someone_else_holds_without_failing_the_sweep(
        node, monkeypatch):
    """A sweep walks past other people's work, as `tracker sync --all` does.
    Creating a ticket claims the item, so doing it for an item somebody else
    holds would take their work; exiting non-zero would make a sweep of a shared
    board look like a failure."""
    root, slugs = _board(node, monkeypatch,
                         [("Theirs", "task", "backlog"), ("Mine", "task", "backlog")])
    _create_responses(monkeypatch)
    monkeypatch.setenv("TCW_WORK_OWNER", "someone.else@example.test")
    code, _out, err = _run(["work", "start", slugs["Theirs"]])
    assert code == 0, err
    monkeypatch.setenv("TCW_WORK_OWNER", "me@example.test")

    posted = _create_responses(monkeypatch)
    code, out, err = _run(["work", "tracker", "create", "--all"])
    assert code == 0, err
    summaries = [p[2]["fields"]["summary"] for p in posted
                 if p[0] == "POST" and p[1].rstrip("/").endswith("/issue")]
    assert summaries == ["Mine"], summaries
    assert "someone.else@example.test" in out + err, (out, err)


def test_all_creates_for_epics_before_their_children(node, monkeypatch):
    """A child's ticket may want to name its parent's, and a parent link cannot
    point at a ticket that does not exist yet."""
    root, _slugs = _board(node, monkeypatch,
                          [("A child", "task", "backlog"),
                           ("An epic", "epic", "backlog")])
    posted = _create_responses(monkeypatch)
    code, _out, err = _run(["work", "tracker", "create", "--all"])
    assert code == 0, err
    summaries = [p[2]["fields"]["summary"] for p in posted
                 if p[0] == "POST" and p[1].rstrip("/").endswith("/issue")]
    assert summaries == ["An epic", "A child"], summaries


def test_all_and_a_slug_together_are_refused(node, monkeypatch):
    root, slug = _created_node(node, monkeypatch, status="backlog")
    posted = _create_responses(monkeypatch)
    code, _out, err = _run(["work", "tracker", "create", slug, "--all"])
    assert code == 1
    assert "name one slug, or pass --all" in err
    assert posted == []


def test_all_refuses_part_rather_than_applying_one_name_to_every_item(
        node, monkeypatch):
    """`--part` says which share of *one* ticket an item is. Spread across a
    sweep it would bind every item as the same part of a different ticket."""
    root, _slugs = _board(node, monkeypatch, [("Alpha", "task", "backlog")])
    posted = _create_responses(monkeypatch)
    code, _out, err = _run(["work", "tracker", "create", "--all", "--part", "api"])
    assert code == 1
    assert "cannot be combined with --all" in err, err
    assert posted == []


def test_neither_a_slug_nor_all_is_refused(node, monkeypatch):
    root, _slug = _created_node(node, monkeypatch, status="backlog")
    posted = _create_responses(monkeypatch)
    code, _out, err = _run(["work", "tracker", "create"])
    assert code == 1
    assert "name an item, or pass --all" in err
    assert posted == []


def test_all_with_dry_run_creates_nothing_and_reports_each_item(node, monkeypatch):
    root, _slugs = _board(node, monkeypatch,
                          [("Alpha", "task", "backlog"), ("Beta", "task", "backlog")])
    posted = _create_responses(monkeypatch)
    code, _out, err = _run(["work", "tracker", "create", "--all", "--dry-run"])
    assert code == 0, err
    assert posted == [], posted
    assert "Alpha" in err and "Beta" in err, err


# ── Landing B: filing an item makes its ticket ───────────────────────────────


ON_NEW_TRACKER = {**CREATE_TRACKER,
                  "create": {**CREATE_TRACKER["create"], "on-new": True}}


def test_without_on_new_filing_makes_no_tracker_call_at_all(node, monkeypatch):
    """Spec criterion 9, the default. Asserted with the credential variables
    removed as well as with a stub, so a call would fail loudly rather than
    quietly succeed against the fixture."""
    root, configure = node
    configure(CREATE_TRACKER)               # a create block, but on-new not set
    monkeypatch.delenv("TCW_JIRA_EMAIL", raising=False)
    monkeypatch.delenv("TCW_JIRA_API_TOKEN", raising=False)
    posted = _create_responses(monkeypatch)
    code, out, err = _run(["work", "new", "Filed quietly"])
    assert code == 0, err
    assert posted == [], posted
    assert "ticket" not in err.lower(), err
    assert out.strip(), "the item is still filed"


def test_on_new_makes_and_binds_a_ticket_when_filing(node, monkeypatch):
    """Spec criterion 10."""
    root, configure = node
    configure(ON_NEW_TRACKER)
    posted = _create_responses(monkeypatch)
    code, out, err = _run(["work", "new", "Filed with a ticket"])
    assert code == 0, err
    slug = out.strip().splitlines()[0]
    creates = [p for p in posted
               if p[0] == "POST" and p[1].rstrip("/").endswith("/issue")]
    assert len(creates) == 1, creates
    assert creates[0][2]["fields"]["summary"] == "Filed with a ticket"
    from tcw.store.fs import FsWorkStore
    from tcw.tracker.intake import binding_of
    bound, _rev = binding_of(FsWorkStore.open(root), slug)
    assert getattr(bound, "ticket_key", "") == "PROBE-1", bound


def test_on_new_covers_an_epic_too(node, monkeypatch):
    """Spec Rule 5, and a deliberate departure from strict mode's `and not
    args.epic`: an epic with no ticket breaks its children's parent links, which
    is the opposite of what exempting it would be for."""
    root, configure = node
    configure(ON_NEW_TRACKER)
    posted = _create_responses(monkeypatch)
    code, _out, err = _run(["work", "new", "An epic", "--epic"])
    assert code == 0, err
    creates = [p for p in posted
               if p[0] == "POST" and p[1].rstrip("/").endswith("/issue")]
    assert len(creates) == 1, creates
    assert creates[0][2]["fields"]["issuetype"] == {"name": "Epic"}


def test_inbox_accept_of_a_raw_entry_makes_a_ticket(node, monkeypatch):
    """Spec criterion 12. A raw entry only — accepting a *ticket* is
    `tracker import`, which binds the ticket that already exists."""
    root, configure = node
    configure(ON_NEW_TRACKER)
    from tcw.store.fs import FsWorkStore
    inbox = FsWorkStore.open(root).root / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "an-idea.md").write_text("# An idea\n\nDo the thing.\n",
                                      encoding="utf-8")
    posted = _create_responses(monkeypatch)
    code, out, err = _run(["work", "inbox", "accept", "an-idea"])
    assert code == 0, err
    slug = out.strip().splitlines()[0]
    creates = [p for p in posted
               if p[0] == "POST" and p[1].rstrip("/").endswith("/issue")]
    assert len(creates) == 1, creates
    from tcw.tracker.intake import binding_of
    assert getattr(binding_of(FsWorkStore.open(root), slug)[0], "ticket_key", "") \
        == "PROBE-1"


def test_an_unreachable_tracker_still_files_the_item_and_records_the_debt(
        node, monkeypatch):
    """Spec criterion 11. Filing must not fail because a tracker is unreachable —
    this runs on every `tcw work new` in a project that enables it, including on
    a train. The debt is recorded instead."""
    root, configure = node
    configure(ON_NEW_TRACKER)
    from tcw.tracker.jira import TrackerError
    _create_responses(monkeypatch, __create__=TrackerError("the network is down"))

    code, out, err = _run(["work", "new", "Filed on a train"])
    assert code == 0, err
    slug = out.strip().splitlines()[0]
    assert "owed" in err, err

    from tcw.store.fs import FsWorkStore
    item = FsWorkStore.open(root).get(slug)
    assert item is not None, "the item was filed"
    assert item.tracker and "owed" in item.tracker, item.tracker
    assert "the network is down" in item.tracker["owed"]["reason"]
    # It owes a ticket; it does not have one. Nothing may read this as a binding.
    from tcw.tracker.intake import Bound, binding_of
    assert not isinstance(binding_of(FsWorkStore.open(root), slug)[0], Bound)


def test_an_owed_ticket_is_visible_on_the_board(node, monkeypatch):
    """Spec Risks: the debt has to be visible, or a project that turns creation on
    quietly accumulates items nobody knows are missing from the tracker."""
    root, configure = node
    configure(ON_NEW_TRACKER)
    from tcw.tracker.jira import TrackerError
    _create_responses(monkeypatch, __create__=TrackerError("the network is down"))
    code, _out, err = _run(["work", "new", "Filed on a train"])
    assert code == 0, err
    code, out, _err = _run(["work", "list"])
    assert code == 0
    assert "owed since" in out, out


def test_filing_names_the_ticket_that_exists_instead_of_calling_it_owed(
        node, monkeypatch):
    """Creation succeeded and placement failed, so a real ticket exists. Filing
    used to write an owed record over that and print "no ticket was created" —
    and, because `_tracker_link` never appends to `reasons`, the recorded reason
    was often the placeholder "creating it did not succeed" for a ticket that
    had been created perfectly well. The board then read `owed since <date>` for
    an item whose ticket was sitting in the tracker."""
    _root, configure = node
    configure(ON_NEW_TRACKER)
    _create_responses(monkeypatch, **{
        "/transitions": (200, {}, json.dumps({"transitions": []}).encode()),
        "/issue/PROBE-1": (200, {}, json.dumps(
            {"id": "10001", "key": "PROBE-1",
             "fields": {"summary": "Thing", "status": {"name": "Triage"},
                        "assignee": None, "description": None}}).encode()),
    })

    code, out, err = _run(["work", "new", "Filed with a stuck workflow"])
    assert code == 0, err                       # filing still never fails
    slug = out.strip().splitlines()[0]

    assert "PROBE-1" in err, err
    assert "no ticket was created" not in err, err
    assert "creating it did not succeed" not in err, err

    from tcw.store.fs import FsWorkStore
    tracker = FsWorkStore.open(_root).get(slug).tracker
    assert tracker == {"created": {"key": "PROBE-1", "id": "10001"}}, tracker

    # And it reads as what it is on the board, not as a binding and not as a debt.
    code, board, _err = _run(["work", "list"])
    assert code == 0
    assert "PROBE-1 made, not bound" in board, board


def test_creating_the_owed_ticket_later_binds_it_and_clears_the_debt(
        node, monkeypatch):
    """Spec criterion 11's second half, and the interaction with task 6: a
    retried filing must not double-create."""
    root, configure = node
    configure(ON_NEW_TRACKER)
    from tcw.tracker.jira import TrackerError
    _create_responses(monkeypatch, __create__=TrackerError("the network is down"))
    code, out, err = _run(["work", "new", "Filed on a train"])
    assert code == 0, err
    slug = out.strip().splitlines()[0]

    posted = _create_responses(monkeypatch)         # the network is back
    code, _out, err = _run(["work", "tracker", "create", slug])
    assert code == 0, err
    creates = [p for p in posted
               if p[0] == "POST" and p[1].rstrip("/").endswith("/issue")]
    assert len(creates) == 1, creates

    from tcw.store.fs import FsWorkStore
    item = FsWorkStore.open(root).get(slug)
    assert item.tracker["ticket"]["key"] == "PROBE-1", item.tracker
    assert "owed" not in item.tracker, item.tracker


def test_all_sweeps_up_owed_tickets(node, monkeypatch):
    """The recovery path for a whole board's worth of debt."""
    root, configure = node
    configure(ON_NEW_TRACKER)
    from tcw.tracker.jira import TrackerError
    _create_responses(monkeypatch, __create__=TrackerError("the network is down"))
    for title in ("Alpha", "Beta"):
        assert _run(["work", "new", title])[0] == 0

    posted = _create_responses(monkeypatch)
    code, _out, err = _run(["work", "tracker", "create", "--all"])
    assert code == 0, err
    creates = [p for p in posted
               if p[0] == "POST" and p[1].rstrip("/").endswith("/issue")]
    assert len(creates) == 2, creates

    # Creating the tickets is half of it. This asserted only the POSTs and the
    # exit code, so replacing the binding call with `return 0` left it green
    # with neither item bound and neither debt cleared.
    from tcw.store.fs import FsWorkStore
    from tcw.tracker.intake import Bound, binding_of
    store = FsWorkStore.open(root)
    for item in store.query():
        binding, _revision = binding_of(store, item.slug)
        assert isinstance(binding, Bound), (item.slug, binding)
        assert "owed" not in _sidecar(root, item.slug), _sidecar(root, item.slug)


def _owed_item(monkeypatch, title="Filed on a train"):
    """File one item while the tracker is unreachable, and return its slug.

    The item ends up carrying an `owed` record and no binding, which is the state
    `binding_value` reports as `{"owed": ...}` — the fourth shape, and the one no
    test moved through a lifecycle before these two.
    """
    from tcw.tracker.jira import TrackerError
    _create_responses(monkeypatch, __create__=TrackerError("the network is down"))
    code, out, err = _run(["work", "new", title])
    assert code == 0, err
    return out.strip().splitlines()[0]


def test_an_owed_item_can_still_be_started(node, monkeypatch):
    """An item that owes a ticket must move through its lifecycle like any other.

    `_deliver_after` guarded on the absence of `problem` rather than the presence
    of `ticket`, so the owed shape reached `value["ticket"]["key"]` and the
    command died *after* the status move had already been committed.
    """
    _root, configure = node
    configure(ON_NEW_TRACKER)
    slug = _owed_item(monkeypatch)

    _create_responses(monkeypatch)                  # the network is back
    code, _out, err = _run(["work", "start", slug])
    assert code == 0, err
    assert "Traceback" not in err, err
    assert "KeyError" not in err, err


def test_one_owed_item_does_not_break_lifecycle_moves_on_every_other_item(
        node, monkeypatch):
    """`_siblings` scans the whole board, so an owed item anywhere reached its
    `value["project"]` and took tracker delivery down for items that were
    properly bound and had nothing to do with it."""
    _root, configure = node
    configure(ON_NEW_TRACKER)
    posted = _create_responses(monkeypatch)
    code, out, err = _run(["work", "new", "Properly bound"])
    assert code == 0, err
    bound_slug = out.strip().splitlines()[0]
    assert any(p[0] == "POST" and p[1].rstrip("/").endswith("/issue")
               for p in posted), posted

    _owed_item(monkeypatch, "Filed while the network was down")

    # What `start` then makes of the ticket is not this test's subject — the
    # stub offers no `Start Progress`, so delivery reports a conflict and exits
    # non-zero either way. The subject is that `_siblings` walked past the owed
    # item and let delivery reach the tracker at all, which the requests prove
    # and a `KeyError` would have prevented.
    posted = _create_responses(monkeypatch)
    _code, _out, err = _run(["work", "start", bound_slug])
    assert "Traceback" not in err, err
    assert "KeyError" not in err, err
    # Addressed by issue id, not key: PROBE-1 is the stub's first minted issue,
    # so its id is 10001.
    assert any("/issue/10001" in str(p[1]) for p in posted), posted


def test_under_strict_mode_a_filed_epic_still_gets_its_ticket(node, monkeypatch):
    """Strict mode and creation-on-filing are not contradictory, which is why
    validation no longer rejects the pair. Strict refuses `tcw work new` only
    for non-epics, so "tasks come from tickets, epics filed here get theirs
    made" is a coherent project — and this is the half that would silently stop
    working if anyone reinstated the rule."""
    _root, configure = node
    configure({**ON_NEW_TRACKER, "strict": True,
               "statuses": {"backlog": "To Do", "active": "In Progress",
                            "completed": "Done", "discarded": "Won't Do"}})
    posted = _create_responses(monkeypatch)

    code, _out, err = _run(["work", "new", "A task"])
    assert code == 1, err                        # still refused
    assert "tcw work tracker import" in err, err

    code, out, err = _run(["work", "new", "An epic", "--epic"])
    assert code == 0, err
    creates = [p for p in posted
               if p[0] == "POST" and p[1].rstrip("/").endswith("/issue")]
    assert len(creates) == 1, creates
    assert creates[0][2]["fields"]["issuetype"]["name"] == "Epic", creates
    from tcw.store.fs import FsWorkStore
    item = FsWorkStore.open(_root).get(out.strip().splitlines()[0])
    assert item.tracker["ticket"]["key"] == "PROBE-1", item.tracker


def test_unlink_clears_a_stale_created_record(node, monkeypatch):
    """A `created` record naming a ticket that is gone — deleted, or moved out of
    reach — used to wedge the item for good: `create` failed against it every
    time, `link` failed too, and `unlink` refused because the item was not bound,
    so hand-editing `tracker.yaml` was the only way out."""
    root, slug = _created_node(node, monkeypatch, status="backlog")
    from tcw.store.fs import FsWorkStore
    from tcw.tracker.intake import (BINDING_SIDECAR, created_record,
                                    with_created_record)
    FsWorkStore.open(root).write_sidecar(
        slug, BINDING_SIDECAR,
        with_created_record(None, {"key": "PROBE-9", "id": "9"}), revision="")

    code, _out, err = _run(["work", "tracker", "unlink", slug,
                            "--reason", "PROBE-9 was deleted in Jira"])
    assert code == 0, err
    assert "PROBE-9" in err, err
    # The wording this replaces: it used to refuse outright.
    assert "is not bound to a ticket" not in err, err
    assert created_record(_sidecar(root, slug)) is None, _sidecar(root, slug)


def test_an_item_that_only_owes_a_ticket_was_never_bound_and_can_be_dropped(
        node, monkeypatch):
    """`ever_bound` answered "does a sidecar file exist", and a `created` or
    `owed` record is a sidecar with no binding in it and none in its history. So
    strict mode refused to drop an item with "It is, or was, bound to a ticket,
    and dropping would erase that record" when there was no such record."""
    root, configure = node
    configure(CREATE_TRACKER)
    _create_responses(monkeypatch)
    code, out, err = _run(["work", "new", "Never bound to anything"])
    assert code == 0, err
    slug = out.strip().splitlines()[0]

    from tcw.store.fs import FsWorkStore
    from tcw.tracker.intake import BINDING_SIDECAR, with_created_record
    FsWorkStore.open(root).write_sidecar(
        slug, BINDING_SIDECAR,
        with_created_record(None, {"key": "PROBE-9", "id": "9"}), revision="")

    configure({**CREATE_TRACKER, "strict": True,
               "statuses": {"backlog": "To Do", "active": "In Progress",
                            "completed": "Done", "discarded": "Won't Do"}})
    code, _out, err = _run(["work", "drop", slug, "--confirm"])
    assert code == 0, err
    assert "was, bound to a ticket" not in err, err
    assert FsWorkStore.open(root).query() == [], "the item is still there"


def test_strict_mode_still_refuses_new_with_its_own_wording(node, monkeypatch):
    """Spec criterion 15 — the absence of a change. Every other criterion here is
    about a new path, so nothing else would notice if this one broke."""
    root, configure = node
    configure({**CREATE_TRACKER, "strict": True,
               "statuses": {"backlog": "To Do", "active": "In Progress",
                            "completed": "Done", "discarded": "Won't Do"}})
    posted = _create_responses(monkeypatch)
    code, _out, err = _run(["work", "new", "Refused"])
    assert code == 1
    assert "tcw work tracker import" in err, err
    assert posted == [], posted
