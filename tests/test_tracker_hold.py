"""`tcw work tracker claim` and `release`: ownership as its own thing.

The decisions themselves are tested a level down, against the tracker functions,
in `test_tracker_ownership.py`. What this file tests is what the commands add
around them, and it is mostly about the **local** half of ownership:

- the item's `owner` is guarded before it is written, which the ticket check
  cannot do on an unbound item or on one whose ticket nobody holds;
- the local write happens last, so a ticket half that failed never leaves the item
  claiming something the tracker disagrees with;
- the local write is committed, so a claim leaves history rather than a staged
  file;
- and neither verb moves anything else — not the item's status, not the ticket's,
  not the binding.

It lives beside `test_tracker_link.py` rather than in `test_tracker_cli.py`
because it needs the stateful fake, and that file is built on a request recorder.
"""

from __future__ import annotations

import subprocess

import pytest
import yaml

from tcw.store.fs import FsWorkStore
from tcw.tracker import jira
from test_tracker_import import (A, B, SENTINEL, TICKET, binding,  # noqa: F401
                                 fake, make_node, run, write_binding)


@pytest.fixture()
def node(tmp_path, fake):  # noqa: F811
    return make_node(tmp_path, "alpha", email_env="TCW_A_EMAIL")


def owner(root, slug: str) -> str:
    return FsWorkStore.open(root).get(slug).owner


def status(root, slug: str) -> str:
    return FsWorkStore.open(root).get(slug).status


def plain_item(root, title="Existing item") -> str:
    return FsWorkStore.open(root).create(title).slug


def uncommitted(root) -> list[str]:
    probe = subprocess.run(["git", "-C", str(root), "status", "--porcelain"],
                           capture_output=True, text=True, check=True)
    return [line for line in probe.stdout.splitlines() if line.strip()]


def as_bob(monkeypatch, root):
    """Point the CLI's tracker credentials and local identity at the other account."""
    config = yaml.safe_load((root / "tcw-config.yaml").read_text(encoding="utf-8"))
    config["work"]["tracker"]["credentials"]["email-env"] = "TCW_B_EMAIL"
    (root / "tcw-config.yaml").write_text(yaml.safe_dump(config, sort_keys=False),
                                          encoding="utf-8")
    monkeypatch.setenv("TCW_WORK_OWNER", "bob@example.test")


# ── claim ────────────────────────────────────────────────────────────────────


def test_claiming_a_bound_item_takes_both_halves_and_moves_nothing(node, fake,  # noqa: F811
                                                                   monkeypatch):
    monkeypatch.setenv("TCW_WORK_OWNER", "alice@example.test")
    slug = write_binding(node, "Bound work")
    before = fake.tickets["10052"].status
    code, _out, err = run(node, "claim", slug)
    assert code == 0, err
    assert owner(node, slug) == "alice@example.test"
    assert fake.tickets["10052"].assignee == A
    assert fake.tickets["10052"].status == before
    assert status(node, slug) == "backlog"          # claiming is not starting
    assert fake.applied == []
    assert SENTINEL not in err


def test_a_claim_is_committed_rather_than_left_staged(node, monkeypatch):
    """`set_field` stages without committing, so this is the difference between a
    claim that leaves history and one that leaves a dirty tree."""
    monkeypatch.setenv("TCW_WORK_OWNER", "alice@example.test")
    slug = write_binding(node, "Bound work")
    subprocess.run(["git", "-C", str(node), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(node), "commit", "-qm", "baseline"], check=True)
    assert run(node, "claim", slug)[0] == 0
    assert uncommitted(node) == []


def test_claiming_twice_succeeds_twice_and_sends_no_transition(node, fake,  # noqa: F811
                                                               monkeypatch):
    monkeypatch.setenv("TCW_WORK_OWNER", "alice@example.test")
    slug = write_binding(node, "Bound work")
    assert run(node, "claim", slug)[0] == 0
    assert run(node, "claim", slug)[0] == 0
    assert owner(node, slug) == "alice@example.test"
    assert fake.applied == []


def test_an_unbound_item_is_claimed_locally_and_says_so(node, fake, monkeypatch):  # noqa: F811
    monkeypatch.setenv("TCW_WORK_OWNER", "alice@example.test")
    slug = plain_item(node)
    code, _out, err = run(node, "claim", slug)
    assert code == 0, err
    assert owner(node, slug) == "alice@example.test"
    assert "not bound to a ticket" in err
    assert fake.writes() == []


