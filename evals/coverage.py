"""The derived coverage gate for the eval test set.

The case table is not hand-kept prose. This module enumerates the skills that
actually ship, subtracts the ones the test set names, subtracts an explicit
exclusion list, and reports whatever is left. A hand-kept table is how the Codex
plugin manifest came to undercount its own skills with no test noticing, and
this item's whole purpose is defeated by silent partial coverage.

It also checks the second thing the test set can rot in: every assertion must
name a predicate the vocabulary declares, so assertions stay data and the grader
stays finite. An assertion that cannot be expressed mechanically carries an
`unmechanized` marker instead, and is skipped here by design — recording the
claim honestly is the point of the marker.

Run it directly to see both answers:

    python evals/coverage.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVALS = Path(__file__).with_name("evals.json")

# The same predicate every guard in tests/test_plugin_manifests.py uses
# (`:106`, `:130`). A bare directory under skills/ is not a skill and trips
# nothing — which is why the mutation check for this gate has to add a file.
SKILL_GLOB = "*/SKILL.md"

EXCLUSIONS = {
    "tcw-extras-autonomous-work":
        "It drives whole work items unattended through other skills, spawning "
        "advisor subagents and a `codex exec` call per checkpoint. A case would "
        "cost a full multi-item run to grade, and would mostly re-measure the "
        "skills it delegates to.",
    **{name: "Composes `work` stage documents that axis A measures, and has "
             "no case of its own yet."
       for name in ("commands-plan-work",
                    "commands-drive-work-to-completion",
                    "commands-verify-work",
                    "commands-process-inbox")},
}

# Not exclusions. A skill a case names counts as covered, but a directory-level
# gate cannot express that only some of its routes are measured, so the
# unmeasured routes are recorded here rather than left to look like clean
# coverage.
PARTIAL = {
    "work-stage":
        "Axis A covers the spec, plan, implement and verify routes. The "
        "`request` route is unmeasured: `request` is the one stage whose job is "
        "asking the user questions, which a non-interactive harness cannot do. "
        "There is no axis A request case to cover it.",
    "configure":
        "B11 measures the documentation-entries route only. `work.md`, "
        "`tracker.md`, `stores.md` and `projects.md` are unmeasured.",
    "setup":
        "B12 measures the new-repository route (`project.md`) only. "
        "Install and repair stay unmeasured: faking a broken `tcw` install "
        "inside a subagent's environment is unsafe and would measure the "
        "simulation. `taxonomy.md` and `capabilities.md` ask the user "
        "questions, which a non-interactive harness cannot answer, the same "
        "reason the `request` stage is unmeasured. Provisioning a project set "
        "up elsewhere needs a remote repository.",
}


def load() -> dict:
    return json.loads(EVALS.read_text(encoding="utf-8"))


def shipped_skills() -> set[str]:
    """Every skill directory that actually ships."""
    return {p.parent.name for p in (REPO / "skills").glob(SKILL_GLOB)}


def covered_skills(data: dict) -> set[str]:
    """Skills the test set names, via `invokes` and `skill`.

    `invokes` is a string, or a list where a case genuinely spans several
    skills (B8). `skill` carries non-skill values such as `cross-axis`, which
    simply subtract nothing.
    """
    named: set[str] = set()
    for case in data["cases"]:
        for key in ("invokes", "skill"):
            value = case.get(key)
            named.update(value if isinstance(value, list) else [value] if value else [])
    return named


def uncovered_skills() -> set[str]:
    """Shipped skills that no case invokes and no exclusion accounts for."""
    return shipped_skills() - covered_skills(load()) - set(EXCLUSIONS)


def undeclared_predicates() -> set[str]:
    """Predicate names used by an assertion but absent from the vocabulary."""
    data = load()
    used = {
        a["predicate"]
        for case in data["cases"]
        for a in case["assertions"]
        if "predicate" in a
    }
    return used - set(data["predicates"])


def _report() -> int:
    uncovered = uncovered_skills()
    undeclared = undeclared_predicates()

    print(f"shipped skills: {len(shipped_skills())}")
    for name, reason in sorted(EXCLUSIONS.items()):
        print(f"  excluded  {name}: {reason}")
    for name, reason in sorted(PARTIAL.items()):
        print(f"  partial   {name}: {reason}")

    if uncovered:
        print(f"\nUNCOVERED: {', '.join(sorted(uncovered))}")
    else:
        print("\nevery shipped skill is covered by a case or an exclusion")

    if undeclared:
        print(f"UNDECLARED PREDICATES: {', '.join(sorted(undeclared))}")
    else:
        print("every assertion names a declared predicate")

    return 1 if (uncovered or undeclared) else 0


if __name__ == "__main__":
    sys.exit(_report())
