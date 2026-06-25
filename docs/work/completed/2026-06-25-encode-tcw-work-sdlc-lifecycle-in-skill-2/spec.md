# Spec — encode the TCW work SDLC lifecycle in the skill

## Capability changes

- Add a plugin-facing capability for agent-driven work planning and execution through TCW skills and commands.
- Update the work-skill capability narrative to reflect the primary lifecycle artifacts: `initial-request.md`, `spec.md`, `plan.md`, `outcome.md`, and `refined-outcome.md`.

## Problem

`tcw-work` already covers the core state machine and transition handshake, but the primary agent SDLC is implicit. Users need a convenient way to ask an agent to plan work or drive a work item through every remaining stage, whether the input is a chat request, a rough backlog item, a planned item, or a mid-flight implementation.

The older `skill-cefailures` inbox commands should not be copied. TCW has its own work item spine. The old generic `docs/inbox` model is out of scope; TCW's `docs/work/inbox` remains only as a transient raw intake channel where current commands still use it.

## Requirements

- Make the primary lifecycle explicit in the `tcw-work` skill.
- Add a lifecycle sub-document with the full stage details:
  - Request Ingestion -> `initial-request.md`
  - Request Processing -> `spec.md`
  - Spec Processing -> `plan.md`
  - Implementation -> `outcome.md`
  - Verification and Refinement -> `refined-outcome.md`
- Document that small work can compress stages with user agreement, while preserving the artifact spine.
- Add command wrappers for `/tcw-plan-work` and `/tcw-drive-work-to-completion`.
- Define `/tcw-drive-work-to-completion` as driving to verification/refinement and stopping for explicit user approval before closeout.
- Clarify that follow-up notes in `outcome.md` are natural language by default; creating TCW follow-up work items is a user closeout decision.
- Preserve `docs/work/inbox` as a transient TCW intake queue for existing `delegate`/`escalate` mechanics; do not revive or reference the old generic `docs/inbox`.

## Non-goals

- Do not change the `tcw work` CLI mechanics in this item.
- Do not remove or redesign `docs/work/inbox`; using backlog directly as the inter-node dropbox is a separate mechanism change.
- Do not automate completion without human verification.

## Acceptance criteria

- `skills/tcw-work/SKILL.md` routes lifecycle-heavy work to a new lifecycle doc.
- The lifecycle doc contains the full stage model and command behavior.
- New command markdown files exist for planning and driving work.
- Skill and command docs distinguish `docs/work/inbox` from the old `docs/inbox` pattern.
- Documentation sync entries are evaluated before completion.
