# Spec — explicit lifecycle-transition cues

## Problem

An agent in another project drove a change without running `tcw work start` /
`tcw work complete`. Two gaps: (a) the skill states the *when* descriptively, not
as an imperative trigger; (b) if the skill never loads, nothing reaches the agent
at all. Fix both.

## Changes

### Skill (`skills/tcw-work/SKILL.md`, router)
Rewrite the lead of "The lifecycle handshake" into imperative, trigger-based cues:
- **Before the first line of code → `tcw work start <slug>`.** Self-check: editing
  code while the item is still in `backlog` means you skipped `start`.
- **The moment work is done & verified → `tcw work complete <slug> …`.** Don't leave
  a shipped item in `active`.
- State that the agent drives these transitions explicitly; the tool never moves an
  item on its own.
Keep the existing per-command detail bullets below the new lead.

### CLI (`tcw/work/cli.py`) — next-step nudges on **stderr**
Follow the existing `_escalate` reminder precedent (stderr, so stdout stays just the
slug for callers):
- `tcw work new` (non-epic) → `→ next: when you begin implementing, run \`tcw work start <slug>\``
- `tcw work start` (both plain + worktree) → `→ next: when done & verified, run \`tcw work complete <slug> --resolution done --confirm\``

## Acceptance criteria

1. Skill lifecycle section reads as a mandatory trigger, not a description.
2. `tcw work new "x"` prints the slug on **stdout** and the start-hint on **stderr**;
   `tcw work start <slug>` prints the complete-hint on stderr. Verified by tests.
3. stdout of `new` is unchanged (still just the slug) — callers that capture it are
   unaffected.
4. Epic `new` does not emit the start-hint (its next step is delegate, not start).

## Out of scope

- tcw-capabilities skill (start/complete are work-axis).
- Adopting-project CLAUDE.md guidance (considered; deferred).
