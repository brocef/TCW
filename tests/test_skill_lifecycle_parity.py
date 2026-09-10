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
from tcw.work.resolve import load_builtins

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skills/tcw-work/SKILL.md"
REFS = REPO / "skills/tcw-work/references"

STAGE_IDS = tuple(s.id for s in LIFECYCLE_STEPS if s.kind == "stage")
TRANSITION_IDS = tuple(s.id for s in LIFECYCLE_STEPS if s.kind == "transition")

# Every stage is a router over a prompt the CLI prints, `inbox` included: it
# ships one too, reached by `tcw work stage prompt inbox` with no work item
# reference.
ROUTER_IDS = STAGE_IDS

STAGE_SECTIONS = ("Purpose", "Inputs", "Produce", "Steps", "Exit")
# Derived, never written out a second time: a router's `Exit` would restate the
# prompt's own `Exit badly` branches by construction, and nothing else differs.
ROUTER_SECTIONS = tuple(s for s in STAGE_SECTIONS if s != "Exit")
MARKERS = ("[auto]", "[gated]", "[prompted]", "[judgment]")

ROUTER_LINE_CEILING = 40

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
    return REFS / "lifecycle" / f"stage-{stage_id}.md"


# ── one document per id, and no orphans ──────────────────────────────────────

@pytest.mark.parametrize("stage_id", STAGE_IDS)
def test_every_stage_has_exactly_one_document(stage_id):
    assert stage_doc(stage_id).is_file(), f"missing stage-{stage_id}.md"


