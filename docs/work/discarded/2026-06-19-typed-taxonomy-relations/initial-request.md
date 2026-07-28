# Typed taxonomy relations

## Product changes

## Technical changes

## Meta changes

Typed term relations (`is-a`, `part-of`) beyond the freeform `relatesTo` field.

Spec: docs/plan/phase-6-beyond.md; phase-2-taxonomy B.9.

## Closed `wontfix` — 2026-07-28 backlog audit

`docs/plan/phase-2-taxonomy.md:157` already settled this as a recorded decision,
not an unexamined gap:

> **`relatesTo`** — **freeform list of refs** now. Typed relations (`is-a`,
> `part-of`) are deferred until a consumer needs them (YAGNI; the tool reads
> pointers, humans write meaning).

Five weeks on, no consumer has appeared, and freeform `relatesTo` ships and works.
Keeping a backlog item open against a decision that was already made just invites
each audit to re-derive the same answer.

Reopen only by naming the consumer — a tool that must *traverse* the relation
rather than display it. That is the condition phase-2 set, and it is still the
right one. `phase-2-taxonomy.md:157` stays put; it is the evidence for this
closure, not a duplicate of it.
