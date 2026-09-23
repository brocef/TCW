"""Probe: `tcw work tracker sync` on a resolved item whose ticket was reopened."""
from __future__ import annotations

import pytest

from test_tracker_sync import (STATUSES, KEY, TICKET_ID, A, B, cli, fake,  # noqa: F401
                               make_node, bound_item, record, status)
from tracker_fake import FakeJira  # noqa: F401


def _complete(root, slug):
    code, out, err = cli(root, "work", "start", slug)
    assert code == 0, err
    code, out, err = cli(root, "work", "submit", slug)
    assert code == 0, err
    code, out, err = cli(root, "work", "complete", slug, "--resolution", "done",
                         "--confirm")
    assert code == 0, err


@pytest.mark.parametrize("assignee", [None, A, B], ids=["unassigned", "alice", "bob"])
def test_sync_of_a_reopened_ticket_on_a_completed_item(tmp_path, fake, assignee):
    root = make_node(tmp_path, statuses=STATUSES)
    slug = bound_item(root)
    _complete(root, slug)
    ticket = fake.tickets[TICKET_ID]
    print("after complete:", ticket.status, ticket.assignee, "record:", record(root, slug))
    # Somebody reopens the ticket in the tracker.
    ticket.status, ticket.assignee = "In Progress", assignee
    code, out, err = cli(root, "work", "tracker", "sync", slug)
    print("exit", code)
    print("OUT:", out)
    print("ERR:", err)
    print("ticket now:", ticket.status, ticket.assignee)
    print("record now:", record(root, slug))