def test_without_a_tracker_configured_the_verb_refuses(tmp_path, fake, monkeypatch):  # noqa: F811
    """The local half needs no tracker, but the command group does. Recorded as a
    test because C4 will feel it if it composes `start` out of this."""
    root = make_node(tmp_path, "beta", email_env=None)
    monkeypatch.setenv("TCW_WORK_OWNER", "alice@example.test")
    slug = plain_item(root)
    code, _out, err = run(root, "claim", slug)
    assert code == 1 and "work.tracker" in err
    assert owner(root, slug) == ""


# ── the opt-in exclusivity ceiling ───────────────────────────────────────────


def with_exclusive_transition(root, name: str = "Start Progress") -> None:
    config = yaml.safe_load((root / "tcw-config.yaml").read_text(encoding="utf-8"))
    config["work"]["tracker"]["exclusive-claim-transition"] = name
    (root / "tcw-config.yaml").write_text(yaml.safe_dump(config, sort_keys=False),
                                          encoding="utf-8")


def test_a_configured_transition_is_applied_and_the_cost_is_reported(node, fake,  # noqa: F811
                                                                     monkeypatch):
    """The key is only worth having if the verb reads it, so this is what proves the
    wiring rather than the function's own behavior."""
    monkeypatch.setenv("TCW_WORK_OWNER", "alice@example.test")
    with_exclusive_transition(node)
    slug = write_binding(node, "Bound work")
    code, _out, err = run(node, "claim", slug)
    assert code == 0, err
    assert fake.applied == ["21"]
    assert fake.tickets["10052"].status == "In Progress"
    assert "In Progress" in err and "exclusive-claim-transition" in err
    assert owner(node, slug) == "alice@example.test"


def test_a_workflow_that_refuses_the_transition_stops_the_claim_dead(node, fake,  # noqa: F811
                                                                     monkeypatch):
    """The refusal *is* the exclusion working: a workflow that will not run the
    transition twice is how a second claimant is turned away. Nothing may be
    assigned, and the item must not end up owned by somebody the tracker rejected."""
    monkeypatch.setenv("TCW_WORK_OWNER", "alice@example.test")
    with_exclusive_transition(node)
    slug = write_binding(node, "Bound work")
    fake.fail("POST", "/transitions", jira.TrackerRequestInvalid("already in progress"))
    code, _out, err = run(node, "claim", slug)
    assert code == 1
    assert "not claimed" in err.replace("\n", " ")
    assert owner(node, slug) == ""
    assert fake.tickets["10052"].assignee is None
    assert fake.tickets["10052"].status == "To Do"
    assert SENTINEL not in err


# ── the local guard, which the ticket check cannot supply ────────────────────


def test_an_unbound_item_somebody_else_holds_is_refused(node, monkeypatch):
    """No ticket, so nothing but the local check stands between one person's claim
    and another person's ownership."""
    monkeypatch.setenv("TCW_WORK_OWNER", "alice@example.test")
    slug = plain_item(node)
    assert run(node, "claim", slug)[0] == 0
    monkeypatch.setenv("TCW_WORK_OWNER", "bob@example.test")
    code, _out, err = run(node, "claim", slug)
    assert code == 1
    assert "alice@example.test" in err and "held by" in err
    assert owner(node, slug) == "alice@example.test"


def test_a_bound_item_with_an_unassigned_ticket_is_refused_too(node, fake,  # noqa: F811
                                                               monkeypatch):
    """The other case the ticket check misses: the item is owned, but the ticket is
    assigned to nobody, so the assignee tells you nothing."""
    monkeypatch.setenv("TCW_WORK_OWNER", "alice@example.test")
    slug = write_binding(node, "Bound work")
    assert run(node, "claim", slug)[0] == 0
    fake.tickets["10052"].assignee = None
    monkeypatch.setenv("TCW_WORK_OWNER", "bob@example.test")
    code, _out, err = run(node, "claim", slug)
    assert code == 1 and "alice@example.test" in err
    assert owner(node, slug) == "alice@example.test"
    assert fake.tickets["10052"].assignee is None


