"""`tcw work start` on an item that is already active.

Active and held by nobody — what `tcw work tracker release` leaves — is taken, since
there is nobody to displace. Active and held by somebody else is refused, and the
refusal names the command that takes it over.
"""

from __future__ import annotations

from tcw.store.fs import FsWorkStore
from test_tracker_sync import (A, STATUSES, TICKET_ID, bound_item, cli, fake,  # noqa: F401
                               make_node, status)


def test_start_takes_an_active_item_nobody_holds(tmp_path, fake):
    """Criterion 3, with the ticket released as well: both halves come back."""
    root = make_node(tmp_path, statuses=STATUSES)
    slug = bound_item(root)
    assert cli(root, "work", "start", slug)[0] == 0
    assert cli(root, "work", "tracker", "release", slug)[0] == 0
    assert FsWorkStore.open(root).get(slug).owner == ""
    code, _out, err = cli(root, "work", "start", slug)
    assert code == 0, err
    item = FsWorkStore.open(root).get(slug)
    assert (item.status, item.owner) == ("active", "a@example.test")
    assert fake.tickets[TICKET_ID].assignee == A


def test_the_store_takes_an_active_item_nobody_holds(tmp_path, fake):
    root = make_node(tmp_path, statuses=None, tracker=False)
    st = FsWorkStore.open(root)
    slug = st.create("Unheld").slug
    st.start(slug, owner="b@example.test")
    st.set_field(slug, "owner", "")
    assert st.start(slug, owner="a@example.test").owner == "a@example.test"


def test_start_of_an_item_somebody_else_holds_names_the_take_over(tmp_path, fake):
    """Criterion 4."""
    root = make_node(tmp_path, statuses=STATUSES)
    st = FsWorkStore.open(root)
    slug = st.create("Theirs").slug
    st.start(slug, owner="b@example.test")
    code, _out, err = cli(root, "work", "start", slug)
    assert code == 1, err
    assert f"tcw work tracker claim {slug} --take-over" in err, err
    assert FsWorkStore.open(root).get(slug).owner == "b@example.test"
    assert status(root, slug) == "active"
