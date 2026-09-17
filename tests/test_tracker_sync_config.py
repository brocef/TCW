"""`work.tracker.statuses`: where a bound item's ticket should be for each local status.

Parsed offline, like the rest of `work.tracker`: a block with a problem fails closed
and `tcw validate` names the key, while the board keeps working.
"""

from __future__ import annotations

import subprocess

import pytest
import yaml

from tcw.store.base import parse_tracker_config, target_status
from tcw.store.fs import FsWorkStore, init
from tcw.validate import validate

VALID = {
    "provider": "jira-cloud",
    "base-url": "https://example.invalid",
    "candidate-query": "assignee = currentUser()",
    "credentials": {"email-env": "TCW_JIRA_EMAIL", "token-env": "TCW_JIRA_API_TOKEN"},
    "transitions": {"start": "Start Progress"},
}
STATUSES = {"active": "In Progress", "review": "In Review", "completed": "Done",
            "discarded": "Won't Do"}


def parsed(statuses):
    return parse_tracker_config({**VALID, "statuses": statuses})


def test_no_statuses_block_is_an_empty_mapping():
    config, problems = parse_tracker_config(VALID)
    assert problems == [] and config.statuses == {}


def test_a_full_block_parses():
    config, problems = parsed(STATUSES)
    assert problems == [] and config.statuses == STATUSES


def test_discarded_may_map_each_resolution():
    config, problems = parsed({"active": "In Progress",
                               "discarded": {"duplicate": "Duplicate",
                                             "wontfix": "Won't Do"}})
    assert problems == []
    assert target_status(config.statuses, "discarded", "duplicate") == "Duplicate"
    assert target_status(config.statuses, "discarded", "superseded") == ""


def test_target_status_is_empty_for_an_unmapped_status():
    config, _ = parsed({"active": "In Progress"})
    assert target_status(config.statuses, "review", None) == ""
    assert target_status(config.statuses, "active", None) == "In Progress"
    assert target_status(config.statuses, "discarded", "wontfix") == ""
    assert target_status(STATUSES, "discarded", "duplicate") == "Won't Do"


@pytest.mark.parametrize("statuses, key", [
    ({"active": "In Progress", "backlog": "To Do"}, "work.tracker.statuses.backlog"),
    ({"active": 7}, "work.tracker.statuses.active"),
    ({"active": "  "}, "work.tracker.statuses.active"),
    ({"active": "In Progress", "discarded": {"done": "Done"}},
     "work.tracker.statuses.discarded.done"),
    ({"active": "In Progress", "discarded": {"wontfix": 3}},
     "work.tracker.statuses.discarded.wontfix"),
    ({"active": "In Progress", "discarded": ["Won't Do"]},
     "work.tracker.statuses.discarded"),
    ({"review": "In Review"}, "work.tracker.statuses.active"),
    ("In Progress", "work.tracker.statuses"),
], ids=["unknown-key", "non-string", "blank", "done-resolution", "non-string-resolution",
        "list", "review-without-active", "not-a-mapping"])
def test_a_bad_block_fails_closed_naming_the_key(statuses, key):
    config, problems = parsed(statuses)
    assert config is None
    assert any(p.startswith(key + ":") for p in problems), problems


@pytest.fixture()
def node(tmp_path):
    root = tmp_path / "node"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    init(["work"], root, project_id="probe")
    return root


def write_statuses(root, statuses) -> None:
    config = {"id": "probe", "work": {"tracker": {**VALID, "statuses": statuses}}}
    (root / "tcw-config.yaml").write_text(yaml.safe_dump(config, sort_keys=False),
                                          encoding="utf-8")


def test_validate_names_the_key_and_the_board_still_reads(node, monkeypatch):
    write_statuses(node, {"review": "In Review"})
    assert any("work.tracker.statuses.active" in p for p in validate(node))
    from tcw.cli import main
    monkeypatch.chdir(node)
    FsWorkStore.open(node).create("Still listed")
    assert main(["work", "list"]) == 0


def test_a_child_inherits_one_status_from_its_parent_key_by_key(tmp_path):
    """Merged like `credentials` and `transitions`: nearest file wins each key."""
    from tcw.store.base import merge_tracker_blocks
    merged, _record, _whole = merge_tracker_blocks([
        ("child", {"statuses": {"review": "Code Review"}}),
        ("parent", {**VALID, "statuses": {"active": "In Progress", "review": "In Review"}}),
    ])
    config, problems = parse_tracker_config(merged)
    assert problems == []
    assert config.statuses == {"active": "In Progress", "review": "Code Review"}
