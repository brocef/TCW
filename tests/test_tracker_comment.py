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
