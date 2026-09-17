"""`tcw validate` reports tracker-configuration problems, and never calls out.

The second half of this file is the more important half. The first draft of this
item's spec put a *live workflow read* behind `tcw validate`, and the review found
why that is unacceptable: this repository binds `command: "tcw validate"` as a
`pre` hook on the `complete` transition (`tcw-config.yaml`), and a `pre` failure
means the store is not touched (`tcw/work/hooks.py`). A network call there makes
completing a work item depend on a tracker being reachable, on credentials being
present in that shell, and on a token not having expired.

`test_validate_makes_no_network_call` and its siblings are the standing guard
against anyone reintroducing that.
"""

from __future__ import annotations

import socket
import subprocess
import time

import pytest
import yaml

from tcw.store.fs import FsWorkStore, init
from tcw.validate import validate

VALID_TRACKER = {
    "provider": "jira-cloud",
    "base-url": "https://example.invalid",
    "candidate-query": "assignee = currentUser()",
    "credentials": {"email-env": "TCW_JIRA_EMAIL", "token-env": "TCW_JIRA_API_TOKEN"},
    "transitions": {"claim": "Start Progress"},
}


@pytest.fixture()
def node(tmp_path):
    """A minimal node with a work store, and a helper to rewrite its config."""
    root = tmp_path / "node"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    init(["work"], root, project_id="probe")

    def set_tracker(value):
        config = {"id": "probe"}
        if value is not _ABSENT:
            config["work"] = {"tracker": value}
        (root / "tcw-config.yaml").write_text(
            yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    return root, set_tracker


_ABSENT = object()


# ── problems reach validate ──────────────────────────────────────────────────


def test_no_tracker_key_produces_no_tracker_problems(node):
    root, set_tracker = node
    set_tracker(_ABSENT)
    assert [p for p in validate(root) if "tracker" in p] == []


def test_a_valid_tracker_produces_no_problems(node):
    root, set_tracker = node
    set_tracker(VALID_TRACKER)
    assert [p for p in validate(root) if "tracker" in p] == []


@pytest.mark.parametrize("key", ["provider", "base-url", "candidate-query",
                                 "credentials", "transitions"])
def test_a_missing_required_key_is_reported_by_validate(node, key):
    root, set_tracker = node
    set_tracker({k: v for k, v in VALID_TRACKER.items() if k != key})
    problems = validate(root)
    assert any(f"work.tracker.{key}" in p for p in problems), problems


def test_a_bad_provider_is_reported_with_its_value(node):
    root, set_tracker = node
    set_tracker({**VALID_TRACKER, "provider": "github"})
    assert any("github" in p for p in validate(root))


def test_a_boolean_strict_is_accepted(node):
    """`strict` arrived with the gates that honour it
    (`tests/test_tracker_strict.py`), so it is no longer an unknown key. Strict mode
    requires statuses, so a block turning it on sets them."""
    root, set_tracker = node
    set_tracker({**VALID_TRACKER, "strict": True, "statuses": {
        "active": "In Progress", "completed": "Done", "discarded": "Won't Do"}})
    assert [p for p in validate(root) if "tracker" in p] == []


def test_a_problem_names_the_config_file(node):
    """So a user with several nodes knows which file to open."""
    root, set_tracker = node
    set_tracker({**VALID_TRACKER, "provider": "github"})
    assert any("tcw-config.yaml" in p for p in validate(root))


# ── the board survives a malformed block ─────────────────────────────────────


@pytest.mark.parametrize("bad", ["a string", 7, ["a"], {"unknown-key": 1}])
def test_a_malformed_block_does_not_break_a_board_read(node, bad):
    """The contract the whole configuration layer exists to keep. `tracker_config`
    discards problems, so listing work still works while validate complains."""
    root, set_tracker = node
    set_tracker(bad)
    store = FsWorkStore.open(root)
    assert store.query() == []          # a board read, not a crash
    assert store.tracker_config() is None
    assert store.tracker_problems(), "validate must still hear about it"


def test_a_malformed_block_still_lets_items_be_created_and_listed(node):
    root, set_tracker = node
    store = FsWorkStore.open(root)
    store.create("An item that predates the bad config")
    set_tracker("not a mapping")
    store = FsWorkStore.open(root)
    assert [i.title for i in store.query()] == ["An item that predates the bad config"]


# ── validate never touches the network ───────────────────────────────────────


def test_validate_makes_no_network_call(node, monkeypatch):
    """The guard. `tcw validate` is a `pre` hook on `complete` in this very
    repository, so a network call here would make completing an item depend on a
    tracker being reachable. Any socket connection attempt fails this test.
    """
    root, set_tracker = node
    set_tracker(VALID_TRACKER)

    def forbidden(*args, **kwargs):
        raise AssertionError(
            "tcw validate attempted a network connection. It is a `pre` hook on "
            "the `complete` transition; a call here makes completing a work item "
            "depend on the tracker being reachable. Move it to an explicit command."
        )

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    validate(root)


def test_validate_reads_no_credential_environment_variable(node, monkeypatch):
    """Reading them would mean a shell without them set produces different
    validate output, which is the same failure in a quieter form."""
    root, set_tracker = node
    set_tracker(VALID_TRACKER)
    monkeypatch.delenv("TCW_JIRA_EMAIL", raising=False)
    monkeypatch.delenv("TCW_JIRA_API_TOKEN", raising=False)

    seen = []
    import os
    real = os.environ.__getitem__

    def watched(key):
        if key in ("TCW_JIRA_EMAIL", "TCW_JIRA_API_TOKEN"):
            seen.append(key)
        return real(key)

    monkeypatch.setattr(type(os.environ), "__getitem__", watched)
    validate(root)
    assert seen == [], f"validate read {seen}"


def test_validate_is_fast_with_an_unroutable_base_url(node):
    """Criterion 7's observable half: no timeout can elapse if no call is made."""
    root, set_tracker = node
    set_tracker({**VALID_TRACKER, "base-url": "https://10.255.255.1",
                 "timeout-seconds": 30})
    started = time.monotonic()
    validate(root)
    assert time.monotonic() - started < 1.0


def test_an_inbox_query_is_not_an_unknown_key(node):
    root, set_tracker = node
    set_tracker({**VALID_TRACKER, "inbox-query": "status = Triage"})
    assert [p for p in validate(root) if "tracker" in p] == []


def test_a_blank_inbox_query_is_named_by_validate(node):
    root, set_tracker = node
    set_tracker({**VALID_TRACKER, "inbox-query": " "})
    assert any("work.tracker.inbox-query: expected a non-empty string" in p
               for p in validate(root))
    assert FsWorkStore.open(root).tracker_config() is None
