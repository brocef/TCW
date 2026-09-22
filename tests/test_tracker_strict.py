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

from tcw.store.base import STRICT_NEEDS_EXCLUSIVE_CLAIM, parse_tracker_config
from tcw.store.fs import FsWorkStore
from tcw.validate import validate
from test_tracker_sync import (A, B, KEY, NAMED_START, SENTINEL, STATUSES,  # noqa: F401
                               TICKET_ID, bound_item, claimed_ticket, cli, fake,
                               make_node, record, status, with_record)
from tracker_fake import BASE_URL

BASE = {
    "provider": "jira-cloud", "base-url": BASE_URL,
    "candidate-query": "assignee = currentUser()",
    "credentials": {"email-env": "TCW_A_EMAIL", "token-env": "TCW_PROBE_TOKEN"},
    "transitions": {"start": "Start Progress"},
}


def strict_node(tmp_path: Path, *, strict, claim_transition,
                statuses: dict | None = STATUSES, name: str = "alpha",
                transitions: dict | None = NAMED_START) -> Path:
    """`claim_transition` sets `exclusive-claim-transition`, or leaves it unset when
    `None`. No default, like `strict`: strict mode requires the key, so the parser
    branches on it. `transitions=None` leaves `work.tracker.transitions` out."""
    root = make_node(tmp_path, statuses=statuses, name=name, transitions=transitions)
    set_tracker_key(root, "strict", strict)
    set_tracker_key(root, "exclusive-claim-transition", claim_transition)
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

# What every strict block needs besides its statuses: without it the block is
# broken, and a test of some other broken part could pass for that reason instead.
CLAIM = {"exclusive-claim-transition": "Start Progress"}


def parsed(**extra):
    return parse_tracker_config({**BASE, **extra})


def test_strict_true_with_the_required_statuses_parses():
    config, problems = parsed(strict=True, statuses=STATUSES, **CLAIM)
    assert problems == [] and config.strict is True


def test_strict_defaults_to_false():
    config, problems = parsed()
    assert problems == [] and config.strict is False


@pytest.mark.parametrize("extra, key", [
    ({"strict": "yes", "statuses": STATUSES}, "work.tracker.strict"),
    ({"strict": True, **CLAIM,
      "statuses": {"completed": "Done", "discarded": "Won't Do"}},
     "work.tracker.statuses.active"),
    ({"strict": True, **CLAIM,
      "statuses": {"active": "In Progress", "discarded": "Won't Do"}},
     "work.tracker.statuses.completed"),
    ({"strict": True, **CLAIM,
      "statuses": {"active": "In Progress", "completed": "Done",
                   "discarded": {"wontfix": "Won't Do"}}},
     "work.tracker.statuses.discarded"),
    ({"strict": True, **CLAIM, "statuses": {"active": "In Progress", "completed": "Done"}},
     "work.tracker.statuses.discarded"),
], ids=["not-boolean", "no-active", "no-completed", "partial-discards", "no-discarded"])
def test_a_strict_block_missing_what_it_needs_is_a_problem(extra, key):
    config, problems = parsed(**extra)
    assert config is None
    assert any(p.startswith(key) for p in problems), problems


def test_validate_names_the_key_and_the_board_still_reads(tmp_path, fake):
    root = strict_node(tmp_path, strict=True, claim_transition="Start Progress",
                       statuses={"active": "In Progress", "discarded": "Won't Do"})
    assert any("work.tracker.statuses.completed" in p for p in validate(root))
    assert cli(root, "work", "list")[0] == 0


# ── strict mode requires exclusive-claim-transition ─────────────────────────


def test_strict_without_the_claim_transition_is_one_problem_naming_it():
    config, problems = parsed(strict=True, statuses=STATUSES)
    assert config is None
    assert problems == [STRICT_NEEDS_EXCLUSIVE_CLAIM]
    [problem] = problems
    assert problem.startswith(
        "work.tracker.exclusive-claim-transition: required when strict is true")
    assert "only one person" in problem and "Name the transition" in problem


def test_strict_with_the_claim_transition_parses():
    config, problems = parsed(strict=True, statuses=STATUSES,
                              **{"exclusive-claim-transition": "Start Progress"})
    assert problems == [] and config.strict is True


@pytest.mark.parametrize("extra", [{}, {"strict": False}], ids=["absent", "false"])
def test_without_strict_the_claim_transition_stays_optional(extra):
    config, problems = parsed(statuses=STATUSES, **extra)
    assert problems == [] and config is not None


