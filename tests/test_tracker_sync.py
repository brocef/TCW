"""Lifecycle synchronization: a bound item's ticket follows the item.

`start` claims; `submit`, `rework`, `complete` and discarding move the ticket to the
tracker status configured for the item's new status; what did not reach the tracker
is recorded in the binding and retried by `tcw work tracker sync`. The local move is
never undone or blocked.

Every node is built by `make_node`, whose `statuses` argument has no default: which
statuses are mapped is the axis delivery branches on.
"""

from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest
import yaml

from tcw.store.base import classify_binding
from tcw.store.fs import FsWorkStore, init
from tcw.tracker.intake import binding_document, unlink_document, with_sync_record
from tcw.work.projection import WORK_ITEM_SCHEMA
from tracker_fake import BASE_URL, SYNC, FakeJira, install_sites

SENTINEL = "sentinel-token-do-not-print"
A, B = "acct-a", "acct-b"
KEY, TICKET_ID = "SYNC-1", "20001"
STATUSES = {"active": "In Progress", "review": "In Review", "completed": "Done",
            "discarded": "Won't Do"}
RECORD = {"state": "pending", "move": "submit", "since": "In Progress", "claim": "done",
          "reason": "the tracker could not be reached", "at": "2026-09-14T10:00:00Z"}


def document(**overrides) -> str:
    values = dict(provider="jira-cloud", project="alpha", part="default",
                  ticket_id=TICKET_ID, ticket_key=KEY,
                  ticket_url=f"{BASE_URL}/browse/{KEY}", bound="2026-09-14", unlinked=[])
    values.update(overrides)
    return binding_document(**values)


# ── the record in the binding ────────────────────────────────────────────────


def test_a_record_is_carried_on_the_binding():
    bound = classify_binding(yaml.safe_load(with_sync_record(document(), RECORD)))
    assert bound.sync == RECORD and bound.ticket_key == KEY


@pytest.mark.parametrize("sync", [5, {**RECORD, "state": "late"},
                                  {**RECORD, "move": "wander"},
                                  {**RECORD, "claim": "maybe"},
                                  {k: v for k, v in RECORD.items() if k != "reason"},
                                  {**RECORD, "at": None}],
                         ids=["not-mapping", "state", "move", "claim", "missing", "null"])
def test_an_unusable_record_is_a_problem_and_the_binding_stays_bound(sync):
    data = yaml.safe_load(document())
    data["sync"] = sync
    bound = classify_binding(data)
    assert bound.ticket_key == KEY
    assert set(bound.sync) == {"problem"}


def test_setting_and_removing_a_record_keeps_every_other_key_in_place():
    original = document()
    with_record = with_sync_record(original, RECORD)
    assert yaml.safe_load(with_record)["sync"] == RECORD
    assert with_sync_record(with_record, None) == original


def test_unlink_takes_the_record_with_the_binding():
    content = unlink_document(with_sync_record(document(), RECORD),
                              reason="wrong ticket", today="2026-09-14")
    data = yaml.safe_load(content)
    assert "sync" not in data
    assert classify_binding(data).__class__.__name__ == "Unbound"


# ── shared fixtures for the delivery tests ───────────────────────────────────


def make_node(tmp_path: Path, *, statuses: dict | None,
              name: str = "alpha", email_env: str = "TCW_A_EMAIL",
              tracker: bool = True, base_url: str = BASE_URL,
              retain: dict | None = None) -> Path:
    """A git-backed node. `statuses` has no default; `None` leaves the block out."""
    root = tmp_path / name
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "a@example.test"],
                   check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "a"], check=True)
    if retain is not None:        # before init, so the scaffolding sees it
        (root / "tcw-config.yaml").write_text(
            yaml.safe_dump({"id": name, "work": {"retain": retain}}), encoding="utf-8")
    init(["work"], root, project_id=name)
    config = yaml.safe_load((root / "tcw-config.yaml").read_text(encoding="utf-8"))
    if tracker:
        block = {
            "provider": "jira-cloud", "base-url": base_url,
            "candidate-query": "assignee = currentUser()",
            "credentials": {"email-env": email_env, "token-env": "TCW_PROBE_TOKEN"},
            "transitions": {"start": "Start Progress"},
        }
        if statuses is not None:
            block["statuses"] = statuses
        config.setdefault("work", {})["tracker"] = block
    (root / "tcw-config.yaml").write_text(yaml.safe_dump(config, sort_keys=False),
                                          encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "init"], check=True)
    return root


def cli(root: Path, *argv: str) -> tuple[int, str, str]:
    from tcw.cli import main
    previous = os.getcwd()
    out, err = io.StringIO(), io.StringIO()
    os.chdir(root)
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = main(list(argv))
            except SystemExit as exit_:
                code = exit_.code or 0
    finally:
        os.chdir(previous)
    return code, out.getvalue(), err.getvalue()


@pytest.fixture()
def fake(monkeypatch):
    monkeypatch.setenv("TCW_A_EMAIL", "a@example.test")
    monkeypatch.setenv("TCW_B_EMAIL", "b@example.test")
    monkeypatch.setenv("TCW_PROBE_TOKEN", SENTINEL)
    monkeypatch.setenv("TCW_WORK_OWNER", "a@example.test")
    fake = FakeJira(workflow=SYNC)
    fake.account("a@example.test", A, "Alice")
    fake.account("b@example.test", B, "Bob")
    fake.ticket(id=TICKET_ID, key=KEY, summary="A ready ticket")
    return fake.install(monkeypatch)


def bound_item(root: Path, title: str = "Bound item", *, part: str = "default",
               ticket: str = KEY) -> str:
    st = FsWorkStore.open(root)
    slug = st.create(title).slug
    code, _out, err = cli(root, "work", "tracker", "link", slug, ticket, "--part", part)
    assert code == 0, err
    return slug


def record(root: Path, slug: str) -> dict | None:
    return FsWorkStore.open(root).get(slug).tracker["sync"]


def binding_text(root: Path, slug: str) -> str:
    return FsWorkStore.open(root).read_sidecar(slug, "tracker.yaml").content


def status(root: Path, slug: str) -> str:
    return FsWorkStore.open(root).get(slug).status


def test_the_json_document_validates_with_a_record_a_problem_and_none(tmp_path, fake):
    root = make_node(tmp_path, statuses=STATUSES)
    slug = bound_item(root)
    st = FsWorkStore.open(root)
    for sync in (None, RECORD, 5):
        content = yaml.safe_load(binding_text(root, slug))
        content.pop("sync", None)
        if sync is not None:
            content["sync"] = sync
        (st.path(slug) / "tracker.yaml").write_text(yaml.safe_dump(content),
                                                    encoding="utf-8")
        code, out, err = cli(root, "work", "show", slug, "--json")
        assert code == 0, err
        import json
        jsonschema.validate(json.loads(out), WORK_ITEM_SCHEMA)


# ── a binding from another site ──────────────────────────────────────────────


SITE_A, SITE_B = "https://a.invalid", "https://b.invalid"


def set_base_url(root: Path, url: str) -> None:
    path = root / "tcw-config.yaml"
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    config["work"]["tracker"]["base-url"] = url
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")


@pytest.fixture()
def two_sites(monkeypatch):
    monkeypatch.setenv("TCW_A_EMAIL", "a@example.test")
    monkeypatch.setenv("TCW_PROBE_TOKEN", SENTINEL)
    monkeypatch.setenv("TCW_WORK_OWNER", "a@example.test")
    old, new = FakeJira(workflow=SYNC, site=SITE_A), FakeJira(workflow=SYNC, site=SITE_B)
    for fake_ in (old, new):
        fake_.account("a@example.test", A, "Alice")
    old.ticket(id="10052", key="OLD-6", summary="On the old site")
    new.ticket(id="10052", key="NEW-9", summary="On the new site", assignee=A)
    install_sites(monkeypatch, old, new)
    return old, new


def test_same_site_compares_scheme_host_and_browse_path():
    from tcw.tracker.intake import same_site
    assert same_site("https://A.invalid/browse/X-1", "https://a.invalid")
    assert same_site("https://a.invalid/jira/browse/X-1", "https://a.invalid/jira")
    assert not same_site("https://b.invalid/browse/X-1", "https://a.invalid")
    assert not same_site("http://a.invalid/browse/X-1", "https://a.invalid")
    assert not same_site("https://a.invalid/other/X-1", "https://a.invalid")
    assert not same_site("", "https://a.invalid")
    assert not same_site("browse/X-1", "https://a.invalid")


def test_import_refuses_a_same_id_ticket_from_another_site(tmp_path, two_sites):
    old, new = two_sites
    root = make_node(tmp_path, statuses=None, base_url=SITE_A)
    code, out, err = cli(root, "work", "tracker", "import", "OLD-6")
    assert code == 0, err
    old_slug = out.strip()
    set_base_url(root, SITE_B)
    code, out, err = cli(root, "work", "tracker", "import", "NEW-9")
    assert code == 1
    assert old_slug in err and SITE_B in err
    assert "already bound" not in err
    assert new.writes() == []


# ── delivery rules, called directly ──────────────────────────────────────────


def deliver_now(root: Path, slug: str, *, move: str | None, previous: str | None,
                check_only: bool = False):
    from tcw.tracker.jira import JiraClient
    from tcw.tracker.sync import deliver
    st = FsWorkStore.open(root)
    config = st.tracker_config()
    return deliver(st, slug, JiraClient(config), config, move=move,
                   previous_status=previous, check_only=check_only)


def claimed_ticket(fake, status: str = "In Progress", assignee: str | None = A):
    held = fake.tickets[TICKET_ID]
    held.status, held.assignee = status, assignee
    return held


def moved_to(root: Path, slug: str, local: str, resolution: str = "") -> None:
    """Move the item locally through the store, which delivers nothing: to `review`
    by starting and submitting, or to `discarded` with `resolution`."""
    st = FsWorkStore.open(root)
    if local == "review":
        st.start(slug, owner="a@example.test")
        st.submit(slug)
    else:
        st.complete(slug, resolution, dod_ack=[], force=True)
    assert st.get(slug).status == local


@pytest.fixture()
def node(tmp_path, fake):
    return make_node(tmp_path, statuses=STATUSES)


def test_submit_moves_a_claimed_ticket_and_writes_nothing(node, fake):
    slug = bound_item(node)
    claimed_ticket(fake)
    moved_to(node, slug, "review")
    before = binding_text(node, slug)
    outcome = deliver_now(node, slug, move="submit", previous="active")
    assert outcome.state == "current", outcome
    assert fake.tickets[TICKET_ID].status == "In Review"
    assert binding_text(node, slug) == before


def test_a_ticket_already_at_the_target_is_not_written_to(node, fake):
    slug = bound_item(node)
    claimed_ticket(fake, "In Review")
    moved_to(node, slug, "review")
    assert deliver_now(node, slug, move="submit", previous="active").state == "current"
    assert fake.writes() == []


