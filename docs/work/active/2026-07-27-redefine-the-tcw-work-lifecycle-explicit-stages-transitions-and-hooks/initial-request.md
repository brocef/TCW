# Redefine the TCW work lifecycle: explicit stages, transitions, and hooks

## Initiative request

TCW's work lifecycle was never defined precisely. It grew as prose spread across
`skills/tcw-work/SKILL.md` and its references, leaving the lifecycle in three
partly-contradictory forms: a 4-status state machine the CLI enforces, a
5-artifact document spine the agent drives by hand, and a set of gates named
inconsistently across six documents.

This initiative replaces that with **one canonical model**: a fixed set of named
**stages** (each producing exactly one artifact) and a fixed set of named
**transitions** (each changing status and committing). Both sets get stable IDs,
because those IDs become a public extension point — users bind their own skills
or shell commands to a stage or a transition through `tcw-config.yaml`.

## Coordination goal

Four child tasks, run in order. The CLI must land before the skill is rewritten,
because the skill would otherwise document transitions the tool does not have —
the drift `CLAUDE.md` explicitly forbids.

1. **Review status and transitions** — add the `review` status and the `submit` /
   `rework` edges; add the `pr` field; delete the dead `phase` field.
2. **Transition commits and config** — auto-commit every transition; add the
   `work.auto-commit-transitions` and `work.trunk-branch` config keys; stop
   persisting the constant `dod:` list.
3. **Skill and command restructure** — one reference doc per stage, delta-only
   epic and cross-node docs, five commands.
4. **Post-mortem skill** — a new skill plus the lifecycle hook that offers it.

## Constraints

- Stage and transition IDs are **public API**. Ordinals must not appear in an ID;
  inserting a stage later must not renumber existing bindings.
- Hook configuration is opaque ordered strings, node-local, and storage-neutral —
  a non-filesystem store must be able to hold the same mapping.
- The compressed path survives: `active → completed` stays legal for small
  changes, with a warning that the verify stage was skipped.
- Verification rigor is hook-defined, never hard-coded. Unbound means the skill's
  stop-and-ask; bound means whatever the user configured.
- `postmortem` is the single artifact writable after an item reaches `completed`.

## Decisions already made

- Stages and transitions are two distinct ladders, not one ordinal list.
- Commands cover stage *ranges*; only stages useful standalone get their own
  command.
- `verify` is not mandatory for the `done` route.
- `phase` is deleted rather than revived.

## Origin

Supersedes two backlog items, both discarded as `superseded` when this planning
session replaced them:

- `2026-07-22-planning-agnostic-tcw-lifecycle-orchestration` — proposed the same
  hook layer, but under a constraint ("do not add statuses") this initiative
  deliberately overrides.
- `2026-07-23-capability-first-lifecycle-author-expected-behavior-before-the-spec-attest-tests-at-completion`
  — its scope is **not** covered here and is recorded as deferred in `spec.md`.

## Open questions for spec

- Should `work.trunk-branch` only warn when `HEAD` differs, or actually commit to
  the named branch? (Design leans warn-only; the strong version needs real
  plumbing.)
- Does `auto-commit-transitions` default to `true` (matches intent, changes
  existing behavior) or `false` (preserves it)?

<!-- tcw:rollup -->
### Rollup: 2026-07-27-redefine-the-tcw-work-lifecycle-explicit-stages-transitions-and-hooks

| node | slug | status | phase | blocked-by |
|---|---|---|---|---|
| . | 2026-07-27-add-the-review-status-and-the-submit-rework-transitions | backlog | - | - |
| . | 2026-07-27-commit-every-work-transition-add-lifecycle-policy-config | backlog | - | 2026-07-27-add-the-review-status-and-the-submit-rework-transitions |
| . | 2026-07-27-add-tcw-work-methodology-to-resolve-a-stage-s-skill-binding | backlog | - | 2026-07-27-commit-every-work-transition-add-lifecycle-policy-config |
| . | 2026-07-27-restructure-the-tcw-work-skill-into-per-stage-references-and-commands | backlog | - | 2026-07-27-add-tcw-work-methodology-to-resolve-a-stage-s-skill-binding |
| . | 2026-07-27-add-the-post-mortem-skill-and-its-verify-stage-trigger | backlog | - | 2026-07-27-restructure-the-tcw-work-skill-into-per-stage-references-and-commands |

**Next:** 2026-07-27-add-the-review-status-and-the-submit-rework-transitions
<!-- /tcw:rollup -->
