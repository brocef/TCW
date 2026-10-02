"""The stage table and the navigation built on its columns (TCW-69 Design 3)."""

import pytest

from tcw.errors import UsageError
from tcw.work.model import (
    STAGES, completion_stage, discard_stage, flow_order, gates_for, inbox_stage,
    is_skip, next_stage, position, records_gate_stage, stage, start_stage,
)

ALL = frozenset(s.name for s in STAGES)


def without(*names):
    return ALL - set(names)


def test_the_table_is_the_spec_s_table():
    rows = [(s.name, s.kind, s.artifact, s.optional, s.verdict, s.on_reject,
             s.completion, s.discard, s.prompt, s.gates) for s in STAGES]
    assert rows == [
        ("inbox", "flow", "none", False, False, None, False, False, True, ()),
        ("request", "flow", "document", False, False, None, False, False, True, ()),
        ("spec", "flow", "document", True, False, None, False, False, True, ()),
        ("plan", "flow", "document", True, False, None, False, False, True, ()),
        ("implement", "flow", "rounds", False, False, None, False, False, True, ()),
        ("review", "flow", "rounds", True, True, "implement", False, False, True, ()),
        ("qa", "flow", "rounds", True, True, "implement", False, False, True, ()),
        ("completed", "terminal", "none", False, False, None, True, False, False,
         ("completion",)),
        ("discarded", "terminal", "none", False, False, None, False, True, False, ()),
        ("postmortem", "side", "document", True, False, None, False, False, True, ()),
    ]


def test_exactly_one_completion_and_one_discard_stage():
    assert [s.name for s in STAGES if s.completion] == ["completed"]
    assert [s.name for s in STAGES if s.discard] == ["discarded"]
    assert completion_stage() == "completed"
    assert discard_stage() == "discarded"


def test_where_new_items_start():
    assert start_stage() == "request"
    assert inbox_stage() == "inbox"


def test_an_unknown_stage_is_a_usage_error():
    with pytest.raises(UsageError):
        stage("bogus")
    assert stage("qa").on_reject == "implement"


def test_flow_order_skips_disabled_stages():
    assert flow_order(without("plan", "qa")) == (
        "inbox", "request", "spec", "implement", "review")


def test_next_stage_follows_the_enabled_flow():
    assert next_stage("request", ALL) == "spec"
    assert next_stage("spec", without("plan")) == "implement"
    assert next_stage("implement", without("review", "qa")) == "completed"
    assert next_stage("qa", ALL) == "completed"


@pytest.mark.parametrize("name", ["completed", "discarded", "postmortem"])
def test_next_stage_from_a_terminal_or_side_stage_is_a_bug(name):
    with pytest.raises(ValueError):
        next_stage(name, ALL)


def test_completion_is_later_than_every_flow_stage():
    assert all(position("completed") > position(s.name)
               for s in STAGES if s.kind == "flow")


def test_skips():
    assert is_skip("spec", "implement", ALL)
    assert not is_skip("spec", "implement", without("plan"))
    assert is_skip("spec", "completed", without("review", "qa"))
    assert not is_skip("qa", "completed", ALL)
    assert not is_skip("review", "spec", ALL)
    assert not is_skip("request", "discarded", ALL)


def test_the_records_gate_follows_the_last_round_stage_without_a_verdict():
    assert records_gate_stage(ALL) == "review"
    assert records_gate_stage(without("review")) == "qa"
    assert records_gate_stage(without("review", "qa")) == "completed"


def test_gates_for_a_target():
    assert gates_for("review", ALL) == ("records",)
    assert gates_for("completed", ALL) == ("completion",)
    assert gates_for("completed", without("review", "qa")) == (
        "completion", "records")
    assert gates_for("plan", ALL) == ()
