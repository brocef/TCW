# Refined outcome: require an exclusive claim transition under strict tracker mode

## Decision

**Accepted** on 2026-09-22 by the coordinating session. The requester chose, for
this epic, to approve only at the epic's own `verify` stage and to let each child
complete on a clean assessment. This one came back clean.

## Evidence

- Full suite as CI runs it (bare `pytest`, run in parallel with `-n auto`, from the
  worktree in a private venv whose `tcw` resolves to the worktree): **4312 passed,
  3 skipped**. That was the run after the verify wording fixes.
  `tcw validate` and `tcw capabilities check` both OK.
- `tcw:verifier`: all 12 acceptance criteria met. It independently repeated four
  code mutations and both `timeout-seconds: -1` removals in a scratch copy, and each
  turned exactly the tests `outcome.md` records red. It traced the check to the
  merged tracker block (`parse_tracker_config`'s only production caller passes
  `merge_tracker_blocks`' output), and found no case of a node being wrongly
  refused or wrongly accepted.

## Folded in at verify

The verifier found three sentences that were true only once C4 lands. The release
history shows a version can be cut between this item and C4 (C1 and C3 shipped in
v2.4.0, before C4), so those sentences were reworded rather than left
(`ec9d5bed`):

- The error message and the comment above it no longer say a claim keeps strict
  mode's promise "by applying this transition". They now say the transition "is
  what stops a second person". Until C4, a strict `start` is still protected by
  `claim_refusal`.
- The same "only by applying" sentence in `docs/guide/jira.md`,
  `skills/configure/references/tracker.md` and the release note's "Why" entry.
- The key's comment in `jira.md`'s main example now says "required under strict
  mode".

`outcome.md` notes that its pasted `tcw validate` output shows the earlier wording.

## Deferred

- **Whether to hold the next version cut until C4 lands.** It is not needed for
  correctness: every sentence this item ships is true without C4. It goes to the
  requester at the epic's `verify` stage.
- **Listing the problems inline in a strict broken-configuration refusal.** Today
  `tcw work start` prints only "Run `tcw validate`". Recorded for the epic's
  closeout as a possible follow-up. It was ruled out of this item's scope at
  `request`.
- No GitHub issue is attached to this item. The epic's #41 and #42 are answered
  only after the version carrying the epic is cut and pushed.

## Closeout

`tcw work complete` merges `work/<slug>` into `main` locally. The push goes with
the epic's release.
