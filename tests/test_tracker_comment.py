"""Progress comments on a bound ticket: `work.tracker.comments` and `link`, the
comment record, and what each lifecycle move posts.

Built on `tests/test_tracker_sync.py`'s helpers and fake tracker, like
`tests/test_tracker_strict.py`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tcw.store.base import link_for
from tcw.store.fs import FsWorkStore
from tcw.validate import validate
from test_tracker_strict import BASE, parsed, set_tracker_key
from test_tracker_sync import (A, B, KEY, SENTINEL, STATUSES, TICKET_ID,  # noqa: F401
                               bound_item, claimed_ticket, cli, fake, make_node,
                               record, status)


# ── configuration ────────────────────────────────────────────────────────────


def test_comments_default_off_and_link_empty():
    config, problems = parsed()
    assert problems == [] and (config.comments, config.link) == (False, "")


def test_comments_and_a_link_parse():
    config, problems = parsed(comments=True, link="https://tcw.example.com/work/{slug}")
    assert problems == [] and config.comments is True
    assert config.link == "https://tcw.example.com/work/{slug}"


def test_a_link_with_comments_off_is_not_a_problem():
    assert parsed(link="https://x.test/{project}/{slug}")[1] == []


@pytest.mark.parametrize("extra, key", [
    ({"comments": "yes"}, "work.tracker.comments"),
    ({"comments": True, "link": "https://x/{branch}"}, "work.tracker.link"),
    ({"comments": True, "link": "ftp://x/{slug}"}, "work.tracker.link"),
    ({"comments": True, "link": "https://x/{slug"}, "work.tracker.link"),
    ({"comments": True, "link": 7}, "work.tracker.link"),
    ({"comments": True, "link": "https://x/{0}"}, "work.tracker.link"),
    ({"comments": True, "link": "https://x/{slug:d}"}, "work.tracker.link"),
    ({"comments": True, "link": "https://x/{slug!r}"}, "work.tracker.link"),
    ({"comments": True, "link": "https://x/{slug:{project}}"}, "work.tracker.link"),
    ({"comments": True, "link": "https://x/{slug.upper}"}, "work.tracker.link"),
    ({"comments": True, "link": "https://x/a b/{slug}"}, "work.tracker.link"),
], ids=["comments-not-boolean", "unknown-placeholder", "not-http", "open-brace",
        "not-text", "positional", "format-spec", "conversion", "nested", "attribute",
        "space"])
def test_a_bad_comment_setting_is_a_problem(extra, key):
    config, problems = parsed(**extra)
    assert config is None and any(p.startswith(key) for p in problems), problems


def test_link_for_substitutes_and_encodes():
    assert (link_for("https://x.test/{project}/w/{slug}", "a b", "s/1")
            == "https://x.test/a%20b/w/s%2F1")


def test_validate_names_a_bad_link_and_the_board_still_reads(tmp_path, fake):
    root = make_node(tmp_path, statuses=STATUSES)
    set_tracker_key(root, "comments", True)
    set_tracker_key(root, "link", "https://x/{branch}")
    assert any("work.tracker.link" in p for p in validate(root))
    assert cli(root, "work", "list")[0] == 0


def test_a_child_can_turn_off_comments_it_inherits(tmp_path):
    from test_tracker_inheritance import ABSENT, COMPLETE, _chain, _store
    nodes = _chain(tmp_path, root_board=False,
                   root={**COMPLETE, "comments": True, "link": "https://x/{slug}"},
                   repo=ABSENT, pkg={"comments": False})
    config = _store(nodes["pkg"]).tracker_config()
    assert _store(nodes["pkg"]).tracker_problems() == []
    assert config.comments is False and config.link == "https://x/{slug}"


# ── the record ───────────────────────────────────────────────────────────────


import jsonschema  # noqa: E402
import yaml  # noqa: E402

from tcw.tracker.intake import read_binding, unlink_document, with_comment_record  # noqa: E402
from tcw.store.base import binding_value  # noqa: E402
from tcw.work.projection import WORK_ITEM_SCHEMA  # noqa: E402
from test_tracker_sync import document  # noqa: E402

OWED = {"move": "submit", "event": "submit-3f9a1c2e", "state": "pending",
        "reason": "the tracker could not be reached", "at": "2026-09-15T10:15:00Z"}


def comment_of(text: str):
    return binding_value(read_binding(text))["comment"]


def test_a_comment_record_is_read_and_removed():
    text = with_comment_record(document(), OWED)
    assert comment_of(text) == OWED
    assert comment_of(with_comment_record(text, None)) is None
    assert "sync" not in yaml.safe_load(text)


@pytest.mark.parametrize("broken", [
    "not a mapping", {**OWED, "state": "held"}, {**OWED, "move": "auto-delete"},
    {**OWED, "event": 7}, {k: v for k, v in OWED.items() if k != "at"},
], ids=["not-mapping", "state", "move", "event", "missing"])
def test_a_malformed_comment_record_is_a_problem_and_the_item_stays_bound(broken):
    data = yaml.safe_load(document())
    data["comment"] = broken
    value = binding_value(read_binding(yaml.safe_dump(data)))
    assert set(value["comment"]) == {"problem"} and value["ticket"]["key"] == KEY


def test_the_schema_takes_a_comment_a_problem_and_none(tmp_path, fake):
    root = make_node(tmp_path, statuses=STATUSES)
    slug = bound_item(root)
    st = FsWorkStore.open(root)
    path = st.path(slug) / "tracker.yaml"
    for value in (None, OWED, {"problem": "x"}):
        data = yaml.safe_load(path.read_text())
        data["comment"] = value
        path.write_text(yaml.safe_dump(data, sort_keys=False))
        code, out, err = cli(root, "work", "show", slug, "--json")
        assert code == 0, err
        import json
        jsonschema.validate(json.loads(out), WORK_ITEM_SCHEMA)


def test_unlink_carries_an_owed_comment_into_the_history():
    text = unlink_document(with_comment_record(document(), OWED), reason="x",
                           today="2026-09-15")
    data = yaml.safe_load(text)
    assert "comment" not in data and data["unlinked"][-1]["comment"] == OWED
    assert binding_value(read_binding(text)) is None


# ── publishing, directly ─────────────────────────────────────────────────────


from tcw.tracker import jira  # noqa: E402


def comments_node(tmp_path, **tracker):
    root = make_node(tmp_path, statuses=STATUSES)
    set_tracker_key(root, "comments", True)
    for key, value in tracker.items():
        set_tracker_key(root, key, value)
    return root


def publish_now(root, slug, *, move, status_state="current"):
    from tcw.tracker.progress import publish
    st = FsWorkStore.open(root)
    config = st.tracker_config()
    return publish(st, slug, jira.JiraClient(config), config, move=move,
                   status_state=status_state)


def retry_now(root, slug):
    from tcw.tracker.progress import retry
    st = FsWorkStore.open(root)
    config = st.tracker_config()
    return retry(st, slug, jira.JiraClient(config), config)


def texts(fake):
    return [(author, jira._document_text(doc)) for author, doc in
            fake.tickets[TICKET_ID].comments]


def owed(root, slug):
    return FsWorkStore.open(root).get(slug).tracker["comment"]


def test_a_move_posts_one_comment_naming_the_item_and_the_move(tmp_path, fake):
    root = comments_node(tmp_path)
    slug = bound_item(root, "Checkout page")
    claimed_ticket(fake)
    assert publish_now(root, slug, move="submit").state == "current"
    [(author, text)] = texts(fake)
    lines = text.splitlines()
    assert author == A and lines[0] == 'TCW: "Checkout page" went to review.'
    assert lines[-1].startswith("tcw-event: submit-") and len(lines) == 2
    assert owed(root, slug) is None


def test_every_move_has_its_words_and_its_own_event(tmp_path, fake):
    root = comments_node(tmp_path)
    slug = bound_item(root, "Checkout page")
    claimed_ticket(fake)
    for move in ("start", "submit", "rework", "submit", "complete"):
        publish_now(root, slug, move=move)
    lines = [text.splitlines() for _author, text in texts(fake)]
    assert [line[0] for line in lines] == [
        'TCW: "Checkout page" started.', 'TCW: "Checkout page" went to review.',
        'TCW: "Checkout page" went back to work.', 'TCW: "Checkout page" went to review.',
        'TCW: "Checkout page" was completed.']
    assert len({line[-1] for line in lines}) == 5


def test_a_discard_names_its_resolution_and_a_part_is_named(tmp_path, fake):
    root = comments_node(tmp_path)
    slug = bound_item(root, "Api", part="api")
    claimed_ticket(fake)
    FsWorkStore.open(root).complete(slug, "wontfix", ["acked"])
    publish_now(root, slug, move="discard")
    assert texts(fake)[0][1].splitlines()[0] == (
        'TCW: "Api" (part api) was discarded as wontfix.')


def test_the_link_is_substituted_and_carried_as_a_link(tmp_path, fake):
    root = comments_node(tmp_path, link="https://example.test/w/{project}/{slug}")
    slug = bound_item(root)
    claimed_ticket(fake)
    publish_now(root, slug, move="start")
    url = f"https://example.test/w/alpha/{slug}"
    assert texts(fake)[0][1].splitlines()[1] == url
    [(_author, doc)] = fake.tickets[TICKET_ID].comments
    marks = [node.get("marks") for block in doc["content"]
             for node in block["content"] if node.get("marks")]
    assert marks == [[{"type": "link", "attrs": {"href": url}}]]


@pytest.mark.parametrize("assignee", [B, None])
def test_a_ticket_that_is_not_yours_gets_no_comment_and_no_record(tmp_path, fake,
                                                                  assignee):
    root = comments_node(tmp_path)
    slug = bound_item(root)
    claimed_ticket(fake, "In Progress", assignee)
    outcome = publish_now(root, slug, move="submit")
    assert outcome.state == "skipped" and fake.tickets[TICKET_ID].comments == []
    assert owed(root, slug) is None


@pytest.mark.parametrize("state", ["pending", "conflicting"])
def test_a_status_that_did_not_follow_owes_the_comment(tmp_path, fake, state):
    root = comments_node(tmp_path)
    slug = bound_item(root)
    outcome = publish_now(root, slug, move="submit", status_state=state)
    assert outcome.recorded and fake.writes() == []
    record_ = owed(root, slug)
    assert (record_["state"], record_["move"]) == (state, "submit")
    assert record_["event"].startswith("submit-")


def test_a_failed_post_is_owed_and_a_retry_posts_it_once(tmp_path, fake):
    root = comments_node(tmp_path)
    slug = bound_item(root)
    claimed_ticket(fake)
    fake.fail("POST", "/comment", jira.TrackerUnavailable("down"))
    assert publish_now(root, slug, move="submit").state == "pending"
    assert owed(root, slug)["state"] == "pending" and texts(fake) == []
    assert retry_now(root, slug).state == "current"
    assert len(texts(fake)) == 1 and owed(root, slug) is None


def test_a_post_that_landed_without_an_answer_is_not_repeated(tmp_path, fake):
    root = comments_node(tmp_path)
    slug = bound_item(root)
    claimed_ticket(fake)
    fake.fail("POST", "/comment", jira.TrackerUnavailable("lost"), apply_first=True)
    publish_now(root, slug, move="submit")
    event = owed(root, slug)["event"]
    assert retry_now(root, slug).state == "current"
    assert [text.splitlines()[-1] for _a, text in texts(fake)] == [f"tcw-event: {event}"]
    assert owed(root, slug) is None


def test_the_marker_in_another_accounts_comment_does_not_count(tmp_path, fake):
    root = comments_node(tmp_path)
    slug = bound_item(root)
    claimed_ticket(fake)
    publish_now(root, slug, move="submit", status_state="pending")
    event = owed(root, slug)["event"]
    fake.tickets[TICKET_ID].comments.append((B, {"type": "doc", "version": 1, "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": f"tcw-event: {event}"}]}]}))
    retry_now(root, slug)
    assert [author for author, _text in texts(fake)] == [B, A]


def test_a_retry_on_a_ticket_no_longer_yours_drops_the_comment(tmp_path, fake):
    root = comments_node(tmp_path)
    slug = bound_item(root)
    publish_now(root, slug, move="complete", status_state="pending")
    claimed_ticket(fake, "Done", B)
    assert retry_now(root, slug).state == "skipped"
    assert owed(root, slug) is None and texts(fake) == []


def test_a_later_posted_move_replaces_an_owed_comment(tmp_path, fake):
    root = comments_node(tmp_path)
    slug = bound_item(root)
    claimed_ticket(fake)
    publish_now(root, slug, move="submit", status_state="pending")
    publish_now(root, slug, move="rework")
    assert owed(root, slug) is None
    assert [text.splitlines()[0] for _a, text in texts(fake)] == [
        'TCW: "Bound item" went back to work.']


def test_comments_turned_off_or_a_broken_record_are_cleared(tmp_path, fake):
    root = comments_node(tmp_path)
    slug = bound_item(root)
    publish_now(root, slug, move="submit", status_state="pending")
    set_tracker_key(root, "comments", False)
    assert retry_now(root, slug).state == "cleared" and owed(root, slug) is None
    set_tracker_key(root, "comments", True)
    path = FsWorkStore.open(root).path(slug) / "tracker.yaml"
    data = yaml.safe_load(path.read_text())
    data["comment"] = "broken"
    path.write_text(yaml.safe_dump(data))
    assert retry_now(root, slug).state == "cleared" and owed(root, slug) is None
    assert fake.writes() == []


def test_comments_off_publishes_nothing(tmp_path, fake):
    root = make_node(tmp_path, statuses=STATUSES)
    slug = bound_item(root)
    claimed_ticket(fake)
    fake.requests.clear()
    assert publish_now(root, slug, move="submit").state == "none"
    assert fake.requests == []


# ── through the commands ─────────────────────────────────────────────────────


import json  # noqa: E402
import subprocess  # noqa: E402


def commit(root):
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "setup", "--allow-empty"],
                   check=True)


def first_lines(fake):
    return [text.splitlines()[0] for _a, text in texts(fake)]


def test_comments_off_the_whole_lifecycle_sends_no_comment(tmp_path, fake):
    root = make_node(tmp_path, statuses=STATUSES)
    slug = bound_item(root)
    for argv in (("start", slug), ("submit", slug), ("rework", slug), ("submit", slug),
                 ("complete", slug, "--resolution", "done", "--confirm")):
        assert cli(root, "work", *argv)[0] == 0, argv
    assert not any("/comment" in path for _m, path, _a in fake.requests)


def test_the_whole_lifecycle_posts_five_comments(tmp_path, fake):
    root = comments_node(tmp_path)
    slug = bound_item(root, "Checkout page")
    for argv in (("start", slug), ("submit", slug), ("rework", slug), ("submit", slug),
                 ("complete", slug, "--resolution", "done", "--confirm")):
        code, _out, err = cli(root, "work", *argv)
        assert code == 0, (argv, err)
    assert first_lines(fake) == [
        'TCW: "Checkout page" started.', 'TCW: "Checkout page" went to review.',
        'TCW: "Checkout page" went back to work.', 'TCW: "Checkout page" went to review.',
        'TCW: "Checkout page" was completed.']
    assert {author for author, _t in texts(fake)} == {A}
    assert len({text.splitlines()[-1] for _a, text in texts(fake)}) == 5
    assert "comment" not in yaml.safe_load(
        FsWorkStore.open(root).read_sidecar(slug, "tracker.yaml").content)


def test_a_discard_with_no_discard_status_moves_nothing_but_still_comments(
        tmp_path, fake):
    """An unmapped `discarded` sends no status move — that is what this pins. The
    comment is not governed by the status mapping, and a discard may act on a ticket
    nobody holds, so the note saying the work was abandoned is still posted."""
    root = make_node(tmp_path, statuses={"active": "In Progress"})
    set_tracker_key(root, "comments", True)
    slug = bound_item(root)
    code, _out, err = cli(root, "work", "complete", slug, "--resolution", "wontfix",
                          "--confirm")
    assert code == 0, err
    assert fake.tickets[TICKET_ID].status == "To Do"      # nothing moved it
    assert len(texts(fake)) == 1 and owed(root, slug) is None


def test_a_held_part_still_posts_its_comment(tmp_path, fake):
    root = comments_node(tmp_path)
    api = bound_item(root, "Api", part="api")
    bound_item(root, "Web", part="web")
    assert cli(root, "work", "start", api)[0] == 0
    code, _out, err = cli(root, "work", "submit", api)
    assert code == 0 and "also bound to" in err, err
    assert first_lines(fake)[-1] == 'TCW: "Api" (part api) went to review.'


def test_a_comment_that_did_not_post_is_owed_and_synced_after_the_ticket_moved_on(
        tmp_path, fake):
    root = comments_node(tmp_path)
    slug = bound_item(root)
    assert cli(root, "work", "start", slug)[0] == 0
    fake.fail("POST", "/comment", jira.TrackerUnavailable("comment post dropped"))
    code, _out, err = cli(root, "work", "submit", slug)
    assert code == 1 and "did not get its progress comment (pending)" in err
    assert f"tcw work tracker sync {slug}" in err
    assert status(root, slug) == "review" and fake.tickets[TICKET_ID].status == "In Review"
    _code, out, _err = cli(root, "work", "show", slug)
    assert "tracker comment: pending after submit" in out
    document_ = json.loads(cli(root, "work", "show", slug, "--json")[1])
    jsonschema.validate(document_, WORK_ITEM_SCHEMA)
    assert document_["tracker"]["comment"]["state"] == "pending"
    assert document_["tracker"]["sync"] is None
    assert "comment pending" in cli(root, "work", "list")[1]
    fake.tickets[TICKET_ID].status = "Done"                  # moved on by hand
    code, out, err = cli(root, "work", "tracker", "sync", "--all")
    assert code == 0, (out, err)
    assert first_lines(fake) == ['TCW: "Bound item" started.',
                                 'TCW: "Bound item" went to review.']
    assert owed(root, slug) is None


def test_a_tracker_that_is_down_owes_both_and_sync_sends_both(tmp_path, fake):
    root = comments_node(tmp_path)
    slug = bound_item(root)
    assert cli(root, "work", "start", slug)[0] == 0
    fake.down = True
    assert cli(root, "work", "submit", slug)[0] == 1
    assert record(root, slug)["state"] == "pending" and owed(root, slug)["state"] == "pending"
    fake.down = False
    code, out, err = cli(root, "work", "tracker", "sync", slug)
    assert code == 0, (out, err)
    assert fake.tickets[TICKET_ID].status == "In Review"
    assert first_lines(fake)[-1] == 'TCW: "Bound item" went to review.'
    assert record(root, slug) is None and owed(root, slug) is None


def test_a_reassigned_ticket_owes_both_until_it_comes_back(tmp_path, fake):
    root = comments_node(tmp_path)
    slug = bound_item(root)
    assert cli(root, "work", "start", slug)[0] == 0
    # Reassigned after the claim gate read the ticket and before the move reached it.
    fake.before("GET", "/myself", lambda: claimed_ticket(fake, "In Progress", B))
    assert cli(root, "work", "submit", slug)[0] == 1
    assert owed(root, slug)["state"] == "conflicting" and len(texts(fake)) == 1
    code, _out, _err = cli(root, "work", "tracker", "sync", slug)
    assert code == 1 and owed(root, slug)["state"] == "conflicting"
    claimed_ticket(fake, "In Progress", A)
    code, out, err = cli(root, "work", "tracker", "sync", slug)
    assert code == 0, (out, err)
    assert fake.tickets[TICKET_ID].status == "In Review" and len(texts(fake)) == 2
    assert record(root, slug) is None and owed(root, slug) is None


def test_sync_drops_an_owed_comment_once_comments_are_off(tmp_path, fake):
    root = comments_node(tmp_path)
    slug = bound_item(root)
    assert cli(root, "work", "start", slug)[0] == 0
    fake.fail("POST", "/comment", jira.TrackerUnavailable("dropped"))
    assert cli(root, "work", "submit", slug)[0] == 1
    set_tracker_key(root, "comments", False)
    code, out, _err = cli(root, "work", "tracker", "sync", "--all")
    assert code == 0 and "comments are turned off" in out
    assert owed(root, slug) is None and len(texts(fake)) == 1


def test_strict_mode_does_not_refuse_over_an_owed_comment(tmp_path, fake):
    root = comments_node(tmp_path)
    set_tracker_key(root, "strict", True)
    set_tracker_key(root, "exclusive-claim-transition", "Start Progress")
    slug = bound_item(root)
    assert cli(root, "work", "start", slug)[0] == 0
    fake.fail("POST", "/comment", jira.TrackerUnavailable("dropped"))
    assert cli(root, "work", "submit", slug)[0] == 1
    assert owed(root, slug) is not None and record(root, slug) is None
    code, _out, err = cli(root, "work", "rework", slug)
    assert code == 0, err


def test_a_lost_comment_does_not_keep_an_unretained_item(tmp_path, fake):
    root = make_node(tmp_path, statuses=STATUSES, retain={"completed": False})
    set_tracker_key(root, "comments", True)
    slug = bound_item(root)
    commit(root)
    assert cli(root, "work", "start", slug)[0] == 0
    fake.fail("POST", "/comment", jira.TrackerUnavailable("dropped"))
    code, _out, err = cli(root, "work", "complete", slug, "--resolution", "done",
                          "--confirm")
    assert code == 1 and "progress comment" in err and "cannot be retried" in err
    assert "tracker sync" not in err
    assert FsWorkStore.open(root).get(slug) is None


def test_no_comment_carries_the_token_or_a_lifecycle_document(tmp_path, fake):
    root = comments_node(tmp_path)
    slug = bound_item(root)
    folder = FsWorkStore.open(root).path(slug)
    for name in ("spec.md", "plan.md", "outcome.md"):
        (folder / name).write_text(f"# x\n\nSECRET-PHRASE-{name}\n")
    outputs = [cli(root, "work", "start", slug)]
    fake.fail("POST", "/comment", jira.TrackerUnavailable("dropped"))
    outputs.append(cli(root, "work", "submit", slug))
    outputs.append(cli(root, "work", "tracker", "sync", slug))
    bodies = json.dumps([doc for _a, doc in fake.tickets[TICKET_ID].comments])
    assert "SECRET-PHRASE" not in bodies and SENTINEL not in bodies
    for _code, out, err in outputs:
        assert SENTINEL not in out + err
    assert SENTINEL not in (FsWorkStore.open(root).path(slug) / "tracker.yaml").read_text()


def test_a_status_step_that_keeps_failing_carries_its_state_onto_the_comment(
        tmp_path, fake):
    root = comments_node(tmp_path)
    slug = bound_item(root)
    assert cli(root, "work", "start", slug)[0] == 0
    fake.down = True
    assert cli(root, "work", "submit", slug)[0] == 1
    assert owed(root, slug)["state"] == "pending"
    fake.down = False
    claimed_ticket(fake, "In Progress", B)
    assert cli(root, "work", "tracker", "sync", slug)[0] == 1
    assert record(root, slug)["state"] == "conflicting"
    assert owed(root, slug)["state"] == "conflicting"
    assert owed(root, slug)["reason"] == record(root, slug)["reason"]


def test_sync_removes_a_malformed_comment_record_and_one_owed_while_comments_are_off(
        tmp_path, fake):
    root = comments_node(tmp_path)
    slug = bound_item(root)
    assert cli(root, "work", "start", slug)[0] == 0
    path = FsWorkStore.open(root).path(slug) / "tracker.yaml"
    data = yaml.safe_load(path.read_text())
    data["comment"] = "broken"
    path.write_text(yaml.safe_dump(data))
    code, out, _err = cli(root, "work", "tracker", "sync", "--all")
    assert code == 0 and "cannot be read" in out and owed(root, slug) is None
    fake.down = True
    assert cli(root, "work", "submit", slug)[0] == 1
    set_tracker_key(root, "comments", False)
    cli(root, "work", "tracker", "sync", slug)                # status still failing
    assert owed(root, slug) is None and record(root, slug) is not None


def test_a_comment_owed_on_a_binding_from_another_site_is_reported(tmp_path, fake):
    root = comments_node(tmp_path)
    slug = bound_item(root)
    publish_now(root, slug, move="submit", status_state="pending")
    set_tracker_key(root, "base-url", "https://elsewhere.invalid")
    assert retry_now(root, slug).state == "conflicting"
    assert owed(root, slug)["state"] == "conflicting"
    assert "elsewhere.invalid" in owed(root, slug)["reason"]
    assert cli(root, "work", "tracker", "sync", slug)[0] == 1


def test_a_completion_of_an_unassigned_ticket_posts_its_comment(tmp_path, fake):
    """A completion moves a ticket nobody holds now (a claim gates work, not
    resolution), so it says so on the ticket, as a discard already did. It used to be
    skipped, because a completion could not move such a ticket."""
    root = comments_node(tmp_path)
    slug = bound_item(root)
    claimed_ticket(fake, "In Progress", None)
    assert publish_now(root, slug, move="complete").state == "current"
    assert len(texts(fake)) == 1 and owed(root, slug) is None


def test_a_discard_of_an_unassigned_ticket_still_posts_its_comment(tmp_path, fake):
    """A discard may close a ticket nobody holds, so the comment saying why must go
    with it — otherwise the ticket is closed with no trace of what closed it, which
    is the whole of the reporter's queue."""
    root = comments_node(tmp_path)
    slug = bound_item(root)
    claimed_ticket(fake, "To Do", None)
    code, out, err = cli(root, "work", "complete", slug, "--resolution", "wontfix",
                         "--confirm", "--force")
    assert code == 0, (out, err)
    assert fake.tickets[TICKET_ID].status == "Won't Do"
    assert len(texts(fake)) == 1, texts(fake)
    assert owed(root, slug) is None