def test_complete_from_review_with_review_unmapped_checks_against_active(tmp_path, fake):
    root = make_node(tmp_path, statuses={"active": "In Progress", "completed": "Done"})
    slug = bound_item(root)
    claimed_ticket(fake, "In Progress")
    st = FsWorkStore.open(root)
    st.start(slug, owner="a@example.test")
    st.submit(slug)
    st.complete(slug, "done", ["acked"])
    assert deliver_now(root, slug, move="complete", previous="review").state == "current"
    assert fake.tickets[TICKET_ID].status == "Done"


def test_a_discard_uses_the_mapping_for_its_resolution(tmp_path, fake):
    root = make_node(tmp_path, statuses={"active": "In Progress",
                                         "discarded": {"duplicate": "Duplicate"}})
    one = bound_item(root, "Duplicate one")
    claimed_ticket(fake)
    FsWorkStore.open(root).start(one, owner="a@example.test")
    moved_to(root, one, "discarded", "duplicate")
    assert deliver_now(root, one, move="discard", previous="active").state == "current"
    assert fake.tickets[TICKET_ID].status == "Duplicate"


def test_a_discard_with_no_mapping_for_its_resolution_sends_nothing(tmp_path, fake):
    root = make_node(tmp_path, statuses={"active": "In Progress",
                                         "discarded": {"duplicate": "Duplicate"}})
    slug = bound_item(root)
    claimed_ticket(fake)
    FsWorkStore.open(root).start(slug, owner="a@example.test")
    moved_to(root, slug, "discarded", "wontfix")
    assert deliver_now(root, slug, move="discard", previous="active").state == "none"
    assert fake.writes() == []


def test_rework_moves_the_ticket_back_to_progress(node, fake):
    slug = bound_item(node)
    claimed_ticket(fake, "In Review")
    moved_to(node, slug, "review")
    FsWorkStore.open(node).rework(slug)
    assert deliver_now(node, slug, move="rework", previous="review").state == "current"
    assert fake.tickets[TICKET_ID].status == "In Progress"


# Every status offers every move, as Jira's default simplified workflow does
# (`jira-claim-experiment.md`): the transition to the target is always there, so
# only the drift check can stop a reopened ticket being dragged forward.
EVERYWHERE = {status: [("21", "Start Progress", "In Progress"),
                       ("41", "Ready for Review", "In Review"),
                       ("31", "Finish", "Done")]
              for status in ("To Do", "In Progress", "In Review", "Done")}


@pytest.mark.parametrize("workflow", ["SYNC", "EVERYWHERE"])
def test_a_ticket_moved_elsewhere_in_the_tracker_is_not_pulled_back(tmp_path, monkeypatch,
                                                                     workflow):
    monkeypatch.setenv("TCW_A_EMAIL", "a@example.test")
    monkeypatch.setenv("TCW_PROBE_TOKEN", SENTINEL)
    fake_ = FakeJira(workflow={"SYNC": SYNC, "EVERYWHERE": EVERYWHERE}[workflow])
    fake_.account("a@example.test", A, "Alice")
    fake_.ticket(id=TICKET_ID, key=KEY, summary="t", status="To Do", assignee=A)
    fake_.install(monkeypatch)
    root = make_node(tmp_path, statuses=STATUSES)
    slug = bound_item(root)
    FsWorkStore.open(root).start(slug, owner="a@example.test")
    FsWorkStore.open(root).submit(slug)
    outcome = deliver_now(root, slug, move="submit", previous="active")
    assert outcome.state == "conflicting" and "moved in the tracker" in outcome.reason
    assert fake_.writes() == []
    assert record(root, slug)["state"] == "conflicting"


def test_a_hand_move_to_the_recorded_target_is_accepted(node, fake):
    slug = bound_item(node)
    claimed_ticket(fake)
    moved_to(node, slug, "review")
    fake.down = True
    assert deliver_now(node, slug, move="submit", previous="active").state == "pending"
    fake.down = False
    fake.tickets[TICKET_ID].status = "In Review"        # moved by hand, where TCW meant
    FsWorkStore.open(node).complete(slug, "done", ["acked"])
    assert deliver_now(node, slug, move="complete", previous="review").state == "current"
    assert fake.tickets[TICKET_ID].status == "Done"
    assert record(node, slug) is None


# `(nobody, discard)` is deliberately absent: an unassigned ticket is the one case a
# discard may move, so that pairing lives in
# `test_an_unassigned_ticket_is_closed_by_a_discard` below.
@pytest.mark.parametrize("assignee, move", [
    *[(B, move) for move in ("submit", "rework", "complete", "discard")],
    *[(None, move) for move in ("submit", "rework", "complete")]],
    ids=lambda v: {B: "someone-else", None: "nobody"}.get(v, v))
def test_a_ticket_not_assigned_to_you_is_never_moved(node, fake, assignee, move):
    slug = bound_item(node)
    st = FsWorkStore.open(node)
    st.start(slug, owner="a@example.test")
    previous = "active"
    if move == "submit":
        st.submit(slug)
        claimed_ticket(fake, "In Progress", assignee)
    elif move == "rework":
        st.submit(slug)
        st.rework(slug)
        previous = "review"
        claimed_ticket(fake, "In Review", assignee)
    elif move == "complete":
        st.complete(slug, "done", ["acked"])
        claimed_ticket(fake, "In Progress", assignee)
    else:
        st.complete(slug, "wontfix", dod_ack=[], force=True)
        claimed_ticket(fake, "In Progress", assignee)
    outcome = deliver_now(node, slug, move=move, previous=previous)
    # Whose it is decides the wording: a ticket somebody holds names them, one nobody
    # holds says so and points at claiming it rather than implying a holder.
    assert outcome.state == "conflicting"
    assert ("not to you" if assignee else "is unassigned") in outcome.reason
    assert fake.writes() == []


def test_an_unassigned_ticket_is_closed_by_a_discard(node, fake):
    """GitHub #41. A queue that hands out unassigned tickets links almost every
    backlog item to one; refusing the discard leaves each ticket open for ever."""
    slug = bound_item(node)
    claimed_ticket(fake, "To Do", None)
    FsWorkStore.open(node).complete(slug, "wontfix", dod_ack=[], force=True)
    outcome = deliver_now(node, slug, move="discard", previous=None)
    assert outcome.state == "current", outcome
    assert fake.tickets[TICKET_ID].status == "Won't Do"
    assert record(node, slug) is None


def test_an_unassigned_ticket_is_not_moved_by_anything_but_a_discard(node, fake):
    slug = bound_item(node)
    st = FsWorkStore.open(node)
    st.start(slug, owner="a@example.test")
    st.submit(slug)
    claimed_ticket(fake, "In Progress", None)
    outcome = deliver_now(node, slug, move="submit", previous="active")
    assert outcome.state == "conflicting"
    assert "unassigned" in outcome.reason and "nobody, not to you" not in outcome.reason
    assert fake.writes() == []


def test_a_discard_still_refuses_a_ticket_someone_else_holds(node, fake):
    slug = bound_item(node)
    claimed_ticket(fake, "To Do", B)
    FsWorkStore.open(node).complete(slug, "wontfix", dod_ack=[], force=True)
    outcome = deliver_now(node, slug, move="discard", previous=None)
    assert outcome.state == "conflicting" and "Bob" in outcome.reason
    assert fake.writes() == []


def test_no_transition_or_two_to_the_target_is_conflicting(tmp_path, monkeypatch):
    monkeypatch.setenv("TCW_A_EMAIL", "a@example.test")
    monkeypatch.setenv("TCW_PROBE_TOKEN", SENTINEL)
    for offered, expect in (
            ([("31", "Finish", "Done")], "offers no transition"),
            ([("41", "Review", "In Review"), ("43", "Peer Review", "In Review")],
             "ids 41, 43")):
        fake_ = FakeJira(workflow={"In Progress": offered, "In Review": [], "Done": []})
        fake_.account("a@example.test", A, "Alice")
        fake_.ticket(id=TICKET_ID, key=KEY, summary="t", status="In Progress", assignee=A)
        fake_.install(monkeypatch)
        (tmp_path / expect.split()[0]).mkdir()
        root = make_node(tmp_path / expect.split()[0], statuses=STATUSES)
        slug = bound_item(root)
        st = FsWorkStore.open(root)
        st.start(slug, owner="a@example.test")
        st.submit(slug)
        outcome = deliver_now(root, slug, move="submit", previous="active")
        assert outcome.state == "conflicting" and expect in outcome.reason, outcome
        assert fake_.writes() == []


@pytest.mark.parametrize("error, state", [
    ("400", "conflicting"), ("503", "pending"), ("no-credentials", "pending")])
def test_errors_are_pending_or_conflicting_by_what_the_tracker_said(node, fake, monkeypatch,
                                                                    error, state):
    from tcw.tracker import jira
    slug = bound_item(node)
    claimed_ticket(fake)
    moved_to(node, slug, "review")
    if error == "no-credentials":
        monkeypatch.delenv("TCW_A_EMAIL")
    else:
        fake.fail("POST", "/transitions", jira._for_status(int(error), {}, "no", "x"))
    outcome = deliver_now(node, slug, move="submit", previous="active")
    assert outcome.state == state, outcome
    assert record(node, slug)["state"] == state


def test_a_ticket_shared_by_two_parts_moves_with_the_last_one(node, fake):
    api = bound_item(node, "Api half", part="api")
    web = bound_item(node, "Web half", part="web")
    claimed_ticket(fake)
    st = FsWorkStore.open(node)
    for slug in (api, web):
        st.start(slug, owner="a@example.test")
    st.complete(api, "done", ["acked"])
    outcome = deliver_now(node, api, move="complete", previous="active")
    assert outcome.state == "held" and web in outcome.reason
    assert fake.writes() == []
    st.complete(web, "done", ["acked"])
    assert deliver_now(node, web, move="complete", previous="active").state == "current"
    assert fake.tickets[TICKET_ID].status == "Done"


def test_a_hand_written_binding_for_someone_elses_ticket_moves_nothing(node, fake):
    st = FsWorkStore.open(node)
    slug = st.create("Hand bound").slug
    (st.path(slug) / "tracker.yaml").write_text(document(), encoding="utf-8")
    claimed_ticket(fake, "In Progress", B)
    st.start(slug, owner="a@example.test")
    st.submit(slug)
    assert deliver_now(node, slug, move="submit", previous="active").state == "conflicting"
    assert fake.writes() == []


def test_a_binding_on_another_site_sends_nothing(node, fake):
    st = FsWorkStore.open(node)
    slug = st.create("Other site").slug
    (st.path(slug) / "tracker.yaml").write_text(
        document(ticket_url="https://elsewhere.invalid/browse/SYNC-1"), encoding="utf-8")
    claimed_ticket(fake)
    st.start(slug, owner="a@example.test")
    st.submit(slug)
    outcome = deliver_now(node, slug, move="submit", previous="active")
    assert outcome.state == "conflicting" and "elsewhere.invalid" in outcome.reason
    assert fake.requests == []


# ── through the lifecycle commands ───────────────────────────────────────────


