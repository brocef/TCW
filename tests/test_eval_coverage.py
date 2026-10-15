"""The eval test set, guarded against the two ways it rots.

A skill added to `skills/` with no eval case is silent partial coverage, which
is the exact failure this item exists to avoid. An assertion naming a predicate
the vocabulary never declared is an assertion the grader can never implement,
which is how axis B's assertions were written as free prose in the first draft.

`evals/coverage.py` is loaded by path rather than imported as `evals.coverage`,
so this guard does not depend on `evals/__init__.py` existing.
"""

import importlib.util
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

_spec = importlib.util.spec_from_file_location(
    "eval_coverage", REPO / "evals" / "coverage.py")
coverage = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(coverage)


def test_every_shipped_skill_is_covered_by_a_case_or_an_exclusion():
    uncovered = coverage.uncovered_skills()
    assert not uncovered, (
        "these skills ship but no eval case invokes them and no exclusion "
        f"accounts for them: {', '.join(sorted(uncovered))}. Add a case to "
        "evals/evals.json, or an entry with its reason to EXCLUSIONS in "
        "evals/coverage.py.")


def test_every_assertion_names_a_declared_predicate():
    undeclared = coverage.undeclared_predicates()
    assert not undeclared, (
        "these assertions name predicates the vocabulary does not declare: "
        f"{', '.join(sorted(undeclared))}. Either declare the predicate, or "
        "record the claim with an `unmechanized` marker if neither grader "
        "family can express it.")


def test_no_exclusion_is_also_covered_by_a_case():
    """An exclusion that a case also covers is a lie sitting in the file: it
    reads as a recorded decision not to measure something that is in fact
    measured, and nothing else would ever flag it."""
    data = coverage.load()
    dead = set(coverage.EXCLUSIONS) & coverage.covered_skills(data)
    assert not dead, (
        f"excluded but also covered by a case: {', '.join(sorted(dead))}")


def test_every_exclusion_and_partial_entry_names_a_shipped_skill():
    """A table entry for a skill that no longer ships, such as one deleted in
    TCW 3.0, reads as a recorded decision about something that is not there."""
    shipped = coverage.shipped_skills()
    stale = (set(coverage.EXCLUSIONS) | set(coverage.PARTIAL)) - shipped
    assert not stale, f"no such skill ships: {', '.join(sorted(stale))}"


# --- what TCW 3.0 removed stays out of the test set -----------------------

DELETED_SKILLS = ("post-mortem", "work-stage", "commands-verify-work")


def _cases():
    return coverage.load()["cases"]


def test_no_case_names_a_deleted_skill():
    for case in _cases():
        for key in ("skill", "invokes"):
            value = case.get(key)
            named = value if isinstance(value, list) else [value]
            for skill in DELETED_SKILLS:
                assert skill not in named, f"{case['id']} {key} names {skill}"


def test_no_case_asserts_a_status_flip_from_missing():
    """3.0 adds a capability record during implement with the status it then
    has; no step flips one from `Missing` later, so no assertion may expect
    one."""
    for case in _cases():
        for assertion in case["assertions"]:
            assert "Missing" not in json.dumps(assertion), (
                f"{case['id']}: {assertion}")


@pytest.mark.parametrize("predicate", ["git_order", "git_commit_per_artifact"])
def test_the_commit_predicates_are_gone(predicate):
    """They graded the commits 2.x made at each transition, which 3.0 does not
    make. Declared nowhere, implemented nowhere, used by no case."""
    data = coverage.load()
    assert predicate not in data["predicates"]
    assert not [c["id"] for c in data["cases"] for a in c["assertions"]
                if a.get("predicate") == predicate]
    for module in ("grade.py", "run_evals.py", "seed_fixture.py"):
        source = (REPO / "evals" / module).read_text(encoding="utf-8")
        assert predicate not in source, f"{predicate} in evals/{module}"


def test_b8_checks_the_declaration_not_a_record_count():
    """At planning an ability is declared in the item's capabilities.yaml, not
    recorded in the ledger."""
    case = next(c for c in _cases() if c["id"] == "B8")
    used = {a.get("predicate"): a.get("args") for a in case["assertions"]}
    assert "new_capability_count" not in used
    assert used["capabilities_declared"] == {"item": "new", "kind": "new",
                                             "count": 1}
    assert used["capability_records_added"] == {"count": 0}


def test_both_qa_cases_are_axis_a_and_ask_for_what_the_spec_names():
    """The default case expects a round with the agent's own verdict and one
    line per scenario; the person-decides case expects the scripted person's
    `rejected` and `decided-by`."""
    qa = {c["id"]: c for c in _cases() if c.get("stage") == "qa"}
    assert len(qa) == 2
    for case in qa.values():
        assert case["axis"] == "A"
        predicates = [a.get("predicate") for a in case["assertions"]]
        assert "round_front_matter" in predicates
    by_shape = {}
    for cid, case in qa.items():
        args = {a["predicate"]: a.get("args", {}) for a in case["assertions"]
                if "predicate" in a}
        by_shape["person" if "round_decided_by" in args else "default"] = (
            case, args)
    default, dargs = by_shape["default"]
    assert "round_lists_scenarios" in dargs
    assert default["arms"] == ["control"]
    person, pargs = by_shape["person"]
    assert pargs["round_verdict_is"]["verdict"] == "rejected"
    assert person["arms"] == ["customized"]
    assert "rejected" in person["prompt"]


# Commands, files and words 3.0 removed. A prompt or fixture text naming one
# tells the agent to do something that no longer exists.
REMOVED = [
    r"tcw work (start|submit|complete|drop|inbox|tracker|scaffold)\b",
    r"stage (gate|validate)\b",
    r"state\.yaml", r"Planning doc", r"--resolution",
    r"docs/work/(backlog|active|review|blocked|completed|discarded|inbox)\b",
    r"work\.lifecycle", r"refined-outcome\.md", r"\boutcome\.md",
]


def _fixture_texts():
    """Everything an agent can read that the harness wrote: every case's
    prompt and notes, the seeder's text, and the assets it copies in."""
    yield "evals/evals.json", (REPO / "evals/evals.json").read_text(
        encoding="utf-8")
    yield "evals/seed_fixture.py", (REPO / "evals/seed_fixture.py").read_text(
        encoding="utf-8")
    for asset in sorted((REPO / "evals/assets").iterdir()):
        if asset.is_file():
            yield f"evals/assets/{asset.name}", asset.read_text(encoding="utf-8")


@pytest.mark.parametrize("pattern", REMOVED)
def test_no_prompt_or_fixture_text_names_what_3_0_removed(pattern):
    hits = [f"{name}: {m.group(0)}" for name, text in _fixture_texts()
            for m in re.finditer(pattern, text)]
    assert not hits, hits