@pytest.mark.parametrize("value", [None, ""], ids=["null", "blank"])
def test_a_written_but_empty_claim_transition_keeps_its_own_one_problem(value):
    config, problems = parsed(strict=True, statuses=STATUSES,
                              **{"exclusive-claim-transition": value})
    assert config is None
    [problem] = [p for p in problems if "exclusive-claim-transition" in p]
    assert len(problems) == 1, problems
    assert "expected a non-empty string" in problem
    assert problem != STRICT_NEEDS_EXCLUSIVE_CLAIM


def test_validate_names_the_missing_claim_transition_and_the_board_still_reads(
        tmp_path, fake):
    root = strict_node(tmp_path, strict=True, claim_transition=None)
    assert f"tcw-config.yaml: {STRICT_NEEDS_EXCLUSIVE_CLAIM}" in validate(root)
    assert cli(root, "work", "list")[0] == 0


def test_without_the_claim_transition_strict_moves_refuse_and_name_validate(
        tmp_path, fake):
    root = strict_node(tmp_path, strict=True, claim_transition="Start Progress")
    idle = bound_item(root, "Idle", part="idle")
    busy = bound_item(root, "Busy", part="busy")
    started(root, busy)
    set_tracker_key(root, "exclusive-claim-transition", None)
    st = FsWorkStore.open(root)
    assert st.tracker_strict() is True
    assert st.tracker_config() is None
    assert st.tracker_problems() == [f"tcw-config.yaml: {STRICT_NEEDS_EXCLUSIVE_CLAIM}"]
    for argv, slug, before in ((("start", idle), idle, "backlog"),
                               (("submit", busy), busy, "active")):
        code, _out, err = cli(root, "work", *argv)
        assert code == 1 and REFUSED in err and "tcw validate" in err, (argv, err)
        assert status(root, slug) == before, argv


@pytest.mark.parametrize("strict, problem, expected", [
    (True, False, True), (False, False, False), (None, False, False),
    (True, True, True), (False, True, False), (None, True, False),
    ("yes", True, True),
], ids=["on", "off", "absent", "on-broken", "off-broken", "absent-broken",
        "string-broken"])
def test_a_broken_block_does_not_switch_strict_off(tmp_path, fake, strict, problem,
                                                  expected):
    root = strict_node(tmp_path, strict=strict, claim_transition="Start Progress")
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
    return strict_node(tmp_path, strict=True, claim_transition="Start Progress")


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


def test_authorize_reads_the_item_from_the_own_store_when_given_one(tmp_path, fake):
    """`own=` is how `complete` judges a worktree item from its branch copy: the
    binding, status and owner come from `own`, everything else from `store`."""
    from tcw.tracker.sync import authorize
    primary = strict_node(tmp_path, strict=True, claim_transition="Start Progress",
                          name="alpha")
    branch = strict_node(tmp_path, strict=True, claim_transition="Start Progress",
                         name="beta")
    slug = bound_item(primary)
    assert bound_item(branch) == slug          # same title, same day, same slug
    started(primary, slug)                     # the stale copy: still `active`
    started(branch, slug, submitted=True)      # the branch copy: `review`
    claimed_ticket(fake, "In Review", A)

    st, client, config = client_for(primary)
    own = FsWorkStore.open(branch)
    assert authorize(st, slug, client, config, target="Done", own=own) is None
    refusal = authorize(st, slug, client, config, target="Done")
    assert refusal is not None and "In Review" in refusal


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
    root = strict_node(tmp_path, strict=True, claim_transition="Start Progress")
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


def test_strict_refuses_a_raw_entry_but_not_a_ticket_through_inbox_accept(strict, fake):
    set_tracker_key(strict, "inbox-query", "status = Triage")
    inbox = FsWorkStore.open(strict).root / "inbox"
    inbox.mkdir(exist_ok=True)
    (inbox / "a-request.md").write_text("# A request\n", encoding="utf-8")
    code, _out, err = cli(strict, "work", "inbox", "accept", "a-request.md")
    assert code == 1 and REFUSED in err and "tcw work tracker import <ticket>" in err
    assert (inbox / "a-request.md").exists()
    code, out, err = cli(strict, "work", "inbox", "accept", KEY)
    assert code == 0, err
    assert REFUSED not in err
    [item] = FsWorkStore.open(strict).query()
    assert out.strip() == item.slug


def test_strict_refuses_a_ticket_through_inbox_accept_where_import_is_refused(
        tmp_path, monkeypatch):
    monkeypatch.setenv("TCW_A_EMAIL", "a@example.test")
    monkeypatch.setenv("TCW_PROBE_TOKEN", SENTINEL)
    fake_ = FakeJira(workflow=GLOBAL)
    fake_.account("a@example.test", A, "Alice")
    fake_.ticket(id=TICKET_ID, key=KEY, summary="t")
    fake_.install(monkeypatch)
    root = strict_node(tmp_path, strict=True, claim_transition="Start Progress")
    set_tracker_key(root, "inbox-query", "status = Triage")
    code, out, err = cli(root, "work", "inbox", "accept", KEY)
    assert code == 1 and out == "" and "second person could claim it too" in err
    assert err.startswith("tcw work inbox accept: ")
    assert FsWorkStore.open(root).query() == []