def test_no_stage_document_exists_for_an_unknown_id():
    found = {p.stem[len("stage-"):]
             for p in (REFS / "lifecycle").glob("stage-*.md")}
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
def test_every_stage_document_has_the_sections_in_order(stage_id):
    """Four sections, for all seven — the `Exit` section is the one shape that
    cannot survive the split, since "how this stage ends badly" is exactly the
    redirect material the prompt carries."""
    wanted = ROUTER_SECTIONS
    found = [h for h in sections(stage_doc(stage_id)) if h in STAGE_SECTIONS]
    assert found == list(wanted), \
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
    both harnesses can run. `--directive` is sugar, never the path.

    Two commands now, and the document has to carry both. `tcw work stage gate`
    is the only thing that refuses, and `tcw work stage prompt` is the only thing
    that answers "what do I do here" — resolving a binding *and* falling back to
    TCW's own instructions, for every stage, `inbox` included.

    Naming only the second would leave a Codex reader with no route to the gate,
    which is the failure this release's split makes possible: `prompt` never
    refuses, so nothing about wanting the instructions makes anyone run the gate.
    """
    text = stage_doc(stage_id).read_text(encoding="utf-8")
    for wanted in (f"tcw work stage gate {stage_id}",
                   f"tcw work stage prompt {stage_id}"):
        assert wanted in text, \
            f"stage-{stage_id}.md never names `{wanted}`"


# ── the routers stay routers ─────────────────────────────────────────────────

def _normalized_sentences(text: str) -> set[str]:
    """Sentences of eight or more words, comparable across two authors.

    Lowercased; Markdown emphasis (`*`, `_`, backticks) dropped; split on line
    boundaries and `.`/`!`/`?`; remaining punctuation removed and whitespace
    collapsed. Short fragments are excluded because headings, bare artifact
    names, and command lines are *addressing* — a router is supposed to share
    those with its prompt. Eight words is where a fragment becomes a claim.
    """
    text = re.sub(r"[*_`]", "", text.lower())
    out = set()
    for chunk in re.split(r"[.!?\n]", text):
        words = re.sub(r"[^a-z0-9 ]+", " ", chunk).split()
        if len(words) >= 8:
            out.add(" ".join(words))
    return out


@pytest.mark.parametrize("stage_id", ROUTER_IDS)
def test_no_router_sentence_appears_in_its_prompt(stage_id):
    """The literal-restatement guard. A router that copies a sentence out of the
    prompt reintroduces the version skew the split exists to remove — and the
    same author now writes both sides, which makes it likelier, not less."""
    shared = _normalized_sentences(stage_doc(stage_id).read_text(encoding="utf-8")) \
        & _normalized_sentences(load_builtins().stage_prompts[stage_id])
    assert not shared, (
        f"stage-{stage_id}.md and prompts/{stage_id}.md share a sentence — "
        f"fix whichever one should not have it: {sorted(shared)}")


@pytest.mark.parametrize("stage_id", ROUTER_IDS)
def test_each_router_stays_within_its_ceiling(stage_id):
    """The backstop behind the shared-sentence check: no test can catch a
    faithful paraphrase, but a router that paraphrased its whole prompt would
    not fit."""
    lines = len(stage_doc(stage_id).read_text(encoding="utf-8").splitlines())
    assert lines <= ROUTER_LINE_CEILING, \
        f"stage-{stage_id}.md is {lines} lines, ceiling is {ROUTER_LINE_CEILING}"


@pytest.mark.parametrize("stage_id", ROUTER_IDS)
def test_each_router_keeps_its_judgment(stage_id):
    """The other direction, and the reason there is no floor: a router reduced to
    a title and a command has deleted the skill-only material rather than routed
    to it. Delegability and the marker notation are both things the CLI does not
    and cannot say."""
    text = stage_doc(stage_id).read_text(encoding="utf-8")
    assert "delegable" in text.lower(), \
        f"stage-{stage_id}.md says nothing about delegability"
    assert any(m in text for m in MARKERS), \
        f"stage-{stage_id}.md carries no enforcement marker"


# ── no ordinals, no dangling routes ──────────────────────────────────────────

def test_no_reference_filename_carries_an_ordinal():
    """Ordinals recreate exactly the renumbering churn stable ids prevent."""
    bad = [p.name for p in REFS.rglob("*.md") if re.search(r"\d", p.stem)]
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
    # Matched by path relative to `references/`, not bare name: a link written
    # `references/lifecycle/stage-spec.md` has to count as reaching the file,
    # and two files in different folders may legitimately share a name.
    orphans = [rel for rel in sorted(p.relative_to(REFS).as_posix()
                                     for p in REFS.rglob("*.md"))
               if rel not in text]
    assert not orphans, f"unreachable from SKILL.md: {orphans}"


# ── the composing skills ─────────────────────────────────────────────────────
#
# Six documents compose a stage out of `cat <router>` + `tcw work stage prompt`:
# the generic `tcw-work-stage`, which takes the stage id as an argument, and one
# `tcw-work-stage-<stage>` per stage a person actually drives, which bakes it in.
#
# Every property below held for one file before the five shipped. Each is now
# parametrised over all six, because a guard that covers one of six near-identical
# documents has stopped being a guard.

STAGE_SKILL = REPO / "skills/tcw-work-stage/SKILL.md"

# Derived from STAGE_IDS, never written out as a second list — a stage added to
# the lifecycle shows up here rather than being silently skipped. Only the two
# exclusions are hand-written, and each is excluded for a reason that would have
# to stop being true before it gets a skill:
#   inbox      — runs before an item exists and takes no work item reference on
#                either verb, so a per-stage skill would wrap a zero-argument
#                command and add nothing.
#   postmortem — already has `tcw-post-mortem`, with a read-only agent behind it;
#                a second skill for the stage would compete with it.
NO_PER_STAGE_SKILL = {"inbox", "postmortem"}
PER_STAGE_IDS = tuple(s for s in STAGE_IDS if s not in NO_PER_STAGE_SKILL)
PER_STAGE_SKILLS = {s: REPO / f"skills/tcw-work-stage-{s}/SKILL.md"
                    for s in PER_STAGE_IDS}

# The generic skill keyed by None: it has no single stage, and every parametrised
# test below has to say what it does differently for that case anyway.
COMPOSING_SKILLS = {None: STAGE_SKILL, **PER_STAGE_SKILLS}


def _composing(stage):
    """The path for a stage id, or for the generic skill when `stage` is None."""
    return COMPOSING_SKILLS[stage]


composing = pytest.mark.parametrize(
    "stage", sorted(COMPOSING_SKILLS, key=lambda s: s or ""),
    ids=lambda s: s or "generic")


def test_the_per_stage_skills_are_exactly_the_stages_that_get_one():
    """Both directions. A stage in `PER_STAGE_IDS` with no file is a skill that
    was planned and never written; a `skills/tcw-work-stage-*/` directory with no
    matching stage is one that appeared without the exclusion list being
    revisited — most likely `postmortem`, whose exclusion is a judgement call
    someone will eventually want to reverse. Reversing it should mean editing
    `NO_PER_STAGE_SKILL`, not just adding a folder.

    The glob discriminates on its own: every per-stage skill carries the
    `tcw-work-stage-` prefix and the generic skill does not match it.
    """
    missing = sorted(s for s, p in PER_STAGE_SKILLS.items() if not p.is_file())
    assert not missing, f"stages with no skill file: {missing}"
    on_disk = {p.parent.name.removeprefix("tcw-work-stage-")
               for p in REPO.glob("skills/tcw-work-stage-*/SKILL.md")}
    assert on_disk == set(PER_STAGE_IDS), (
        f"skills on disk {sorted(on_disk)} disagree with the stages that get one "
        f"{sorted(PER_STAGE_IDS)}; excluded deliberately: {sorted(NO_PER_STAGE_SKILL)}")


@pytest.mark.parametrize("stage", PER_STAGE_IDS)
def test_a_per_stage_skill_takes_the_item_alone(stage):
    """The whole point of splitting the generic skill. `arguments: [stage, item]`
    made the caller restate a stage they already knew, and forced the item to be
    supplied positionally after it; `arguments: [item]` leaves one argument, and
    an omitted one interpolates to the empty string, which the CLI accepts."""
    front = _composing(stage).read_text().split("---")[1]
    args = next(l for l in front.splitlines() if l.startswith("arguments:"))
    assert args.strip() == "arguments: [item]", args
    assert "$stage" not in _composing(stage).read_text(), (
        f"tcw-work-stage-{stage} still interpolates a stage argument")


@composing
def test_the_composing_skill_reads_a_router_that_exists(stage):
    """Each of these skills names a router path. Nothing at runtime checks it —
    a failed `cat` is swallowed by `|| true` so the rest of the skill still
    renders, which is the right behaviour and also the reason a rename would go
    unnoticed. Resolve the path here instead.

    The generic skill's path is a template holding `$stage`, so it is resolved
    against every stage id; a per-stage skill's names one stage literally and is
    checked once. Same property, two shapes.
    """
    body = _composing(stage).read_text()
    m = re.search(r'cat "\$\{CLAUDE_PLUGIN_ROOT\}/(\S+?)"', body)
    assert m, "the skill no longer cats a router out of the plugin root"
    template = m.group(1)
    if stage is None:
        assert "$stage" in template, template
        targets = {s: REPO / template.replace("$stage", s) for s in STAGE_IDS}
    else:
        assert f"stage-{stage}.md" in template, (
            f"tcw-work-stage-{stage} cats {template}, not its own stage router")
        targets = {stage: REPO / template}
    for stage_id, target in targets.items():
        assert target.is_file(), f"{stage_id}: {target} does not exist"


@composing
def test_the_composing_skill_names_the_gate_in_its_own_prose(stage):
    """The whole hazard of composing a stage out of `prompt`: it resolves the
    instructions without the gate. A skill that stopped naming `gate` would be
    a documented route around the legality check and the `pre` bindings.

    **Fenced blocks are stripped before the assertion**, and that is the point of
    this test rather than an implementation detail. It once searched the whole
    body, which worked while the literal appeared exactly once, in the prose
    warning. A later change added the same line to the manual-fallback fence —
    an example of what to run by hand, not a warning — and the guard stopped
    biting: the entire warning could be deleted with this test still green.
    Neither change was wrong on its own, which is why nothing caught it.
    """
    slot = "$stage" if stage is None else stage
    body = _composing(stage).read_text()
    assert f"tcw work stage prompt {slot} $item" in body
    prose = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
    assert f"tcw work stage gate {slot} $item" in prose, (
        "the skill names the gate only inside its manual-fallback fence, so the "
        "prose warning against routing around the gate can be deleted freely")


@composing
def test_every_injected_command_survives_its_own_failure(stage):
    """The second of two ways this skill renders empty, and the one that shipped
    unguarded.

    A non-zero exit from an injected command aborts the whole invocation: the
    model is shown nothing at all, not an error, and not the static body either.
    That is indistinguishable from the skill not existing, which is exactly why
    it needs a test rather than a reader noticing. `|| true` is what keeps a
    missing router or any CLI error from blanking the page.

    The sibling test covers the other cause, an undeclared command.
    """
    body = _composing(stage).read_text()
    injected = re.findall(r"^!`(.+)`$", body, flags=re.MULTILINE)
    assert injected, "the skill no longer injects any command"
    for cmd in injected:
        assert cmd.rstrip().endswith("|| true"), (
            f"injected command renders the whole skill empty if it exits "
            f"non-zero: {cmd}")


@composing
def test_the_composing_skill_declares_the_commands_it_injects(stage):
    """An injected command that is not pre-approved aborts the whole skill
    invocation — the model is shown nothing at all, not an error. Both commands
    have to be in `allowed-tools` or the skill silently renders empty."""
    body = _composing(stage).read_text()
    front = body.split("---")[1]
    allowed = next(l for l in front.splitlines() if l.startswith("allowed-tools:"))
    assert "Bash(tcw *)" in allowed and "Bash(cat *)" in allowed, allowed
