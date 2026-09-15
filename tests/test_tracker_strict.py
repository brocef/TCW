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