def test_a_broken_strict_block_still_refuses_new(tmp_path, fake):
    root = strict_node(tmp_path, strict=True, claim_transition="Start Progress")
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
    set_tracker_key(root, "exclusive-claim-transition", "Start Progress")
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


def test_a_workflow_that_cannot_exclude_refuses_import(tmp_path, monkeypatch):
    """`import` still claims through the claim transition and asks whether the workflow
    offers it again. A strict `start` no longer does: its exclusivity is
    `exclusive-claim-transition`'s (see the tests after this one)."""
    monkeypatch.setenv("TCW_A_EMAIL", "a@example.test")
    monkeypatch.setenv("TCW_PROBE_TOKEN", SENTINEL)
    monkeypatch.setenv("TCW_WORK_OWNER", "a@example.test")
    fake_ = FakeJira(workflow=GLOBAL)
    fake_.account("a@example.test", A, "Alice")
    fake_.ticket(id=TICKET_ID, key=KEY, summary="t")
    fake_.ticket(id="20002", key="SYNC-2", summary="u")
    fake_.install(monkeypatch)
    root = strict_node(tmp_path, strict=True, claim_transition="Start Progress")
    code, out, err = cli(root, "work", "tracker", "import", KEY)
    assert code == 1 and out == "" and "second person could claim it too" in err
    assert FsWorkStore.open(root).query() == []


def test_strict_import_of_a_held_ticket_needs_no_start_transition(tmp_path, monkeypatch):
    """`claim_refusal` reads `transitions.start` to ask whether the workflow could
    still admit a second claimant. With no such key, there is no claim to re-offer
    and nothing was promised, so the import of a ticket this account already holds
    is not stopped. Exclusivity here is `exclusive-claim-transition`'s, which is
    untouched by this change."""
    monkeypatch.setenv("TCW_A_EMAIL", "a@example.test")
    monkeypatch.setenv("TCW_PROBE_TOKEN", SENTINEL)
    monkeypatch.setenv("TCW_WORK_OWNER", "a@example.test")
    fake_ = FakeJira(workflow=SYNC)
    fake_.account("a@example.test", A, "Alice")
    fake_.ticket(id=TICKET_ID, key=KEY, summary="t", status="In Progress", assignee=A)
    fake_.install(monkeypatch)
    root = strict_node(tmp_path, strict=True, claim_transition="Start Progress",
                       transitions=None)
    code, out, err = cli(root, "work", "tracker", "import", KEY)
    assert code == 0, err
    [item] = FsWorkStore.open(root).query()
    assert out.strip() == item.slug
    assert fake_.applied == []


# A workflow with two ways into progress, so which one a strict start applied shows
# whether it came from `exclusive-claim-transition` or from `transitions.start`.
TWO_WAYS_IN = {**SYNC, "To Do": [("61", "Claim", "In Progress"), *SYNC["To Do"]]}


def test_a_strict_start_takes_the_ticket_through_the_exclusive_claim_transition(
        tmp_path, monkeypatch):
    monkeypatch.setenv("TCW_A_EMAIL", "a@example.test")
    monkeypatch.setenv("TCW_PROBE_TOKEN", SENTINEL)
    monkeypatch.setenv("TCW_WORK_OWNER", "a@example.test")
    fake_ = FakeJira(workflow=TWO_WAYS_IN)
    fake_.account("a@example.test", A, "Alice")
    fake_.ticket(id=TICKET_ID, key=KEY, summary="t")
    fake_.install(monkeypatch)
    root = strict_node(tmp_path, strict=True, claim_transition="Claim")
    slug = bound_item(root)
    fake_.requests.clear()
    code, _out, err = cli(root, "work", "start", slug)
    assert code == 0, err
    assert fake_.applied == ["61"], fake_.applied
    writes = fake_.writes()
    # Applied first, so a workflow that refuses a second claimant stops them before
    # they reach the assignment.
    assert writes.index(("POST", f"/rest/api/3/issue/{TICKET_ID}/transitions")) < \
        writes.index(("PUT", f"/rest/api/3/issue/{TICKET_ID}/assignee"))
    held = fake_.tickets[TICKET_ID]
    assert (held.status, held.assignee, status(root, slug)) == ("In Progress", A, "active")


