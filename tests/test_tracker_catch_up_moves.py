"""A lifecycle move on a legacy `catch-up` binding is carried as on any other
binding when its ticket is where the move expects it, so the gate and delivery
never disagree (spec: 2026-09-29-refuse-a-catch-up-rework-whose-ticket-is-already-past-the-item)."""

from __future__ import annotations

import pytest
import yaml

from tcw.store.fs import FsWorkStore
from test_tracker_strict import started, strict  # noqa: F401
from test_tracker_strict_gate import COMPLETE, catch_up
from test_tracker_sync import (A, TICKET_ID, binding_text, bound_item,  # noqa: F401
                               claimed_ticket, cli, fake, node, record, status)


def _clean_binding(root, slug) -> None:
    assert record(root, slug) is None, record(root, slug)
    assert "catch-up" not in binding_text(root, slug)


# ── 1, 2: rework applies its own transition and leaves nothing behind ────────

@pytest.mark.parametrize("mode", ["strict", "node"])
@pytest.mark.xfail(strict=True, reason="not implemented yet")
def test_a_catch_up_rework_moves_the_ticket_back(mode, request, fake):  # noqa: F811
    root = request.getfixturevalue(mode)
    slug = bound_item(root)
    claimed_ticket(fake, "In Review", A)
    started(root, slug, submitted=True)
    catch_up(root, slug)
    code, _out, err = cli(root, "work", "rework", slug)
    assert code == 0, err
    assert status(root, slug) == "active"
    assert fake.tickets[TICKET_ID].status == "In Progress"
    assert fake.applied == ["42"], fake.applied          # "Back to Progress", not a start
    _clean_binding(root, slug)


# ── 3: a start whose ticket is already ahead is held, not a conflict ────────

@pytest.mark.parametrize("mode", ["strict", "node"])
@pytest.mark.xfail(strict=True, reason="not implemented yet")
def test_a_catch_up_start_of_a_ticket_already_ahead_is_held(mode, request, fake):  # noqa: F811
    root = request.getfixturevalue(mode)
    slug = bound_item(root)
    claimed_ticket(fake, "In Review", A)
    catch_up(root, slug)
    code, _out, err = cli(root, "work", "start", slug)
    assert code == 0, err
    assert status(root, slug) == "active"
    assert fake.tickets[TICKET_ID].status == "In Review" and fake.applied == []
    assert record(root, slug) is None, record(root, slug)


# ── 4: a conflict the old behavior recorded clears on the next sync ──────────

@pytest.mark.xfail(strict=True, reason="not implemented yet")
def test_a_recorded_rework_conflict_clears_on_sync(node, fake):  # noqa: F811
    from tcw.tracker.sync import _now
    slug = bound_item(node)
    claimed_ticket(fake, "In Review", A)
    started(node, slug, submitted=True)
    FsWorkStore.open(node).rework(slug)
    st = FsWorkStore.open(node)
    content = yaml.safe_load(binding_text(node, slug))
    content["catch-up"] = True
    content["sync"] = {"state": "conflicting", "move": "rework", "since": "In Review",
                       "reason": "SYNC-1 is in 'In Review', which is past where its "
                                 "item is, so it was not moved back.", "at": _now()}
    (st.path(slug) / "tracker.yaml").write_text(yaml.safe_dump(content, sort_keys=False),
                                                encoding="utf-8")
    code, out, err = cli(node, "work", "tracker", "sync", slug)
    assert code == 0, out + err
    assert fake.tickets[TICKET_ID].status == "In Progress"
    _clean_binding(node, slug)


# ── 5: what must still be refused ────────────────────────────────────────────

def test_a_strict_catch_up_rework_with_the_ticket_done_moves_nothing(strict, fake):  # noqa: F811
    slug = bound_item(strict)
    claimed_ticket(fake, "In Review", A)
    started(strict, slug, submitted=True)
    catch_up(strict, slug)
    claimed_ticket(fake, "Done", A)
    code, _out, err = cli(strict, "work", "rework", slug)
    assert code == 1, err
    assert status(strict, slug) == "review" and fake.applied == []


def test_a_catch_up_completion_still_works(strict, fake):  # noqa: F811
    slug = bound_item(strict)
    claimed_ticket(fake, "In Review", A)
    started(strict, slug, submitted=True)
    catch_up(strict, slug)
    code, _out, err = cli(strict, "work", "complete", slug, *COMPLETE)
    assert code == 0, err
    assert fake.tickets[TICKET_ID].status == "Done"
