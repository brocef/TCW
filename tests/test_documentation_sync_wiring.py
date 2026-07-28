"""The documentation-sync skill exists and is wired in, not dangling.

`tcw validate` only resolves `tcw://` markdown links, so it can't catch a stale
`skill-cefailures` reference or a missing skill file. This is that guard: the
skill's files exist, no `skill-cefailures` reference survives the absorption, and
the tcw-work lifecycle actually invokes the skill (positive check — an absence
grep alone would stay green if a rewire were skipped).
"""
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

SKILL_DIR = REPO / "skills" / "documentation-sync"
SKILL_FILES = [
    SKILL_DIR / "SKILL.md",
    SKILL_DIR / "references" / "release-notes-and-changelogs.md",
    SKILL_DIR / "references" / "setup.md",
]

# Absorption must leave no dangling reference to the source plugin here.
NO_CEFAILURES_ROOTS = [
    REPO / "AGENTS.md",
    REPO / "README.md",
    REPO / "skills",
    REPO / ".claude-plugin",
    REPO / ".codex-plugin",
]

# The two stages where AGENTS.md requires the skill: `plan` names a task per
# trigger expected to fire, and `implement` evaluates them before the work is
# reported complete. Retargeted from the retired task/epic lifecycle documents.
LIFECYCLE_REFS = [
    REPO / "skills" / "tcw-work" / "references" / "stage-plan.md",
    REPO / "skills" / "tcw-work" / "references" / "stage-implement.md",
]


def _md_files(root: Path):
    if root.is_dir():
        yield from root.rglob("*.md")
        yield from root.rglob("*.json")
    else:
        yield root


def test_skill_files_exist():
    for f in SKILL_FILES:
        assert f.is_file(), f"missing documentation-sync skill file: {f}"


def test_no_skill_cefailures_references():
    offenders = [
        f
        for root in NO_CEFAILURES_ROOTS
        for f in _md_files(root)
        if "skill-cefailures" in f.read_text(encoding="utf-8")
    ]
    assert not offenders, f"stale skill-cefailures references: {offenders}"


# The exact invocation phrase, present only after the rewire. The bare word
# "documentation-sync" is NOT sufficient — both lifecycle files already contained
# it pre-rewire ("documentation-sync expectations" / "explicit documentation-sync
# tasks"), so asserting the word alone would pass even if the rewire were reverted.
INVOKE_PHRASE = "invoke the `documentation-sync` skill"


def test_lifecycle_invokes_documentation_sync():
    """Positive check: the rewire landed. Both lifecycle references must invoke
    the skill by name, or a skipped gate would pass the absence check above."""
    for ref in LIFECYCLE_REFS:
        assert INVOKE_PHRASE in ref.read_text(encoding="utf-8"), (
            f"{ref} does not invoke the documentation-sync skill"
        )


def test_skill_has_no_cut_version_command_ref():
    """The absorbed skill defers to the project's version-cut process; it must not
    resurrect the external `:cut-version` command reference."""
    offenders = [
        f for f in SKILL_DIR.rglob("*.md")
        if ":cut-version" in f.read_text(encoding="utf-8")
    ]
    assert not offenders, f"stray :cut-version command reference: {offenders}"