# ── the claim transition never moves a ticket backwards ─────────────────────
#
# `exclusive-claim-transition` leads onto `statuses.active`. A workflow that offers
# it from every status — the `GLOBAL` one below — would therefore apply it to a
# ticket already in review and drag that ticket back down, which is the one thing no
# lifecycle move does. What happens instead depends on strict mode.


def global_claim_node(tmp_path, monkeypatch, *, strict: bool, ticket_status: str):
    monkeypatch.setenv("TCW_A_EMAIL", "a@example.test")
    monkeypatch.setenv("TCW_PROBE_TOKEN", SENTINEL)
    monkeypatch.setenv("TCW_WORK_OWNER", "a@example.test")
    fake_ = FakeJira(workflow=GLOBAL)
    fake_.account("a@example.test", A, "Alice")
    fake_.ticket(id=TICKET_ID, key=KEY, summary="t", status=ticket_status)
    fake_.install(monkeypatch)
    return strict_node(tmp_path, strict=strict,
                       claim_transition="Start Progress"), fake_


def test_a_start_above_the_claim_transition_takes_the_ticket_without_applying_it(
        tmp_path, monkeypatch):
    """Without strict mode: the transition is skipped, the ticket is taken by the
    assignment and its read-back alone, it is left in review, and the output says the
    claim was the weaker kind."""
    root, fake_ = global_claim_node(tmp_path, monkeypatch, strict=False,
                                    ticket_status="In Review")
    slug = bound_item(root)
    fake_.applied.clear()
    code, _out, err = cli(root, "work", "start", slug)
    assert code == 0, err
    assert fake_.applied == [], fake_.applied
    held = fake_.tickets[TICKET_ID]
    assert (held.status, held.assignee) == ("In Review", A)
    assert status(root, slug) == "active"
    assert "exclusive-claim-transition" in err, err
    assert "assignment and reading it back" in err, err


def test_a_strict_start_above_the_claim_transition_is_refused_before_the_item_moves(
        tmp_path, monkeypatch):
    """Under strict mode: refused, because strict mode's exclusivity *is* that
    transition and an assignment on its own is not the proof it asks for. The item
    does not move, nothing is sent, and the message names both ways out."""
    root, fake_ = global_claim_node(tmp_path, monkeypatch, strict=True,
                                    ticket_status="In Review")
    slug = bound_item(root)
    fake_.requests.clear()
    code, _out, err = cli(root, "work", "start", slug)
    assert code == 1 and REFUSED in err, err
    # GLOBAL offers the transition from every status, so here it really would have
    # moved the ticket back — the reason the refusal is entitled to give.
    assert f"would move {KEY} back" in err, err
    assert f"Move {KEY} back to 'In Progress'" in err, err
    assert "turn work.tracker.strict off" in err, err
    assert status(root, slug) == "backlog"
    assert fake_.writes() == [] and fake_.tickets[TICKET_ID].status == "In Review"


@pytest.mark.parametrize("ticket_status", ["To Do", "In Progress"],
                         ids=["below-the-ladder", "on-the-claims-own-rung"])
def test_a_strict_start_on_the_claims_own_status_still_asserts_through_it(
        tmp_path, monkeypatch, ticket_status):
    """The refusal above is only for a ticket *past* the claim's status. One on it, or
    below it, is claimed through the transition exactly as before."""
    root, fake_ = global_claim_node(tmp_path, monkeypatch, strict=True,
                                    ticket_status=ticket_status)
    slug = bound_item(root)
    fake_.applied.clear()
    code, _out, err = cli(root, "work", "start", slug)
    assert code == 0, err
    assert fake_.applied == ["21"], fake_.applied
    assert fake_.tickets[TICKET_ID].assignee == A and status(root, slug) == "active"


# ── a claim whose transition landed and whose assignment did not ────────────
#
# The ticket has moved and is held by nobody, and running the command again cannot
# recover it: the transition is no longer offered from where the ticket now sits,
# which is the very property that makes it exclusive. Both callers have to say what
# happened and name the one thing that does work.


def refuse_the_assignment(fake_) -> None:
    from tcw.tracker import jira
    fake_.fail("PUT", "/assignee",
               jira._for_status(400, {}, "cannot assign", "x"))


MOVED_UNASSIGNED = f"{KEY} was moved to 'In Progress' but is not assigned to you."


def test_a_strict_start_says_it_took_the_ticket_not_that_it_was_already_held(
        tmp_path, monkeypatch):
    """`_strict_claim` takes the ticket before the item moves, so by the time delivery
    runs the ticket is this account's. Reporting that as *already* held would describe
    a claim this same command had just made."""
    root, fake_ = global_claim_node(tmp_path, monkeypatch, strict=True,
                                    ticket_status="To Do")
    slug = bound_item(root)
    code, _out, err = cli(root, "work", "start", slug)
    assert code == 0, err
    assert "already held by you" not in err, err
    assert f"{KEY} is held by you." in err, err


