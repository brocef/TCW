"""Strict mode refuses a move its ticket's workflow cannot follow, and `import`
can nest a child (spec: 2026-09-15-make-the-strict-tracker-gate-refuse-unfollowable-moves-and-allow-child-items)."""

from __future__ import annotations

import pytest

from tcw.store.fs import FsWorkStore
from test_tracker_strict import (REFUSED, set_tracker_key, started,  # noqa: F401
                                 strict)
from test_tracker_sync import (A, TICKET_ID, binding_text, bound_item,  # noqa: F401
                               claimed_ticket, cli, fake, record, status)
from tests.work.jira.fake import STRICT_LADDER


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


# ── an already-bound ticket: the placement asked for is checked, never applied
# (spec: 2026-09-27-say-so-when-tracker-import-parent-meets-a-ticket-already-bound-here)

def epic(root, title: str = "Parent") -> str:
    return FsWorkStore.open(root).create_work(title, type="epic").item.slug


def reimport(root, *options: str):
    """`tcw work tracker import` of the fake's ticket, with `options`."""
    return cli(root, "work", "tracker", "import", TICKET_ID, *options)


def bound_state(root, slug: str) -> bytes:
    return next(root.rglob(f"{slug}/state.yaml")).read_bytes()


def test_a_reimport_asking_for_another_parent_is_refused(strict, unclaimed):  # noqa: F811
    parent = epic(strict)
    code, out, err = reimport(strict)
    assert code == 0, err
    slug = out.split()[0]
    writes, before = len(unclaimed.writes()), bound_state(strict, slug)
    code, out, err = reimport(strict, "--parent", parent)
    assert code == 1 and out.split() == [slug], (out, err)
    assert parent in err and slug in err and "was not moved" in err, err
    assert "tcw serve" in err, err
    assert "→ already bound" not in err, err
    assert FsWorkStore.open(strict).get(slug).parent == ""
    assert len(unclaimed.writes()) == writes
    assert bound_state(strict, slug) == before


def test_a_reimport_asking_for_another_initiative_is_refused(strict, unclaimed):  # noqa: F811
    initiative = epic(strict, "Initiative")
    slug = reimport(strict)[1].split()[0]
    writes, before = len(unclaimed.writes()), bound_state(strict, slug)
    code, out, err = reimport(strict, "--initiative", initiative)
    assert code == 1 and out.split() == [slug], (out, err)
    assert f"tcw work edit {slug} --initiative {initiative}" in err, err
    assert FsWorkStore.open(strict).get(slug).initiative == ""
    assert len(unclaimed.writes()) == writes
    assert bound_state(strict, slug) == before


@pytest.mark.parametrize("option", ["--parent", "--initiative"])
def test_the_same_placement_again_is_a_plain_rerun(strict, unclaimed, option):  # noqa: F811
    target = epic(strict)
    code, out, err = reimport(strict, option, target)
    assert code == 0, err
    slug = out.split()[0]
    code, out, err = reimport(strict, option, target)
    assert code == 0 and out.split() == [slug] and "→ already bound" in err, err


def test_a_reimport_without_a_parent_leaves_a_nested_item_alone(strict, unclaimed):  # noqa: F811
    parent = epic(strict)
    slug = reimport(strict, "--parent", parent)[1].split()[0]
    code, out, err = reimport(strict)
    assert code == 0 and out.split() == [slug] and "→ already bound" in err, err


def test_both_placements_mismatched_say_so_once_each(strict, unclaimed):  # noqa: F811
    parent, initiative = epic(strict), epic(strict, "Initiative")
    reimport(strict)
    code, _out, err = reimport(strict, "--parent", parent,
                               "--initiative", initiative)
    lines = [ln for ln in err.splitlines() if ln.startswith("tcw work tracker import:")]
    assert code == 1 and len(lines) == 2, err
    assert parent in lines[0] and initiative in lines[1], err
    assert "→ already bound" not in err, err


def test_a_bound_item_gone_before_it_is_read_is_reported(strict, unclaimed,  # noqa: F811
                                                         monkeypatch):
    parent = epic(strict)
    slug = reimport(strict)[1].split()[0]
    real_get = FsWorkStore.get
    monkeypatch.setattr(FsWorkStore, "get",
                        lambda self, ref: None if ref == slug else real_get(self, ref))
    code, out, err = reimport(strict, "--parent", parent)
    assert code == 1 and out.split() == [slug], (out, err)
    assert "could not be read again" in err and "Traceback" not in err, err


# ── review fold-in: the other gated moves, and a legacy catch-up binding ────

def test_rework_is_refused_when_the_workflow_cannot_follow(strict, fake):  # noqa: F811
    slug = bound_item(strict)
    claimed_ticket(fake, "In Review", A)
    started(strict, slug, submitted=True)
    fake.workflow = {**fake.workflow, "In Review": [
        t for t in fake.workflow["In Review"] if t[2] != "In Progress"]}
    code, _out, err = cli(strict, "work", "rework", slug)
    assert code == 1 and "no transition to 'In Progress'" in err, err
    assert status(strict, slug) == "review"


