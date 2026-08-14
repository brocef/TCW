"""The `tcw-work` skill must agree with `LIFECYCLE_STEPS`.

This is the guard the lifecycle epic exists to install. The two documents it
replaces — `task-lifecycle.md` and `epic-lifecycle.md` — were ~85% identical and
had already drifted from each other and from the code, and nothing noticed
because nothing checked. Prose describing a tool is only trustworthy if something
fails when it stops being true.

**What this can and cannot check.** It checks structure and artifact names
against the machine-readable table: one document per id, no orphans, `Produce`
and `Inputs` covering what the table says, five sections in order, every step
marked. It does **not** check that a step's marker is *correct* —
`LIFECYCLE_STEPS` records gates, not procedures, so there is nothing to compare a
procedure against. Claiming otherwise would be the same dishonesty the epic is
removing.
"""
import re
from pathlib import Path

import pytest

from tcw.store.base import LIFECYCLE_STEPS, LIFECYCLE_STEPS_BY_ID

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skills/tcw-work/SKILL.md"
REFS = REPO / "skills/tcw-work/references"

STAGE_IDS = tuple(s.id for s in LIFECYCLE_STEPS if s.kind == "stage")
TRANSITION_IDS = tuple(s.id for s in LIFECYCLE_STEPS if s.kind == "transition")

STAGE_SECTIONS = ("Purpose", "Inputs", "Produce", "Steps", "Exit")
MARKERS = ("[auto]", "[gated]", "[prompted]", "[judgment]")

# Retired by this restructure. A dangling route is worse than the duplication it
# replaced, so their names must not survive anywhere in the repository.
DELETED = ("lifecycle.md", "task-lifecycle.md", "epic-lifecycle.md",
           "process-inbox.md")

SKILL_LINE_BUDGET = 60


def sections(path: Path) -> dict[str, str]:
    """Split a Markdown file on `## ` headings, preserving order."""
    out: dict[str, str] = {}
    current = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            out[current] = ""
        elif current is not None:
            out[current] += line + "\n"
    return out


def artifacts_in(text: str) -> set[str]:
    """Every `<name>.md` mentioned in a chunk of text."""
    return set(re.findall(r"\b([a-z][a-z0-9-]*\.md)\b", text))


def stage_doc(stage_id: str) -> Path:
    return REFS / f"stage-{stage_id}.md"


# ── one document per id, and no orphans ──────────────────────────────────────

@pytest.mark.parametrize("stage_id", STAGE_IDS)
def test_every_stage_has_exactly_one_document(stage_id):
    assert stage_doc(stage_id).is_file(), f"missing stage-{stage_id}.md"


def test_no_stage_document_exists_for_an_unknown_id():
    found = {p.stem[len("stage-"):] for p in REFS.glob("stage-*.md")}
    assert found == set(STAGE_IDS), f"orphaned or missing: {found ^ set(STAGE_IDS)}"


@pytest.mark.parametrize("transition_id", TRANSITION_IDS)
def test_every_transition_has_a_section_in_transitions_md(transition_id):
    heads = sections(REFS / "transitions.md")
    assert any(transition_id in h for h in heads), \
        f"transitions.md has no section for '{transition_id}'"


# ── the documents agree with the table ───────────────────────────────────────

@pytest.mark.parametrize("stage_id", STAGE_IDS)
def test_produce_names_every_artifact_the_table_lists(stage_id):
    """`inbox` produces none and `verify` produces one of two — both are values,
    not exceptions. The table is the source; the document must cover it.

    Filenames, matched against the set `artifacts_in()` returns rather than
    substring-searched in the body: the tuple holds *extensionless* names, and
    `"spec" in body` passes against `specification` and the bare word "spec".

    Subset, not equality: three Produce sections legitimately name an artifact
    they do not produce — `stage-inbox.md` explains that `inbox accept` preserves
    the entry as `intake.md` while producing no lifecycle artifact, and
    `stage-request.md` and `stage-plan.md` cross-reference `rollup.md` and
    `epic-deltas.md`. The subset direction is the one that catches a real defect.
    """
    step = LIFECYCLE_STEPS_BY_ID[stage_id]
    named = artifacts_in(sections(stage_doc(stage_id))["Produce"])
    wanted = {f"{n}.md" for n in step.produces}
    assert wanted <= named, \
        f"stage-{stage_id}.md 'Produce' omits {', '.join(sorted(wanted - named))}"


@pytest.mark.parametrize("stage_id", STAGE_IDS)
def test_inputs_names_every_artifact_the_table_lists(stage_id):
    """The section most likely to drift: it grows quietly as an author remembers
    one more thing a stage reads."""
    step = LIFECYCLE_STEPS_BY_ID[stage_id]
    body = sections(stage_doc(stage_id))["Inputs"]
    for artifact in step.inputs:
        assert artifact in body, \
            f"stage-{stage_id}.md 'Inputs' omits {artifact}"