def test_a_strict_start_whose_assignment_failed_says_the_ticket_moved(tmp_path,
                                                                      monkeypatch):
    root, fake_ = global_claim_node(tmp_path, monkeypatch, strict=True,
                                    ticket_status="To Do")
    slug = bound_item(root)
    refuse_the_assignment(fake_)
    code, _out, err = cli(root, "work", "start", slug)
    assert code == 1 and REFUSED in err, err
    assert MOVED_UNASSIGNED in err, err
    assert "Assign it to yourself in the tracker, then run this again." in err, err
    assert f"Run `tcw work start {slug}` again" not in err, err
    assert status(root, slug) == "backlog"
    held = fake_.tickets[TICKET_ID]
    assert (held.status, held.assignee) == ("In Progress", None)


def test_a_start_whose_assignment_failed_after_the_transition_says_the_ticket_moved(
        tmp_path, monkeypatch):
    """The same through `deliver`, which claims for a start outside strict mode."""
    root, fake_ = global_claim_node(tmp_path, monkeypatch, strict=False,
                                    ticket_status="To Do")
    slug = bound_item(root)
    refuse_the_assignment(fake_)
    code, _out, err = cli(root, "work", "start", slug)
    assert code == 1, err
    assert MOVED_UNASSIGNED in err, err
    assert f"Take it with `tcw work tracker claim {slug}`" not in err, err
    assert status(root, slug) == "active"
    held = fake_.tickets[TICKET_ID]
    assert (held.status, held.assignee) == ("In Progress", None)


def fail_the_read_back(fake_) -> None:
    """Let the assignment land and break the read that would confirm it, armed from
    inside the assignment so it cannot catch an earlier read."""
    from tcw.tracker import jira
    fake_.before("PUT", "/assignee", lambda: fake_.fail(
        "GET", f"/rest/api/3/issue/{TICKET_ID}?",
        jira.TrackerUnavailable("down (fake)")))


@pytest.mark.parametrize("strict", [True, False], ids=["strict", "not-strict"])
def test_a_claim_whose_read_back_failed_does_not_call_the_ticket_unassigned(
        tmp_path, monkeypatch, strict):
    """The read-back is the *other* failure after an applied assertion, and it happens
    only once the assignment has landed — so the ticket is not unassigned, and saying
    it is contradicts the sentence printed beside it. It also replaces advice that
    would have worked: running the command again succeeds, because a claim of a ticket
    already yours returns before it sends anything."""
    root, fake_ = global_claim_node(tmp_path, monkeypatch, strict=strict,
                                    ticket_status="To Do")
    slug = bound_item(root)
    fail_the_read_back(fake_)
    code, _out, err = cli(root, "work", "start", slug)
    assert code == 1, err
    assert "but is not assigned to you" not in err, err
    assert "Run this again to find out." in err, err
    assert f"Take it with `tcw work tracker claim {slug}`" not in err, err
    # Which of the two callers ran: strict mode refuses before the item moves
    # (`_strict_claim`), and without it the claim is `deliver`'s, after the move.
    assert status(root, slug) == ("backlog" if strict else "active")
    held = fake_.tickets[TICKET_ID]
    assert (held.status, held.assignee) == ("In Progress", A)


def test_the_strict_past_the_claim_refusal_only_says_it_would_move_it_back_if_it_could(
        tmp_path, monkeypatch):
    """The refusal is the same either way — strict mode's proof of exclusivity is
    missing whether or not the transition is offered from there — but the reason is
    not. On a workflow that does not offer it from the ticket's status, nothing would
    have moved the ticket back, and saying it would is untrue."""
    monkeypatch.setenv("TCW_A_EMAIL", "a@example.test")
    monkeypatch.setenv("TCW_PROBE_TOKEN", SENTINEL)
    monkeypatch.setenv("TCW_WORK_OWNER", "a@example.test")
    fake_ = FakeJira(workflow=SYNC)               # 'Start Progress' only from 'To Do'
    fake_.account("a@example.test", A, "Alice")
    fake_.ticket(id=TICKET_ID, key=KEY, summary="t", status="In Review")
    fake_.install(monkeypatch)
    root = strict_node(tmp_path, strict=True, claim_transition="Start Progress")
    slug = bound_item(root)
    code, _out, err = cli(root, "work", "start", slug)
    assert code == 1 and REFUSED in err, err
    assert f"{KEY}'s workflow does not offer that transition from there" in err, err
    assert "would move" not in err, err
    assert f"Move {KEY} back to 'In Progress'" in err, err
    assert status(root, slug) == "backlog" and fake_.writes() == []


