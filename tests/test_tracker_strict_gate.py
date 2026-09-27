"""Strict mode refuses a move its ticket's workflow cannot follow, and `import`
can nest a child (spec: 2026-09-15-make-the-strict-tracker-gate-refuse-unfollowable-moves-and-allow-child-items)."""

from __future__ import annotations

import pytest

from tcw.store.fs import FsWorkStore
from test_tracker_strict import (REFUSED, set_tracker_key, started,  # noqa: F401
                                 strict)
from test_tracker_sync import (A, TICKET_ID, bound_item, claimed_ticket, cli,  # noqa: F401
                               fake, record, status)


def no_route_to_review(fake):
    fake.workflow = {**fake.workflow,
                     "In Progress": [t for t in fake.workflow["In Progress"]
                                     if t[2] != "In Review"]}


def two_routes_to_review(fake):
    fake.workflow = {**fake.workflow,
                     "In Progress": [*fake.workflow["In Progress"],
                                     ("43", "Send for Review", "In Review")]}


# ── criterion 1: no transition to the target ────────────────────────────────

def test_submit_is_refused_when_the_workflow_cannot_follow(strict, fake):  # noqa: F811
    slug = bound_item(strict)
    claimed_ticket(fake, "In Progress", A)
    started(strict, slug)
    no_route_to_review(fake)
    code, _out, err = cli(strict, "work", "submit", slug)
    assert code == 1 and REFUSED in err and "no transition to 'In Review'" in err, err
    assert status(strict, slug) == "active"
    assert record(strict, slug) is None
    assert fake.applied == []


# ── criterion 2: several transitions, with and without a configured name ────

def test_two_routes_are_refused_without_a_name(strict, fake):  # noqa: F811
    slug = bound_item(strict)
    claimed_ticket(fake, "In Progress", A)
    started(strict, slug)
    two_routes_to_review(fake)
    code, _out, err = cli(strict, "work", "submit", slug)
    assert code == 1 and "more than one transition" in err, err
    assert status(strict, slug) == "active"


def test_two_routes_pass_when_a_configured_name_picks_one(strict, fake):  # noqa: F811
    set_tracker_key(strict, "transitions", {"start": "Start Progress",
                                            "submit": "Send for Review"})
    slug = bound_item(strict)
    claimed_ticket(fake, "In Progress", A)
    started(strict, slug)
    two_routes_to_review(fake)
    code, _out, err = cli(strict, "work", "submit", slug)
    assert code == 0, err
    assert status(strict, slug) == "review"
    assert fake.applied == ["43"]


# ── criterion 3: not asked for a held sibling or an unmapped target ─────────

def test_a_held_sibling_is_not_refused_for_the_workflow(strict, fake):  # noqa: F811
    api = bound_item(strict, "Api", part="api")
    bound_item(strict, "Web", part="web")
    claimed_ticket(fake, "In Progress", A)
    started(strict, api)
    no_route_to_review(fake)
    code, _out, err = cli(strict, "work", "submit", api)
    assert code == 0, err
    assert status(strict, api) == "review"


def test_an_unmapped_target_is_not_asked(strict, fake):  # noqa: F811
    set_tracker_key(strict, "statuses", {"active": "In Progress", "completed": "Done",
                                         "discarded": "Won't Do"})
    slug = bound_item(strict)
    claimed_ticket(fake, "In Progress", A)
    started(strict, slug)
    no_route_to_review(fake)
    code, _out, err = cli(strict, "work", "submit", slug)
    assert code == 0, err


# ── criterion 4: import nests a child ────────────────────────────────────────

@pytest.fixture()
def unclaimed(fake):  # noqa: F811
    claimed_ticket(fake, "To Do", None)
    return fake


def imported(root, out: str) -> str:
    return [ln for ln in out.split() if ln.startswith("20")][0].rstrip(".")


def test_import_nests_the_child_under_a_parent(strict, unclaimed):  # noqa: F811
    parent = FsWorkStore.open(strict).create_work("Parent", type="epic").item.slug
    code, out, err = cli(strict, "work", "tracker", "import", TICKET_ID, "--parent", parent)
    assert code == 0, err
    children = [i for i in FsWorkStore.open(strict).query() if i.parent == parent]
    assert len(children) == 1, [(i.slug, i.parent) for i in FsWorkStore.open(strict).query()]


def test_import_sets_the_initiative(strict, unclaimed):  # noqa: F811
    epic = FsWorkStore.open(strict).create_work("Initiative", type="epic").item.slug
    code, out, err = cli(strict, "work", "tracker", "import", TICKET_ID,
                         "--initiative", epic)
    assert code == 0, err
    assert [i for i in FsWorkStore.open(strict).query() if i.initiative == epic]


def test_an_unknown_parent_is_refused_before_the_ticket_is_touched(strict, unclaimed):  # noqa: F811
    code, _out, err = cli(strict, "work", "tracker", "import", TICKET_ID,
                          "--parent", "2026-01-01-nothing")
    assert code == 1 and "2026-01-01-nothing" in err, err
    assert unclaimed.writes() == []