def commits_touching(root: Path, slug: str) -> int:
    out = subprocess.run(["git", "-C", str(root), "log", "--oneline", "--all", "--",
                          f"docs/work/*/{slug}"], capture_output=True, text=True).stdout
    return len(out.splitlines())


def test_start_claims_a_linked_ticket(node, fake):
    slug = bound_item(node)
    code, _out, err = cli(node, "work", "start", slug)
    assert code == 0, err
    assert status(node, slug) == "active"
    held = fake.tickets[TICKET_ID]
    assert (held.status, held.assignee) == ("In Progress", A)
    assert f"claimed {KEY}" in err
    assert record(node, slug) is None


def test_start_of_a_ticket_someone_else_holds_starts_locally_and_records_it(node, fake):
    slug = bound_item(node)
    claimed_ticket(fake, "In Progress", B)
    code, _out, err = cli(node, "work", "start", slug)
    assert code == 1
    assert status(node, slug) == "active"
    assert fake.writes() == []
    assert "Bob" in err and f"{slug} moved to active and was committed" in err
    sync = record(node, slug)
    assert (sync["state"], sync["move"], sync["claim"]) == ("conflicting", "start", "owed")
    dirty = subprocess.run(["git", "-C", str(node), "status", "--porcelain", "--",
                            f"docs/work/backlog/{slug}"], capture_output=True, text=True)
    assert dirty.stdout == "", "the move out of backlog was not committed"


def test_an_owed_claim_is_retried_before_the_next_move(node, fake):
    slug = bound_item(node)
    claimed_ticket(fake, "In Progress", B)
    cli(node, "work", "start", slug)
    claimed_ticket(fake, "To Do", None)                   # Bob let it go
    code, _out, err = cli(node, "work", "submit", slug)
    assert code == 0, err
    held = fake.tickets[TICKET_ID]
    assert (held.status, held.assignee) == ("In Review", A)
    assert record(node, slug) is None


def test_a_move_the_tracker_misses_is_pending_and_sync_finishes_it(node, fake):
    slug = bound_item(node)
    assert cli(node, "work", "start", slug)[0] == 0
    fake.down = True
    code, _out, err = cli(node, "work", "submit", slug)
    assert code == 1
    assert status(node, slug) == "review"
    assert "moved to review and was committed" in err and "(pending)" in err
    assert record(node, slug)["state"] == "pending"
    fake.down = False
    commits = commits_touching(node, slug)
    code, out, err = cli(node, "work", "tracker", "sync", slug)
    assert code == 0, err
    assert out.strip() == f"{slug}: current"
    assert fake.tickets[TICKET_ID].status == "In Review"
    assert record(node, slug) is None
    assert status(node, slug) == "review" and commits_touching(node, slug) == commits


def test_a_complete_that_misses_the_tracker_keeps_an_unretained_item(tmp_path, fake):
    root = make_node(tmp_path, statuses=STATUSES, retain={"completed": False})
    slug = bound_item(root)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "bind"], check=True)
    assert cli(root, "work", "start", slug)[0] == 0
    fake.down = True
    code, _out, err = cli(root, "work", "complete", slug, "--resolution", "done",
                          "--confirm", "--force")
    assert code == 1
    assert "was kept rather than removed" in err and f"tcw work delete {slug}" in err
    assert FsWorkStore.open(root).get(slug) is not None
    assert record(root, slug) is None
    fake.down = False
    code, _out, err = cli(root, "work", "delete", slug)
    assert code == 0, err


VERBS = [("start",), ("submit",), ("rework",), ("complete", "--resolution", "done",
                                                 "--confirm", "--force")]


def test_with_no_tracker_a_bound_item_moves_as_before_and_loads_no_tracker_code(tmp_path):
    root = make_node(tmp_path, statuses=None, tracker=False)
    st = FsWorkStore.open(root)
    slug = st.create("Bound, nothing configured").slug
    (st.path(slug) / "tracker.yaml").write_text(document(), encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "bind"], check=True)
    repo = Path(__file__).resolve().parents[1]
    for verb in VERBS:
        probe = (f"import sys; sys.path.insert(0, {str(repo)!r})\n"
                 "import io, contextlib\nfrom tcw.cli import main\n"
                 "err = io.StringIO()\n"
                 "with contextlib.redirect_stderr(err), contextlib.redirect_stdout(err):\n"
                 f"    code = main(['work', {verb[0]!r}, {slug!r}, *{list(verb[1:])!r}])\n"
                 "print('EXIT', code)\n"
                 "print('TRACKER', 'tracker' in err.getvalue().lower())\n"
                 "print('LOADED', ','.join(n for n in sys.modules if n.startswith('tcw.tracker')))\n")
        if verb[0] == "rework":
            subprocess.run([sys.executable, "-c", probe.replace("'rework'", "'submit'")],
                           cwd=root, capture_output=True, text=True, check=True)
        result = subprocess.run([sys.executable, "-c", probe], cwd=root,
                                capture_output=True, text=True, timeout=120)
        assert "EXIT 0" in result.stdout, (verb, result.stdout, result.stderr)
        assert "TRACKER False" in result.stdout, (verb, result.stdout)
        assert result.stdout.strip().endswith("LOADED"), (verb, result.stdout)


def test_a_tracker_block_with_problems_records_the_move_as_pending(node, fake):
    slug = bound_item(node)
    path = node / "tcw-config.yaml"
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    config["work"]["tracker"]["statuses"] = {"review": "In Review"}   # no active
    fake.requests.clear()
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    code, _out, err = cli(node, "work", "start", slug)
    assert code == 1 and status(node, slug) == "active"
    sync = record(node, slug)
    assert sync["state"] == "pending" and "tcw validate" in sync["reason"]
    assert fake.requests == []


def test_no_delivery_outcome_prints_or_stores_the_token(node, fake):
    slug = bound_item(node)
    outputs = [cli(node, "work", "start", slug)]
    fake.down = True
    outputs.append(cli(node, "work", "submit", slug))
    fake.down = False
    claimed_ticket(fake, "Done", A)
    outputs.append(cli(node, "work", "tracker", "sync", slug))
    for _code, out, err in outputs:
        assert SENTINEL not in out + err
    for path in FsWorkStore.open(node).root.rglob("*"):
        if path.is_file():
            assert SENTINEL not in path.read_text(encoding="utf-8", errors="replace"), path


# ── tcw work tracker sync ────────────────────────────────────────────────────


def with_record(root: Path, slug: str, sync) -> None:
    st = FsWorkStore.open(root)
    content = yaml.safe_load(binding_text(root, slug))
    content["sync"] = sync
    (st.path(slug) / "tracker.yaml").write_text(yaml.safe_dump(content, sort_keys=False),
                                                encoding="utf-8")


def test_sync_all_visits_recorded_items_and_skips_another_owners(node, fake, monkeypatch):
    second = "20002"
    fake.ticket(id=second, key="SYNC-2", summary="Another", status="In Review",
                assignee=A)
    fake.ticket(id="20003", key="SYNC-3", summary="Theirs", status="In Progress",
                assignee=B)
    mine = bound_item(node, "Mine, done")
    plain = bound_item(node, "No record", ticket="SYNC-2")
    theirs = bound_item(node, "Theirs", ticket="SYNC-3")
    st = FsWorkStore.open(node)
    claimed_ticket(fake, "In Review")
    st.start(mine, owner="a@example.test")
    st.submit(mine)
    st.complete(mine, "done", ["acked"])                  # retained: completed is kept
    with_record(node, mine, {**RECORD, "move": "complete", "since": "In Review"})
    st.start(plain, owner="a@example.test")
    st.start(theirs, owner="b@example.test")
    with_record(node, theirs, {**RECORD, "since": "In Progress"})
    fake.requests.clear()
    code, out, err = cli(node, "work", "tracker", "sync", "--all")
    lines = sorted(out.strip().splitlines())
    assert lines == sorted([f"{mine}: current", f"{theirs}: skipped — held by "
                                                f"b@example.test"]), (out, err)
    assert code == 0
    assert fake.tickets[TICKET_ID].status == "Done"
    assert not [p for _m, p, _a in fake.requests if "20002" in p or "20003" in p]


def test_sync_all_exits_one_while_a_move_stays_pending(node, fake):
    slug = bound_item(node)
    assert cli(node, "work", "start", slug)[0] == 0
    fake.down = True
    cli(node, "work", "submit", slug)
    code, out, _err = cli(node, "work", "tracker", "sync", "--all")
    assert code == 1 and out.startswith(f"{slug}: pending — ")


def test_sync_of_an_item_with_no_record_checks_and_never_moves(node, fake):
    slug = bound_item(node)
    claimed_ticket(fake, "In Progress")
    st = FsWorkStore.open(node)
    st.start(slug, owner="a@example.test")
    st.submit(slug)                                       # e.g. from `tcw serve`
    before = binding_text(node, slug)
    fake.requests.clear()
    code, out, _err = cli(node, "work", "tracker", "sync", slug)
    assert code == 1 and "conflicting" in out
    assert fake.writes() == [] and binding_text(node, slug) == before


def test_sync_of_a_named_slug_someone_else_started_exits_one(node, fake):
    """A named slug is a user asking about one item: skipping it is not success.

    Under strict mode `binding_refusal` sends the user here while a record exists,
    so a silent exit 0 leaves the item stuck with nothing reporting a failure.
    """
    slug = bound_item(node)
    st = FsWorkStore.open(node)
    st.start(slug, owner="b@example.test")
    with_record(node, slug, {**RECORD, "move": "start", "since": "", "claim": "owed"})
    code, out, err = cli(node, "work", "tracker", "sync", slug)
    assert code == 1, (out, err)
    assert "skipped" in out and "b@example.test" in out
    assert "pending" in out and "TCW_WORK_OWNER" in out
    assert record(node, slug) is not None


def test_sync_of_a_named_slug_someone_else_started_with_nothing_owed_exits_zero(node,
                                                                             fake):
    """The skip is only a failure when it leaves something undone."""
    slug = bound_item(node)
    FsWorkStore.open(node).start(slug, owner="b@example.test")
    code, out, err = cli(node, "work", "tracker", "sync", slug)
    assert code == 0, (out, err)
    assert "skipped" in out and "b@example.test" in out


def test_the_strict_refusal_names_the_owner_to_sync_as(node, fake):
    from tcw.tracker.sync import binding_refusal
    slug = bound_item(node)
    st = FsWorkStore.open(node)
    st.start(slug, owner="b@example.test")
    with_record(node, slug, {**RECORD, "move": "start", "since": "", "claim": "owed"})
    st = FsWorkStore.open(node)
    bound, refusal = binding_refusal(st, slug, st.tracker_config())
    assert bound is None and refusal is not None
    assert "TCW_WORK_OWNER" in refusal and "b@example.test" in refusal


def test_sync_needs_exactly_one_of_a_slug_or_all(node, fake):
    assert cli(node, "work", "tracker", "sync")[0] == 1
    assert cli(node, "work", "tracker", "sync", "x", "--all")[0] == 1


