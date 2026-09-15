"""`tcw work tracker link` and `unlink`: bind an existing item, and remove a binding
while keeping the record of it.

`link` records a cross-reference and nothing else: it reads the ticket to prove it
exists, then writes the binding, leaving the ticket exactly as it found it. What is
tested here is that whole list of things it must not touch. Claiming is `import`'s
alone (`test_tracker_claim.py`). `unlink` is a local repair: it makes no tracker
call and needs no tracker configured.
"""

from __future__ import annotations

import pytest
import yaml

from tcw.store.fs import FsWorkStore
from test_tracker_import import (SENTINEL, TICKET, binding, fake,  # noqa: F401
                                 make_node, run, write_binding)

SECOND = "TCWCLAIM-7"


@pytest.fixture()
def node(tmp_path, fake):  # noqa: F811
    fake.ticket(id="10053", key=SECOND, summary="Another ready ticket")
    return make_node(tmp_path, "alpha", email_env="TCW_A_EMAIL")


def snapshot(root, slug) -> dict:
    """Every file in the item's folder, by name, so "nothing changed" is checkable."""
    folder = FsWorkStore.open(root).path(slug)
    return {p.name: p.read_bytes() for p in folder.iterdir() if p.is_file()}


def plain_item(root, title="Existing item") -> str:
    st = FsWorkStore.open(root)
    slug = st.create_work(title, intake="Raw input.\n").item.slug
    st.write_artifact(slug, "initial-request", "# Request\n\nDo the thing.\n")
    return slug


def resolve(root, slug, status: str) -> None:
    """Drive `slug` into a terminal status. `status` has no default: which one is
    the axis these tests vary, and a default would hide whichever cell it picked."""
    st = FsWorkStore.open(root)
    if status == "completed":
        st.start(slug)
        st.complete(slug, "done", ["acked"])
    elif status == "discarded":
        st.complete(slug, "wontfix", dod_ack=[], force=True)
    else:
        raise ValueError(f"not a resolved status: {status}")
    assert st.get(slug).status == status


RESOLVED = pytest.mark.parametrize("status", ["completed", "discarded"])


# ── link ─────────────────────────────────────────────────────────────────────


def test_with_no_tracker_link_refuses_naming_the_key(tmp_path, fake):  # noqa: F811
    root = make_node(tmp_path, "alpha", email_env=None)
    slug = plain_item(root)
    before = snapshot(root, slug)
    code, _out, err = run(root, "link", slug, TICKET)
    assert code == 1 and "work.tracker" in err
    assert snapshot(root, slug) == before


def ticket_state(fake, ticket_id="10052") -> tuple:  # noqa: F811
    """The two ticket fields a claim would change, and `link` must not."""
    held = fake.tickets[ticket_id]
    return held.status, held.assignee


def _assert_tracker_untouched(fake, before, ticket_id="10052") -> None:  # noqa: F811
    """`link` records a cross-reference: nothing is written to the tracker, and the
    ticket's status and assignee are what they were. Every test that links calls
    this, so one that skips it is visible in the diff."""
    assert fake.writes() == []
    assert ticket_state(fake, ticket_id) == before


def _assert_only_the_binding_changed(root, slug, before) -> None:
    """`tracker.yaml` is the whole of `link`'s local effect: every other file in the
    item's folder is byte-for-byte what it was, and none is removed."""
    after = snapshot(root, slug)
    assert {n: b for n, b in after.items() if n != "tracker.yaml"} == before
    item = FsWorkStore.open(root).get(slug)
    assert (item.status, item.owner) == ("backlog", "")


def test_link_binds_without_touching_the_body(node, fake):  # noqa: F811
    slug = plain_item(node)
    before, ticket_before = snapshot(node, slug), ticket_state(fake)
    code, _out, err = run(node, "link", slug, TICKET)
    assert code == 0, err
    doc = binding(node, slug)
    assert doc["ticket"]["key"] == TICKET and "claimed-by" not in doc
    _assert_only_the_binding_changed(node, slug, before)
    _assert_tracker_untouched(fake, ticket_before)


def test_link_binds_a_ticket_someone_else_holds(node, fake):  # noqa: F811
    """Recording a reference takes the ticket from nobody, so who holds it is not
    `link`'s business. `import` still refuses one (`test_tracker_claim.py`)."""
    fake.tickets["10052"].assignee = "acct-b"
    slug = plain_item(node)
    ticket_before = ticket_state(fake)
    code, _out, err = run(node, "link", slug, TICKET)
    assert code == 0, err
    assert binding(node, slug)["ticket"]["key"] == TICKET
    _assert_tracker_untouched(fake, ticket_before)
    assert fake.tickets["10052"].assignee == "acct-b"


def _refused_without_change(node, fake, slug, *argv):  # noqa: F811
    before = snapshot(node, slug)
    writes = len(fake.writes())
    code, _out, err = run(node, "link", slug, *argv)
    assert code == 1
    assert len(fake.writes()) == writes
    assert snapshot(node, slug) == before
    return err


def test_link_refuses_an_item_already_bound_and_names_its_ticket(node, fake):  # noqa: F811
    slug = write_binding(node, "Bound item")
    err = _refused_without_change(node, fake, slug, SECOND)
    assert TICKET in err and "unlink" in err


def test_link_refuses_a_key_another_item_holds(node, fake):  # noqa: F811
    holder = write_binding(node, "Holder")
    slug = plain_item(node)
    err = _refused_without_change(node, fake, slug, TICKET)
    assert holder in err


def test_link_refuses_a_malformed_binding_on_the_item(node, fake):  # noqa: F811
    slug = plain_item(node)
    (FsWorkStore.open(node).path(slug) / "tracker.yaml").write_text(
        "ticket: TCWCLAIM-6\n", encoding="utf-8")
    err = _refused_without_change(node, fake, slug, TICKET)
    assert slug in err


