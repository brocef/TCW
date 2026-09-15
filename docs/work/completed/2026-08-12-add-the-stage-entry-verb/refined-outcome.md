# Refined outcome — Add the stage-entry verb

## The acceptance decision, stated accurately

**Closed on the requester's standing instruction to drive the whole initiative
through without stopping per slice, with verification deferred to the end.** Not
a per-item acceptance — the same decision that closed C1, C2, and C3.

## Evidence at closure

1458 Python tests (baseline 1442), `tcw validate` OK, `tcw capabilities check` OK.

The check worth naming is the legality matrix: every pair in
`STAGE_IDS` × `WORK_STATUSES` — 35 combinations — is accepted or rejected
according to `STAGE_STATUSES`, rather than the two illegal pairs the first draft
named. And `postmortem` on a discarded item has its own assertion outside the
matrix, because a matrix driven from the table cannot catch the table being
wrong.

## What a verifier should look at

**The third epic amendment.** C4 moved the stage/status legality table from C5 to
itself, in the epic's own spec. Confirm the epic still describes what its
children built: C2 amended `body`, C3 amended the role table, C4 amended the
table's ownership.

**C5's spec is not yet written and now inherits a constraint** — it consumes
`STAGE_STATUSES` rather than defining it.

## Deferred, deliberately

- **The README's lifecycle section** is correct but not final; C7 owns its
  rewrite.
- **`builtin` still resolves to nothing** until C5 and C6 fill the registries, so
  `tcw work stage` on an unconfigured node prints nothing today. That is the
  window the initiative planned for, not a defect of C4.

## Closeout choices

- **Version:** deferred to the end of the initiative.
- **Merge/PR route:** deferred with it; all slices land on
  `epic/polymorphic-work-lifecycle`.
- **Follow-up items:** `tcw capabilities add` blocks on stdin when given none.
  Small, real, and unrelated to this initiative — worth filing at the epic's
  verification rather than now.