def test_an_unreadable_record_leaves_the_binding_usable(node, fake):
    slug = bound_item(node)
    with_record(node, slug, 5)
    other = FsWorkStore.open(node).create("Another").slug
    fake.ticket(id="20002", key="SYNC-2", summary="Another")
    assert cli(node, "work", "tracker", "link", other, "SYNC-2")[0] == 0
    code, _out, err = cli(node, "work", "start", slug)
    assert code == 0, err
    assert record(node, slug) is None                    # overwritten by the delivery
    assert cli(node, "work", "tracker", "unlink", slug, "--reason", "done")[0] == 0


# ── what show, list and the JSON document say ───────────────────────────────


def board_row(root: Path, slug: str) -> str:
    code, out, err = cli(root, "work", "list", "--all")
    assert code == 0, err
    [line] = [x for x in out.splitlines() if x.startswith(slug + " |")]
    return line


def show_lines(root: Path, slug: str) -> list[str]:
    code, out, err = cli(root, "work", "show", slug)
    assert code == 0, err
    return [x for x in out.splitlines() if x.startswith("tracker")]


def test_show_and_list_state_a_record(node, fake):
    slug = bound_item(node)
    assert show_lines(node, slug) == [f"tracker: {KEY} (jira-cloud, part default) "
                                      f"{BASE_URL}/browse/{KEY}"]
    assert board_row(node, slug).endswith(f"| ticket: {KEY}")
    with_record(node, slug, RECORD)
    assert show_lines(node, slug)[1] == (
        "tracker sync: pending after submit (2026-09-14T10:00:00Z): the tracker could "
        "not be reached")
    assert board_row(node, slug).endswith(f"| ticket: {KEY} (pending)")
    with_record(node, slug, {**RECORD, "state": "conflicting", "claim": "owed"})
    assert show_lines(node, slug)[1].endswith("; the claim is still owed")


def test_a_part_and_a_state_share_the_brackets(node, fake):
    slug = bound_item(node, part="api")
    with_record(node, slug, {**RECORD, "state": "conflicting"})
    assert board_row(node, slug).endswith(f"| ticket: {KEY} (part api, conflicting)")


def test_an_unreadable_record_is_named_where_the_item_is_read(node, fake):
    slug = bound_item(node)
    with_record(node, slug, 5)
    assert show_lines(node, slug)[1] == ("tracker sync: record cannot be read "
                                         "('sync' is not a mapping)")
    assert board_row(node, slug).endswith(f"| ticket: {KEY} (unreadable sync record)")


# ── review findings ──────────────────────────────────────────────────────────


def test_an_owed_claim_does_not_skip_the_hold_on_a_shared_ticket(node, fake):
    api = bound_item(node, "Api half", part="api")
    web = bound_item(node, "Web half", part="web")
    claimed_ticket(fake, "In Progress", B)
    for slug in (api, web):
        assert cli(node, "work", "start", slug)[0] == 1        # Bob holds it
    claimed_ticket(fake, "To Do", None)                        # Bob lets go
    code, _out, err = cli(node, "work", "complete", api, "--resolution", "done",
                          "--confirm", "--force")
    assert code == 0, err
    assert fake.tickets[TICKET_ID].status != "Done"
    assert web in err


def test_a_move_recorded_before_the_configuration_was_fixed_is_delivered(node, fake):
    slug = bound_item(node)
    assert cli(node, "work", "start", slug)[0] == 0
    path = node / "tcw-config.yaml"
    good = path.read_text(encoding="utf-8")
    broken = yaml.safe_load(good)
    broken["work"]["tracker"]["statuses"] = {"review": "In Review"}
    path.write_text(yaml.safe_dump(broken), encoding="utf-8")
    assert cli(node, "work", "submit", slug)[0] == 1
    assert record(node, slug)["since"] == ""
    path.write_text(good, encoding="utf-8")
    code, out, err = cli(node, "work", "tracker", "sync", slug)
    assert code == 0, (out, err)
    assert fake.tickets[TICKET_ID].status == "In Review"


def test_a_discard_of_an_imported_item_recorded_while_down_is_delivered(node, fake):
    code, out, err = cli(node, "work", "tracker", "import", KEY)
    assert code == 0, err
    slug = out.strip()
    fake.down = True
    assert cli(node, "work", "complete", slug, "--resolution", "wontfix",
               "--confirm")[0] == 1
    fake.down = False
    code, out, err = cli(node, "work", "tracker", "sync", slug)
    assert code == 0, (out, err)
    assert fake.tickets[TICKET_ID].status == "Won't Do"


def test_an_owed_claim_on_a_ticket_already_at_the_target_is_current(node, fake):
    slug = bound_item(node)
    claimed_ticket(fake, "In Progress", B)
    assert cli(node, "work", "start", slug)[0] == 1
    claimed_ticket(fake, "Done", B)                            # Bob finished it
    FsWorkStore.open(node).complete(slug, "done", ["acked"])
    code, out, err = cli(node, "work", "tracker", "sync", slug)
    assert code == 0 and out.strip() == f"{slug}: current", (out, err)
    assert fake.writes() == [] and record(node, slug) is None


def test_abandoning_an_item_whose_claim_is_owed_does_not_claim_the_ticket(tmp_path, fake):
    root = make_node(tmp_path, statuses={"active": "In Progress",
                                         "discarded": {"duplicate": "Duplicate"}})
    slug = bound_item(root)
    claimed_ticket(fake, "In Progress", B)
    assert cli(root, "work", "start", slug)[0] == 1
    claimed_ticket(fake, "To Do", None)
    fake.requests.clear()
    code, _out, err = cli(root, "work", "complete", slug, "--resolution", "wontfix",
                          "--confirm")
    assert code == 0, err
    assert fake.writes() == []
    assert record(root, slug) is None


def test_clearing_a_record_does_not_block_removing_an_unretained_item(tmp_path, fake):
    root = make_node(tmp_path, statuses=STATUSES, retain={"completed": False})
    slug = bound_item(root)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "bind"], check=True)
    assert cli(root, "work", "start", slug)[0] == 0
    fake.down = True
    assert cli(root, "work", "submit", slug)[0] == 1
    fake.down = False
    code, _out, err = cli(root, "work", "complete", slug, "--resolution", "done",
                          "--confirm")
    assert code == 0, err
    assert FsWorkStore.open(root).get(slug) is None


def test_a_record_naming_auto_delete_is_unusable_not_a_crash(node, fake):
    slug = bound_item(node)
    with_record(node, slug, {**RECORD, "move": "auto-delete"})
    assert set(record(node, slug)) == {"problem"}
    code, out, _err = cli(node, "work", "tracker", "sync", slug)
    assert code in (0, 1) and out.startswith(f"{slug}: ")


def test_sync_reports_a_held_item_without_failing(node, fake):
    api = bound_item(node, "Api half", part="api")
    web = bound_item(node, "Web half", part="web")
    claimed_ticket(fake)
    st = FsWorkStore.open(node)
    for slug in (api, web):
        st.start(slug, owner="a@example.test")
    st.submit(api)
    with_record(node, api, RECORD)
    code, out, err = cli(node, "work", "tracker", "sync", api)
    assert code == 0 and out.startswith(f"{api}: held — "), (out, err)


def test_a_move_whose_commit_was_refused_is_still_delivered(node, fake):
    slug = bound_item(node)
    subprocess.run(["git", "-C", str(node), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(node), "commit", "-qm", "bind"], check=True)
    assert cli(node, "work", "start", slug)[0] == 0
    hook = node / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 1\n")
    hook.chmod(0o755)
    code, _out, err = cli(node, "work", "submit", slug)
    assert code == 1
    assert status(node, slug) == "review"
    assert fake.tickets[TICKET_ID].status == "In Review", err


def test_complete_of_a_worktree_item_names_a_staged_record(node, fake):
    slug = bound_item(node)
    subprocess.run(["git", "-C", str(node), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(node), "commit", "-qm", "bind"], check=True)
    code, _out, err = cli(node, "work", "start", slug, "--worktree")
    assert code == 0, err
    tree = node / ".worktrees" / slug
    (tree / "code.txt").write_text("the change\n")
    subprocess.run(["git", "-C", str(tree), "add", "code.txt"], check=True)
    subprocess.run(["git", "-C", str(tree), "commit", "-qm", "code"], check=True)
    fake.down = True
    assert cli(node, "work", "submit", slug)[0] == 1
    fake.down = False
    code, _out, err = cli(node, "work", "complete", slug, "--resolution", "done",
                          "--confirm")
    assert code == 1
    assert "tracker.yaml" in err and "tcw work tracker sync" in err


# ── review round two ─────────────────────────────────────────────────────────


def test_an_empty_since_on_complete_accepts_only_the_nearest_mapped_status(node, fake):
    from tcw.tracker.sync import expected_statuses
    record_ = {**RECORD, "move": "complete", "since": ""}
    assert expected_statuses(STATUSES, None, record_, "done") == ("In Review", "Done")
    no_review = {k: v for k, v in STATUSES.items() if k != "review"}
    assert expected_statuses(no_review, None, record_, "done") == ("In Progress", "Done")


def test_open_work_with_no_mapping_keeps_its_owed_claim(tmp_path, fake):
    root = make_node(tmp_path, statuses={"active": "In Progress", "completed": "Done"})
    slug = bound_item(root)
    claimed_ticket(fake, "In Progress", B)
    assert cli(root, "work", "start", slug)[0] == 1
    assert cli(root, "work", "submit", slug)[0] == 1       # review unmapped; Bob still has it
    assert record(root, slug)["claim"] == "owed"
    claimed_ticket(fake, "To Do", None)
    code, out, err = cli(root, "work", "tracker", "sync", slug)
    assert code == 0, (out, err)
    assert fake.tickets[TICKET_ID].assignee == A and record(root, slug) is None


def test_an_owed_claim_on_a_ticket_already_yours_at_the_target_sends_nothing(tmp_path,
                                                                             monkeypatch):
    monkeypatch.setenv("TCW_A_EMAIL", "a@example.test")
    monkeypatch.setenv("TCW_PROBE_TOKEN", SENTINEL)
    monkeypatch.setenv("TCW_WORK_OWNER", "a@example.test")
    fake_ = FakeJira(workflow={s: [("21", "Start Progress", "In Progress"),
                                   ("41", "Ready for Review", "In Review")]
                               for s in ("To Do", "In Progress", "In Review")})
    fake_.account("a@example.test", A, "Alice")
    fake_.ticket(id=TICKET_ID, key=KEY, summary="t", status="In Review", assignee=A)
    fake_.install(monkeypatch)
    root = make_node(tmp_path, statuses=STATUSES)
    slug = bound_item(root)
    st = FsWorkStore.open(root)
    st.start(slug, owner="a@example.test")
    st.submit(slug)
    with_record(root, slug, {**RECORD, "move": "start", "since": "", "claim": "owed"})
    fake_.requests.clear()
    code, out, err = cli(root, "work", "tracker", "sync", slug)
    assert code == 0, (out, err)
    assert fake_.writes() == [] and record(root, slug) is None


