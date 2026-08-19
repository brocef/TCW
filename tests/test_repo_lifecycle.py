"""This repository's own `work.lifecycle` configuration.

Unlike every other suite here these run against the real repo tree rather than a
`tmp_path` fixture, because what is under test *is* this node's configuration —
a copy in a fixture would be testing the copy.

The load-bearing one is `test_repo_templates_carry_every_builtin_heading`.
`artifacts:` is first-match-wins, so a bound template **replaces** the built-in
rather than extending it; this repo's `spec` template therefore restates
`tcw.work.templates._SPEC`'s sections, and nothing but this test stops the two
drifting apart when a future release adds a section to the built-in.
"""

from pathlib import Path

import pytest
import yaml

import tcw.work.templates as templates
from tcw.store.base import parse_lifecycle_policy

REPO = Path(__file__).resolve().parent.parent
LIFECYCLE = REPO / "docs" / "lifecycle"


def _headings(text: str) -> set[str]:
    return {line.strip() for line in text.splitlines() if line.startswith("## ")}


@pytest.fixture(scope="module")
def policy():
    raw = yaml.safe_load((REPO / "tcw-config.yaml").read_text())
    policy, problems = parse_lifecycle_policy(raw["work"]["lifecycle"])
    assert problems == []
    return policy


def test_the_repo_config_parses_with_no_problems():
    """The advisory problem list, which `tcw validate` surfaces and
    `lifecycle_policy()` discards. Empty is the only acceptable answer for the
    repository that ships the parser."""
    raw = yaml.safe_load((REPO / "tcw-config.yaml").read_text())
    _, problems = parse_lifecycle_policy(raw["work"]["lifecycle"])
    assert problems == []


def test_repo_templates_carry_every_builtin_heading():
    """The drift guard. Catches a built-in gaining a section; does not catch one
    changing its guidance text, which is a known ceiling rather than an
    oversight."""
    builtin = _headings(templates._SPEC)
    for name in ("spec.md", "spec-bug.md"):
        mine = _headings((LIFECYCLE / "templates" / name).read_text())
        assert builtin <= mine, f"{name} is missing {sorted(builtin - mine)}"


def test_the_plan_stage_has_no_bound_template(policy):
    """Deliberate. A `plan` template was written, came out identical to the
    built-in, and was dropped: binding an unchanged copy takes on drift for no
    gain. Asserted so nobody re-adds one without changing it."""
    assert "plan" not in policy.artifacts


def test_every_bound_file_exists_and_says_something(policy):
    refs = [b.ref
            for group in (*policy.stages.values(), *policy.artifacts.values())
            for b in (group.prompt if hasattr(group, "prompt") else group)
            if b.kind == "file"]
    assert refs, "no file: bindings — this test is guarding nothing"
    for ref in refs:
        path = REPO / ref
        assert path.is_file(), f"bound file does not exist: {ref}"
        assert path.read_text().strip(), f"bound file is empty: {ref}"


def test_the_moved_rules_are_reachable():
    """What makes deleting the prose from AGENTS.md safe. The litmus test is
    this repo's prime directive and is cited from module docstrings; it has to
    live somewhere a citation can point."""
    text = (LIFECYCLE / "abstraction.md").read_text()
    assert "Could a non-filesystem store implement this operation" in text
    assert "Abstract spine, filesystem leverage" in text
    assert "don't pre-abstract" in (LIFECYCLE / "implementation.md").read_text()
    assert "Agentskills specification" in (LIFECYCLE / "harness.md").read_text()


# ── this repository's own documentation entries ──────────────────────────────

def test_this_repos_documentation_entries_parse():
    """Acceptance criterion 11. The four entries that used to be a Markdown
    bullet list in `AGENTS.md` are now configuration `tcw validate` checks."""
    from tcw.store.base import parse_documentation_entries
    config = yaml.safe_load((REPO / "tcw-config.yaml").read_text(encoding="utf-8"))
    entries, problems = parse_documentation_entries(
        config["work"]["documentation"])
    assert problems == []
    assert [e.path for e in entries] == [
        "README.md",
        "docs/release-notes/upcoming.md",
        "docs/changelogs/upcoming.md",
        "skills/<component>/SKILL.md",
    ]
    assert {e.trigger for e in entries} == {
        "Public-API", "Any-Code-Change", "Skill-Driven-Component"}


def test_the_agent_guide_no_longer_carries_the_entry_list():
    """The migration the previous item could not finish. The *section* stays —
    it explains why the entries exist — but the entries themselves are config."""
    guide = (REPO / "AGENTS.md").read_text(encoding="utf-8")
    for trigger in ("[Public-API]", "[Any-Code-Change]", "[Skill-Driven-Component]"):
        assert trigger not in guide, f"{trigger} still listed in AGENTS.md"


def test_a_path_placeholder_survives_this_repos_own_config():
    """`skills/<component>/SKILL.md` is a pattern, not a resolvable path.
    Requiring entry paths to exist would reject the node that wrote the rule."""
    from tcw.store.fs import FsWorkStore
    entries = FsWorkStore.open(REPO).documentation()
    assert any("<component>" in e.path for e in entries)