# ── what a strict start's own claim line withholds, and what it must not ────


def test_a_strict_start_whose_commit_is_refused_still_says_it_claimed_once(
        tmp_path, monkeypatch):
    """A refused commit leaves the item moved, so that path delivers the move too —
    and it has to withhold the delivery's claim line for the same reason the ordinary
    path does: this very command took the ticket moments ago and already said so."""
    root, fake_ = global_claim_node(tmp_path, monkeypatch, strict=True,
                                    ticket_status="To Do")
    slug = bound_item(root)
    hook = root / ".git" / "hooks" / "pre-commit"       # the commit, and only it, fails
    hook.write_text("#!/bin/sh\nexit 1\n")
    hook.chmod(0o755)
    code, _out, err = cli(root, "work", "start", slug)
    assert code == 1, err
    assert f"{KEY} is already held by you." not in err, err
    assert err.count(f"{KEY} is held by you.") == 1, err


def steal_before_the_nth_read(fake_, n: int) -> None:
    """Leave the ticket held by nobody just before the `n`th read of it from now on:
    somebody letting it go in the window between the claim and the delivery."""
    answer, reads = fake_.answer, []

    def counting(client, method, path, body):
        if method == "GET" and "?fields=" in path:
            reads.append(path)
            if len(reads) == n:
                fake_.tickets[TICKET_ID].assignee = None
        return answer(client, method, path, body)

    fake_.answer = counting


def test_a_strict_start_reports_a_claim_the_delivery_had_to_make_again(tmp_path,
                                                                      monkeypatch):
    """The other half of the same rule: what a strict start withholds is the sentence
    saying the ticket was *already* held, and nothing else. If the ticket is let go
    between the strict claim and the delivery, the delivery takes it back — and a
    claim this run made is news whoever said what before it."""
    root, fake_ = global_claim_node(tmp_path, monkeypatch, strict=True,
                                    ticket_status="To Do")
    slug = bound_item(root)
    steal_before_the_nth_read(fake_, 3)       # the strict claim's two reads, then this
    code, _out, err = cli(root, "work", "start", slug)
    assert code == 0, err
    assert err.count(f"{KEY} is held by you.") == 2, err
    assigned = [path for _method, path in fake_.writes() if path.endswith("/assignee")]
    assert len(assigned) == 2, fake_.writes()
    assert fake_.tickets[TICKET_ID].assignee == A


def test_a_strict_start_refuses_a_second_claimant_the_workflow_excludes(tmp_path,
                                                                       monkeypatch):
    """Bob reads the ticket free; before his claim goes out, Alice's whole start runs.
    Bob's own read said nobody held it, so only the workflow refusing the exclusive
    claim transition from 'In Progress' can stop him — and it does, before his
    assignment could overwrite hers, and before his item moves."""
    monkeypatch.setenv("TCW_A_EMAIL", "a@example.test")
    monkeypatch.setenv("TCW_B_EMAIL", "b@example.test")
    monkeypatch.setenv("TCW_PROBE_TOKEN", SENTINEL)
    fake_ = FakeJira(workflow=SYNC)
    fake_.account("a@example.test", A, "Alice")
    fake_.account("b@example.test", B, "Bob")
    fake_.ticket(id=TICKET_ID, key=KEY, summary="t")
    fake_.install(monkeypatch)
    alice = strict_node(tmp_path, strict=True, claim_transition="Start Progress")
    bob = make_node(tmp_path, statuses=STATUSES, name="beta", email_env="TCW_B_EMAIL")
    set_tracker_key(bob, "strict", True)
    set_tracker_key(bob, "exclusive-claim-transition", "Start Progress")
    monkeypatch.setenv("TCW_WORK_OWNER", "a@example.test")
    hers = bound_item(alice)
    monkeypatch.setenv("TCW_WORK_OWNER", "b@example.test")
    his = bound_item(bob)

    def alice_starts():
        monkeypatch.setenv("TCW_WORK_OWNER", "a@example.test")
        assert cli(alice, "work", "start", hers)[0] == 0
        monkeypatch.setenv("TCW_WORK_OWNER", "b@example.test")

    fake_.before("POST", "/transitions", alice_starts, account=B)
    code, _out, err = cli(bob, "work", "start", his)
    assert code == 1 and REFUSED in err and "would not accept" in err, err
    assert status(bob, his) == "backlog" and status(alice, hers) == "active"
    assert fake_.tickets[TICKET_ID].assignee == A
    assert fake_.writes(B) == [("POST", f"/rest/api/3/issue/{TICKET_ID}/transitions")]


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
    claimed_ticket(fake, "To Do", A)                   # moved back in the tracker
    code, _out, err = cli(strict, "work", "complete", slug, "--resolution", "done",
                          "--confirm")
    assert code == 1 and REFUSED in err and "moved in the tracker" in err, err
    assert tree.exists() and not (strict / "code.txt").exists()


