"""Making a ticket for an item, and putting it somewhere the inbox will not find.

The hazard this file exists for is not "the ticket is wrong". It is that a
created ticket left in the workflow's entry status is selected by
`work.tracker.inbox-query`, so `tcw work inbox` offers it back as new inbound
work and accepting it creates a *second* item for the one that created it.
`tcw work tracker create` therefore refuses unless it knows where to put the
ticket, and refuses **before** creating anything.
"""
from __future__ import annotations

import pytest

from tcw.store.base import TrackerConfig, TrackerCreate
from tcw.tracker.create import (
    create_and_place, description_document, placement_target, unplaceable,
)
from tcw.tracker.jira import TrackerError, Transition


class StubClient:
    """Records every call, so a test can assert what did *not* reach the tracker."""

    def __init__(self, transitions=None, created_key="EX-7"):
        self.calls: list[tuple] = []
        self._transitions = transitions if transitions is not None else [
            Transition(id="11", name="Accept", to_status="To Do", to_status_id="2")]
        self._created_key = created_key

    def create_issue(self, **kwargs):
        self.calls.append(("create", kwargs))
        return {"id": "10001", "key": self._created_key}

    def transitions(self, key):
        self.calls.append(("transitions", key))
        return self._transitions

    def apply_transition(self, issue_id, transition_id):
        self.calls.append(("apply_transition", issue_id, transition_id))

    def created(self) -> list:
        return [c for c in self.calls if c[0] == "create"]


_MISSING = object()


def config(*, statuses=None, create=_MISSING) -> TrackerConfig:
    return TrackerConfig(
        provider="jira-cloud", base_url="https://ex.invalid",
        candidate_query="project = EX", email_env="E", token_env="T",
        start_transition="Start",
        statuses=statuses if statuses is not None else {"backlog": "To Do"},
        create=(TrackerCreate(project="EX", issue_type="Task",
                              issue_types={"epic": "Epic", "bug": "Bug"})
                if create is _MISSING else create),
    )


# ── the refusal that makes the hazard unreachable ───────────────────────────


def test_creation_refuses_when_no_backlog_status_is_mapped():
    """Spec criterion 3. Without this the ticket stays where the tracker put it,
    which is the status inbox-query selects."""
    reason = unplaceable(config(statuses={"active": "In Progress"}))
    assert reason is not None
    assert "work.tracker.statuses.backlog" in reason


def test_the_refusal_happens_before_anything_is_created():
    """The important half. A refusal *after* a create leaves a real ticket in a
    shared tracker that TCW then declines to bind — worse than not running."""
    client = StubClient()
    with pytest.raises(TrackerError) as error:
        create_and_place(client, config(statuses={"active": "In Progress"}),
                         slug="s", title="T", body="b", is_epic=False, tags=[])
    assert "work.tracker.statuses.backlog" in str(error.value)
    assert client.created() == [], client.calls


def test_creation_refuses_with_no_create_block():
    assert unplaceable(config(create=None)) is not None
    assert unplaceable(config()) is None


# ── placing the ticket ──────────────────────────────────────────────────────


def test_a_created_ticket_is_moved_out_of_the_entry_status():
    client = StubClient()
    created = create_and_place(client, config(), slug="s", title="T", body="b",
                               is_epic=False, tags=[])
    assert created.key == "EX-7"
    assert created.status == "To Do"
    assert ("apply_transition", "10001", "11") in client.calls


def test_the_hop_is_chosen_by_destination_not_by_name():
    """`Accept → To Do` is the real shape: the transition's name is not the
    target's name, so matching on name would never fire."""
    client = StubClient(transitions=[
        Transition(id="99", name="Backlog", to_status="Somewhere Else", to_status_id="9"),
        Transition(id="11", name="Accept", to_status="To Do", to_status_id="2")])
    create_and_place(client, config(), slug="s", title="T", body="b",
                     is_epic=False, tags=[])
    assert ("apply_transition", "10001", "11") in client.calls
    assert ("apply_transition", "10001", "99") not in client.calls


def test_an_unreachable_target_says_what_was_offered_and_that_the_ticket_exists():
    """It cannot be undone from here, so the message has to admit it."""
    client = StubClient(transitions=[
        Transition(id="61", name="Cancel", to_status="Won't Do", to_status_id="6")])
    with pytest.raises(TrackerError) as error:
        create_and_place(client, config(), slug="s", title="T", body="b",
                         is_epic=False, tags=[])
    message = str(error.value)
    assert "Cancel → Won't Do" in message
    assert "is not bound to any item" in message


# ── what the ticket is made of ──────────────────────────────────────────────


def test_the_issue_type_comes_from_the_item():
    client = StubClient()
    create_and_place(client, config(), slug="s", title="T", body="b",
                     is_epic=True, tags=["bug"])
    assert client.created()[0][1]["issue_type"] == "Epic"

    client = StubClient()
    create_and_place(client, config(), slug="s", title="T", body="b",
                     is_epic=False, tags=["bug"])
    assert client.created()[0][1]["issue_type"] == "Bug"

    client = StubClient()
    create_and_place(client, config(), slug="s", title="T", body="b",
                     is_epic=False, tags=["docs"])
    assert client.created()[0][1]["issue_type"] == "Task"


def test_an_epic_tagged_bug_is_still_an_epic():
    """Typing it Bug would put its children under a bug in the hierarchy."""
    client = StubClient()
    create_and_place(client, config(), slug="s", title="T", body="b",
                     is_epic=True, tags=["bug"])
    assert client.created()[0][1]["issue_type"] == "Epic"


def test_the_description_carries_the_body_and_names_the_item():
    doc = description_document(slug="2026-01-01-thing", body="First.\n\nSecond.",
                               item_url="https://example.invalid/x")
    texts = [n["content"][0]["text"] for n in doc["content"]]
    assert "First." in texts and "Second." in texts
    assert any("2026-01-01-thing" in t for t in texts)
    assert doc["type"] == "doc"


def test_an_item_with_no_body_still_gets_a_description():
    """Jira rejects an empty description document, and an item filed with a bare
    title is ordinary."""
    doc = description_document(slug="s", body="   ")
    assert doc["content"], doc


def test_the_created_key_is_reported_before_the_move():
    """What lets an interrupted run resume by binding instead of creating again:
    the key is handed over the moment the tracker reports it."""
    seen: list[str] = []
    client = StubClient(transitions=[])          # the move will fail
    with pytest.raises(TrackerError):
        create_and_place(client, config(), slug="s", title="T", body="b",
                         is_epic=False, tags=[],
                         on_created=lambda key, issue_id: seen.append(key))
    assert seen == ["EX-7"]


def test_placement_is_always_the_backlog_status():
    """Even for work under way. Jumping straight to In Progress would leave a
    ticket in progress that nobody holds; the delivery path claims it."""
    assert placement_target(config(statuses={"backlog": "To Do",
                                             "active": "In Progress"}), "active") == "To Do"
