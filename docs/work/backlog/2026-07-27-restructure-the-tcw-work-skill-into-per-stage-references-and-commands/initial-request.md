# Restructure the tcw-work skill into per-stage references and commands

Epic: [Redefine the TCW work lifecycle](tcw://W/2026-07-27-redefine-the-tcw-work-lifecycle-explicit-stages-transitions-and-hooks)

Child 4 of 5. Depends on children 1–3. Documentation only, no code.

**Before writing anything, re-read what children 1–3 actually shipped.** This
child's job is to describe reality, not to restate the epic plan's predictions.

## Scope

- One `stage-<id>.md` per stage on the fixed shape **Purpose / Inputs / Produce /
  Steps / Exit**, every step carrying its actor (`tcw`/agent/user) and
  enforcement marker (`[auto]`/`[gated]`/`[prompted]`/`[judgment]`).
  - `Inputs` separates bounded lifecycle context from unrestricted repository
    discovery. These are different things and conflating them made the first
    draft self-contradictory.
  - `Produce` names the artifact path **and its required sections** — this child
    owns every artifact's shape, including `rework.md` and `post-mortem.md`.
  - `Exit` covers ending well **and** ending badly. No sixth section.
- **No ordinals in filenames.** Order lives only in the router's table.
- `transitions.md` (all five in one file), `hooks.md`, `delegation.md`,
  `methodology.md`, `epic-deltas.md`, `cross-node-deltas.md`; `decompose.md`
  unchanged.
- **Delete** `lifecycle.md`, `task-lifecycle.md`, `epic-lifecycle.md`,
  `process-inbox.md` — and sweep every surviving document, command, and manifest
  for links to them. A dangling route is worse than the duplication it replaced.
- `SKILL.md` becomes a router under a hard **60-line** cap. On breach the rule is
  **extract, never grow**: it loads on every use, so its size is paid forever
  while a reference file is paid only when its gate fires.
- Harness-specific fallbacks live in **stage documents**, never the router — they
  are per-stage, and every harness reads the stage doc anyway.
- Commands: `tcw-process-inbox`, `tcw-plan-work` (request → plan),
  `tcw-drive-work-to-completion` (current → end), `tcw-verify-work`,
  `tcw-post-mortem`. Each must also have a skill-based entry path; Codex has no
  slash commands.
- The read-only `tcw-verifier` agent — an accelerator only. Codex has no custom
  agents, so the stage document must stand alone without it.
- Plugin manifests list every new command and skill.

## Done when — automatically checkable

- Every stage and transition id resolves to exactly one document.
- No id or filename carries an ordinal.
- `SKILL.md` is ≤60 lines.
- No reference to a deleted file survives anywhere in the repo.
- Plugin manifests list every command and skill.

## Done when — manual sign-off, not a test

- No rule is stated in two places.
- Every stage document is followable by a Codex agent with no injection, no
  custom agents, and no slash commands.

Neither is programmatically verifiable. They are sign-off criteria for this
child's `verify` stage; calling them tests would be dishonest.