def test_complete_is_not_refused_for_a_ticket_someone_else_holds(strict, fake):
    """A claim gates work, not resolution: strict mode still asks where the ticket is
    before a completion, but not who holds it."""
    slug = bound_item(strict)
    assert cli(strict, "work", "start", slug)[0] == 0
    claimed_ticket(fake, "In Progress", B)
    code, _out, err = cli(strict, "work", "complete", slug, "--resolution", "done",
                          "--confirm", "--force")
    assert code == 0 and REFUSED not in err, err
    assert status(strict, slug) == "completed"
    assert (fake.tickets[TICKET_ID].status, fake.tickets[TICKET_ID].assignee) == ("Done", B)


def test_complete_judges_the_ticket_from_the_worktree_s_copy(strict, fake):
    """A worktree item submitted on its branch: the ticket is where the branch's
    `submit` put it, and the primary checkout's copy — still `active` — would
    refuse it as out of place."""
    slug = bound_item(strict)
    commit_all(strict)
    assert cli(strict, "work", "start", slug, "--worktree")[0] == 0
    tree = strict / ".worktrees" / slug
    assert cli(tree, "work", "submit", slug)[0] == 0
    assert status(strict, slug) == "active"             # the stale copy
    assert status(tree, slug) == "review"               # the branch copy
    claimed_ticket(fake, "In Review", A)

    code, _out, err = cli(strict, "work", "complete", slug, "--resolution", "done",
                          "--confirm")
    assert code == 0 and REFUSED not in err
    assert status(strict, slug) == "completed"


def test_start_claims_nothing_for_a_start_the_store_would_refuse(strict, fake):
    blocker = bound_item(strict, "Blocker", part="blocker")
    slug = bound_item(strict, "Blocked")
    FsWorkStore.open(strict).add_blocker(slug, blocker)
    code, _out, _err = cli(strict, "work", "start", slug)
    assert code == 1 and fake.writes() == [] and status(strict, slug) == "backlog"


def test_start_of_a_ticket_already_yours_in_review_leaves_it_there(strict, fake):
    """Strict mode asks that the ticket be held by you, and it is. Where it sits is not
    strict mode's question any more — the claim no longer moves it — and a start does
    not move a ticket back."""
    slug = bound_item(strict)
    claimed_ticket(fake, "In Review", A)
    fake.requests.clear()
    code, _out, err = cli(strict, "work", "start", slug)
    assert code == 0 and REFUSED not in err, err
    assert status(strict, slug) == "active"
    assert fake.tickets[TICKET_ID].status == "In Review" and fake.writes() == []


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


@pytest.mark.parametrize("promote", [True, False])
def test_a_type_change_is_refused(strict, fake, promote):
    """An epic is ungated, so a type change would lift or strand a ticket gate."""
    if promote:
        slug, to, before = bound_item(strict), "epic", ""
    else:
        code, out, err = cli(strict, "work", "new", "An epic", "--epic")
        assert code == 0, err
        slug, to, before = out.strip(), "", "epic"
    code, _out, err = cli(strict, "work", "edit", slug, "--type", to)
    assert code == 1
    assert "refused under strict tracker mode" in err
    assert "tcw work new --epic" in err
    assert FsWorkStore.open(strict).get(slug).type == before


def test_no_refusal_prints_the_token(strict, fake):
    slug = bound_item(strict)
    claimed_ticket(fake, "In Progress", B)
    outputs = [cli(strict, "work", "start", slug), cli(strict, "work", "new", "x")]
    fake.down = True
    outputs.append(cli(strict, "work", "start", slug))
    for _code, out, err in outputs:
        assert SENTINEL not in out + err


def test_strict_false_runs_c3s_start_as_before(tmp_path, fake):
    root = strict_node(tmp_path, strict=False, claim_transition="Start Progress")
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
        ]
        for code, text in refused:
            assert code == 409 and "strict tracker mode" in text and SENTINEL not in text
        # Refused in every mode, as a generated sidecar, not only under strict mode.
        code, text = send("PUT", f"/api/work/{slug}/sidecars/tracker.yaml",
                          {"content": document(ticket_key="SYNC-9")})
        assert code == 409 and "tcw work tracker" in text and SENTINEL not in text
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
    root = strict_node(tmp_path, strict=True, claim_transition="Start Progress")
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
    full = {**COMPLETE, "statuses": STATUSES, **CLAIM}
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