# ── verification gaps ────────────────────────────────────────────────────────


def test_the_whole_lifecycle_through_the_commands(node, fake):
    slug = bound_item(node)
    for argv, where in ((("start",), "In Progress"), (("submit",), "In Review"),
                        (("complete", "--resolution", "done", "--confirm"), "Done")):
        code, _out, err = cli(node, "work", argv[0], slug, *argv[1:])
        assert code == 0, (argv, err)
        assert fake.tickets[TICKET_ID].status == where
    assert record(node, slug) is None


@pytest.mark.parametrize("argv", [("start",), ("tracker", "sync")])
def test_start_and_sync_send_nothing_through_a_binding_on_another_site(node, fake, argv):
    st = FsWorkStore.open(node)
    slug = st.create("Other site").slug
    (st.path(slug) / "tracker.yaml").write_text(
        document(ticket_url="https://elsewhere.invalid/browse/SYNC-1"), encoding="utf-8")
    if argv == ("tracker", "sync"):
        st.start(slug, owner="a@example.test")
        with_record(node, slug, {**RECORD, "move": "start", "since": ""})
    code, _out, _err = cli(node, "work", *argv[:-1], argv[-1], slug) if len(argv) > 1 \
        else cli(node, "work", argv[0], slug)
    assert code == 1
    assert fake.requests == []
    assert record(node, slug)["state"] == "conflicting"


# ── naming the transition a move uses ────────────────────────────────────────


def ambiguous_node(tmp_path, monkeypatch, **transitions):
    """A workflow whose `In Progress` offers two transitions into `Done` — one for
    finished work and one for abandoned work, which is GitHub #40's shape."""
    from tracker_fake import AMBIGUOUS, FakeJira
    monkeypatch.setenv("TCW_A_EMAIL", "a@example.test")
    monkeypatch.setenv("TCW_PROBE_TOKEN", SENTINEL)
    monkeypatch.setenv("TCW_WORK_OWNER", "a@example.test")
    fake_ = FakeJira(workflow=AMBIGUOUS)
    fake_.account("a@example.test", A, "Alice")
    fake_.ticket(id=TICKET_ID, key=KEY, summary="t", status="In Progress", assignee=A)
    fake_.install(monkeypatch)
    root = make_node(tmp_path, statuses={**STATUSES, "discarded": "Done"})
    for move, value in transitions.items():
        set_transition(root, move, value)
    return root, fake_


def applied_ids(fake_):
    return fake_.applied


def set_transition(root, move: str, value) -> None:
    path = root / "tcw-config.yaml"
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    config["work"]["tracker"]["transitions"][move] = value
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")


def test_a_named_transition_resolves_a_workflow_with_two_routes_to_one_status(
        tmp_path, monkeypatch):
    root, fake_ = ambiguous_node(tmp_path, monkeypatch, complete="Finish")
    slug = bound_item(root)
    st = FsWorkStore.open(root)
    st.start(slug, owner="a@example.test")
    st.complete(slug, "done", ["acked"])
    outcome = deliver_now(root, slug, move="complete", previous="active")
    assert outcome.state == "current", outcome
    assert fake_.tickets[TICKET_ID].status == "Done"
    assert applied_ids(fake_) == ["31"], applied_ids(fake_)
    assert record(root, slug) is None


def test_a_discard_transition_may_be_named_per_resolution(tmp_path, monkeypatch):
    root, fake_ = ambiguous_node(tmp_path, monkeypatch,
                                 discard={"wontfix": "Abandon"})
    slug = bound_item(root)
    st = FsWorkStore.open(root)
    st.start(slug, owner="a@example.test")
    st.complete(slug, "wontfix", dod_ack=[], force=True)
    outcome = deliver_now(root, slug, move="discard", previous="active")
    assert outcome.state == "current", outcome
    assert fake_.tickets[TICKET_ID].status == "Done"
    assert applied_ids(fake_) == ["32"], applied_ids(fake_)


def test_without_a_name_two_routes_to_one_status_are_still_refused(tmp_path,
                                                                  monkeypatch):
    """The request's explicit constraint: the derived rule keeps working for every
    project relying on it, and only a configured name changes the answer."""
    root, fake_ = ambiguous_node(tmp_path, monkeypatch)
    slug = bound_item(root)
    st = FsWorkStore.open(root)
    st.start(slug, owner="a@example.test")
    st.complete(slug, "done", ["acked"])
    outcome = deliver_now(root, slug, move="complete", previous="active")
    assert outcome.state == "conflicting" and "more than one transition" in outcome.reason
    assert fake_.writes() == []


def test_a_named_transition_the_ticket_does_not_offer_is_refused_not_ignored(
        tmp_path, monkeypatch):
    """Falling back to the derived rule would make a typo'd name invisible for ever."""
    root, fake_ = ambiguous_node(tmp_path, monkeypatch, complete="Finnish")
    slug = bound_item(root)
    st = FsWorkStore.open(root)
    st.start(slug, owner="a@example.test")
    st.complete(slug, "done", ["acked"])
    outcome = deliver_now(root, slug, move="complete", previous="active")
    assert outcome.state == "conflicting" and "Finnish" in outcome.reason
    assert fake_.writes() == []


def test_a_named_transition_leading_elsewhere_is_refused_before_it_is_applied(
        tmp_path, monkeypatch):
    """A transition landing somewhere other than the mapped status yields a ticket
    that never reads as delivered, so every later move would report drift."""
    root, fake_ = ambiguous_node(tmp_path, monkeypatch, submit="Finish")
    slug = bound_item(root)
    st = FsWorkStore.open(root)
    st.start(slug, owner="a@example.test")
    st.submit(slug)
    outcome = deliver_now(root, slug, move="submit", previous="active")
    assert outcome.state == "conflicting"
    assert "'Finish'" in outcome.reason and "'Done'" in outcome.reason
    assert fake_.writes() == []


def test_a_name_matching_two_transitions_is_refused(tmp_path, monkeypatch):
    root, fake_ = ambiguous_node(tmp_path, monkeypatch, complete="Same Name")
    slug = bound_item(root)
    st = FsWorkStore.open(root)
    st.start(slug, owner="a@example.test")
    st.complete(slug, "done", ["acked"])
    outcome = deliver_now(root, slug, move="complete", previous="active")
    assert outcome.state == "conflicting"
    # Naming the configured transition is what proves the named path refused this,
    # rather than the derived rule refusing two routes to Done as it would anyway.
    assert "'Same Name' matches more than one" in outcome.reason
    assert fake_.writes() == []


# ── drift is judged against the path, not two points ─────────────────────────


def test_a_hand_move_to_a_status_between_the_record_and_its_target_is_accepted(node, fake):
    """Two failed moves leave a record aiming at Done from In Progress. A person who
    moves the ticket to In Review has done part of what TCW failed to do, not moved
    it away, so TCW finishes the journey rather than calling it drift."""
    slug = bound_item(node)
    st = FsWorkStore.open(node)
    st.start(slug, owner="a@example.test")
    claimed_ticket(fake, "In Progress", A)
    st.submit(slug)
    fake.down = True
    assert deliver_now(node, slug, move="submit", previous="active").state == "pending"
    st = FsWorkStore.open(node)
    st.complete(slug, "done", ["acked"])
    assert deliver_now(node, slug, move="complete", previous="review").state == "pending"
    fake.down = False
    assert record(node, slug)["since"] == "In Progress"
    claimed_ticket(fake, "In Review", A)                  # moved by hand, part way
    outcome = deliver_now(node, slug, move=None, previous=None)
    assert outcome.state == "current", outcome
    assert fake.tickets[TICKET_ID].status == "Done"
    assert record(node, slug) is None


def test_the_path_is_walked_rather_than_the_status_mapping_inverted(tmp_path, fake):
    """`completed` and `discarded` mapped to one name — GitHub #40's own config —
    means a status cannot be inverted to a single rung, so the window has to come
    from walking the path toward the target."""
    root = make_node(tmp_path, statuses={**STATUSES, "discarded": "Done"})
    slug = bound_item(root)
    st = FsWorkStore.open(root)
    st.start(slug, owner="a@example.test")
    claimed_ticket(fake, "In Progress", A)
    st.submit(slug)
    fake.down = True
    assert deliver_now(root, slug, move="submit", previous="active").state == "pending"
    st = FsWorkStore.open(root)
    st.complete(slug, "done", ["acked"])
    assert deliver_now(root, slug, move="complete", previous="review").state == "pending"
    fake.down = False
    claimed_ticket(fake, "In Review", A)
    outcome = deliver_now(root, slug, move=None, previous=None)
    assert outcome.state == "current", outcome
    assert fake.tickets[TICKET_ID].status == "Done"


# ── a ticket linked to work already under way ────────────────────────────────


def test_a_plain_link_of_started_work_leaves_the_ticket_and_warns(node, fake):
    """Changing the ticket is opt-in. A plain link records the binding, notes that the
    status was not synced, leaves nothing for `sync` to act on, and says how to opt in."""
    st = FsWorkStore.open(node)
    slug = st.create("Already under way").slug
    st.start(slug, owner="a@example.test")
    code, _out, err = cli(node, "work", "tracker", "link", slug, KEY)
    assert code == 0, err
    assert record(node, slug) is None and fake.writes() == []
    assert yaml.safe_load(binding_text(node, slug))["status-synced"] is False
    assert "warning:" in err and "'To Do'" in err and "'In Progress'" in err
    assert "--sync-status" in err


def test_link_of_a_backlog_item_records_nothing(node, fake):
    slug = bound_item(node)                                # links while in backlog
    assert record(node, slug) is None
    assert "status-synced" not in yaml.safe_load(binding_text(node, slug))


def test_a_move_after_a_plain_link_says_why_and_moves_nothing(node, fake):
    """GitHub #42's shape without the opt-in: the next move must not blame a hand move
    nobody made, and must not leave a record `sync` would act on."""
    st = FsWorkStore.open(node)
    slug = st.create("Already under way").slug
    st.start(slug, owner="a@example.test")
    assert cli(node, "work", "tracker", "link", slug, KEY)[0] == 0
    code, _out, err = cli(node, "work", "submit", slug)
    assert code == 0, err
    assert "linked without syncing its status" in err and "--sync-status" in err
    assert "by hand" not in err
    assert fake.writes() == [] and record(node, slug) is None
    code, out, _err = cli(node, "work", "tracker", "sync", slug)
    assert code == 0 and out.startswith(f"{slug}: held — "), out


def test_a_move_that_arrives_after_a_plain_link_clears_the_note(node, fake):
    st = FsWorkStore.open(node)
    slug = st.create("Already under way").slug
    st.start(slug, owner="a@example.test")
    claimed_ticket(fake, "In Progress", A)             # already matches, and is ours
    code, _out, err = cli(node, "work", "tracker", "link", slug, KEY)
    assert code == 0 and "warning:" not in err
    assert cli(node, "work", "submit", slug)[0] == 0
    assert fake.tickets[TICKET_ID].status == "In Review"
    assert "status-synced" not in yaml.safe_load(binding_text(node, slug))


