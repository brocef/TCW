"""The runner's bookkeeping, which nothing else would catch.

The runner is the orchestrator: it selects cases, decides which contrast applies,
builds the isolation map, and aggregates what came back. If it silently drops a
transcript or miscounts a capped run, every reading is wrong in the same
direction and a human reading the pass rate would never see it. The plan's first
draft shipped it with no test at all.

Nothing here spawns an agent. The one thing that cannot be tested without
spending money — whether the isolation map really suppresses the plugins — was
settled by probe and is recorded in the plan.
"""

import json

import pytest

from evals import run_evals


@pytest.fixture(scope="module")
def cases():
    return run_evals.load_cases()


# --- the test set parses, and says what the runner needs ------------------

def test_every_case_declares_what_the_runner_reads(cases):
    for case in cases:
        assert case["axis"] in run_evals.MAX_TURNS, case["id"]
        assert case["arms"], case["id"]
        assert case["prompt"], case["id"]


def test_axis_a_arms_are_fixture_variants_and_axis_b_arms_are_the_toggle(cases):
    """The two axes ask different questions and therefore contrast different
    things. Getting this backwards would run axis A against one fixture and
    measure nothing at all."""
    for case in cases:
        if case["axis"] == "A":
            assert set(case["arms"]) <= {"customized", "control"}, case["id"]
        else:
            assert set(case["arms"]) == {"with-skill", "no-skill"}, case["id"]


# --- which fixture, and which invocation ----------------------------------

def test_axis_a_arms_pick_opposite_fixture_variants():
    case = {"axis": "A"}
    assert run_evals.variant_for(case, "customized") is True
    assert run_evals.variant_for(case, "control") is False


def test_axis_b_holds_the_fixture_constant_across_its_arms():
    """Axis B toggles the plugin. If it also swapped the fixture, its two arms
    would differ by two things and the delta would mean nothing."""
    case = {"axis": "B"}
    assert run_evals.variant_for(case, "with-skill") is True
    assert run_evals.variant_for(case, "no-skill") is True


def test_only_the_axis_b_baseline_drops_the_plugin(tmp_path):
    settings = tmp_path / "settings.json"
    flag = "--plugin-dir"

    a_control = run_evals.command({"axis": "A", "prompt": "x"}, "control", settings)
    assert flag in a_control, "axis A holds the skill in both arms"

    b_with = run_evals.command({"axis": "B", "prompt": "x"}, "with-skill", settings)
    b_without = run_evals.command({"axis": "B", "prompt": "x"}, "no-skill", settings)
    assert flag in b_with
    assert flag not in b_without


def test_the_plugin_comes_from_this_checkout_not_the_marketplace_clone(tmp_path):
    """Enabling `tcw@tcw` would load the published clone, a different commit
    with auto-update on. The treatment arm must name this checkout instead, and
    `tcw@tcw` must be among the keys forced false."""
    argv = run_evals.command({"axis": "A", "prompt": "x"}, "customized",
                             tmp_path / "s.json")
    assert argv[argv.index("--plugin-dir") + 1] == str(run_evals.REPO)
    assert "tcw@tcw" not in [a for a in argv]
    assert run_evals.isolation_map().get("tcw@tcw") is False


def test_the_isolation_map_unions_every_settings_file(tmp_path, monkeypatch):
    """Plugin enablement is split across files. Reading one of them leaks the
    other's plugins into both arms, which is what the plan's first draft would
    have done."""
    user = tmp_path / "user.json"
    project = tmp_path / "project.json"
    user.write_text(json.dumps({"enabledPlugins": {"alpha@m": True}}))
    project.write_text(json.dumps({"enabledPlugins": {"beta@m": True}}))
    monkeypatch.setattr(run_evals, "SETTINGS_FILES", (user, project))

    assert run_evals.isolation_map() == {"alpha@m": False, "beta@m": False}


def test_the_isolation_map_survives_a_missing_or_unreadable_settings_file(
        tmp_path, monkeypatch):
    present = tmp_path / "present.json"
    present.write_text(json.dumps({"enabledPlugins": {"alpha@m": True}}))
    broken = tmp_path / "broken.json"
    broken.write_text("{ not json")
    monkeypatch.setattr(run_evals, "SETTINGS_FILES",
                        (present, broken, tmp_path / "absent.json"))

    assert run_evals.isolation_map() == {"alpha@m": False}


# --- the prompt's item reference ------------------------------------------