CLAIM_FROM_PARENT = "Start"
MISSING = [f"tcw-config.yaml: {STRICT_NEEDS_EXCLUSIVE_CLAIM}"]


@pytest.mark.parametrize("parent_has_key, pkg_extra, expected", [
    (True, {}, []),
    (False, {}, MISSING),
    (False, {"exclusive-claim-transition": CLAIM_FROM_PARENT}, []),
    (False, {"strict": False}, []),
], ids=["parent-sets-it", "nobody-sets-it", "child-sets-it", "child-not-strict"])
def test_the_claim_transition_requirement_follows_inheritance(tmp_path, parent_has_key,
                                                              pkg_extra, expected):
    """The key can come from the parent or the child, and a child that turns strict
    off needs none. Missing, it is the child's own problem even though `strict`
    came from the parent: nobody wrote the key, so no ancestor file is to blame."""
    from test_tracker_inheritance import ABSENT, COMPLETE, QUERY_ONLY, _chain, _store
    parent = {**COMPLETE, "statuses": STATUSES, "strict": True}
    if parent_has_key:
        parent["exclusive-claim-transition"] = CLAIM_FROM_PARENT
    nodes = _chain(tmp_path, root_board=False, root=parent, repo=ABSENT,
                   pkg={**QUERY_ONLY, **pkg_extra})
    assert _store(nodes["pkg"]).tracker_problems() == expected


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


def test_sync_takes_an_owed_claim_through_the_exclusive_claim_transition(tmp_path,
                                                                       monkeypatch):
    from test_tracker_sync import record
    monkeypatch.setenv("TCW_A_EMAIL", "a@example.test")
    monkeypatch.setenv("TCW_PROBE_TOKEN", SENTINEL)
    monkeypatch.setenv("TCW_WORK_OWNER", "a@example.test")
    fake_ = FakeJira(workflow=GLOBAL)
    fake_.account("a@example.test", A, "Alice")
    fake_.account("b@example.test", B, "Bob")
    fake_.ticket(id=TICKET_ID, key=KEY, summary="t")
    fake_.install(monkeypatch)
    root = strict_node(tmp_path, strict=False, claim_transition="Start Progress")
    slug = bound_item(root)
    claimed_ticket(fake_, "In Progress", B)
    assert cli(root, "work", "start", slug)[0] == 1          # started; claim owed
    claimed_ticket(fake_, "To Do", None)                     # Bob let it go
    set_tracker_key(root, "strict", True)
    set_tracker_key(root, "exclusive-claim-transition", "Start Progress")
    fake_.requests.clear()
    code, out, err = cli(root, "work", "tracker", "sync", slug)
    # The owed claim is taken through the exclusive claim transition, as `start`
    # would take it; it is already where the item is, so nothing else is sent.
    assert code == 0, (out, err)
    assert fake_.applied == ["21"] and fake_.tickets[TICKET_ID].assignee == A
    assert record(root, slug) is None


# ── a held item and its record, with strict on ───────────────────────────────


def test_a_held_item_drops_its_record_so_strict_mode_does_not_lock_it(strict, fake):
    api = bound_item(strict, "Api", part="api")
    assert cli(strict, "work", "start", api)[0] == 0
    with_record(strict, api, {"state": "pending", "move": "start", "since": "",
                              "reason": "down", "at": "2026-09-15T00:00:00Z"})
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
    set_tracker_key(root, "exclusive-claim-transition", "Start Progress")
    code, _out, err = cli(root, "work", "submit", slug)
    assert code == 1 and REFUSED in err
    assert "linked without syncing its status" in err and "tcw work tracker claim" in err
    assert "--sync-status" not in err
    assert status(root, slug) == "active" and fake.writes() == []


def test_a_broken_strict_block_refuses_inbox_accept_even_with_ticket(tmp_path, fake):
    root = strict_node(tmp_path, strict=True, claim_transition="Start Progress")
    set_tracker_key(root, "inbox-query", "status = Triage")
    set_tracker_key(root, "timeout-seconds", -1)
    code, _out, err = cli(root, "work", "inbox", "accept", "--ticket", KEY)
    assert code == 1 and REFUSED in err and "tcw validate" in err
    assert "--ticket needs" not in err
    assert FsWorkStore.open(root).query() == []


def test_strict_without_an_inbox_query_refuses_an_unknown_ref_in_todays_words(strict, fake):
    code, out, err = cli(strict, "work", "inbox", "accept", "no-such-thing")
    assert (code, out) == (1, "")
    assert REFUSED in err and "no-such-thing was not accepted" in err
    assert "no such inbox entry" not in err
