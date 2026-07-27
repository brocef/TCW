# Planning-agnostic TCW lifecycle orchestration

## Requested outcome

Make TCW's work lifecycle configurable at stable checkpoints so users can map
their preferred agent skills onto TCW without replacing TCW's durable artifact
or status model. TCW continues to own state, evidence requirements, transitions,
and closeout gates; mapped skills own the methodology used to perform work.

Expose these fixed checkpoint IDs:

`request -> spec -> plan -> start -> implement -> review -> verify -> integrate -> complete`

Preserve the existing artifact spine:

`initial-request.md -> spec.md -> plan.md -> outcome.md -> refined-outcome.md`

Add a read-only lifecycle inspection command, validation for configured skill
references, agent guidance that invokes mapped skills through a bounded prompt
envelope, a skill-based compatibility audit, and an already-integrated worktree
completion route.

## Constraints

- Keep lifecycle configuration storage-neutral in the model; the filesystem
  adapter may read it from `tcw-config.yaml`.
- Treat configured skill references as opaque, ordered strings. Do not add
  built-in methodology presets or custom prompt text.
- Omitted mappings use methodology-neutral TCW guidance. Configured but missing
  skills fail closed at agent preflight.
- Do not add statuses, lifecycle artifacts, approval documents, or formal
  per-stage progress state.
- TCW alone owns lifecycle commits, `start`, capability reconciliation, and
  `complete`.
- TDD, parallel agents, worktree preparation, and similar techniques remain
  skill-owned methods.
- Lifecycle configuration is node-local and does not inherit across connected
  projects.
- Superpowers is an interoperability example, not a maintained preset.
- Release selection and publication remain explicit closeout decisions.

## Known compatibility target

The design should support mappings such as Superpowers' brainstorming,
writing-plans, subagent-driven-development, requesting-code-review,
verification-before-completion, and finishing-a-development-branch skills while
auditing fixed artifact paths, hard-coded handoffs, required subskills, approval
gates, completion claims, and integration behavior.

## Planning boundary

This work item captures the requested design and implementation plan only. Do
not start or implement it until explicitly requested in a later session.
