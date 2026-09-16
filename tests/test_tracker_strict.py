"""Strict tracker mode: local work only for items whose ticket is claimed by, and
assigned to, the account the local credentials authenticate as.

Built on `tests/test_tracker_sync.py`'s helpers and fake tracker. Every node here is
made by `strict_node`, whose `strict` argument has no default: whether strict mode
is on is the axis every gate branches on.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tcw.store.base import parse_tracker_config
from tcw.store.fs import FsWorkStore
from tcw.validate import validate
from test_tracker_sync import (A, B, KEY, SENTINEL, STATUSES, TICKET_ID,  # noqa: F401
                               bound_item, claimed_ticket, cli, fake, make_node,
                               record, status, with_record)
from tracker_fake import BASE_URL

BASE = {
    "provider": "jira-cloud", "base-url": BASE_URL,
    "candidate-query": "assignee = currentUser()",
    "credentials": {"email-env": "TCW_A_EMAIL", "token-env": "TCW_PROBE_TOKEN"},
    "transitions": {"claim": "Start Progress"},
}


def strict_node(tmp_path: Path, *, strict, statuses: dict | None = STATUSES,
                name: str = "alpha") -> Path:
    root = make_node(tmp_path, statuses=statuses, name=name)
    set_tracker_key(root, "strict", strict)
    return root


def set_tracker_key(root: Path, key: str, value) -> None:
    path = root / "tcw-config.yaml"
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if value is None:
        config["work"]["tracker"].pop(key, None)
    else:
        config["work"]["tracker"][key] = value
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")


# ── configuration ────────────────────────────────────────────────────────────


def parsed(**extra):
    return parse_tracker_config({**BASE, **extra})


def test_strict_true_with_the_required_statuses_parses():
    config, problems = parsed(strict=True, statuses=STATUSES)
    assert problems == [] and config.strict is True


def test_strict_defaults_to_false():
    config, problems = parsed()
    assert problems == [] and config.strict is False


@pytest.mark.parametrize("extra, key", [
    ({"strict": "yes", "statuses": STATUSES}, "work.tracker.strict"),
    ({"strict": True, "statuses": {"completed": "Done", "discarded": "Won't Do"}},
     "work.tracker.statuses.active"),
    ({"strict": True, "statuses": {"active": "In Progress", "discarded": "Won't Do"}},
     "work.tracker.statuses.completed"),
    ({"strict": True, "statuses": {"active": "In Progress", "completed": "Done",
                                   "discarded": {"wontfix": "Won't Do"}}},
     "work.tracker.statuses.discarded"),
    ({"strict": True, "statuses": {"active": "In Progress", "completed": "Done"}},
     "work.tracker.statuses.discarded"),
], ids=["not-boolean", "no-active", "no-completed", "partial-discards", "no-discarded"])
def test_a_strict_block_missing_what_it_needs_is_a_problem(extra, key):
    config, problems = parsed(**extra)
    assert config is None
    assert any(p.startswith(key) for p in problems), problems


def test_validate_names_the_key_and_the_board_still_reads(tmp_path, fake):
    root = strict_node(tmp_path, strict=True,
                       statuses={"active": "In Progress", "discarded": "Won't Do"})
    assert any("work.tracker.statuses.completed" in p for p in validate(root))
    assert cli(root, "work", "list")[0] == 0


@pytest.mark.parametrize("strict, problem, expected", [
    (True, False, True), (False, False, False), (None, False, False),
    (True, True, True), (False, True, False), (None, True, False),
    ("yes", True, True),
], ids=["on", "off", "absent", "on-broken", "off-broken", "absent-broken",
        "string-broken"])
def test_a_broken_block_does_not_switch_strict_off(tmp_path, fake, strict, problem,
                                                  expected):
    root = strict_node(tmp_path, strict=strict)
    if problem:
        set_tracker_key(root, "timeout-seconds", -1)
    st = FsWorkStore.open(root)
    assert (st.tracker_config() is None) is (problem or strict == "yes")
    assert st.tracker_strict() is expected


# ── authorize and claim_refusal, directly ────────────────────────────────────


def client_for(root: Path):
    from tcw.tracker.jira import JiraClient
    st = FsWorkStore.open(root)
    return st, JiraClient(st.tracker_config()), st.tracker_config()


def authorize_now(root: Path, slug: str, target: str):
    from tcw.tracker.sync import authorize
    st, client, config = client_for(root)
    return authorize(st, slug, client, config, target=target)


@pytest.fixture()
def strict(tmp_path, fake):
    return strict_node(tmp_path, strict=True)


def started(root: Path, slug: str, *, submitted: bool = False) -> None:
    st = FsWorkStore.open(root)
    st.start(slug, owner="a@example.test")
    if submitted:
        st.submit(slug)


def test_a_claimed_ticket_where_the_item_left_it_authorizes(strict, fake):
    slug = bound_item(strict)
    claimed_ticket(fake, "In Progress", A)
    started(strict, slug)
    assert authorize_now(strict, slug, "In Review") is None


@pytest.mark.parametrize("assignee, words", [(B, "assigned to Bob"),
                                             (None, "is unassigned")])
def test_a_ticket_not_assigned_to_you_authorizes_nothing_even_at_the_target(
        strict, fake, assignee, words):
    slug = bound_item(strict)
    started(strict, slug)
    claimed_ticket(fake, "In Review", assignee)
    reason = authorize_now(strict, slug, "In Review")
    assert reason and words in reason


def test_a_ticket_moved_back_in_the_tracker_authorizes_nothing(strict, fake):
    slug = bound_item(strict)
    started(strict, slug)
    claimed_ticket(fake, "To Do", A)
    assert "moved in the tracker" in authorize_now(strict, slug, "In Review")


def test_a_held_part_in_review_is_authorized_from_active(strict, fake):
    slug = bound_item(strict, part="api")
    other = bound_item(strict, "Web", part="web")
    started(strict, slug, submitted=True)
    claimed_ticket(fake, "In Progress", A)          # C3 held it for the other part
    assert authorize_now(strict, slug, "Done") is None
    FsWorkStore.open(strict).drop(other)            # no other part: sent back instead
    assert "moved in the tracker" in authorize_now(strict, slug, "Done")


def test_an_unreachable_tracker_authorizes_nothing(strict, fake):
    slug = bound_item(strict)
    started(strict, slug)
    fake.down = True
    assert "unknown" in authorize_now(strict, slug, "In Review")


def test_an_undelivered_change_must_be_synced_first(strict, fake):
    from test_tracker_sync import RECORD
    slug = bound_item(strict)
    started(strict, slug)
    claimed_ticket(fake, "In Progress", A)
    with_record(strict, slug, RECORD)
    assert "tcw work tracker sync" in authorize_now(strict, slug, "In Review")


def test_a_claim_on_a_workflow_that_offers_it_everywhere_is_refused(tmp_path, monkeypatch):
    from tcw.tracker.intake import claim, read_ticket
    from tcw.tracker.sync import claim_refusal
    from tracker_fake import GLOBAL, FakeJira
    monkeypatch.setenv("TCW_A_EMAIL", "a@example.test")
    monkeypatch.setenv("TCW_PROBE_TOKEN", SENTINEL)
    fake_ = FakeJira(workflow=GLOBAL)
    fake_.account("a@example.test", A, "Alice")
    fake_.ticket(id=TICKET_ID, key=KEY, summary="t")
    fake_.install(monkeypatch)
    root = strict_node(tmp_path, strict=True)
    _st, client, config = client_for(root)
    outcome = claim(client, read_ticket(client, TICKET_ID))
    assert outcome.claimed
    reason = claim_refusal(client, config, TICKET_ID, outcome)
    assert reason and "second person could claim it too" in reason


def test_a_claim_on_the_directed_workflow_is_not_refused(strict, fake):
    from tcw.tracker.intake import claim, read_ticket
    from tcw.tracker.sync import claim_refusal
    _st, client, config = client_for(strict)
    outcome = claim(client, read_ticket(client, TICKET_ID))
    assert outcome.claimed and claim_refusal(client, config, TICKET_ID, outcome) is None


def test_a_claim_row_1e_from_the_wrong_status_is_refused(strict, fake):
    from tcw.tracker.intake import claim, read_ticket
    from tcw.tracker.sync import claim_refusal
    claimed_ticket(fake, "In Review", A)
    _st, client, config = client_for(strict)
    outcome = claim(client, read_ticket(client, TICKET_ID))
    assert outcome.claimed and outcome.row == "1e"
    assert "not a claim" in claim_refusal(client, config, TICKET_ID, outcome)


# ── the command gates ────────────────────────────────────────────────────────


import subprocess  # noqa: E402

from tracker_fake import GLOBAL, SYNC, FakeJira  # noqa: E402

REFUSED = "refused under strict tracker mode"


def folder_bytes(root: Path, slug: str) -> dict:
    folder = FsWorkStore.open(root).path(slug)
    return {p.name: p.read_bytes() for p in folder.iterdir() if p.is_file()}


def commit_all(root: Path) -> None:
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "setup", "--allow-empty"],
                   check=True)


def test_new_and_inbox_accept_are_refused(strict, fake):
    code, out, err = cli(strict, "work", "new", "Unbound work")
    assert code == 1 and REFUSED in err and "tcw work tracker import" in err
    assert out == "" and FsWorkStore.open(strict).query() == []
    inbox = FsWorkStore.open(strict).root / "inbox"
    inbox.mkdir(exist_ok=True)
    (inbox / "a-request.md").write_text("# A request\n", encoding="utf-8")
    code, _out, err = cli(strict, "work", "inbox", "accept", "a-request.md")
    assert code == 1 and REFUSED in err
    assert FsWorkStore.open(strict).query() == []


def test_a_broken_strict_block_still_refuses_new(tmp_path, fake):
    root = strict_node(tmp_path, strict=True)
    set_tracker_key(root, "timeout-seconds", -1)
    code, _out, err = cli(root, "work", "new", "x")
    assert code == 1 and REFUSED in err


def test_an_unbound_item_cannot_start_submit_or_complete_but_can_be_discarded(tmp_path,
                                                                             fake):
    root = make_node(tmp_path, statuses=STATUSES)
    st = FsWorkStore.open(root)
    idle = st.create("Idle").slug
    busy = st.create("Busy").slug
    st.start(busy, owner="a@example.test")
    set_tracker_key(root, "strict", True)
    code, _out, err = cli(root, "work", "start", idle)
    assert code == 1 and REFUSED in err and status(root, idle) == "backlog"
    for argv in (("submit", busy), ("complete", busy, "--resolution", "done",
                                    "--confirm")):
        code, _out, err = cli(root, "work", *argv)
        assert code == 1 and REFUSED in err, argv
    assert status(root, busy) == "active"
    code, _out, err = cli(root, "work", "complete", idle, "--resolution", "wontfix",
                          "--confirm")
    assert code == 0, err
    assert status(root, idle) == "discarded"


def test_start_claims_an_unassigned_ticket(strict, fake):
    slug = bound_item(strict)
    code, _out, err = cli(strict, "work", "start", slug)
    assert code == 0, err
    held = fake.tickets[TICKET_ID]
    assert (held.status, held.assignee, status(strict, slug)) == ("In Progress", A,
                                                                   "active")


@pytest.mark.parametrize("flags", [(), ("--force",), ("--take-over",)])
def test_start_of_someone_elses_ticket_is_refused_and_moves_nothing(strict, fake, flags):
    slug = bound_item(strict)
    claimed_ticket(fake, "In Progress", B)
    code, _out, err = cli(strict, "work", "start", slug, *flags)
    assert code == 1 and REFUSED in err and "Bob" in err
    assert fake.writes() == [] and status(strict, slug) == "backlog"


def test_a_reassigned_ticket_refuses_submit_and_changes_no_file(strict, fake):
    slug = bound_item(strict)
    assert cli(strict, "work", "start", slug)[0] == 0
    claimed_ticket(fake, "In Progress", B)
    before = folder_bytes(strict, slug)
    code, _out, err = cli(strict, "work", "submit", slug)
    assert code == 1 and REFUSED in err and "Bob" in err
    assert status(strict, slug) == "active" and folder_bytes(strict, slug) == before


def test_a_reassigned_ticket_refuses_rework(strict, fake):
    slug = bound_item(strict)
    assert cli(strict, "work", "start", slug)[0] == 0
    assert cli(strict, "work", "submit", slug)[0] == 0
    claimed_ticket(fake, "In Review", B)
    code, _out, err = cli(strict, "work", "rework", slug)
    assert code == 1 and REFUSED in err and status(strict, slug) == "review"

def test_a_hand_written_binding_for_an_unclaimed_ticket_refuses_submit(strict, fake):
    from test_tracker_sync import document
    st = FsWorkStore.open(strict)
    slug = st.create_work("Hand bound", intake="x").item.slug
    (st.path(slug) / "tracker.yaml").write_text(document(), encoding="utf-8")
    st.start(slug, owner="a@example.test")
    code, _out, err = cli(strict, "work", "submit", slug)
    assert code == 1 and "is unassigned" in err


def test_a_ticket_moved_back_refuses_submit(strict, fake):
    slug = bound_item(strict)
    assert cli(strict, "work", "start", slug)[0] == 0
    claimed_ticket(fake, "To Do", A)
    code, _out, err = cli(strict, "work", "submit", slug)
    assert code == 1 and "moved in the tracker" in err


def test_an_unreachable_tracker_refuses_submit(strict, fake):
    slug = bound_item(strict)
    assert cli(strict, "work", "start", slug)[0] == 0
    fake.down = True
    code, _out, err = cli(strict, "work", "submit", slug)
    assert code == 1 and f"{slug} was not changed" in err and "unknown" in err
    assert status(strict, slug) == "active"


def test_a_workflow_that_cannot_exclude_refuses_import_and_start(tmp_path, monkeypatch):
    monkeypatch.setenv("TCW_A_EMAIL", "a@example.test")
    monkeypatch.setenv("TCW_PROBE_TOKEN", SENTINEL)
    monkeypatch.setenv("TCW_WORK_OWNER", "a@example.test")
    fake_ = FakeJira(workflow=GLOBAL)
    fake_.account("a@example.test", A, "Alice")
    fake_.ticket(id=TICKET_ID, key=KEY, summary="t")
    fake_.ticket(id="20002", key="SYNC-2", summary="u")
    fake_.install(monkeypatch)
    root = strict_node(tmp_path, strict=True)
    code, out, err = cli(root, "work", "tracker", "import", KEY)
    assert code == 1 and out == "" and "second person could claim it too" in err
    assert FsWorkStore.open(root).query() == []
    slug = FsWorkStore.open(root).create("Linked").slug
    set_tracker_key(root, "strict", False)
    assert cli(root, "work", "tracker", "link", slug, "SYNC-2")[0] == 0
    set_tracker_key(root, "strict", True)
    code, _out, err = cli(root, "work", "start", slug)
    assert code == 1 and "second person could claim it too" in err
    assert status(root, slug) == "backlog"


def test_drop_refuses_an_item_that_was_ever_bound(strict, fake):
    bound = bound_item(strict, "Bound")
    unlinked = bound_item(strict, "Unlinked", ticket=KEY, part="other")
    assert cli(strict, "work", "tracker", "unlink", unlinked, "--reason", "x")[0] == 0
    for slug in (bound, unlinked):
        code, _out, err = cli(strict, "work", "drop", slug, "--confirm")
        assert code == 1 and REFUSED in err
        assert FsWorkStore.open(strict).get(slug) is not None
    set_tracker_key(strict, "strict", False)
    plain = FsWorkStore.open(strict).create("Plain").slug
    set_tracker_key(strict, "strict", True)
    assert cli(strict, "work", "drop", plain, "--confirm")[0] == 0


def test_discards_are_never_refused(strict, fake):
    idle = bound_item(strict, "Idle")
    held = bound_item(strict, "Held", part="other")
    assert cli(strict, "work", "start", held)[0] == 0
    claimed_ticket(fake, "In Progress", B)
    for slug in (idle, held):
        _code, _out, err = cli(strict, "work", "complete", slug, "--resolution",
                               "wontfix", "--confirm")
        assert REFUSED not in err
        assert status(strict, slug) == "discarded"


def test_complete_is_refused_before_the_worktree_merge(strict, fake):
    slug = bound_item(strict)
    commit_all(strict)
    assert cli(strict, "work", "start", slug, "--worktree")[0] == 0
    tree = strict / ".worktrees" / slug
    (tree / "code.txt").write_text("change\n")
    subprocess.run(["git", "-C", str(tree), "add", "code.txt"], check=True)
    subprocess.run(["git", "-C", str(tree), "commit", "-qm", "code"], check=True)
    claimed_ticket(fake, "In Progress", B)
    code, _out, err = cli(strict, "work", "complete", slug, "--resolution", "done",
                          "--confirm")
    assert code == 1 and REFUSED in err
    assert tree.exists() and not (strict / "code.txt").exists()


def test_start_claims_nothing_for_a_start_the_store_would_refuse(strict, fake):
    blocker = bound_item(strict, "Blocker", part="blocker")
    slug = bound_item(strict, "Blocked")
    FsWorkStore.open(strict).add_blocker(slug, blocker)
    code, _out, _err = cli(strict, "work", "start", slug)
    assert code == 1 and fake.writes() == [] and status(strict, slug) == "backlog"


def test_start_refuses_a_ticket_already_yours_in_review(strict, fake):
    slug = bound_item(strict)
    claimed_ticket(fake, "In Review", A)
    code, _out, err = cli(strict, "work", "start", slug)
    assert code == 1 and "not a claim" in err and status(strict, slug) == "backlog"


def test_two_parts_held_in_progress_can_both_complete(strict, fake):
    api = bound_item(strict, "Api", part="api")
    web = bound_item(strict, "Web", part="web")
    for slug in (api, web):
        assert cli(strict, "work", "start", slug)[0] == 0
        assert cli(strict, "work", "submit", slug)[0] == 0
    assert fake.tickets[TICKET_ID].status == "In Progress"       # held for the other part
    code, _out, err = cli(strict, "work", "complete", api, "--resolution", "done",
                          "--confirm")
    assert code == 0 and status(strict, api) == "completed", err
    code, _out, err = cli(strict, "work", "complete", web, "--resolution", "done",
                          "--confirm")
    assert code == 0, err
    assert fake.tickets[TICKET_ID].status == "Done"


def test_an_epic_is_not_gated(strict, fake):
    code, out, err = cli(strict, "work", "new", "An epic", "--epic")
    assert code == 0, err
    slug = out.strip()
    assert cli(strict, "work", "start", slug)[0] == 0
    code, _out, err = cli(strict, "work", "complete", slug, "--resolution", "done",
                          "--confirm", "--force")
    assert code == 0, err


def test_no_refusal_prints_the_token(strict, fake):
    slug = bound_item(strict)
    claimed_ticket(fake, "In Progress", B)
    outputs = [cli(strict, "work", "start", slug), cli(strict, "work", "new", "x")]
    fake.down = True
    outputs.append(cli(strict, "work", "start", slug))
    for _code, out, err in outputs:
        assert SENTINEL not in out + err


def test_strict_false_runs_c3s_start_as_before(tmp_path, fake):
    root = strict_node(tmp_path, strict=False)
    slug = bound_item(root)
    claimed_ticket(fake, "In Progress", B)
    code, _out, err = cli(root, "work", "start", slug)
    assert code == 1 and REFUSED not in err and status(root, slug) == "active"


# ── tcw serve ────────────────────────────────────────────────────────────────


def test_serve_refuses_what_it_cannot_check_and_changes_nothing(strict, fake):
    import json
    import threading
    from urllib.error import HTTPError
    from urllib.request import Request, urlopen

    from tcw.serve import HOST, TcwServer
    from test_tracker_sync import document

    st = FsWorkStore.open(strict)
    slug = bound_item(strict)
    unlinked = st.create_work("Unlinked", intake="x").item.slug
    (st.path(unlinked) / "tracker.yaml").write_text("unlinked: {reason: x}\n")
    epic = st.create_work("An epic", intake="x", type="epic").item.slug
    fake.requests.clear()
    httpd = TcwServer((HOST, 0), strict)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    def send(method, path, body=None):
        request = Request(f"http://{HOST}:{httpd.server_port}{path}", method=method,
                          data=json.dumps(body).encode() if body is not None else b"",
                          headers={"Content-Type": "application/json"})
        try:
            with urlopen(request) as res:
                return res.status, res.read().decode()
        except HTTPError as e:
            return e.code, e.read().decode()

    try:
        before = folder_bytes(strict, slug), len(st.query())
        refused = [
            send("POST", "/api/work", {"title": "Web work"}),
            send("POST", f"/api/work/{slug}/actions/start", {}),
            send("POST", f"/api/work/{slug}/actions/complete",
                 {"resolution": "done", "dod_ack": []}),
            send("DELETE", f"/api/work/{slug}"),
            send("DELETE", f"/api/work/{unlinked}"),
            send("PUT", f"/api/work/{slug}/sidecars/tracker.yaml",
                 {"content": document(ticket_key="SYNC-9")}),
        ]
        for code, text in refused:
            assert code == 409 and "strict tracker mode" in text and SENTINEL not in text
        assert (folder_bytes(strict, slug), len(st.query())) == before
        assert fake.requests == []
        assert send("POST", "/api/work", {"title": "Web epic", "type": "epic"})[0] == 201
        assert send("POST", f"/api/work/{epic}/actions/start", {})[0] == 200
        code, text = send("POST", f"/api/work/{slug}/actions/complete",
                          {"resolution": "wontfix", "dod_ack": []})
        assert code == 200, text
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)
    assert status(strict, slug) == "discarded"


# ── a ticket shared by parts, with strict off ────────────────────────────────


from test_tracker_sync import deliver_now, make_node as sync_node  # noqa: E402


@pytest.fixture()
def node(tmp_path, fake):
    return sync_node(tmp_path, statuses=STATUSES)


def test_the_last_shared_part_completes_from_review_a_ticket_held_in_progress(node, fake):
    api = bound_item(node, "Api half", part="api")
    web = bound_item(node, "Web half", part="web")
    claimed_ticket(fake)
    st = FsWorkStore.open(node)
    for slug in (api, web):
        st.start(slug, owner="a@example.test")
        st.submit(slug)
    assert deliver_now(node, web, move="submit", previous="active").state == "held"
    st.complete(api, "done", ["acked"])
    st.complete(web, "done", ["acked"])
    assert deliver_now(node, web, move="complete", previous="review").state == "current"
    assert fake.tickets[TICKET_ID].status == "Done"


def test_an_unshared_ticket_sent_back_from_review_is_not_carried_forward(node, fake):
    slug = bound_item(node)
    claimed_ticket(fake, "In Progress", A)
    st = FsWorkStore.open(node)
    st.start(slug, owner="a@example.test")
    st.submit(slug)
    st.complete(slug, "done", ["acked"])
    assert deliver_now(node, slug, move="complete", previous="review").state == "conflicting"
    assert fake.writes() == []


def test_a_ticket_taken_again_after_a_discard_is_not_carried_forward(node, fake):
    first = bound_item(node, "First")
    st = FsWorkStore.open(node)
    st.complete(first, "wontfix", ["acked"])
    again = bound_item(node, "Again")                    # the same part, re-taken
    claimed_ticket(fake, "In Progress", A)
    st.start(again, owner="a@example.test")
    st.submit(again)
    st.complete(again, "done", ["acked"])
    assert deliver_now(node, again, move="complete", previous="review").state == "conflicting"
    assert fake.writes() == []


# ── the review's cases ───────────────────────────────────────────────────────


def test_complete_is_refused_when_a_reviewer_sent_the_ticket_back(strict, fake):
    slug = bound_item(strict)
    assert cli(strict, "work", "start", slug)[0] == 0
    assert cli(strict, "work", "submit", slug)[0] == 0
    claimed_ticket(fake, "In Progress", A)
    code, _out, err = cli(strict, "work", "complete", slug, "--resolution", "done",
                          "--confirm")
    assert code == 1 and REFUSED in err and "moved in the tracker" in err
    assert status(strict, slug) == "review"


def test_take_over_of_an_active_item_claims_first(strict, fake):
    slug = bound_item(strict)
    FsWorkStore.open(strict).start(slug, owner="b@example.test")
    claimed_ticket(fake, "In Progress", B)
    code, _out, err = cli(strict, "work", "start", slug, "--take-over")
    assert code == 1 and REFUSED in err and "Bob" in err
    assert FsWorkStore.open(strict).get(slug).owner == "b@example.test"
    assert fake.writes() == []


def test_a_broken_strict_block_names_validate(tmp_path, fake):
    root = strict_node(tmp_path, strict=True)
    set_tracker_key(root, "timeout-seconds", -1)
    code, _out, err = cli(root, "work", "new", "x")
    assert code == 1 and "tcw validate" in err


def test_an_epic_cannot_take_a_worktree(strict, fake):
    commit_all(strict)
    code, out, _err = cli(strict, "work", "new", "An epic", "--epic")
    slug = out.strip()
    code, _out, err = cli(strict, "work", "start", slug, "--worktree")
    assert code == 1 and REFUSED in err and "--worktree" in err
    assert status(strict, slug) == "backlog" and not (strict / ".worktrees").exists()


def test_strict_survives_problems_that_come_from_an_ancestor(tmp_path):
    from test_tracker_inheritance import ABSENT, COMPLETE, _chain, _store
    full = {**COMPLETE, "statuses": STATUSES}
    nodes = _chain(tmp_path, root_board=False, root="off", repo=ABSENT,
                   pkg={**full, "strict": True})
    assert _store(nodes["pkg"]).tracker_config() is None
    assert _store(nodes["pkg"]).tracker_strict() is True
    nodes = _chain(tmp_path / "b", root_board=False, root={**full, "strict": True,
                   "colour": "red"}, repo=ABSENT, pkg={"candidate-query": "x"})
    assert _store(nodes["pkg"]).tracker_config() is None
    assert _store(nodes["pkg"]).tracker_strict() is True
    nodes = _chain(tmp_path / "c", root_board=False, root={**full, "strict": True,
                   "colour": "red"}, repo=ABSENT, pkg={"strict": False})
    assert _store(nodes["pkg"]).tracker_strict() is False


def test_an_unreadable_binding_is_refused_not_a_traceback(strict, fake):
    slug = bound_item(strict)
    assert cli(strict, "work", "start", slug)[0] == 0
    (FsWorkStore.open(strict).path(slug) / "tracker.yaml").write_bytes(b"ticket: \xff\n")
    code, _out, err = cli(strict, "work", "submit", slug)
    assert code == 1 and REFUSED in err and "not bound to a readable ticket" in err
    assert status(strict, slug) == "active"


def test_a_discard_of_a_ticket_nobody_claimed_is_allowed(strict, fake):
    slug = bound_item(strict)
    claimed_ticket(fake, "To Do", None)
    _code, _out, err = cli(strict, "work", "complete", slug, "--resolution", "wontfix",
                           "--confirm")
    assert REFUSED not in err and status(strict, slug) == "discarded"


def test_sync_rechecks_an_owed_claim_under_strict_mode(tmp_path, monkeypatch):
    from test_tracker_sync import record
    monkeypatch.setenv("TCW_A_EMAIL", "a@example.test")
    monkeypatch.setenv("TCW_PROBE_TOKEN", SENTINEL)
    monkeypatch.setenv("TCW_WORK_OWNER", "a@example.test")
    fake_ = FakeJira(workflow=GLOBAL)
    fake_.account("a@example.test", A, "Alice")
    fake_.account("b@example.test", B, "Bob")
    fake_.ticket(id=TICKET_ID, key=KEY, summary="t")
    fake_.install(monkeypatch)
    root = strict_node(tmp_path, strict=False)
    slug = bound_item(root)
    claimed_ticket(fake_, "In Progress", B)
    assert cli(root, "work", "start", slug)[0] == 1          # started; claim owed
    claimed_ticket(fake_, "To Do", None)                     # Bob let it go
    set_tracker_key(root, "strict", True)
    code, out, err = cli(root, "work", "tracker", "sync", slug)
    assert code == 1 and "second person could claim it too" in out + err
    assert record(root, slug)["claim"] == "owed"


# ── a held item and its record, with strict on ───────────────────────────────


def test_a_held_item_drops_its_record_so_strict_mode_does_not_lock_it(strict, fake):
    api = bound_item(strict, "Api", part="api")
    assert cli(strict, "work", "start", api)[0] == 0
    with_record(strict, api, {"state": "pending", "move": "start", "since": "",
                              "claim": "done", "reason": "down", "at": "2026-09-15T00:00:00Z"})
    bound_item(strict, "Web", part="web")
    code, out, _err = cli(strict, "work", "tracker", "sync", api)
    assert code == 0 and "held" in out
    assert record(strict, api) is None
    code, _out, err = cli(strict, "work", "submit", api)
    assert code == 0, err


def test_an_unusable_record_on_an_unmapped_status_is_cleared_by_sync(tmp_path, fake):
    root = make_node(tmp_path, statuses={"active": "In Progress"})
    slug = bound_item(root)
    assert cli(root, "work", "start", slug)[0] == 0
    assert cli(root, "work", "submit", slug)[0] == 0           # review is unmapped
    with_record(root, slug, "not a mapping")
    code, out, _err = cli(root, "work", "tracker", "sync", slug)
    assert code == 0 and record(root, slug) is None, out


def test_a_finished_held_item_keeps_the_record_that_can_still_deliver_its_move(
        tmp_path, fake):
    from test_tracker_sync import RECORD
    root = make_node(tmp_path, statuses=STATUSES)
    api = bound_item(root, "Api", part="api")
    claimed_ticket(fake, "In Review")
    st = FsWorkStore.open(root)
    st.start(api, owner="a@example.test")
    st.submit(api)
    st.complete(api, "done", ["acked"])
    with_record(root, api, {**RECORD, "move": "complete", "since": "In Review"})
    web = bound_item(root, "Web", part="web")
    assert "held" in cli(root, "work", "tracker", "sync", api)[1]
    assert record(root, api) is not None
    assert cli(root, "work", "tracker", "unlink", web, "--reason", "wrong part")[0] == 0
    code, out, err = cli(root, "work", "tracker", "sync", "--all")
    assert code == 0, (out, err)
    assert fake.tickets[TICKET_ID].status == "Done"


def test_a_refusal_for_a_plainly_linked_ticket_names_the_opt_in(tmp_path, fake):
    """Strict mode refuses the move before it happens, so its refusal is the only place
    to say the ticket was linked without its status synced, and how to opt in."""
    root = make_node(tmp_path, statuses=STATUSES)
    st = FsWorkStore.open(root)
    slug = st.create("Already under way").slug
    st.start(slug, owner="a@example.test")
    assert cli(root, "work", "tracker", "link", slug, "SYNC-1")[0] == 0
    set_tracker_key(root, "strict", True)
    code, _out, err = cli(root, "work", "submit", slug)
    assert code == 1 and REFUSED in err
    assert "linked without syncing its status" in err and "--sync-status" in err
    assert status(root, slug) == "active" and fake.writes() == []