def ladder_node(tmp_path, monkeypatch, workflow, *, status="To Do", assignee=None):
    from tracker_fake import FakeJira
    monkeypatch.setenv("TCW_A_EMAIL", "a@example.test")
    monkeypatch.setenv("TCW_PROBE_TOKEN", SENTINEL)
    monkeypatch.setenv("TCW_WORK_OWNER", "a@example.test")
    fake_ = FakeJira(workflow=workflow)
    fake_.account("a@example.test", A, "Alice")
    fake_.ticket(id=TICKET_ID, key=KEY, summary="t", status=status, assignee=assignee)
    fake_.install(monkeypatch)
    return make_node(tmp_path, statuses=STATUSES), fake_


def under_way(root, status="active") -> str:
    """An item already past `backlog`, not yet bound — GitHub #42's shape."""
    st = FsWorkStore.open(root)
    slug = st.create("Already under way").slug
    st.start(slug, owner="a@example.test")
    if status == "review":
        st.submit(slug)
    elif status == "completed":
        st.complete(slug, "done", ["acked"])
    elif status == "discarded":
        st.complete(slug, "wontfix", dod_ack=[], force=True)
    return slug


def sync_link(root, slug):
    return cli(root, "work", "tracker", "link", slug, KEY, "--sync-status")


def transitions_fail(fake_, *which: int):
    """Make the numbered POSTs to a transitions endpoint fail as unreachable (1-based);
    returns the function that puts the fake back."""
    from tcw.tracker.jira import TrackerUnavailable
    answer, posts = fake_.answer, []

    def failing(client, method, path, body):
        if method == "POST" and path.endswith("/transitions"):
            posts.append(path)
            if len(posts) in which:
                raise TrackerUnavailable("the tracker could not be reached (fake)")
        return answer(client, method, path, body)

    fake_.answer = failing
    return lambda: setattr(fake_, "answer", answer)


def test_sync_status_walks_a_ticket_up_where_there_is_no_shortcut(tmp_path, monkeypatch):
    """No shortcut to Done in this workflow, so catching up takes three transitions:
    the claim onto In Progress, then In Review, then Done."""
    from tracker_fake import STRICT_LADDER
    root, fake_ = ladder_node(tmp_path, monkeypatch, STRICT_LADDER)
    slug = under_way(root, "completed")
    code, _out, err = sync_link(root, slug)
    assert code == 0, err
    assert fake_.tickets[TICKET_ID].status == "Done"
    assert fake_.applied == ["21", "41", "31"], fake_.applied
    assert record(root, slug) is None
    # Permission to walk ends once the ticket is in step.
    assert "catch-up" not in yaml.safe_load(binding_text(root, slug))


def test_sync_status_takes_a_shortcut_when_the_workflow_offers_one(tmp_path, monkeypatch):
    """Where In Progress offers Finish straight to Done, the ticket is not marched
    through review it never had."""
    root, fake_ = ladder_node(tmp_path, monkeypatch, SYNC)
    slug = under_way(root, "completed")
    assert sync_link(root, slug)[0] == 0
    assert fake_.tickets[TICKET_ID].status == "Done"
    assert fake_.applied == ["21", "31"], fake_.applied


def test_a_walk_that_cannot_finish_leaves_the_ticket_where_it_reached(tmp_path,
                                                                     monkeypatch):
    from tracker_fake import BROKEN_LADDER
    root, fake_ = ladder_node(tmp_path, monkeypatch, BROKEN_LADDER)
    slug = under_way(root, "completed")
    code, _out, err = sync_link(root, slug)
    assert code == 1 and "conflicting" in err, err
    assert fake_.tickets[TICKET_ID].status == "In Review"       # as far as it got
    written = record(root, slug)
    assert written["since"] == "In Review"                      # actually observed
    assert written["claim"] == "done"                           # the claim did land


def test_sync_finishes_a_sync_status_link_the_tracker_did_not_answer(tmp_path,
                                                                     monkeypatch):
    """What `--sync-status` could not deliver stays recorded, so the command a user runs
    next finishes it."""
    from tracker_fake import STRICT_LADDER
    root, fake_ = ladder_node(tmp_path, monkeypatch, STRICT_LADDER)
    slug = under_way(root, "review")
    restore = transitions_fail(fake_, 1)
    assert sync_link(root, slug)[0] == 1
    assert record(root, slug)["claim"] == "owed"
    assert fake_.tickets[TICKET_ID].status == "To Do"
    restore()
    code, out, err = cli(root, "work", "tracker", "sync", slug)
    assert code == 0, (out, err)
    assert fake_.tickets[TICKET_ID].status == "In Review"
    assert record(root, slug) is None


def test_the_walk_aims_at_the_items_status_not_the_recorded_move(tmp_path, monkeypatch):
    """The item moved on while nothing was sent (from `tcw serve`, say), so the record
    still names `start`. One sync must take the ticket to where the item is now."""
    from tracker_fake import STRICT_LADDER
    root, fake_ = ladder_node(tmp_path, monkeypatch, STRICT_LADDER)
    slug = under_way(root, "active")
    restore = transitions_fail(fake_, 1)
    assert sync_link(root, slug)[0] == 1
    assert record(root, slug)["move"] == "start"
    restore()
    FsWorkStore.open(root).submit(slug)                  # delivers nothing
    code, out, err = cli(root, "work", "tracker", "sync", slug)
    assert code == 0, (out, err)
    assert fake_.tickets[TICKET_ID].status == "In Review"


def test_a_ticket_behind_its_item_with_no_record_is_still_drift(tmp_path, monkeypatch):
    """No record at all — the ordinary bound item whose ticket somebody moved. There
    is nothing owed, so nothing is caught up. The `claim: done` case, which is what
    the gate actually turns on, is
    `test_a_claimed_ticket_moved_back_is_not_walked_forward_again`."""
    from tracker_fake import STRICT_LADDER
    root, fake_ = ladder_node(tmp_path, monkeypatch, STRICT_LADDER,
                              status="In Progress", assignee=A)
    slug = bound_item(root)                                   # linked while in backlog
    st = FsWorkStore.open(root)
    st.start(slug, owner="a@example.test")
    st.submit(slug)
    fake_.tickets[TICKET_ID].status = "To Do"                 # pushed back by hand
    fake_.applied.clear()
    outcome = deliver_now(root, slug, move="submit", previous="active")
    assert outcome.state == "conflicting", outcome
    assert fake_.applied == [] and fake_.tickets[TICKET_ID].status == "To Do"


def test_a_claimed_ticket_moved_back_is_not_walked_forward_again(tmp_path, monkeypatch):
    """The catch-up is gated on the claim being *owed*, and this is the case that
    proves it: a record saying TCW already claimed the ticket, and a ticket somebody
    then pushed back below where it was left. Walking it forward here would undo a
    person's deliberate move. Mutating the gate to accept `claim: done` must turn
    this red — without a record in play, nothing distinguishes the two."""
    from tracker_fake import STRICT_LADDER
    root, fake_ = ladder_node(tmp_path, monkeypatch, STRICT_LADDER,
                              status="In Review", assignee=A)
    slug = bound_item(root)
    st = FsWorkStore.open(root)
    st.start(slug, owner="a@example.test")
    st.submit(slug)
    with_record(root, slug, {"state": "pending", "move": "submit",
                             "since": "In Progress", "claim": "done",
                             "reason": "the tracker could not be reached",
                             "at": "2026-09-15T10:00:00Z"})
    fake_.tickets[TICKET_ID].status = "To Do"          # pushed back, by hand
    fake_.applied.clear()
    outcome = deliver_now(root, slug, move=None, previous=None)
    assert outcome.state == "conflicting", outcome
    assert fake_.applied == [], fake_.applied
    assert fake_.tickets[TICKET_ID].status == "To Do"


def _ticket_offering(*offered, status: str = "In Progress"):
    """One `TicketRead`, ours, for a direct call on `assess_move`."""
    from tcw.tracker.intake import TicketRead
    from tcw.tracker.jira import Transition
    return TicketRead(
        issue_id=TICKET_ID, key=KEY, url="", summary="t", status=status, category="new",
        assignee_id=A, assignee_name="Alice", me_id=A, me_name="Alice",
        offered=tuple(Transition(id=str(i), name=name, to_status=to)
                      for i, (name, to) in enumerate(offered, start=1)))


@pytest.mark.parametrize("move, removable", [("start", False), ("complete", True)],
                         ids=["start-is-required", "complete-is-optional"])
def test_only_a_removable_transition_key_is_offered_for_removal(move, removable):
    """The refusal tells you to fix the key it named, and offers to let TCW work the
    transition out instead — which means deleting the key. Four of the five may be
    deleted. `transitions.start` may not: the parser requires it, because a start has
    no status-derived rule to fall back to, so advising its removal would advise
    something `tcw validate` then refuses."""
    from tcw.tracker.sync import CONFLICTING, assess_move
    verdict, reason = assess_move(
        _ticket_offering(("Ready for Review", "In Review")),
        target="Done", expected=("In Progress",), move=move,
        named_transition="Not Offered Here")
    assert verdict == CONFLICTING, reason
    assert f"Fix work.tracker.transitions.{move}" in reason, reason
    assert ("remove it to let TCW find the transition itself" in reason) is removable, reason


def _also_name(root: Path, **moves: str) -> None:
    """Name transitions for more moves than `make_node` sets up."""
    path = root / "tcw-config.yaml"
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    config["work"]["tracker"]["transitions"].update(moves)
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")


@pytest.mark.parametrize("recorded, since, named, extra", [
    ("start", "To Do", {}, "a start whose confirming read failed"),
    ("complete", "In Progress", {"complete": "Finish"}, "a completion the tracker missed"),
], ids=["stale-start", "stale-complete"])
def test_a_stale_record_does_not_strand_an_item_that_has_moved_on(
        node, fake, recorded, since, named, extra):
    """`deliver` serves the *recorded* move when the caller names none
    (`tcw/tracker/sync.py`, `move = move or record["move"]`), and that record can name
    a move the item is already past: {extra}, and then a local status change that
    delivered nothing.

    The transition configured for that move leads where *that* move lands, not to the
    target the item's current status asks for, so naming it can only refuse — with
    "offers no transition named" when the ticket does not offer it, and with "leads to
    ... not ..." when it does. Either way the item is stuck. The name is right only
    when the move's own mapped status is the one being moved to.

    `start` is the case this repository's rename created, because `transitions.start`
    is required and so every project has one. `complete` is the same defect reached
    through the other refusal, and it was there before.
    """
    if named:
        _also_name(node, **named)
    slug = bound_item(node)
    claimed_ticket(fake)                       # In Progress, and ours
    moved_to(node, slug, "review")             # the item moved on, delivering nothing
    with_record(node, slug, {"state": "pending", "move": recorded, "since": since,
                             "claim": "owed" if recorded == "start" else "done",
                             "reason": f"could not read {KEY} back",
                             "at": "2026-09-15T10:00:00Z"})
    outcome = deliver_now(node, slug, move=None, previous=None)
    assert outcome.state != "conflicting", outcome
    assert fake.tickets[TICKET_ID].status == "In Review"


