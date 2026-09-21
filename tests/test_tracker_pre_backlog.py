"""`work.tracker.pre-backlog`: taking a ticket out of a status that comes before the
backlog, such as Jira's `Triage`, before claiming it.

A project names each such status and the transition that takes a ticket from it to
`statuses.backlog`. Only then does a claim — from `start`, `link --sync-status`,
`sync`, `tracker import` or `inbox accept` — apply that transition first. Without
it the ticket stays where it is, and the refusal names the setting.
"""

from __future__ import annotations

import subprocess

import pytest
import yaml

from tcw.store.base import merge_tracker_blocks, parse_tracker_config, pre_backlog_entry
from tcw.validate import validate

VALID = {
    "provider": "jira-cloud",
    "base-url": "https://example.invalid",
    "candidate-query": "assignee = currentUser()",
    "credentials": {"email-env": "TCW_JIRA_EMAIL", "token-env": "TCW_JIRA_API_TOKEN"},
    "transitions": {"start": "Start Progress"},
}
BACKLOG_STATUSES = {"backlog": "To Do", "active": "In Progress", "review": "In Review",
                    "completed": "Done", "discarded": {"wontfix": "Won't Do"}}


def parsed(pre_backlog, statuses=BACKLOG_STATUSES):
    return parse_tracker_config({**VALID, "statuses": statuses, "pre-backlog": pre_backlog})


# ── Task 1: the setting ───────────────────────────────────────────────────────

@pytest.mark.parametrize("pre_backlog, statuses, key", [
    (["Triage"], BACKLOG_STATUSES, "work.tracker.pre-backlog"),
    ({"  ": "Accept"}, BACKLOG_STATUSES, "work.tracker.pre-backlog"),
    ({"Triage": 11}, BACKLOG_STATUSES, "work.tracker.pre-backlog.Triage"),
    ({"Triage": "Accept", "triage ": "Accept"}, BACKLOG_STATUSES,
     "work.tracker.pre-backlog."),
    ({"in progress": "Accept"}, BACKLOG_STATUSES, "work.tracker.pre-backlog.in progress"),
    ({"Won't Do": "Accept"}, BACKLOG_STATUSES, "work.tracker.pre-backlog.Won't Do"),
    ({"Triage": "Accept"}, {"active": "In Progress"}, "work.tracker.statuses.backlog"),
], ids=["not-a-mapping", "blank-status", "non-string-transition", "same-status-twice",
        "also-active", "also-a-discard-resolution", "no-backlog"])
def test_a_bad_pre_backlog_fails_closed_naming_the_key(pre_backlog, statuses, key):
    config, problems = parsed(pre_backlog, statuses)
    assert config is None
    assert any(p.startswith(key) for p in problems), problems


def test_a_valid_pre_backlog_parses():
    config, problems = parsed({" Triage ": " Accept "})
    assert problems == []
    assert config.pre_backlog == {"Triage": "Accept"}
    assert pre_backlog_entry(config.pre_backlog, "  triage ") == ("Triage", "Accept")
    assert pre_backlog_entry(config.pre_backlog, "To Do") == ("", "")


def test_no_pre_backlog_is_an_empty_mapping():
    config, problems = parse_tracker_config({**VALID, "statuses": BACKLOG_STATUSES})
    assert problems == [] and config.pre_backlog == {}


def test_validate_names_pre_backlog(tmp_path):
    from tcw.store.fs import init
    root = tmp_path / "node"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    init(["work"], root, project_id="probe")
    config = {"id": "probe", "work": {"tracker": {
        **VALID, "statuses": {"active": "In Progress"},
        "pre-backlog": {"Triage": "Accept"}}}}
    (root / "tcw-config.yaml").write_text(yaml.safe_dump(config, sort_keys=False),
                                          encoding="utf-8")
    problems = validate(root)
    assert any("work.tracker.statuses.backlog: required when pre-backlog is set" in p
               for p in problems), problems


def test_a_child_inherits_pre_backlog_entries():
    merged, _record, _whole = merge_tracker_blocks([
        ("child", {"pre-backlog": {"Needs Info": "Accept"}}),
        ("parent", {**VALID, "statuses": BACKLOG_STATUSES,
                    "pre-backlog": {"Triage": "Accept"}}),
    ])
    config, problems = parse_tracker_config(merged)
    assert problems == []
    assert config.pre_backlog == {"Triage": "Accept", "Needs Info": "Accept"}
