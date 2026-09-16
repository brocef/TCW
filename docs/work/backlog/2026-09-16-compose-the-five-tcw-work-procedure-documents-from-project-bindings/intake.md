# Compose the five tcw-work procedure documents from project bindings

Child 4 of the epic
`2026-09-16-make-every-procedural-skill-in-tcw-overridable-by-the-project-that-uses-it`.
Blocked by children 1 and 2. Spec this against what child 2 actually shipped.

## What to deliver

Convert `skills/tcw-work/references/procedures/`'s `audit-backlog.md`,
`consolidate-plans.md`, `decompose.md`, `delegation.md` and `search.md` so each
composes from the procedure mechanism, with its current contents as the
`builtin` default.

Write `delegation.md` first: it states the doctrine the whole initiative cites
("Delegable means permitted, never required"; the shipped agents are
"accelerators only"), and converting it is the proof the doctrine survives its
own treatment.

## Constraints

- Only files under `skills/tcw-work/references/procedures/` belong to this child.
- A project that configures nothing reads exactly today's text.

## Acceptance criteria carried from the epic

Epic criteria 8 and 11 for these five documents.

## Origin

Opened by the epic's `implement` stage (plan task 4) on 2026-09-16.