def test_a_discard_goes_straight_to_its_status_without_working_the_ticket_up(
        tmp_path, monkeypatch):
    """Abandoning work must not march the ticket through the statuses that mean
    somebody is doing it. Three sets of notifications and SLA clocks to close a
    ticket nobody held is the opposite of what a discard says."""
    workflow = {
        "To Do": [("21", "Start Progress", "In Progress"), ("51", "Drop", "Won't Do")],
        "In Progress": [("41", "Ready for Review", "In Review"),
                        ("51", "Drop", "Won't Do")],
        "In Review": [("31", "Finish", "Done"), ("51", "Drop", "Won't Do")],
        "Done": [], "Won't Do": [],
    }
    root, fake_ = ladder_node(tmp_path, monkeypatch, workflow)
    slug = under_way(root, "discarded")
    code, _out, err = sync_link(root, slug)
    assert code == 0, err
    assert fake_.tickets[TICKET_ID].status == "Won't Do"
    assert fake_.applied == ["51"], fake_.applied


def test_the_window_for_a_discard_record_is_its_two_ends(node, fake):
    """A discard can start from anywhere, so there is no path between `since` and the
    discard status to accept — only the two ends."""
    from tcw.tracker.sync import expected_statuses
    rec = {"state": "pending", "move": "discard", "since": "In Progress",
           "claim": "done", "reason": "x", "at": "2026-09-15T00:00:00Z"}
    assert expected_statuses(STATUSES, None, rec, "wontfix") == ("In Progress",
                                                                "Won't Do")


def test_sync_status_does_not_pull_back_a_ticket_already_past_its_item(tmp_path,
                                                                       monkeypatch):
    """On a workflow offering the claim from every status, claiming a ticket that is
    already in review would move it back to In Progress. It is refused instead, and
    the claim stays owed."""
    from tracker_fake import GLOBAL
    root, fake_ = ladder_node(tmp_path, monkeypatch, GLOBAL, status="In Review")
    slug = under_way(root, "active")
    code, _out, err = sync_link(root, slug)
    assert code == 1 and "past where its item is" in err, err
    assert fake_.applied == [] and fake_.tickets[TICKET_ID].status == "In Review"
    assert record(root, slug)["claim"] == "owed"


def test_sync_status_does_not_move_an_already_resolved_ticket(tmp_path, monkeypatch):
    """The walk passes the ticket's own status as where it is expected, so the resolved
    check `assess_move` makes without a window has to be made before the walk."""
    workflow = {"To Do": [("21", "Start Progress", "In Progress")], "In Progress": [],
                "Done": [("51", "Abandon", "Won't Do")], "Won't Do": []}
    root, fake_ = ladder_node(tmp_path, monkeypatch, workflow, status="Done")
    slug = under_way(root, "discarded")
    code, _out, err = sync_link(root, slug)
    assert code == 1 and "already resolved" in err, err
    assert fake_.applied == [] and fake_.tickets[TICKET_ID].status == "Done"


def test_a_walk_interrupted_after_the_claim_resumes_on_the_next_sync(tmp_path,
                                                                     monkeypatch):
    """The claim lands, then the tracker drops out before the first hop. The record
    now says the claim is done, so the next sync is not on the owed path — and on a
    workflow with no shortcut, one transition cannot reach Done from In Progress."""
    from tracker_fake import STRICT_LADDER
    root, fake_ = ladder_node(tmp_path, monkeypatch, STRICT_LADDER)
    slug = under_way(root, "completed")
    restore = transitions_fail(fake_, 2)
    assert sync_link(root, slug)[0] == 1
    assert record(root, slug)["claim"] == "done"
    assert fake_.tickets[TICKET_ID].status == "In Progress"
    restore()
    outcome = deliver_now(root, slug, move=None, previous=None)
    assert outcome.state == "current", outcome
    assert fake_.tickets[TICKET_ID].status == "Done"
    assert record(root, slug) is None


def test_a_claim_landing_off_the_ladder_stops_the_catch_up(tmp_path, monkeypatch):
    """The claim is how a ticket gets onto the first rung. If it lands somewhere the
    project has not mapped, there is no rung to walk on from — and continuing would
    choose each hop by the item's own move, so a refusal would name the wrong
    `transitions` key and the record would rest on an unmapped status."""
    workflow = {"To Do": [("21", "Start Progress", "Triage")],
                "Triage": [("22", "Begin", "In Progress")],
                "In Progress": [("31", "Finish", "Done")], "Done": []}
    root, fake_ = ladder_node(tmp_path, monkeypatch, workflow)
    slug = under_way(root, "completed")
    assert sync_link(root, slug)[0] == 1
    reason = record(root, slug)["reason"]
    assert "'Triage'" in reason and "'In Progress'" in reason
    assert fake_.tickets[TICKET_ID].status == "Triage"
    assert fake_.applied == ["21"]          # the claim only; no hop from an unmapped rung


def test_sync_status_on_a_resolved_item_records_its_own_move(tmp_path, monkeypatch):
    """`link` on a finished item is how work already done is tied to the ticket that
    tracked it. What `--sync-status` records is that item's own move, so the ticket
    catches up to where the item ended rather than to somewhere it never was."""
    root, fake_ = ladder_node(tmp_path, monkeypatch, SYNC)
    slug = under_way(root, "completed")
    transitions_fail(fake_, 1)
    assert sync_link(root, slug)[0] == 1
    written = record(root, slug)
    assert written["move"] == "complete" and written["claim"] == "owed"


def test_a_resolved_items_ticket_already_at_its_status_is_left_alone(tmp_path, fake):
    """The common case of linking finished work: the ticket is already where the item
    ended, so nothing is sent, nothing is recorded, and no warning is printed."""
    root = make_node(tmp_path, statuses=STATUSES, retain={"completed": True})
    st = FsWorkStore.open(root)
    slug = st.create("Done long ago").slug
    st.start(slug, owner="a@example.test")
    st.complete(slug, "done", ["acked"])
    claimed_ticket(fake, "Done", None)
    code, _out, err = cli(root, "work", "tracker", "link", slug, KEY)
    assert code == 0 and "warning:" not in err
    code, out, err = cli(root, "work", "tracker", "sync", slug)
    assert code == 0, (out, err)
    assert fake.writes() == [] and record(root, slug) is None


@pytest.mark.parametrize("workflow_name", ["GLOBAL", "SYNC"])
def test_sync_status_carries_on_from_a_ticket_already_yours_part_way_up(
        tmp_path, monkeypatch, workflow_name):
    """A ticket already assigned to you and already in review needs no claim. Claiming
    anyway moves it back on a workflow offering the claim from everywhere, and on one
    that does not, the claim lands off `active` and the catch-up is refused."""
    import tracker_fake
    root, fake_ = ladder_node(tmp_path, monkeypatch, getattr(tracker_fake, workflow_name),
                              status="In Review", assignee=A)
    slug = under_way(root, "completed")
    code, _out, err = sync_link(root, slug)
    assert code == 0, err
    assert fake_.tickets[TICKET_ID].status == "Done"
    assert fake_.applied == ["31"], fake_.applied


def test_sync_status_does_not_claim_back_an_unassigned_ticket_part_way_up(tmp_path,
                                                                          monkeypatch):
    """Unassigned and already in review: the claim would move it back, so it is
    refused and nothing is sent."""
    from tracker_fake import GLOBAL
    root, fake_ = ladder_node(tmp_path, monkeypatch, GLOBAL, status="In Review")
    slug = under_way(root, "completed")
    code, _out, err = sync_link(root, slug)
    assert code == 1, err
    assert fake_.applied == [] and fake_.tickets[TICKET_ID].status == "In Review"


def test_a_status_shared_by_review_and_completed_uses_the_complete_transition(
        tmp_path, monkeypatch):
    """With `review` and `completed` both mapped to Done, the rung is the completion:
    its hop must use `transitions.complete`, not `transitions.submit`."""
    from tracker_fake import FakeJira
    monkeypatch.setenv("TCW_A_EMAIL", "a@example.test")
    monkeypatch.setenv("TCW_PROBE_TOKEN", SENTINEL)
    monkeypatch.setenv("TCW_WORK_OWNER", "a@example.test")
    fake_ = FakeJira(workflow={
        "To Do": [("21", "Start Progress", "In Progress")],
        "In Progress": [("61", "Review", "Done"), ("62", "Finish", "Done")],
        "Done": []})
    fake_.account("a@example.test", A, "Alice")
    fake_.ticket(id=TICKET_ID, key=KEY, summary="t", status="To Do")
    fake_.install(monkeypatch)
    root = make_node(tmp_path, statuses={**STATUSES, "review": "Done"})
    set_transition(root, "submit", "Review")
    set_transition(root, "complete", "Finish")
    slug = under_way(root, "completed")
    code, _out, err = sync_link(root, slug)
    assert code == 0, err
    assert fake_.applied == ["21", "62"], fake_.applied


def test_sync_status_on_a_review_item_does_not_claim_back_an_unassigned_ticket_in_review(
        tmp_path, monkeypatch):
    from tracker_fake import GLOBAL
    root, fake_ = ladder_node(tmp_path, monkeypatch, GLOBAL, status="In Review")
    slug = under_way(root, "review")
    code, _out, err = sync_link(root, slug)
    assert code == 1 and "Assign it to yourself" in err, err
    assert fake_.applied == [] and fake_.tickets[TICKET_ID].status == "In Review"
    assert record(root, slug)["claim"] == "owed"


# ── what a plain link's note does not explain away ───────────────────────────


def plain_linked_in_step(tmp_path, monkeypatch, *, assignee=A):
    """An active item plain-linked while its ticket is already In Progress."""
    root, fake_ = ladder_node(tmp_path, monkeypatch, SYNC, status="In Progress",
                              assignee=assignee)
    fake_.account("b@example.test", B, "Bob")
    slug = under_way(root, "active")
    code, _out, err = cli(root, "work", "tracker", "link", slug, KEY)
    assert code == 0, err
    return root, fake_, slug


def test_a_ticket_somebody_else_holds_stays_a_recorded_conflict_after_a_plain_link(
        tmp_path, monkeypatch):
    root, fake_, slug = plain_linked_in_step(tmp_path, monkeypatch, assignee=B)
    fake_.tickets[TICKET_ID].status = "To Do"          # out of step as well as Bob's
    code, _out, err = cli(root, "work", "submit", slug)
    assert code == 1 and "Bob" in err and "linked without" not in err, err
    assert record(root, slug)["state"] == "conflicting"