def test_a_stage_producing_nothing_says_so_explicitly():
    """Silence and "produces nothing" are different claims, and only one of them
    is useful to an agent deciding whether it is finished."""
    body = sections(stage_doc("inbox"))["Produce"].lower()
    assert "no lifecycle artifact" in body


# ── shape ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("stage_id", STAGE_IDS)
def test_every_stage_document_has_the_five_sections_in_order(stage_id):
    found = [h for h in sections(stage_doc(stage_id)) if h in STAGE_SECTIONS]
    assert found == list(STAGE_SECTIONS), \
        f"stage-{stage_id}.md sections are {found}"


@pytest.mark.parametrize("stage_id", STAGE_IDS)
def test_every_stage_document_marks_its_steps(stage_id):
    body = sections(stage_doc(stage_id))["Steps"]
    assert any(m in body for m in MARKERS), \
        f"stage-{stage_id}.md 'Steps' carries no enforcement marker"


@pytest.mark.parametrize("stage_id", STAGE_IDS)
def test_no_unrecognized_marker_is_used(stage_id):
    """A typo'd marker is worse than a missing one: it reads as enforcement that
    does not exist."""
    text = stage_doc(stage_id).read_text(encoding="utf-8")
    used = set(re.findall(r"\[(auto|gated|prompted|judgment|[a-z]+)\]", text))
    unknown = used - {"auto", "gated", "prompted", "judgment"}
    # Markdown links are `[text](url)`; exclude anything followed by `(`.
    unknown = {u for u in unknown if not re.search(rf"\[{u}\]\(", text)}
    assert not unknown, f"stage-{stage_id}.md uses unknown marker(s): {unknown}"


@pytest.mark.parametrize("stage_id", STAGE_IDS)
def test_every_stage_document_names_the_harness_neutral_binding_command(stage_id):
    """Codex receives no context injection, so every stage must carry the command
    both harnesses can run. `--directive` is sugar, never the path."""
    text = stage_doc(stage_id).read_text(encoding="utf-8")
    assert "tcw work lifecycle" in text, \
        f"stage-{stage_id}.md never tells the agent how to find its bindings"


# ── no ordinals, no dangling routes ──────────────────────────────────────────

def test_no_reference_filename_carries_an_ordinal():
    """Ordinals recreate exactly the renumbering churn stable ids prevent."""
    bad = [p.name for p in REFS.glob("*.md") if re.search(r"\d", p.stem)]
    assert not bad, f"ordinal in filename(s): {bad}"


@pytest.mark.parametrize("name", DELETED)
def test_no_reference_to_a_deleted_document_survives(name):
    hits = []
    for path in REPO.rglob("*.md"):
        parts = set(path.parts)
        if parts & {".git", "node_modules", "build", ".venv", ".worktrees"}:
            continue
        rel = str(path.relative_to(REPO))
        # Archives, not routes. A work item or a shipped changelog naming a file
        # that existed at the time is a true historical statement; rewriting
        # history to keep a grep clean is worse than the grep.
        if rel.startswith(("docs/work/", "docs/changelogs/", "docs/release-notes/")):
            continue
        if name in path.read_text(encoding="utf-8") and path.name != name:
            hits.append(str(path.relative_to(REPO)))
    assert not hits, f"'{name}' is deleted but still referenced by: {hits}"


# ── the router ───────────────────────────────────────────────────────────────

def test_the_router_stays_within_its_line_budget():
    """`SKILL.md` loads on every use of the skill, so its size is a recurring
    cost paid forever. The rule on breach is extract, never grow."""
    all_lines = SKILL.read_text(encoding="utf-8").splitlines()
    # Frontmatter is required metadata, not prose — budget the body it precedes.
    body = all_lines[all_lines.index("---", 1) + 1:]
    lines = len(body)
    assert lines <= SKILL_LINE_BUDGET, \
        f"SKILL.md body is {lines} lines, budget is {SKILL_LINE_BUDGET} — extract, don't grow"


@pytest.mark.parametrize("stage_id", STAGE_IDS)
def test_the_router_routes_to_every_stage_document(stage_id):
    assert f"stage-{stage_id}.md" in SKILL.read_text(encoding="utf-8"), \
        f"SKILL.md never routes to stage-{stage_id}.md"


def test_the_router_routes_to_every_reference_file():
    """An unreachable reference file is dead weight that still costs a reader
    the time to wonder whether it matters."""
    text = SKILL.read_text(encoding="utf-8")
    orphans = [p.name for p in sorted(REFS.glob("*.md")) if p.name not in text]
    assert not orphans, f"unreachable from SKILL.md: {orphans}"
