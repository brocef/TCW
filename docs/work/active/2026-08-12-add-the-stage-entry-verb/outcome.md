# Outcome — Add the stage-entry verb

All eight plan tasks shipped. Suite green at 1458 Python (baseline before this
item: 1442). Every acceptance criterion is met.

## What shipped, task by task

| # | Task | Commit |
| - | ---- | ------ |
| 1–6 | `STAGE_STATUSES`, the verb, `--no-exec`, and every check | `1125da9` |
| 7–8 | Documentation Sync and the capability ledger | `d7802b1` |

Two commits rather than eight: the verb is ~70 lines on top of C3's resolver, and
splitting the table from the command that is its only consumer would have made
the first commit untestable rather than reviewable.

## The review found a wrong row and an unauthorized boundary change

**`postmortem` was legal in `discarded` in the first draft, and should not be.**
Verified against the contract: the stage's own objective says "legal in review or
after completion", and `base.py:440-444` says `completed` means *shipped* while
`discarded` means *closed without shipping*. A post-mortem on work nobody did is
not the out-of-band review this stage is. It has its own named test, separate
from the matrix, because a matrix derived from the table would have agreed with a
wrong table.

**Taking C5's legality table with a note was not a resolution.** The first draft
said C4 would define it "because C4 landed first" and recorded that as a
deviation. Review was right that a child overruling its epic quietly is how the
epic stops being the source of truth — so the **epic** is amended instead. That
is the third amendment this initiative has needed (C2's `body` cap, C3's role
table, now this), and each one is in the epic rather than in the child.

**The capability delta was missing entirely.** The epic assigns
`work/run-a-lifecycle-stage` to C4 and makes C7 consolidation-only, so nothing
downstream would have flipped it — C4 could have completed with its promised
ledger entry simply absent. Now criterion 11.

**Two criteria admitted the implementations they were meant to exclude:**

- Criterion 2 tested "the item folder is byte-identical", which is a filesystem
  assertion for an abstract property. A Jira-backed store has no folder, and an
  implementation could call an abstract mutator that happens to be a no-op on the
  filesystem. Now **two** assertions: no mutating `WorkStore` method is called
  (15 of them, guarded), plus the folder manifest.
- Criteria 4 and 5 named the two illegal pairs someone thought to test. Now the
  full `STAGE_IDS` × `WORK_STATUSES` product — 35 pairs, each accepted or
  rejected according to the table.

Three `bllm-review` findings were rejected after being checked: checks and
generators already inherit C3's timeout and output cap; `Condition.matches` is
set operations on tuples and has no runtime failure path; and prompt redaction is
a feature nobody asked for in a verb that prints less than `tcw work show` does.

## What the implementation actually cost

Thin, as the request predicted: `STAGE_STATUSES` is a dict, and `_stage` is
ordering, three error paths, and a call into C3's resolver. Every hard part —
condition filtering, the `generate` contract, plan mode — was already built and
tested, which is what the initiative's ordering was for.

The one thing worth noting is that `--no-exec` needed **nothing** new. C3 shipped
`execute=False` as a parameter of the same traversal rather than as a report
derived from a real run, precisely so C4 would not have to build a second code
path that could disagree with the first.

## Verified by hand

- **`tcw work stage` against this repository's own items**, including the
  illegal combinations.
- **`tcw validate`, `tcw capabilities check`** clean.

## Notes

- The plan goes to stderr, not stdout. A caller piping stdout under `--no-exec`
  gets the partial prompt — what genuinely resolved without running anything —
  rather than a plan they might act on.
- `tcw capabilities add` blocks on stdin when invoked without one. Not a defect
  of this item, but it cost a two-minute timeout here and is worth knowing.
- C5 now consumes `STAGE_STATUSES` rather than defining it. Its spec should say
  so when it is written.
