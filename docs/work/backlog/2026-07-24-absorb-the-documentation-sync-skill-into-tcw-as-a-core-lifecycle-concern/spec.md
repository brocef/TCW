# Spec — Absorb the documentation-sync skill into TCW

## Capability changes

**None.** This work is instruction-only: it adds an agent-facing skill and process docs and rewires
internal references. It does not change the `tcw` CLI surface, any store-interface method, or any
user-facing product behavior. No taxonomy Vocabulary/Feature delta and no capability ledger delta;
the tcw-capabilities planning gate is therefore N/A. (Confirmed against the abstraction litmus test:
nothing here becomes a store operation — doc-sync is agent behavior layered above the model.)

## Problem

TCW's documentation-sync behavior is **borrowed, not owned**:

- `AGENTS.md:49` tells agents to invoke the external `skill-cefailures:documentation-sync` skill.
- `skills/tcw-work/references/task-lifecycle.md:60,135` and `epic-lifecycle.md:49,98` say only
  "evaluate Documentation Sync triggers" / "documentation-sync expectations" — they name the step but
  own none of its meaning.

So TCW depends on an unrelated plugin for a step it wants to treat as core to its own work lifecycle.
If `skill-cefailures` is absent, renamed, or diverges, TCW's lifecycle guidance dangles.

## Goals

1. TCW owns a `documentation-sync` skill under `skills/`, ported and adapted from the source.
2. The `tcw-work` lifecycle invokes it at two gates — **plan-time** and **completion-time** — as an
   explicit handoff, mirroring the existing `tcw-work → tcw-capabilities` pattern.
3. All in-repo references point at the TCW-owned skill; the `skill-cefailures` dependency is gone.
4. The absorbed skill stays portable: its version guidance defers generically to "the project's
   version-cut process" (TCW's `scripts/cut_version.py` pointer stays in `AGENTS.md ## Versioning`),
   and it replaces the FOLLOWUPS.md pattern with "create a `tcw work` backlog item."

## Non-goals

- No new `tcw` subcommand; no CLI-enforced doc-sync gate (`tcw work complete` stays byte-identical).
- No port of the external `:cut-version` command (TCW already owns `scripts/cut_version.py`).
- No port of the FOLLOWUPS.md pattern.
- No edits to the `skill-cefailures` repo from here (tracked as a separate follow-up; see below).

## Current-state findings

- **Trigger vocabulary mismatch.** The source skill defines four triggers (`Public-API`,
  `Public-{Name}-API`, `Any-Code-Change`, `Only-Breaking`). But TCW's own section
  (`AGENTS.md:51-54`) already uses a **fifth, project-defined trigger**: `[Skill-Driven-Component]`.
  The absorbed skill must therefore treat the four as a **base vocabulary that projects may extend**
  with their own named triggers (defined inline in their Documentation Sync section) — and should call
  out `Skill-Driven-Component` as TCW's own example, so the skill and `AGENTS.md` don't contradict.
