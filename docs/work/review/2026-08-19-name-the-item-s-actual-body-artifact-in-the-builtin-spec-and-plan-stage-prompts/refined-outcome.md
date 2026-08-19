# Refined outcome: accepted

**Decision: accepted**, by the requester (@brocef, who is also the reporter of
issue #22), 2026-08-19, after a judgment-call review at `verify`. No `rework`.

## Evidence at acceptance

Run immediately before this file was written:

- `python -m pytest -q` → **1761 passed** (1734 before this item; +25 from
  `tests/test_body_prompt.py`, +2 from the taxonomy additions).
- `tcw validate` → `validate OK`; `tcw taxonomy check` → `taxonomy OK`;
  `tcw capabilities drift` → `no capability drift`.
- The three body states rendered through the real CLI, not asserted from tests:
  an intake-only item's `spec` prompt opens `` **Inputs.** `intake.md`, read as
  filed. ``, a request-bearing item's opens `` `initial-request.md` ``, and an
  item with neither falls back to "the item's body artifact" naming no file.
- The pipeline the rewritten `tcw-triage-issues` §5 documents was executed end
  to end: piping text into `tcw work new` produced `intake.md` only, the board
  showed `i`, and `tcw work stage spec` named `intake.md`.

## The five judgment calls, and how they were decided

| # | Call                                                              | Decision                                                       |
| - | ----------------------------------------------------------------- | ---------------------------------------------------------------- |
| 1 | Criteria 4 and 7 reworded mid-implementation                      | **Accepted as a correction.** See below.                        |
| 2 | The clause cut to fit the 50-line ceiling                         | Approved as cut.                                                |
| 3 | Spec **Goal 6** (the abstraction goal)                            | **Removed** at the user's direction (`04bfc1d`). The code that met it stays — `BODY_ORDER` is still in `tcw/store/base.py`; only the goal statement was struck. Confirmed with the user. |
| 4 | The editor fix not filed as its own work item                     | Fine as is.                                                     |
| 5 | `consolidate-plans.md:54` deliberately left alone                 | Fine as is.                                                     |

**On call 1** — the spec promised that an intake-only item's prompt would never
print `initial-request.md` and would contain no "nobody asked" sentence. Neither
is deliverable: the prompt's branch prose is static (conditional language was a
stated non-goal), so the paragraph explains *both* artifacts and only the
substituted value varies per item. The criteria were reworded to the properties
that are actually load-bearing — the paragraph **opens** with the resolved
artifact, and the "nobody asked" conclusion is **scoped** to
`initial-request.md` with the intake branch asserted positively beside it. The
user accepted this as a fair correction to a promise that was too strict, rather
than a scope miss. Delivering the literal criteria would have meant building the
conditional-text machinery the spec ruled out.

## Found at verify, and fixed before closeout

- **A capability delta was missed.** The spec's Capability changes table
  promised three; implementation shipped two. `work/run-a-lifecycle-stage` never
  got its wording. Caught by step 4's ledger reconcile — not by any test, since
  nothing checks a description against a promise. Fixed in `696da94`, and
  `outcome.md`'s claim that all three read back correctly was corrected rather
  than left standing (`20b5129`).

## Follow-ups — done, not deferred

Both were offered as new backlog items; the user directed they be folded into
this change instead (`ccf42ef`).

- **Taxonomy gap closed.** `work-item/body-surface` and `work-item/intake` are
  now registered Vocabulary terms. Neither existed, despite the body surface
  being the rule `tcw work show`, the `R`/`i` board letters, and now the stage
  prompts all resolve through. `work-inbox`'s vocabulary list was left alone:
  there is no `tcw taxonomy edit`, and hand-editing the store where no command
  exists is what the house rule forbids.
- **The stranded fragment fixed.** The `spec` prompt's `**Inputs.**` line now
  breaks after the span's own sentence, so a short resolution no longer leaves
  `… read as filed. An` dangling. `substitute_body`'s docstring states the rule
  for the next prompt author, since nothing re-flows a resolved prompt.

## Closeout choices

- **Version: keep `1.0.0`.** No cut. `v1.0.0` is **published** — the tag
  resolves on `origin` at `612e28c` and
  `skills/documentation-sync/scripts/unpushed-version.sh` exits `1`
  (`NOT-FOLDABLE`) — so folding into it was never an option, and the user chose
  to leave the version alone. The notes stay in
  `docs/{changelogs,release-notes}/upcoming.md` and ship with whatever is cut
  next.
- **Merge route: none needed.** The work was done directly on `main`; there is
  no branch or worktree to merge back.
- **Remote: nothing pushed.** Local `main` is ahead of `origin/main` and stays
  that way. Publishing is the user's step.
- **Post-mortem: not offered.** Nothing here was a serious unforeseen problem.
  The two spec defects (an over-strict pair of criteria, a missed capability
  delta) were both caught by the process working as intended — the second by the
  `verify` ledger reconcile that exists for exactly that. Worth revisiting only
  if the same class recurs.

## Notes

- The dual review of the spec earned its keep: `codex` and `bllm-review`
  independently caught the design flaw that would have broken the fix (sharing
  `substitute_documentation`'s block walk, which would have rendered a line
  break mid-sentence), and `codex` additionally found four sweep rows the spec
  had missed. Recorded here because the review happened *before* `plan`, which
  is why it was cheap.
- Two sweep rows (18–19) were found during implementation, not by the spec's
  repo-wide sweep. One of them — `cross-node-deltas.md` claiming
  `tcw work reconcile` writes into `initial-request.md` — was stale on its own
  terms, unrelated to this item's defect. A repo-wide sweep that reads for one
  pattern will still miss adjacent rot.
- An out-of-band defect was fixed during this item and is recorded in
  `outcome.md`: the test suite launched the developer's GUI editor on every run.
  Unrelated to this work, reported mid-implementation, fixed at the shared seam.
