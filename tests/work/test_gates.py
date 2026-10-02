"""The records gate, the completion gate and drift (TCW-69 Design 7; AC 13, 14, 18)."""

from datetime import date

import pytest

from tcw.store.fs import FsCapabilitiesStore, FsProjectRegistry
from tcw.work.gates import (
    ABSENT, INHERITED, REMOVED, STILL_LOCAL, Declared, Present, Unchecked,
    completion_gate, drift_problems, ledger_reader, parse_declarations,
    records_gate, records_problems,
)
from tcw.work.layout import Layout
from tcw.work.model import STAGES, Item, Slug
from tests.test_capabilities_rm import repo, write_cap
from tests.work.fake_reader import FakeReader

ALL = frozenset(s.name for s in STAGES)
SLUG = Slug("tcw", "1-thing")


@pytest.fixture
def layout(tmp_path):
    return Layout(tmp_path / "work", ALL, frozenset())


def declare(layout, text, slug=SLUG):
    path = layout.capabilities_file(slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def write_round(layout, stage, n, text=""):
    path = layout.stage_dir(SLUG, stage) / f"round-{n}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def verdict(state, judges):
    return f"---\nverdict: {state}\njudges: {judges}\n---\n"


# -- declarations -----------------------------------------------------------

def test_a_missing_file_declares_nothing(layout):
    assert parse_declarations(layout.capabilities_file(SLUG)) == Declared()
    assert records_gate(layout, SLUG, FakeReader()) == []


def test_the_full_schema_parses(layout):
    declare(layout, "new: [a/b]\nchanged: [c]\nremoved: [d]\n"
                    "taxonomy:\n  new: [t1]\n  changed: [t2]\n  removed: [t3]\n")
    declared = parse_declarations(layout.capabilities_file(SLUG))
    assert declared == Declared(new=("a/b",), changed=("c",), removed=("d",),
                                term_new=("t1",), term_changed=("t2",),
                                term_removed=("t3",))


@pytest.mark.parametrize("text", [
    "added: [a]\n",                 # the 2.x alias is gone
    "new: a\n",
    "new: [1]\n",
    "taxonomy: [a]\n",
    "taxonomy:\n  renamed: [a]\n",
    "- a\n",
    "new: [a\n",                    # unreadable YAML
])
def test_a_malformed_file_fails_the_gate_and_the_mid_work_check(layout, text):
    declare(layout, text)
    assert isinstance(parse_declarations(layout.capabilities_file(SLUG)), str)
    assert records_gate(layout, SLUG, FakeReader())
    assert records_problems(layout, SLUG, FakeReader(), finished=False)


# -- the records gate (AC 13) -------------------------------------------------

@pytest.mark.parametrize("text, reader", [
    ("new: [x/y]\n", FakeReader()),
    ("new: [x/y]\n", FakeReader({"x/y": Present("Missing")})),
    ("changed: [x/y]\n", FakeReader()),
    ("removed: [x/y]\n", FakeReader(removals={"x/y": STILL_LOCAL})),
    ("removed: [x/y]\n", FakeReader(removals={"x/y": INHERITED})),
    ("taxonomy:\n  new: [term]\n", FakeReader()),
    ("taxonomy:\n  changed: [term]\n", FakeReader()),
    ("taxonomy:\n  removed: [term]\n", FakeReader(terms={"term": Present()})),
    ("new: [x/y]\n", FakeReader({"x/y": Unchecked("child unreachable")})),
    ("removed: [x/y]\n", FakeReader(removals={"x/y": Unchecked("no ledger")})),
    ("taxonomy:\n  new: [term]\n", FakeReader(terms={"term": Unchecked("bad")})),
])
def test_records_gate_failures(layout, text, reader):
    declare(layout, text)
    assert records_gate(layout, SLUG, reader)


def test_records_gate_passes_when_everything_is_in_the_records(layout):
    declare(layout, "new: [a]\nchanged: [b]\nremoved: [c]\n"
                    "taxonomy:\n  new: [t]\n  removed: [gone]\n")
    reader = FakeReader({"a": Present("Supported"), "b": Present("Missing")},
                        terms={"t": Present()})
    assert records_gate(layout, SLUG, reader) == []


def test_the_mid_work_check_reports_only_what_is_wrong_already(layout):
    declare(layout, "new: [not-yet]\nremoved: [inherited, still-here]\n")
    reader = FakeReader(removals={"inherited": INHERITED, "still-here": STILL_LOCAL})
    problems = records_problems(layout, SLUG, reader, finished=False)
    assert len(problems) == 1 and "inherited" in problems[0]
    assert len(records_gate(layout, SLUG, reader)) == 3


def test_an_unchecked_answer_is_reported_mid_work(layout):
    declare(layout, "new: [x]\n")
    reader = FakeReader({"x": Unchecked("project 'kid' is not reachable")})
    [problem] = records_problems(layout, SLUG, reader, finished=False)
    assert "not reachable" in problem


# -- the completion gate (AC 14) ----------------------------------------------

def test_completion_gate_needs_every_verdict_accepted(layout):
    assert completion_gate(layout, SLUG)                       # no review round
    write_round(layout, "implement", 1)
    write_round(layout, "review", 1, "no front matter")
    assert completion_gate(layout, SLUG)                       # invalid
    write_round(layout, "review", 2, verdict("accepted", 1))
    write_round(layout, "qa", 1, verdict("rejected", 1))
    assert completion_gate(layout, SLUG)                       # qa rejected
    write_round(layout, "qa", 2, verdict("accepted", 1))
    assert completion_gate(layout, SLUG) == []
    write_round(layout, "implement", 2)
    problems = completion_gate(layout, SLUG)                   # both stale now
    assert len(problems) == 2 and all("stale" in p for p in problems)


def test_completion_gate_names_the_round_to_write(layout):
    [problem, _] = completion_gate(layout, SLUG)
    assert "round-1.md" in problem


def test_an_external_verdict_stage_is_not_checked(tmp_path):
    layout = Layout(tmp_path, ALL, frozenset({"request", "qa"}))
    write_round(layout, "review", 1, verdict("accepted", 0))
    assert completion_gate(layout, SLUG) == []


def test_disabled_verdict_stages_are_not_checked(tmp_path):
    layout = Layout(tmp_path, ALL - {"review", "qa"}, frozenset())
    assert completion_gate(layout, SLUG) == []


# -- drift (AC 18) ------------------------------------------------------------

def item(folder, created):
    return Item(slug=Slug("tcw", folder), title=folder, stage="completed",
                created=created, priority="medium", effort=None,
                complexity=None, tags=(), assignee=None, parent=None,
                blocked_by=())


def test_drift(layout):
    first = item("1-first", date(2026, 1, 1))
    declare(layout, "new: [x/y]\n", first.slug)
    reader = FakeReader()
    [problem] = drift_problems(layout, [first], reader)
    assert "x/y" in problem and "1-first" in problem

    later = item("2-later", date(2026, 2, 1))
    declare(layout, "removed: [x/y]\n", later.slug)
    assert drift_problems(layout, [first, later], reader) == []

    earlier = item("0-earlier", date(2025, 12, 1))
    declare(layout, "removed: [x/y]\n", earlier.slug)
    assert len(drift_problems(layout, [first, earlier], reader)) == 1


def test_same_day_disagreement_is_ambiguous(layout):
    a, b = item("1-a", date(2026, 1, 1)), item("2-b", date(2026, 1, 1))
    declare(layout, "new: [x/y]\n", a.slug)
    declare(layout, "removed: [x/y]\n", b.slug)
    [problem] = drift_problems(layout, [a, b], FakeReader())
    assert "ambiguous" in problem


def test_a_changed_path_that_is_missing_is_not_drift(layout):
    a = item("1-a", date(2026, 1, 1))
    declare(layout, "changed: [x/y]\n", a.slug)
    assert drift_problems(layout, [a], FakeReader({"x/y": Present("Missing")})) == []
    declare(layout, "new: [x/y]\n", a.slug)
    assert drift_problems(layout, [a], FakeReader({"x/y": Present("Missing")}))


def test_drift_covers_removals_terms_and_unchecked(layout):
    a = item("1-a", date(2026, 1, 1))
    declare(layout, "removed: [gone]\ntaxonomy:\n  new: [t]\n  removed: [old]\n"
                    "changed: [far]\n", a.slug)
    reader = FakeReader({"far": Unchecked("unreachable")},
                        removals={"gone": STILL_LOCAL}, terms={"old": Present()})
    problems = drift_problems(layout, [a], reader)
    assert len(problems) == 4
    assert any("unchecked" in p for p in problems)


# -- the production reader ----------------------------------------------------

def production_reader(root):
    own = FsCapabilitiesStore.open(root)
    registry = FsProjectRegistry.open(root).require_valid()
    return ledger_reader(own, registry, registry.current.id,
                         open_child=lambda pid: f"no child {pid}", taxonomy=None)


def test_the_production_reader_reports_a_local_status(tmp_path):
    root = repo(tmp_path, "solo")
    write_cap(root, "x/y", id="cap-xy0001", Status="Missing")
    reader = production_reader(root)
    assert reader.capability("x/y") == Present("Missing")
    assert reader.capability("x/z") == ABSENT
    assert isinstance(reader.term("anything"), Unchecked)


def test_the_production_reader_answers_removals(tmp_path):
    root = repo(tmp_path, "solo")
    write_cap(root, "x/y", id="cap-xy0001", Status="Supported")
    reader = production_reader(root)
    assert reader.removal("x/y") == STILL_LOCAL
    assert reader.removal("x/gone") == REMOVED
