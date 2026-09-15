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
], ids=["comments-not-boolean", "unknown-placeholder", "not-http", "open-brace",
        "not-text", "positional"])
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