def test_complete_is_refused_when_the_workflow_cannot_reach_done(strict, fake):  # noqa: F811
    slug = bound_item(strict)
    claimed_ticket(fake, "In Progress", A)
    started(strict, slug)
    fake.workflow = STRICT_LADDER                   # In Progress → In Review → Done
    code, _out, err = cli(strict, "work", "complete", slug, "--resolution", "done",
                          "--confirm", "--force")
    assert code == 1 and "no transition to 'Done'" in err, err
    assert status(strict, slug) == "active"


def test_a_ticket_already_at_the_target_passes(strict, fake):  # noqa: F811
    slug = bound_item(strict)
    claimed_ticket(fake, "In Review", A)
    started(strict, slug)
    fake.workflow = {**fake.workflow, "In Review": []}
    assert cli(strict, "work", "submit", slug)[0] == 0


def catch_up(root, slug):
    """Mark the binding as the retired `link --sync-status` left it."""
    import yaml
    content = yaml.safe_load(binding_text(root, slug))
    content["catch-up"] = True
    content.pop("sync", None)
    (FsWorkStore.open(root).path(slug) / "tracker.yaml").write_text(
        yaml.safe_dump(content, sort_keys=False), encoding="utf-8")


COMPLETE = ("--resolution", "done", "--confirm", "--force")


def test_a_catch_up_walk_is_refused_and_taken_one_step_at_a_time(strict, fake):  # noqa: F811
    """Replaces "walked, not refused": the walk's later rungs cannot be checked
    before they are made (spec: 2026-09-27-close-two-strict-mode-gaps-…)."""
    slug = bound_item(strict)
    claimed_ticket(fake, "In Progress", A)
    started(strict, slug)
    catch_up(strict, slug)
    fake.workflow = STRICT_LADDER
    code, _out, err = cli(strict, "work", "complete", slug, *COMPLETE)
    assert code == 1 and "one step at a time" in err and "'In Review'" in err, err
    assert status(strict, slug) == "active" and fake.applied == []
    assert cli(strict, "work", "submit", slug)[0] == 0
    code, _out, err = cli(strict, "work", "complete", slug, *COMPLETE)
    assert code == 0, err
    assert fake.tickets[TICKET_ID].status == "Done"


def test_a_catch_up_walk_broken_part_way_is_refused_before_anything_moves(
        strict, fake):  # noqa: F811
    from tests.work.jira.fake import BROKEN_LADDER
    slug = bound_item(strict)
    claimed_ticket(fake, "In Progress", A)
    started(strict, slug)
    catch_up(strict, slug)
    fake.workflow = BROKEN_LADDER
    code, _out, err = cli(strict, "work", "complete", slug, *COMPLETE)
    assert code == 1 and "one step at a time" in err, err
    assert status(strict, slug) == "active"
    assert record(strict, slug) is None and fake.applied == []


def test_the_advice_for_an_item_already_in_review_names_no_submit(strict, fake):  # noqa: F811
    """A shared part lets a review item's ticket lag two rungs behind; there is
    no `submit` left to take, and the tracker step the advice names works."""
    api = bound_item(strict, "Api", part="api")
    web = bound_item(strict, "Web", part="web")
    claimed_ticket(fake, "In Progress", A)
    FsWorkStore.open(strict).complete(web, "wontfix", [], force=True)
    started(strict, api, submitted=True)
    catch_up(strict, api)
    fake.workflow = STRICT_LADDER
    code, _out, err = cli(strict, "work", "complete", api, *COMPLETE)
    assert code == 1 and "`tcw work submit" not in err, err
    assert "move SYNC-1 to 'In Review' yourself" in err, err
    claimed_ticket(fake, "In Review", A)
    code, _out, err = cli(strict, "work", "complete", api, *COMPLETE)
    assert code == 0, err


def test_a_catch_up_completion_of_a_ticket_someone_else_holds_is_refused(
        strict, fake):  # noqa: F811
    from test_tracker_sync import B
    slug = bound_item(strict)
    claimed_ticket(fake, "In Review", A)
    started(strict, slug, submitted=True)
    catch_up(strict, slug)
    claimed_ticket(fake, "In Review", B)
    code, _out, err = cli(strict, "work", "complete", slug, *COMPLETE)
    assert code == 1 and "assigned to Bob" in err, err
    assert status(strict, slug) == "review"
    assert record(strict, slug) is None and fake.applied == []


def test_a_catch_up_completion_one_step_away_and_held_passes(strict, fake):  # noqa: F811
    slug = bound_item(strict)
    claimed_ticket(fake, "In Review", A)
    started(strict, slug, submitted=True)
    catch_up(strict, slug)
    code, _out, err = cli(strict, "work", "complete", slug, *COMPLETE)
    assert code == 0, err
    assert fake.tickets[TICKET_ID].status == "Done"


def test_a_catch_up_binding_one_step_away_is_still_refused(strict, fake):  # noqa: F811
    """Only a walk of more than one rung is `deliver`'s to finish."""
    import yaml
    slug = bound_item(strict)
    claimed_ticket(fake, "In Progress", A)
    started(strict, slug)
    content = yaml.safe_load(binding_text(strict, slug))
    content["catch-up"] = True
    content.pop("sync", None)
    (FsWorkStore.open(strict).path(slug) / "tracker.yaml").write_text(
        yaml.safe_dump(content, sort_keys=False), encoding="utf-8")
    no_route_to_review(fake)
    code, _out, err = cli(strict, "work", "submit", slug)
    assert code == 1 and "no transition to 'In Review'" in err, err
    assert status(strict, slug) == "active"
