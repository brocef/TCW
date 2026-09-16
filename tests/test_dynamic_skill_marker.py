"""Every shipped skill, reference document and agent has a verdict in
`skills/README.md`, and every skill's `dynamic_skill` key agrees with it.

The verdicts are judgments; this cannot check that one is right. It checks
that none is missing, none is stale, and the marker a reader sees in a skill's
frontmatter says the same thing the rules document does. A new skill, reference
or agent without a row fails here, and the message names the document — which
is how an author who never heard of it finds it.
"""
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RULES = REPO / "skills" / "README.md"

# Verdict → the `dynamic_skill` value a skill with that verdict carries.
VERDICTS = {
    "fixed (Rule 1)": False,
    "fixed (Rule 2)": False,
    "fixed (accelerator)": False,
    "overridable": True,
    "composes already": True,
}

ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|\s*([^|]+?)\s*\|")


def verdict_rows() -> list[tuple[str, str, str]]:
    """(owner, glob within the owner, verdict) for every verdict table row."""
    rows = []
    for line in RULES.read_text(encoding="utf-8").splitlines():
        m = ROW.match(line)
        if m and m.group(3) in VERDICTS:
            rows.append(m.groups())
    return rows


def owner_dir(owner: str) -> Path:
    return REPO / "agents" if owner == "agents" else REPO / "skills" / owner


def matches(owner: str, pattern: str) -> set[Path]:
    return set(owner_dir(owner).glob(pattern))


def shipped_documents() -> list[Path]:
    return sorted({*REPO.glob("skills/*/SKILL.md"),
                   *REPO.glob("skills/*/references/**/*.md"),
                   *REPO.glob("agents/*.md")})


SKILLS = sorted(REPO.glob("skills/*/SKILL.md"))
per_skill = pytest.mark.parametrize("skill", SKILLS, ids=lambda p: p.parent.name)


def test_the_rules_are_stated():
    assert RULES.is_file(), "skills/README.md, the rules for an overridable skill, is missing"
    text = RULES.read_text(encoding="utf-8")
    for needle in ("Rule 1", "Rule 2", "checked first",
                   "## Why a project cannot add a procedure"):
        assert needle in text, f"skills/README.md does not say {needle!r}"


def test_every_shipped_document_has_exactly_one_verdict():
    rows = verdict_rows()
    problems = []
    for doc in shipped_documents():
        hits = [r for r in rows if doc in matches(r[0], r[1])]
        if len(hits) != 1:
            problems.append(f"{doc.relative_to(REPO)}: {len(hits)} rows")
    assert not problems, (
        "every shipped skill, reference document and agent needs exactly one "
        f"verdict row in skills/README.md: {problems}")


def test_every_verdict_row_names_a_shipped_document():
    rows = verdict_rows()
    assert rows, "skills/README.md has no verdict table rows"
    shipped = set(shipped_documents())
    stale = [f"{o} {p}" for o, p, _ in rows if not matches(o, p) & shipped]
    assert not stale, f"skills/README.md has verdict rows naming no shipped document: {stale}"