def test_link_refuses_a_malformed_binding_on_another_item(node, fake):  # noqa: F811
    other = plain_item(node, "Broken")
    (FsWorkStore.open(node).path(other) / "tracker.yaml").write_text(
        "- nonsense\n", encoding="utf-8")
    slug = plain_item(node)
    err = _refused_without_change(node, fake, slug, TICKET)
    assert other in err


def test_link_refuses_an_invalid_part(node, fake):  # noqa: F811
    """`--part` is validated before the store is opened or the tracker is called,
    so a bad one costs nothing and is refused naming the value."""
    slug = plain_item(node)
    err = _refused_without_change(node, fake, slug, TICKET, "--part", "Not A Part")
    assert "Not A Part" in err
    assert fake.requests == []


def test_link_refuses_an_unknown_ticket(node, fake):  # noqa: F811
    """The ticket read is what proves the key exists, and it is the one tracker call
    `link` keeps. A typo must not leave a binding pointing at nothing."""
    slug = plain_item(node)
    _refused_without_change(node, fake, slug, "NOSUCH-1")
    assert not (FsWorkStore.open(node).path(slug) / "tracker.yaml").exists()


@RESOLVED
def test_link_binds_a_resolved_item(node, fake, status):  # noqa: F811
    """Finished work can be linked to the ticket that tracked it. Nothing about a
    binding needs the item to still be open, now that binding does not claim."""
    slug = plain_item(node)
    resolve(node, slug, status)
    ticket_before = ticket_state(fake)
    code, _out, err = run(node, "link", slug, TICKET)
    assert code == 0, err
    assert "a resolved item's binding is not changed" not in err
    assert binding(node, slug)["ticket"]["key"] == TICKET
    _assert_tracker_untouched(fake, ticket_before)


def test_link_refuses_a_slug_that_does_not_exist(node, fake):  # noqa: F811
    """The status guard is gone; the existence check is not. In a node that does
    not retain resolved items this is also what a completed slug now hits."""
    before = len(fake.writes())
    code, _out, err = run(node, "link", "2026-01-01-not-a-real-item", TICKET)
    assert code == 1
    assert "no such work item in this node" in err
    assert len(fake.writes()) == before


# ── unlink ───────────────────────────────────────────────────────────────────


def test_unlink_without_a_reason_changes_nothing(node, fake):  # noqa: F811
    slug = write_binding(node, "Bound item")
    before = snapshot(node, slug)
    code, _out, _err = run(node, "unlink", slug)
    assert code != 0
    assert snapshot(node, slug) == before
    code, _out, _err = run(node, "unlink", slug, "--reason", "  ")
    assert code == 1
    assert snapshot(node, slug) == before


def test_unlink_refuses_an_unbound_item(node, fake):  # noqa: F811
    slug = plain_item(node)
    before = snapshot(node, slug)
    code, _out, err = run(node, "unlink", slug, "--reason", "wrong ticket")
    assert code == 1 and "not bound" in err
    assert snapshot(node, slug) == before


def test_unlink_needs_no_tracker_and_keeps_the_record(tmp_path, fake):  # noqa: F811
    root = make_node(tmp_path, "alpha", email_env=None)
    slug = write_binding(root, "Bound item")
    code, out, err = run(root, "unlink", slug, "--reason", "bound to the wrong ticket")
    assert code == 0, err
    assert fake.requests == []
    assert "unchanged" in out + err
    doc = binding(root, slug)
    assert "ticket" not in doc
    [entry] = doc["unlinked"]
    assert entry["ticket"]["key"] == TICKET
    assert entry["reason"] == "bound to the wrong ticket"
    assert entry["unlinked-on"]


def test_an_unlinked_item_can_be_linked_again_and_keeps_its_history(node, fake):  # noqa: F811
    slug = write_binding(node, "Bound item")
    assert run(node, "unlink", slug, "--reason", "wrong ticket")[0] == 0
    code, _out, err = run(node, "link", slug, SECOND)
    assert code == 0, err
    doc = binding(node, slug)
    assert doc["ticket"]["key"] == SECOND
    assert [e["reason"] for e in doc["unlinked"]] == ["wrong ticket"]


# ── no credential anywhere ───────────────────────────────────────────────────


def test_no_link_or_unlink_path_prints_or_stores_the_token(node, fake):  # noqa: F811
    outputs = []
    slug = plain_item(node)
    outputs += run(node, "link", slug, TICKET)[1:]
    outputs += run(node, "link", slug, SECOND)[1:]                    # refused: bound
    outputs += run(node, "unlink", slug, "--reason", "wrong")[1:]
    outputs += run(node, "link", plain_item(node, "Other"), TICKET)[1:]  # already yours
    assert all(SENTINEL not in text for text in outputs)
    for path in FsWorkStore.open(node).root.rglob("*"):
        if path.is_file():
            assert SENTINEL not in path.read_text(encoding="utf-8", errors="replace"), path


@RESOLVED
def test_unlink_removes_a_binding_from_a_resolved_item(node, fake, status):  # noqa: F811
    """A wrong binding on finished work was unrepairable: `unlink` refused every
    resolved status, so the only way out was editing the sidecar by hand."""
    slug = write_binding(node, "Bound item")
    resolve(node, slug, status)
    code, _out, err = run(node, "unlink", slug, "--reason", "wrong ticket")
    assert code == 0, err
    assert "a resolved item's binding is not changed" not in err
    doc = binding(node, slug)
    assert "ticket" not in doc
    assert [e["reason"] for e in doc["unlinked"]] == ["wrong ticket"]
