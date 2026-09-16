"""No skill points into another skill's `references/` by path.

A pointer to another skill's document names the skill and the document in
words ("the `configure` skill's `docs-sync.md`"). The eval routing checks
look for these paths in the tool calls an agent makes, so a path written into
some other skill's text could be matched by an agent that only read that text
rather than opening the document.
"""
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SKILLS = REPO / "skills"


@pytest.mark.parametrize("owner", ("setup", "configure"))
def test_only_the_owning_skill_names_its_reference_paths(owner):
    needle = f"{owner}/references/"
    hits = sorted(
        str(p.relative_to(REPO))
        for p in SKILLS.rglob("*")
        if p.is_file() and not p.is_relative_to(SKILLS / owner)
        and needle in p.read_text(encoding="utf-8", errors="replace"))
    assert not hits, f"{needle} appears outside skills/{owner}/: {hits}"
