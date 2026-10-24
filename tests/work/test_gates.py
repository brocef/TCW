"""The records gate, the completion gate and drift (TCW-69 Design 7; AC 13, 14, 18)."""

from datetime import date

import pytest

from tcw.store.fs import FsCapabilitiesStore, FsProjectRegistry
from tcw.work.gates import (
    ABSENT, REMOVED, STILL_LOCAL, Declared, Invalid, Present, Route,
    Unchecked, completion_gate, drift_problems, parse_declarations, project_reader,
    records_gate, records_problems, route_capability_path,
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
    declare(layout, "new: [not-yet]\nremoved: [unchecked, still-here]\n")
    reader = FakeReader(removals={"unchecked": Unchecked("no ledger"),
                                  "still-here": STILL_LOCAL})
    problems = records_problems(layout, SLUG, reader, finished=False)
    assert len(problems) == 1 and "no ledger" in problems[0]
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
    [problem] = completion_gate(layout, SLUG)      # review is still checked
    assert problem.startswith("review:")
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
    assert (problem.kind, problem.where) == ("drift", "x/y")
    assert "1-first" in problem.message
    assert str(problem).startswith("drift: x/y: ")

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
    assert problem.kind == "ambiguous"


def test_a_changed_path_that_is_missing_is_not_drift(layout):
    a = item("1-a", date(2026, 1, 1))
    declare(layout, "changed: [x/y]\n", a.slug)
    assert drift_problems(layout, [a], FakeReader({"x/y": Present("Missing")})) == []
    declare(layout, "new: [x/y]\n", a.slug)
    assert drift_problems(layout, [a], FakeReader({"x/y": Present("Missing")}))


def test_a_new_among_the_newest_declarations_keeps_the_missing_check(layout):
    a, b = item("1-a", date(2026, 1, 1)), item("2-b", date(2026, 1, 1))
    declare(layout, "new: [x/y]\n", a.slug)
    declare(layout, "changed: [x/y]\n", b.slug)
    assert drift_problems(layout, [a, b], FakeReader({"x/y": Present("Missing")}))


def test_one_item_declaring_both_ways_is_not_called_two_items(layout):
    a = item("1-a", date(2026, 1, 1))
    declare(layout, "new: [x/y]\nremoved: [x/y]\n", a.slug)
    [problem] = drift_problems(layout, [a], FakeReader())
    assert problem.kind == "ambiguous" and "same day" not in problem.message
    assert "tcw.work/1-a" in problem.message


def test_drift_covers_removals_terms_and_unchecked(layout):
    a = item("1-a", date(2026, 1, 1))
    declare(layout, "removed: [gone]\ntaxonomy:\n  new: [t]\n  removed: [old]\n"
                    "changed: [far]\n", a.slug)
    reader = FakeReader({"far": Unchecked("unreachable")},
                        removals={"gone": STILL_LOCAL}, terms={"old": Present()})
    problems = drift_problems(layout, [a], reader)
    assert len(problems) == 4
    assert {p.kind for p in problems} == {"drift", "unchecked"}
    assert any(p.where == "term old" for p in problems)


# -- the production reader (TCW-110 Design 6.2, AC 11, 12, 23) ---------------

def production_reader(root):
    return project_reader(root, FsProjectRegistry.open(root).require_valid())


def test_the_production_reader_reports_a_local_status(tmp_path):
    root = repo(tmp_path, "solo")
    write_cap(root, "x/y", Status="Missing")
    reader = production_reader(root)
    assert reader.capability("solo.capabilities/x/y") == Present("Missing")
    assert reader.capability("solo.capabilities/x/z") == ABSENT
    assert isinstance(reader.term("solo.taxonomy/anything"), Unchecked)


def test_the_production_reader_answers_removals(tmp_path):
    root = repo(tmp_path, "solo")
    write_cap(root, "x/y", Status="Supported")
    reader = production_reader(root)
    assert reader.removal("solo.capabilities/x/y") == STILL_LOCAL
    assert reader.removal("solo.capabilities/x/gone") == REMOVED


@pytest.mark.parametrize("ask, entry", [
    ("capability", "x/y"), ("removal", "x/y"), ("term", "t"),
    ("capability", "core/x/y"), ("term", "core/t"),
])
def test_ac11_a_3x_entry_is_invalid_naming_tcw_migrate(tmp_path, ask, entry):
    root = repo(tmp_path, "solo")
    answer = getattr(production_reader(root), ask)(entry)
    assert isinstance(answer, Invalid)
    assert "TCW 3.x reference" in answer.reason and "tcw migrate" in answer.reason


def test_ac11_the_records_gate_refuses_a_3x_entry(tmp_path, monkeypatch, capsys):
    from tcw.cli import main
    from tests.work.projects import make_project, write_item
    root = make_project(tmp_path, "p")
    folder = write_item(root, "2026-10-01-a", {"title": "a", "stage": "implement"})
    (folder / "implement").mkdir()
    (folder / "implement" / "round-1.md").write_text("Done.\n")
    (folder / "capabilities.yaml").write_text("changed: [cli/x]\n")
    monkeypatch.chdir(root)
    code = main(["work", "advance", "2026-10-01-a", "--dry-run"])
    out = "".join(capsys.readouterr())
    assert code == 3, out
    assert "cli/x: 'cli/x' is a TCW 3.x reference" in out and "tcw migrate" in out


@pytest.fixture
def app_and_server(tmp_path):
    """`app` with a child `server` holding the capability `x`."""
    from tcw.store.fs import init
    from tests.projectfiles import connect_projects
    from tests.work.projects import make_project
    app = make_project(tmp_path, "app")
    server = make_project(tmp_path, "server")
    init(["capabilities"], app)
    init(["capabilities"], server)
    write_cap(server, "x", Status="Supported")
    connect_projects(app, "children", "server")
    connect_projects(server, "parent", "app")
    return app, server


def test_ac12_an_entry_is_read_from_its_projects_ledger(app_and_server):
    app, _ = app_and_server
    reader = production_reader(app)
    assert reader.capability("server.capabilities/x") == Present("Supported")
    assert reader.capability("app.capabilities/x") == ABSENT
    assert reader.removal("server.capabilities/x") == STILL_LOCAL


def test_ac12_a_project_not_on_this_machine_could_not_be_checked(app_and_server):
    import shutil
    app, server = app_and_server
    shutil.rmtree(server)
    assert isinstance(production_reader(app).capability("server.capabilities/x"),
                      Unchecked)


def test_an_unknown_project_is_invalid(app_and_server):
    app, _ = app_and_server
    answer = production_reader(app).capability("servr.capabilities/x")
    assert isinstance(answer, Invalid) and "check the spelling" in answer.reason


def test_a_project_with_no_ledger_says_to_name_the_ledgers_project(tmp_path):
    from tests.work.projects import make_project
    root = make_project(tmp_path, "p")
    answer = production_reader(root).capability("p.capabilities/x")
    assert isinstance(answer, Unchecked)
    assert answer.reason == ("this project ('p') keeps no capabilities ledger; name the "
                             "ledger's project in the entry (<project>.capabilities/x)")


@pytest.fixture
def app_overriding_core(tmp_path):
    """TCW-112 AC 31: `core`'s `cli/x` is `Missing`; `app` inherits it and
    has its own `cli/x` at the same path, holding only `Status: Supported`."""
    from tests.test_capabilities_rm import connect
    core = repo(tmp_path, "core")
    write_cap(core, "cli/x", Status="Missing", body="Core body")
    app = repo(tmp_path, "app")
    connect(app, core)
    write_cap(app, "cli/x", complete=False, Status="Supported")
    return core, app


def test_ac31_every_entry_routes_to_its_owners_own_ledger(app_overriding_core):
    """TCW-112 Design 7.1: whether or not `app` inherits from `core`."""
    from tcw.ids import FullId
    from tcw.locate import Locator
    _, app = app_overriding_core
    own = FsCapabilitiesStore.open(app)
    route = route_capability_path("core.capabilities/cli/x", own=own,
                                  project_id="app", locator=Locator.of(app),
                                  project_root=app)
    assert route.full_id == FullId("core", "capabilities", "cli/x")
    assert route.store.project_id == "core" and route.store is not own


def test_ac31_the_gate_reads_each_owners_own_object(app_overriding_core, layout):
    _, app = app_overriding_core
    reader = production_reader(app)
    assert reader.capability("app.capabilities/cli/x") == Present("Supported")
    assert reader.capability("core.capabilities/cli/x") == Present("Missing")
    declare(layout, "changed: [app.capabilities/cli/x]\n")
    assert records_gate(layout, SLUG, reader) == []
    declare(layout, "new: [core.capabilities/cli/x]\n")
    [problem] = records_gate(layout, SLUG, reader)
    assert "still Missing" in problem


def test_ac31_a_removed_override_passes_though_the_original_exists(app_overriding_core,
                                                                   layout):
    _, app = app_overriding_core
    FsCapabilitiesStore.open(app).reset("cli/x")
    reader = production_reader(app)
    assert reader.removal("app.capabilities/cli/x") == REMOVED
    assert reader.capability("app.capabilities/cli/x") == ABSENT
    declare(layout, "removed: [app.capabilities/cli/x]\n")
    assert records_gate(layout, SLUG, reader) == []


def test_ac31_an_owner_not_on_this_machine_is_not_checked_never_absent(
        app_overriding_core, layout):
    import shutil
    core, app = app_overriding_core
    shutil.rmtree(core)
    reader = production_reader(app)
    assert isinstance(reader.capability("core.capabilities/cli/x"), Unchecked)
    declare(layout, "changed: [core.capabilities/cli/x]\n")
    [problem] = records_gate(layout, SLUG, reader)
    assert "could not be checked" in problem and "not in the ledger" not in problem


def test_ac31_an_own_override_whose_parent_is_missing_is_not_checked(
        app_overriding_core):
    """Its combined Status needs `core` (Design 7.1): unchecked, not absent."""
    import shutil
    core, app = app_overriding_core
    shutil.rmtree(core)
    assert isinstance(production_reader(app).capability("app.capabilities/cli/x"),
                      Unchecked)
    assert production_reader(app).removal("app.capabilities/cli/x") == STILL_LOCAL


def test_a_term_of_a_project_not_extended_is_read_from_its_own_taxonomy(tmp_path):
    from tests.inherit import entry
    from tests.projectfiles import connect_projects
    from tests.work.projects import make_project
    from tcw.store.fs import init
    app = make_project(tmp_path, "app", config={})
    core = make_project(tmp_path, "core", config={})
    init(["taxonomy"], core)
    entry(core, "taxonomy", "term")
    connect_projects(app, "parent", "core", inherit="none")
    reader = production_reader(app)
    assert reader.term("core.taxonomy/term") == Present()
    assert reader.term("core.taxonomy/missing") == ABSENT


def test_a_term_of_a_project_not_on_this_machine_could_not_be_checked(tmp_path):
    import shutil
    from tests.projectfiles import write_manifest
    from tests.work.projects import make_project
    app = make_project(tmp_path, "app", config={})
    make_project(tmp_path, "core", config={})
    write_manifest(app, {"core": "../core"})
    shutil.rmtree(tmp_path / "core")
    assert isinstance(production_reader(app).term("core.taxonomy/term"), Unchecked)


@pytest.mark.parametrize("text", ["new: [x/y]\n", "changed: [x/y]\n", "removed: [x/y]\n",
                                  "taxonomy:\n  removed: [t]\n"])
def test_every_list_reports_a_3x_entry_even_mid_work(tmp_path, text):
    root = repo(tmp_path, "solo")
    layout = Layout(tmp_path / "work", ALL, frozenset())
    declare(layout, text)
    [problem] = records_problems(layout, SLUG, production_reader(root), finished=False)
    assert "TCW 3.x reference" in problem and "tcw migrate" in problem
