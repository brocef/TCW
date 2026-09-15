# Refined outcome — Project a work item as JSON

## The acceptance decision, stated accurately

**Closed on the requester's instruction to drive the whole initiative through
without stopping per slice, with verification deferred to the end of the epic.**
Not a per-item acceptance, and it should not be read as one — the same standing
decision that closed C1.

C2's implementation is complete and its criteria are met; its acceptance is
pending until the initiative is verified as a whole.

## Evidence at closure

1346 Python tests (baseline 1314), 52 web unit, 14 end-to-end, `tcw validate` OK,
`tcw capabilities check` OK, `tcw capabilities drift` clean.

The check worth naming: the four `tcw work show` baselines were captured from the
CLI at `c2fe1fc`, **before** `_show` was touched, and reproduce byte-for-byte
from the changed binary. It is the only assertion in this item that the
implementer could not have written into agreement with the implementation, and it
is the one the initiative's history said was most needed.

## What was reviewed, and by what

`codex` and `bllm-review` ran against the spec **before implementation**, which
is the first time in this initiative that has happened rather than review landing
at `verify`. Eight findings were folded in; two were rejected after being
reproduced and failing to hold. The full table is in `outcome.md`.

The finding that matters: criteria 1 and 2 as first drafted could both pass while
the schema and the projection agreed on an incomplete document. Criterion 3 —
schema property set equals `WorkItem`'s fields plus two — closes it, and it
closes it against the *model* rather than against another artifact the
implementer wrote.

No independent verifier has assessed the finished code. That is what the
end-of-initiative verification is for.

## Deferred, deliberately

**The `body` cap belongs to C3.** The epic's spec was amended in `0cd2f54` to
assign it there. If C3 does not implement it, the projection ships an unbounded
`body` into a `generate` hook's stdin, and the amendment becomes a promise nobody
kept. Worth checking explicitly when C3 is verified.

**A key collision raises rather than degrading.** In `serve` this surfaces as a
failure on one item's page. Nothing in this repository triggers it and the
message names both keys, but it is the one place C2 chose failure over output.

## Closeout choices

- **Version:** deferred to the end of the initiative, with C1's.
- **Merge/PR route:** deferred with it; all slices land on
  `epic/polymorphic-work-lifecycle`.
- **Follow-up items:** none from C2.
