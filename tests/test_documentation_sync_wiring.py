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
    SKILL_DIR / "references" / "cut-version.md",
]

# Claude-only slash commands are thin routers; the procedure they route to must
# live in the skill so a Codex user reaches it too (AGENTS.md harness rule).
COMMAND_ROUTES = {
    REPO / "commands" / "tcw-docs-sync-setup.md": "references/setup.md",
    REPO / "commands" / "tcw-cut-version.md": "references/cut-version.md",
}

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
    REPO / "skills" / "tcw-work" / "references" / "lifecycle" / "stage-plan.md",
    REPO / "skills" / "tcw-work" / "references" / "lifecycle" / "stage-implement.md",
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
    """The version-cut procedure lives in this skill's own `references/cut-version.md`
    (reachable without slash commands). It must not point at the external
    plugin-namespaced `…:cut-version` command it was absorbed from."""
    offenders = [
        f for f in SKILL_DIR.rglob("*.md")
        if ":cut-version" in f.read_text(encoding="utf-8")
    ]
    assert not offenders, f"stray :cut-version command reference: {offenders}"


def test_commands_route_into_the_skill():
    """Each slash command is a router: it must exist and name the skill reference
    that carries the procedure, so Codex (no slash commands) reaches the same
    content by invoking the skill directly."""
    for cmd, ref in COMMAND_ROUTES.items():
        assert cmd.is_file(), f"missing command: {cmd}"
        body = cmd.read_text(encoding="utf-8")
        assert "documentation-sync" in body, f"{cmd} does not name the skill"
        assert ref in body, f"{cmd} does not route to {ref}"


# ── which form the skill recommends ────────────────────────────────────────

def test_the_skill_presents_the_markdown_section_as_the_fallback():
    """`SKILL.md` and `references/setup.md` must agree on which form is
    recommended. `setup.md` already says "prefer config in a TCW project"; the
    section in `SKILL.md` that shows the Markdown format must not read as the
    default, or a project owner arriving at that heading sets up the legacy form
    without ever learning the config one exists.
    """
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    heading, _, body = skill.partition("## The Documentation Sync Section")
    assert body, "the section that documents the Markdown format has been renamed"
    intro = body.split("```", 1)[0]
    assert "fallback" in intro.lower(), (
        "the Markdown-section documentation must name itself the fallback:\n"
        f"{intro.strip()}")
    assert "tcw-config.yaml" in intro or "work docs" in intro, (
        "it must point at the recommended form, not just describe itself")


def test_the_skill_and_setup_reference_do_not_contradict_each_other():
    """Both name the config form as the recommended one."""
    setup = (SKILL_DIR / "references" / "setup.md").read_text(encoding="utf-8")
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    for name, text in (("setup.md", setup), ("SKILL.md", skill)):
        assert "work.documentation" in text, f"{name} never names the config form"
    # setup.md's framing is the one SKILL.md has to match.
    assert "prefer config" in setup.lower()