- **Two places enumerate skills — both must move.** `README.md:712-742` ("Skills — the judgment
  layer") lists "**five skills**" by name and frames them as CLI drivers ("They name `tcw …` commands
  … never reimplement tool logic"). **`.codex-plugin/plugin.json:22`** (`longDescription`) is a
  *second, parallel* enumeration: "ships **five skills** — the three axis drivers … tcw-plugin … and
  tcw-report — driving the tcw CLI." Both carry the same two problems: a stale count and a CLI-driver
  framing that mis-describes a **cross-cutting process skill**. Adding documentation-sync requires
  updating *both*. Nothing catches drift here: `tests/test_plugin_manifests.py` guards only version
  agreement, not the skill list.
  - **Count-free framing (optional soften):** `.claude-plugin/plugin.json:4` and
    `.claude-plugin/marketplace.json:10` say "skills that drive the tcw CLI" — no count, so they don't
    lie, but the framing is now slightly off. Low stakes; soften opportunistically alongside the README.
  - **Do NOT touch:** `docs/changelogs/v0.11.1.md:17` (a **frozen released** changelog that mentions
    "all five skills") and the `2026-07-22-evaluate-and-refine-the-plugin-skills…` backlog spec (a
    **different** work item). Both match a naive `grep "five skills"` and are explicitly out of scope.
- **No test enumerates skills.** `grep` of `tests/` finds nothing keyed on `skills/`, `SKILL.md`, or a
  skills manifest. Adding a skill folder breaks no existing test. `.claude-plugin/plugin.json` points
  `"skills": "./skills/"` (a directory), so no per-skill registration is needed.
- **TCW already owns the downstream structure.** `docs/release-notes/upcoming.md`,
  `docs/changelogs/upcoming.md`, `scripts/cut_version.py`, and the `## Versioning` section
  (`AGENTS.md:56+`) exist. The absorbed release-notes/changelogs guidance describes structure TCW
  already uses; it just gives TCW an owned reference for it and must point version-cutting at the
  script, not the external command.
- **CLAUDE.md is a symlink to AGENTS.md** (`CLAUDE.md -> AGENTS.md`). The portable skill text can say
  "the project's CLAUDE.md"; for TCW that resolves to AGENTS.md.

## Proposed behavior

### New skill: `skills/documentation-sync/`

A thin router plus on-demand references, per `AGENTS.md:45` skill-authoring rules.

- **`SKILL.md`** (router, always-relevant judgment inline):
  - What a `## Documentation Sync` section is and the invoke-before-complete directive.
  - **Trigger reference** table: the four base triggers + the partition rule + the public-surface
    judgment call, **plus** an explicit "projects may define additional named triggers" note using
    TCW's `Skill-Driven-Component` as the worked example.
  - The evaluation loop (read trigger → assess change → update or skip).
  - Plan-integration guidance (named-file tasks for concrete scope; one re-evaluation gate for
    exploratory scope).
  - "When to offer version/changelog options" — the four options. To keep the skill **portable**, the
    bump path stays generic: "use the project's version-cut process (see its CLAUDE.md / Versioning
    section)" — do **not** hardcode `scripts/cut_version.py` into the skill body. The TCW-specific
    `scripts/cut_version.py` pointer lives only in `AGENTS.md ## Versioning`, where it already is
    (avoids duplicating that guidance and smuggling a TCW path into a reusable skill). Keep-current
    updates the `upcoming.md` files in place.
  - Companion-doc gates (release-notes reference; setup reference).
  - Common-mistakes table (trigger-evaluation slips).
- **`references/release-notes-and-changelogs.md`** (read on demand): RN-vs-changelog distinction,
  entry + hash-range format, version cross-check, existing-project migration offers. Adapted: the
  rotation/version-cut steps defer generically to "the project's version-cut process" (not a hardcoded
  path), keeping the reference portable.
- **`references/setup.md`** (read on demand): how to scaffold a `## Documentation Sync` section into a
  project's CLAUDE.md and create tracked files/dirs that don't exist. Adapted: **drop FOLLOWUPS.md**;
  where the source offered a FOLLOWUPS log, instead recommend `tcw work new "<deferred item>"`.

Keep the skill **portable** (generic "any project's CLAUDE.md" framing) so other projects installing
the TCW plugin can adopt doc-sync — not narrowed to TCW's own AGENTS.md.

### Lifecycle integration (`tcw-work`)

Tighten the loose pointers into explicit handoffs (one-line invoke, not an inlined trigger loop):

- `task-lifecycle.md` §3 (plan) and §closeout, `epic-lifecycle.md` plan + completion: replace
  "evaluate Documentation Sync triggers" with "invoke the `documentation-sync` skill to evaluate
  triggers" at the **plan** gate (surface predicted doc tasks in `plan.md`) and the **completion**
  gate (before `tcw work complete`).

### Rewiring

**Ordering:** create `skills/documentation-sync/` *first*, then rewire the references that point at it,
so no reference dangles at any commit (it all lands together, but sequence create-before-rewire).

- `AGENTS.md:49`: point the directive at TCW's own skill instead of `skill-cefailures:documentation-sync`.
- `README.md:712-742`: add the sixth skill entry; change "five skills" → "six skills"; soften the
  CLI-driver framing so it admits one cross-cutting process skill. Concretely, the closing line
  "They name `tcw …` commands … never reimplement tool logic" becomes something like: *"The five axis/
  plugin skills name `tcw …` commands and never reimplement tool logic; documentation-sync is a
  cross-cutting process skill that governs when docs must move with code."* (Exact wording is the
  implementer's, but it must stop asserting that *all* skills drive the CLI.)
- `.codex-plugin/plugin.json:22` (`longDescription`): update "ships five skills" → "six", add
  documentation-sync to the enumeration, and adjust the "driving the tcw CLI" tail so it doesn't
  mis-describe the process skill.
