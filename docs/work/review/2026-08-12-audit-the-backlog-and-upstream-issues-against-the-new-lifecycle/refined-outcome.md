# Refined outcome — Audit the backlog and upstream issues against the new lifecycle

**Accepted** by the requester on 2026-08-18, with no rework.

## How this item's correctness was established

C8 carries no acceptance criterion in the epic — it ships no behaviour a suite
can assert, and the epic said so when it filed it. Its correctness *is* the
requester approving each disposition, which they did in one pass, having been
shown the evidence for each row rather than the conclusion alone.

Every claim the coordinating session acted on was re-verified against the tree
rather than accepted from an auditor:

- `git diff --stat main...HEAD` over `tcw/taxonomy` and `tcw/capabilities` — both
  **empty** across the epic, which is what makes four "unaffected" dispositions
  hold rather than assert.
- `_validate_fields` in `tcw/store/fs.py` checks field names and `Status` only;
  `_check_subject`/`_check_feature` at `:1851`/`:1864`. The write-time validation
  gap is exactly as its item describes.
- `tcw/work/cli.py:1334` declares `--tag` and no `--tags`.
- `README.md:111-113` lists `tcw-post-mortem`, disproving a claim in the eval
  harness's own plan.
- `_hosted_projects()` (`tcw/serve/__init__.py:415-427`) still omits the anchor's
  own id, so issue #12 is live and untouched by this epic.
- `README.md:605` is the only `###` between lines 590 and 1150.

## Criteria

All 8 met. Criterion 3 — nothing tracked changing before approval — was
discharged by task 2 doing nothing, which is the only way that criterion can be
met.

## The deviation, accepted knowingly

The plan said to dispatch the `tcw:tcw-backlog-auditor` agent, whose definition
scopes it to **one** item. Eleven items went out as **three grouped dispatches**
instead. The agent's load-bearing property — it reports and never edits,
transitions, or tags — was preserved, and the coordinating session re-read every
claim before acting on it.

Accepted rather than reworked, because the alternative buys nothing: eleven
dispatches of an agent that reports would have produced the same eleven reports.
Recorded in `outcome.md` and here so the deviation is visible, since the plan is
the document it contradicts.

## What was accepted without a check behind it

- **Whether each disposition is *right*.** The evidence makes a row reviewable,
  not correct. This is the whole of C8's correctness and why the requester
  approved a table rather than being told what happened.
- **Whether the two rescopes stayed inside their bound** — "correct what the item
  means, do not redesign it". A judgment; the per-item commits are the only real
  guard, and both are readable on their own.

## Deliberately deferred

**GitHub issue #12** — re-verified as live and unrelated to the epic. The
requester chose to skip it: no comment, no close, no work item. Deferred by
decision, not overlooked, and recorded here so a later reader does not read the
silence as an oversight.

## Note for the epic's closeout

The epic's plan predicted two discards and named both items; **both already read
`completed`**, and its prediction that the three `remote/*` items would inherit
C1's intake surface and C2's DTO held for only one of them. Nothing to correct —
a forecast written before the design was built, wrong in the direction that costs
nothing. Worth carrying into the epic's own outcome as a note on the limits of
planning-time prediction.
