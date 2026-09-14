"""`tcw work tracker link` and `unlink`: bind an existing item, and remove a binding
while keeping the record of it.

`link` claims by exactly the rules `import` does (`test_tracker_claim.py`); what is
tested here is what it must not touch. `unlink` is a local repair: it makes no
tracker call and needs no tracker configured.
"""

from __future__ import annotations

import pytest
import yaml

from tcw.store.fs import FsWorkStore
from test_tracker_import import (A, BASE_URL, SENTINEL, TICKET, binding, fake,  # noqa: F401
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


# ── link ─────────────────────────────────────────────────────────────────────


def test_with_no_tracker_link_refuses_naming_the_key(tmp_path, fake):  # noqa: F811
    root = make_node(tmp_path, "alpha", email_env=None)
    slug = plain_item(root)
    before = snapshot(root, slug)
    code, _out, err = run(root, "link", slug, TICKET)
    assert code == 1 and "work.tracker" in err
    assert snapshot(root, slug) == before


def test_link_claims_and_binds_without_touching_the_body(node, fake):  # noqa: F811
    slug = plain_item(node)
    before = snapshot(node, slug)
    code, _out, err = run(node, "link", slug, TICKET)
    assert code == 0, err
    after = snapshot(node, slug)
    assert after["intake.md"] == before["intake.md"]
    assert after["initial-request.md"] == before["initial-request.md"]
    doc = binding(node, slug)
    assert doc["ticket"]["key"] == TICKET and doc["claimed-by"]["account-id"] == A
    assert fake.tickets["10052"].assignee == A


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


def test_link_refuses_a_resolved_item(node, fake):  # noqa: F811
    st = FsWorkStore.open(node)
    slug = plain_item(node)
    st.start(slug)
    st.complete(slug, "done", ["acked"])
    err = _refused_without_change(node, fake, slug, TICKET)
    assert "completed" in err


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


def test_link_refuses_a_ticket_someone_else_holds(node, fake):  # noqa: F811
    fake.tickets["10052"].assignee = "acct-b"
    slug = plain_item(node)
    err = _refused_without_change(node, fake, slug, TICKET)
    assert "Bob" in err


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


def test_unlink_refuses_a_resolved_item(node, fake):  # noqa: F811
    st = FsWorkStore.open(node)
    slug = write_binding(node, "Bound item")
    st.start(slug)
    st.complete(slug, "done", ["acked"])
    before = snapshot(node, slug)
    code, _out, _err = run(node, "unlink", slug, "--reason", "wrong ticket")
    assert code == 1
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