@pytest.mark.parametrize("bound", [True, False])
def test_take_over_claims_it_anyway(node, monkeypatch, bound):
    monkeypatch.setenv("TCW_WORK_OWNER", "alice@example.test")
    slug = write_binding(node, "Bound work") if bound else plain_item(node)
    assert run(node, "claim", slug)[0] == 0
    monkeypatch.setenv("TCW_WORK_OWNER", "bob@example.test")
    code, _out, err = run(node, "claim", slug, "--take-over")
    assert code == 0, err
    assert owner(node, slug) == "bob@example.test"


# ── release ──────────────────────────────────────────────────────────────────


def test_releasing_drops_both_halves_and_leaves_everything_else(node, fake,  # noqa: F811
                                                                monkeypatch):
    monkeypatch.setenv("TCW_WORK_OWNER", "alice@example.test")
    slug = write_binding(node, "Bound work")
    assert run(node, "claim", slug)[0] == 0
    before_status, before_binding = fake.tickets["10052"].status, binding(node, slug)
    code, _out, err = run(node, "release", slug)
    assert code == 0, err
    assert owner(node, slug) == ""
    assert fake.tickets["10052"].assignee is None
    assert fake.tickets["10052"].status == before_status
    assert binding(node, slug) == before_binding
    assert status(node, slug) == "backlog"
    assert fake.applied == []


def test_after_a_release_somebody_else_can_claim_it(node, fake, monkeypatch):  # noqa: F811
    monkeypatch.setenv("TCW_WORK_OWNER", "alice@example.test")
    slug = write_binding(node, "Bound work")
    assert run(node, "claim", slug)[0] == 0
    assert run(node, "release", slug)[0] == 0
    as_bob(monkeypatch, node)
    code, _out, err = run(node, "claim", slug)
    assert code == 0, err
    assert owner(node, slug) == "bob@example.test"
    assert fake.tickets["10052"].assignee == B


def test_releasing_somebody_elses_work_is_refused_unless_forced(node, monkeypatch):
    monkeypatch.setenv("TCW_WORK_OWNER", "alice@example.test")
    slug = write_binding(node, "Bound work")
    assert run(node, "claim", slug)[0] == 0
    monkeypatch.setenv("TCW_WORK_OWNER", "bob@example.test")
    code, _out, err = run(node, "release", slug)
    assert code == 1 and "alice@example.test" in err
    assert owner(node, slug) == "alice@example.test"
    code, _out, err = run(node, "release", slug, "--force")
    assert code == 0, err
    assert owner(node, slug) == ""


def test_an_active_item_can_be_released_and_stays_active(node, fake, monkeypatch):  # noqa: F811
    """Stepping away from work under way is what the verb is for, so this is the
    main case rather than an edge one. The item stays active with no owner, and a
    claim is how the next person picks it up."""
    monkeypatch.setenv("TCW_WORK_OWNER", "alice@example.test")
    slug = write_binding(node, "Bound work")
    FsWorkStore.open(node).start(slug, owner="alice@example.test")
    assert run(node, "claim", slug)[0] == 0
    code, _out, err = run(node, "release", slug)
    assert code == 0, err
    assert status(node, slug) == "active" and owner(node, slug) == ""
    as_bob(monkeypatch, node)
    assert run(node, "claim", slug)[0] == 0
    assert owner(node, slug) == "bob@example.test"
    assert status(node, slug) == "active"


def test_a_tracker_that_will_not_unassign_leaves_the_owner_alone(node, fake,  # noqa: F811
                                                                 monkeypatch):
    """A Jira project can forbid unassigned issues. The two halves of ownership must
    then stay agreed — the ticket keeps its assignee, so the item keeps its owner."""
    monkeypatch.setenv("TCW_WORK_OWNER", "alice@example.test")
    slug = write_binding(node, "Bound work")
    assert run(node, "claim", slug)[0] == 0
    fake.fail("PUT", "/assignee", jira.TrackerRequestInvalid("cannot be unassigned"))
    code, _out, err = run(node, "release", slug)
    assert code == 1
    assert "could not be released" in err
    assert owner(node, slug) == "alice@example.test"
    assert fake.tickets["10052"].assignee == A
    assert SENTINEL not in err