def test_the_item_placeholder_resolves_to_a_minted_slug():
    """Slugs carry today's date and are minted by the CLI, so a case names which
    fixture item it addresses and the manifest says what it was called."""
    manifest = {"items": {"backlog": "2026-01-01-a"},
                "stage_items": {"spec": "2026-01-01-a"}}
    case = {"prompt": "Work the spec stage for {item}.", "item": "backlog",
            "stage": "spec"}
    assert run_evals.prompt_for(case, manifest) == (
        "Work the spec stage for 2026-01-01-a.")


def test_an_unresolved_placeholder_never_reaches_a_real_invocation(cases):
    """A prompt still carrying `{item}` would ask an agent to work on a work item
    literally called `{item}`, and the case would fail for a reason that has
    nothing to do with what it measures."""
    manifest = {"items": {k: f"slug-{k}" for k in
                          ("backlog", "active", "completed")},
                "stage_items": {s: f"slug-{s}" for s in
                                ("spec", "plan", "implement", "verify",
                                 "postmortem")}}
    for case in cases:
        assert "{item}" not in run_evals.prompt_for(case, manifest), case["id"]


# --- isolation, read from the init event ----------------------------------

def _init(paths):
    return {"plugins": [{"path": p, "name": "tcw"} for p in paths]}


def test_a_clean_treatment_arm_reports_no_problems():
    problems = run_evals.check_isolation(
        {"axis": "A"}, "customized", _init([str(run_evals.REPO)]))
    assert problems == []


def test_a_leaked_foreign_plugin_is_reported():
    problems = run_evals.check_isolation(
        {"axis": "A"}, "customized",
        _init([str(run_evals.REPO), "/somewhere/else"]))
    assert problems, "a second plugin in the treatment arm went unreported"


def test_the_marketplace_clone_would_be_reported_rather_than_accepted():
    """The exact failure the probe ruled out. If a future change reintroduced
    it, this is what says so."""
    clone = "/Users/somebody/.claude/plugins/marketplaces/tcw"
    problems = run_evals.check_isolation({"axis": "A"}, "customized",
                                         _init([clone]))
    assert problems and clone in problems[0]


def test_a_baseline_arm_holding_any_plugin_is_reported():
    problems = run_evals.check_isolation({"axis": "B"}, "no-skill",
                                         _init([str(run_evals.REPO)]))
    assert problems


def test_a_baseline_arm_with_no_plugins_is_clean():
    assert run_evals.check_isolation({"axis": "B"}, "no-skill",
                                     {"plugins": []}) == []


# --- aggregation ----------------------------------------------------------

def _entry(**kw):
    base = {"arm": "customized", "exit_status": 0, "capped": False,
            "cost_usd": 1.0, "wall_seconds": 2.0, "num_turns": 3}
    return {**base, **kw}


def test_a_capped_run_leaves_the_denominator():
    """A budget limit and a skill defect are different findings. Folding a capped
    run into the pass rate reads the first as the second."""
    report = run_evals.aggregate([
        _entry(), _entry(capped=True), _entry(),
    ])
    arm = report["arms"]["customized"]
    assert arm["runs"] == 3
    assert arm["capped"] == 1
    assert arm["graded"] == 2


def test_a_failure_is_counted_apart_from_a_cap():
    report = run_evals.aggregate([_entry(exit_status=1), _entry(capped=True)])
    arm = report["arms"]["customized"]
    assert arm["failed"] == 1
    assert arm["capped"] == 1
    assert arm["graded"] == 1


def test_arms_are_totalled_separately():
    report = run_evals.aggregate([
        _entry(arm="with-skill", cost_usd=2.0),
        _entry(arm="no-skill", cost_usd=0.5),
    ])
    assert report["arms"]["with-skill"]["cost_usd"] == 2.0
    assert report["arms"]["no-skill"]["cost_usd"] == 0.5


def test_a_run_that_produced_no_result_event_does_not_crash_aggregation():
    """A killed or crashed run has no `result` event, so its cost and turn count
    are absent. Aggregation has to survive that rather than lose the whole
    batch."""
    report = run_evals.aggregate([_entry(cost_usd=None, num_turns=None)])
    arm = report["arms"]["customized"]
    assert arm["runs"] == 1
    assert arm["cost_usd"] == 0.0


# --- selection ------------------------------------------------------------

def test_selection_filters_by_axis_and_by_case(cases):
    assert {c["axis"] for c in run_evals.select(cases, "a", None)} == {"A"}
    assert [c["id"] for c in run_evals.select(cases, None, ["a1"])] == ["A1"]
    assert run_evals.select(cases, "a", ["B1"]) == []