- `.claude-plugin/plugin.json:4` and `.claude-plugin/marketplace.json:10` (optional, low-stakes):
  soften "skills that drive the tcw CLI" for consistency; no count to fix.
- **Third lifecycle touchpoint (uniformity):** `task-lifecycle.md:131` ("documentation updates still
  needed," in the closeout decision list) — optionally point it at the skill too so closeout guidance
  is uniform with the two primary gates.

## Acceptance criteria

- `skills/documentation-sync/SKILL.md` + the two references exist, self-consistent, with **zero**
  references to `skill-cefailures`, `:cut-version`, or `FOLLOWUPS.md` (except, at most, a one-line
  "TCW uses `tcw work` items instead of a FOLLOWUPS log" note).
- The skill's trigger reference documents `Skill-Driven-Component` (or the "projects may add named
  triggers" mechanism that covers it) so it agrees with `AGENTS.md`.
- `grep -rn "skill-cefailures" AGENTS.md skills/ README.md .claude-plugin/ .codex-plugin/` returns
  nothing (broadened to the plugin manifests, not just README/skills).
- **Skill count + framing reconciled everywhere it appears:** README (`five`→`six` + softened framing)
  **and** `.codex-plugin/plugin.json:22` (`five`→`six` + documentation-sync added). Frozen changelog
  `docs/changelogs/v0.11.1.md` and the other backlog spec are left untouched.
- `tcw-work` lifecycle references invoke the `documentation-sync` skill by name at plan + completion gates.
- **Regression guard added** — since `tcw validate` only resolves `tcw://` markdown links (not skill
  invocations or plugin-description consistency), add one small pytest (alongside `test_plugin_manifests.py`)
  asserting: `skills/documentation-sync/SKILL.md` exists; no `skill-cefailures` string remains in
  `AGENTS.md`, `README.md`, `skills/`, or the two `*-plugin` manifests. (This is the one runnable check
  for the rewire; it directly guards the reviewers' reference-integrity concern.)
- `tcw validate` passes; full existing test suite passes.
- Doc-sync self-application for this very change: changelog updated; README (Public-API) updated;
  release-notes evaluated; version option offered at closeout.

## Open decisions (recommendations; confirm at plan review)

1. **Skill folder name:** `documentation-sync` (recommended — it's a cross-cutting process skill, not a
   `tcw`-axis driver) vs. `tcw-documentation-sync` (matches the existing `tcw-*` folder convention).
   Invoked as `tcw:documentation-sync` either way. **Lean: `documentation-sync`.**
2. **Setup shape:** `references/setup.md` only (recommended — lazier, reached by a gate condition) vs.
   also a `/tcw-...` slash command in `commands/` for discoverability. **Lean: reference only.**
3. **Lifecycle binding tightness:** one-line "invoke documentation-sync" handoff (recommended, matches
   tcw-capabilities) vs. inlining the trigger loop into lifecycle prose. **Lean: one-line handoff.**

## Risks / dependencies

- **Trigger-vocabulary drift** between the skill and `AGENTS.md` if `Skill-Driven-Component` isn't
  reconciled — the top correctness risk; acceptance criteria pin it.
- **README framing** — dropping a non-CLI skill into a "these drive the CLI" list reads wrong if the
  framing isn't softened.
- **Naming collision** with `skill-cefailures:documentation-sync` while both are installed — harmless
  (plugin-namespaced); resolved once the separate follow-up removes the source.
- No code/model dependency; independent of the other backlog items.

## Related follow-up (separate repo)

Open a work item / GitHub issue on `github.com/brocef/skill-cefailures` to remove or deprecate its
`documentation-sync` skill once TCW's copy lands. Not actionable as a `tcw work` item in this repo
(skill-cefailures is not a TCW node). Decide at closeout whether to file it now.

## Documentation Sync impact (for the plan)

- `docs/changelogs/upcoming.md` [Any-Code-Change] — **fires**: new skill + AGENTS.md/lifecycle rewire.
- `README.md` [Public-API] — **fires**: skills list changes. (The `.codex-plugin` / `.claude-plugin`
  description edits are part of this same public-surface change, not a separate trigger.)
- `docs/release-notes/upcoming.md` [Public-API] — evaluate; likely a light entry or none (agent-facing,
  not end-user CLI behavior).
- `skills/<component>/SKILL.md` [Skill-Driven-Component] — satisfied inherently (the tcw-work reference
  edits *are* the skill update).
