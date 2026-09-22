"""The claim gate: `submit` and `rework` of a bound item need its ticket held by you.

A claim gates work, not resolution. These two moves are work, so for an item with a
ticket bound to it they refuse before the item moves unless the ticket is assigned to
the account the tracker credentials sign in as — whether or not strict mode is on.
`complete` and a discard are not gated. An item with no ticket is not gated either.

The gate refuses only on an answer: a tracker that cannot be reached cannot say
somebody else holds the ticket, so outside strict mode the move goes ahead.

Built on the stateful fake in `tests/tracker_fake.py`, through `tests/test_tracker_sync.py`'s
helpers, because the gate reads the ticket's real assignee.
"""

from __future__ import annotations

import pytest

from tcw.store.fs import FsWorkStore
from test_tracker_strict import set_tracker_key
from test_tracker_sync import (A, B, STATUSES, TICKET_ID, bound_item,  # noqa: F401
                               claimed_ticket, cli, fake, make_node, record, status)


@pytest.fixture()
def node(tmp_path, fake):
    return make_node(tmp_path, statuses=STATUSES)


def started(root, *, submitted: bool = False) -> str:
    """A bound item started through the command, so its ticket is yours."""
    slug = bound_item(root)
    assert cli(root, "work", "start", slug)[0] == 0
    if submitted:
        assert cli(root, "work", "submit", slug)[0] == 0
    return slug


@pytest.mark.parametrize("verb, before, ticket_status", [
    ("submit", "active", "In Progress"), ("rework", "review", "In Review")])
def test_a_ticket_someone_else_holds_refuses_the_move_before_it_is_made(
        node, fake, verb, before, ticket_status):
    """Criteria 6 and 7: refused, naming the holder, and the item has not moved."""
    slug = started(node, submitted=before == "review")
    claimed_ticket(fake, ticket_status, B)
    fake.requests.clear()
    code, _out, err = cli(node, "work", verb, slug)
    assert code == 1 and "held by Bob" in err, err
    assert f"{slug} was not moved" in err
    assert status(node, slug) == before and fake.writes() == []
    assert record(node, slug) is None


@pytest.mark.parametrize("verb, before, ticket_status", [
    ("submit", "active", "In Progress"), ("rework", "review", "In Review")])
def test_a_released_item_is_refused_and_told_to_claim(node, fake, verb, before,
                                                      ticket_status):
    """Criterion 6b: `release` leaves the item active with no owner and the ticket
    held by nobody. The way back is `tcw work tracker claim`, and the message says so."""
    slug = started(node, submitted=before == "review")
    assert cli(node, "work", "tracker", "release", slug)[0] == 0
    assert FsWorkStore.open(node).get(slug).owner == ""
    assert fake.tickets[TICKET_ID].assignee is None
    code, _out, err = cli(node, "work", verb, slug)
    assert code == 1 and "held by nobody" in err, err
    assert f"tcw work tracker claim {slug}" in err
    assert status(node, slug) == before


def test_claiming_it_back_lets_the_move_through(node, fake):
    slug = started(node)
    assert cli(node, "work", "tracker", "release", slug)[0] == 0
    assert cli(node, "work", "submit", slug)[0] == 1
    assert cli(node, "work", "tracker", "claim", slug)[0] == 0
    code, _out, err = cli(node, "work", "submit", slug)
    assert code == 0, err
    assert status(node, slug) == "review"
    assert fake.tickets[TICKET_ID].status == "In Review"


def test_an_item_with_no_ticket_is_not_gated(node, fake):
    """Criterion 6c: the gate reads the ticket only. The item's `owner` records who
    holds the work; it is not a permission."""
    st = FsWorkStore.open(node)
    slug = st.create("Unbound").slug
    st.start(slug, owner="b@example.test")
    fake.requests.clear()
    code, _out, err = cli(node, "work", "submit", slug)
    assert code == 0, err
    assert status(node, slug) == "review" and fake.requests == []


def test_an_unreachable_tracker_does_not_refuse_outside_strict_mode(node, fake):
    """Criterion 10: nothing answered, so nothing refused. The move is made, and the
    command exits non-zero naming `sync` because the ticket did not follow."""
    slug = started(node)
    fake.down = True
    code, _out, err = cli(node, "work", "submit", slug)
    assert code == 1, err
    assert status(node, slug) == "review"
    assert "tcw work tracker sync" in err and "was not moved" not in err, err
    assert record(node, slug)["state"] == "pending"


def test_an_unreachable_tracker_refuses_under_strict_mode(node, fake):
    """Criterion 11: strict mode refuses on silence by design."""
    slug = started(node)
    set_tracker_key(node, "strict", True)
    set_tracker_key(node, "exclusive-claim-transition", "Start Progress")
    fake.down = True
    code, _out, err = cli(node, "work", "submit", slug)
    assert code == 1 and "refused under strict tracker mode" in err, err
    assert status(node, slug) == "active"


@pytest.mark.parametrize("resolution", ["done", "wontfix"])
def test_a_resolution_is_not_gated(node, fake, resolution):
    """A claim gates work, not resolution: `complete` and a discard go ahead on a
    ticket somebody else holds."""
    slug = started(node)
    claimed_ticket(fake, "In Progress", B)
    code, _out, err = cli(node, "work", "complete", slug, "--resolution", resolution,
                          "--confirm", "--force")
    assert code == 0, err
    assert status(node, slug) == ("completed" if resolution == "done" else "discarded")