def test_a_plain_link_in_step_and_yours_leaves_no_note_so_drift_is_reported(
        tmp_path, monkeypatch):
    root, fake_, slug = plain_linked_in_step(tmp_path, monkeypatch)
    assert "status-synced" not in yaml.safe_load(binding_text(root, slug))
    fake_.tickets[TICKET_ID].status = "To Do"                 # moved back by hand
    code, _out, err = cli(root, "work", "submit", slug)
    assert code == 1 and "linked without" not in err, err
    assert record(root, slug)["state"] == "conflicting"


def plain_linked_out_of_step(tmp_path, monkeypatch):
    """An active item plain-linked while its unassigned ticket is still To Do."""
    root, fake_ = ladder_node(tmp_path, monkeypatch, SYNC)
    slug = under_way(root, "active")
    assert cli(root, "work", "tracker", "link", slug, KEY)[0] == 0
    assert yaml.safe_load(binding_text(root, slug))["status-synced"] is False
    return root, fake_, slug


def test_a_misnamed_transition_stays_a_conflict_while_the_note_stands(tmp_path,
                                                                      monkeypatch):
    """The note stands, but the ticket has since been put in step and taken: a
    transition the project misnamed is a real conflict, not something the note hides."""
    root, fake_, slug = plain_linked_out_of_step(tmp_path, monkeypatch)
    fake_.tickets[TICKET_ID].status, fake_.tickets[TICKET_ID].assignee = "In Progress", A
    set_transition(root, "submit", "Ready For Reveiw")
    code, _out, err = cli(root, "work", "submit", slug)
    assert code == 1 and "offers no transition named" in err, err


def test_sync_clears_the_note_once_the_ticket_is_where_its_item_says(tmp_path,
                                                                     monkeypatch):
    """Checking writes nothing else, but a note that is no longer true is removed —
    otherwise a ticket put right by hand would stay explained away for good."""
    root, fake_, slug = plain_linked_out_of_step(tmp_path, monkeypatch)
    FsWorkStore.open(root).submit(slug)                        # delivers nothing
    fake_.tickets[TICKET_ID].status, fake_.tickets[TICKET_ID].assignee = "In Review", A
    code, out, err = cli(root, "work", "tracker", "sync", slug)
    assert code == 0 and out.startswith(f"{slug}: current"), (out, err)
    assert "status-synced" not in yaml.safe_load(binding_text(root, slug))


def test_without_sync_status_sync_does_not_walk_a_ticket_through_statuses(tmp_path,
                                                                          monkeypatch):
    """An ordinary binding: completing straight from active on a workflow with no
    shortcut is a conflict, and a later `sync` must not start walking it."""
    from tracker_fake import STRICT_LADDER
    root, fake_ = ladder_node(tmp_path, monkeypatch, STRICT_LADDER)
    slug = bound_item(root)                                    # linked in the backlog
    assert cli(root, "work", "start", slug)[0] == 0
    assert cli(root, "work", "complete", slug, "--resolution", "done", "--confirm",
               "--force")[0] == 1
    fake_.applied.clear()
    code, _out, _err = cli(root, "work", "tracker", "sync", slug)
    assert code == 1 and fake_.applied == [], fake_.applied
    assert fake_.tickets[TICKET_ID].status == "In Progress"


def test_sync_status_refuses_an_item_somebody_else_started(tmp_path, monkeypatch):
    root, fake_ = ladder_node(tmp_path, monkeypatch, SYNC)
    st = FsWorkStore.open(root)
    slug = st.create("Theirs").slug
    st.start(slug, owner="b@example.test")
    code, _out, err = sync_link(root, slug)
    assert code == 1, err
    # The command to run as them is the link that was refused, not a sync of a binding
    # that does not exist.
    assert (f"TCW_WORK_OWNER=b@example.test tcw work tracker link {slug} {KEY} "
            f"--sync-status") in err, err
    assert fake_.writes() == []
    assert FsWorkStore.open(root).read_sidecar(slug, "tracker.yaml") is None


def test_sync_status_on_a_backlog_item_says_it_did_nothing(node, fake):
    slug = FsWorkStore.open(node).create("Not started").slug
    code, _out, err = cli(node, "work", "tracker", "link", slug, KEY, "--sync-status")
    assert code == 0 and "--sync-status did nothing" in err, err
    assert fake.writes() == []


def test_an_owed_claim_without_sync_status_is_followed_by_one_transition_only(
        tmp_path, monkeypatch):
    """A `start` whose claim did not reach the tracker leaves `claim: owed`. When the
    item has moved on, `sync` claims and then makes the single move it always made —
    walking through several statuses is only for a binding that asked for it."""
    from tracker_fake import STRICT_LADDER
    root, fake_ = ladder_node(tmp_path, monkeypatch, STRICT_LADDER)
    slug = bound_item(root)
    fake_.down = True
    assert cli(root, "work", "start", slug)[0] == 1
    fake_.down = False
    assert record(root, slug)["claim"] == "owed"
    FsWorkStore.open(root).complete(slug, "done", ["acked"])    # delivers nothing
    code, _out, _err = cli(root, "work", "tracker", "sync", slug)
    assert code == 1
    assert fake_.applied == ["21"], fake_.applied
    assert fake_.tickets[TICKET_ID].status == "In Progress"


def test_an_unclaimed_ticket_in_step_after_a_plain_link_is_an_ordinary_conflict(
        tmp_path, monkeypatch):
    """The note is about status alone. A ticket already in step but unassigned gets
    none, so a move reports the assignment and records it — the same whether or not
    `sync` ran first."""
    root, fake_, slug = plain_linked_in_step(tmp_path, monkeypatch, assignee=None)
    assert "status-synced" not in yaml.safe_load(binding_text(root, slug))
    code, _out, err = cli(root, "work", "submit", slug)
    assert code == 1 and "unassigned" in err and "linked without" not in err, err
    assert record(root, slug)["state"] == "conflicting"


def test_a_held_check_removes_an_unreadable_record(tmp_path, monkeypatch):
    """Checking writes nothing, except to remove what nothing will deliver."""
    root, fake_, slug = plain_linked_out_of_step(tmp_path, monkeypatch)
    with_record(root, slug, 5)
    assert "problem" in record(root, slug)
    code, out, err = cli(root, "work", "tracker", "sync", slug)
    assert code == 0 and out.startswith(f"{slug}: held — "), (out, err)
    assert record(root, slug) is None


def test_skipping_the_claim_still_refuses_a_resolved_ticket(tmp_path, monkeypatch):
    """A `start` whose claim did not arrive, an item completed since, and a ticket of
    yours already closed as Won't Do. `claim` would have refused it; carrying on
    without a claim must too, rather than change its resolution."""
    root, fake_ = ladder_node(tmp_path, monkeypatch, {
        "To Do": [("21", "Start Progress", "In Progress")],
        "Won't Do": [("31", "Finish", "Done")], "Done": []})
    slug = bound_item(root)
    fake_.down = True
    assert cli(root, "work", "start", slug)[0] == 1
    fake_.down = False
    FsWorkStore.open(root).complete(slug, "done", ["acked"])    # delivers nothing
    fake_.tickets[TICKET_ID].status, fake_.tickets[TICKET_ID].assignee = "Won't Do", A
    code, _out, _err = cli(root, "work", "tracker", "sync", slug)
    assert code == 1
    assert fake_.applied == [] and fake_.tickets[TICKET_ID].status == "Won't Do"


def test_strict_mode_still_asks_whether_an_assignment_is_exclusive_without_a_claim(
        tmp_path, monkeypatch):
    """Already yours and in progress, so no claim transition is applied — but under
    strict mode a workflow offering the claim again from there authorizes nothing, and
    that check must not be skipped with the transition."""
    from tracker_fake import GLOBAL
    root, fake_ = ladder_node(tmp_path, monkeypatch, GLOBAL, status="In Progress",
                              assignee=A)
    slug = under_way(root, "review")
    path = root / "tcw-config.yaml"
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    config["work"]["tracker"]["strict"] = True
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    code, _out, err = sync_link(root, slug)
    assert code == 1 and "second person" in err, err
    assert fake_.applied == [] and fake_.tickets[TICKET_ID].status == "In Progress"


def test_an_unclaimed_ticket_put_in_step_after_a_plain_link_is_an_ordinary_conflict(
        tmp_path, monkeypatch):
    """The note stands, but the ticket has since been put in step by hand and nobody
    has taken it. The status no longer needs explaining; the assignment is a real
    conflict and is recorded as one."""
    root, fake_, slug = plain_linked_out_of_step(tmp_path, monkeypatch)
    fake_.tickets[TICKET_ID].status = "In Progress"
    code, _out, err = cli(root, "work", "submit", slug)
    assert code == 1 and "unassigned" in err and "linked without" not in err, err
    assert record(root, slug)["state"] == "conflicting"


def test_strict_mode_carries_on_from_a_ticket_already_yours_in_review(tmp_path,
                                                                    monkeypatch):
    """The exclusivity check is about the claim's own status. A ticket already yours
    and past it, on a workflow whose claim is exclusive, is not refused for not being
    in progress — that would leave moving it back as the only way on."""
    root, fake_ = ladder_node(tmp_path, monkeypatch, SYNC, status="In Review",
                              assignee=A)
    slug = under_way(root, "completed")
    path = root / "tcw-config.yaml"
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    config["work"]["tracker"]["strict"] = True
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    code, _out, err = sync_link(root, slug)
    assert code == 0, err
    assert fake_.tickets[TICKET_ID].status == "Done" and fake_.applied == ["31"]


def test_the_suggested_link_for_somebody_elses_item_keeps_its_part(tmp_path,
                                                                  monkeypatch):
    root, fake_ = ladder_node(tmp_path, monkeypatch, SYNC)
    st = FsWorkStore.open(root)
    slug = st.create("Theirs").slug
    st.start(slug, owner="b@example.test")
    code, _out, err = cli(root, "work", "tracker", "link", slug, KEY, "--part", "api",
                          "--sync-status")
    assert code == 1, err
    assert (f"TCW_WORK_OWNER=b@example.test tcw work tracker link {slug} {KEY} "
            f"--part api --sync-status") in err, err


def test_a_closed_ticket_somebody_else_holds_is_refused_as_closed(tmp_path,
                                                                 monkeypatch):
    """Asking the user to assign a closed ticket to themselves only leads to the next
    refusal, so the resolved check comes first."""
    root, fake_ = ladder_node(tmp_path, monkeypatch, {
        "To Do": [("21", "Start Progress", "In Progress")],
        "Won't Do": [("31", "Finish", "Done")], "Done": []})
    fake_.account("b@example.test", B, "Bob")
    slug = bound_item(root)
    fake_.down = True
    assert cli(root, "work", "start", slug)[0] == 1
    fake_.down = False
    FsWorkStore.open(root).complete(slug, "done", ["acked"])    # delivers nothing
    fake_.tickets[TICKET_ID].status, fake_.tickets[TICKET_ID].assignee = "Won't Do", B
    code, out, _err = cli(root, "work", "tracker", "sync", slug)
    assert code == 1 and "already resolved" in out and "Assign it" not in out, out
    assert fake_.applied == []
