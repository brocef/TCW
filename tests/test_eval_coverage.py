"""The eval test set, guarded against the two ways it rots.

A skill added to `skills/` with no eval case is silent partial coverage, which
is the exact failure this item exists to avoid. An assertion naming a predicate
the vocabulary never declared is an assertion the grader can never implement,
which is how axis B's assertions were written as free prose in the first draft.

`evals/coverage.py` is loaded by path rather than imported as `evals.coverage`,
so this guard does not depend on `evals/__init__.py` existing.
"""

import importlib.util
from pathlib import Path

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
