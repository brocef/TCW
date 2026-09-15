# Refined outcome — Build taxonomy list's tree from real parentage instead of sorting path strings

**Verdict: accepted.** Verified in the coordinating session on 2026-07-30.
Subagent dispatch was unavailable (account session limit), so every stage ran
inline.

## Evidence, criterion by criterion

| # | Criterion | Verdict | Evidence |
| --- | --- | --- | --- |
| 1 | Issue's reproduction renders `event-reporting` as a childless root | met | Real CLI in a throwaway repo, output matches the spec's expected block exactly |
| 2 | Depth-first pre-order at three levels | met | `test_cli_list_is_depth_first_preorder_at_three_levels` asserts full output over `a`, `a/b`, `a/b/c`, `a/b/c2`, `a/d`, `a-sibling` |
| 3 | Siblings alphabetical within a level | met | Same test (`c` before `c2`, `b` before `d`) |
| 4 | Inherited terms after local, grouped by origin, never interleaved | met | `test_cli_list_never_splices_an_inherited_tree_into_the_local_one` — but see the honest caveat below |
| 5 | `--local` unaffected | met | Untouched code path; `test_list_flags_inherited_origin` still green |
| 6 | Row format byte-identical for a non-colliding taxonomy | met | Verified against the throwaway repro's non-colliding terms. **Not** verifiable against this repo, which turned out to be a colliding taxonomy — see below |
| 7 | Regression test pins the hyphen-vs-slash collision | met | Proven red against the old key |
| 8 | `pytest -q` green | met | `1133 passed in 186.14s` |
| 9 | Changelog `Fixed` + release-note entry | met | Both committed in `4c67477` |

`tests/test_taxonomy.py` went 30 → 33.

## What raises confidence

- **The red-test proof was done properly, and its first attempt is recorded as
  having failed silently.** `git stash push` on an already-committed file stashed
  nothing and the suite reported green against fixed code — the exact false
  positive the step exists to catch. Redone via `git checkout 5948866^ --`, which
  produced two genuine failures, then restored and re-confirmed green.
- **The outcome does not overstate coverage.** Two of the three new tests
  discriminate the defect; the inherited-origin case passes against the old key
  too, and `outcome.md` says so plainly instead of claiming three-for-three. That
  is the correct call — it is still a valid guard against a future regression in
  origin grouping, just not evidence for this fix.
- **This repo's own taxonomy exhibited the bug**, which the plan predicted it
  would not. `status` and `subject` rendered under
  `capability-feature-association` instead of `capability`. The intended
  "confirm the change is inert" check became a second live reproduction, and the
  discrepancy is recorded as a plan error rather than quietly absorbed.
- **The design choice is justified rather than merely made.** Segment-tuple sort
  over an explicit tree, because taxonomy parentage *is* the path
  (`tcw/store/base.py:142`), while `tcw/work/cli.py` and the web client's
  `buildPathTree` build explicit trees only because their parentage can point
  outside the path. One line against roughly thirty, same result.
- **Origin grouping is structural, not cosmetic.** Each `extends` alias is a
  separate store with its own slug namespace (`tcw/store/fs.py:774-779`), so
  splicing trees across origins would manufacture exactly the false parentage
  this item removes. This answers the request's first open question with a
  reason, not a preference.
- **The request's second open question is answered by inspection:** the web
  editor's `buildPathTree` attaches nodes to `map.get(parentPath)` and cannot
  exhibit this bug, so the CLI was the only affected renderer.
- **Abstraction litmus test: not applicable** — presentation-layer ordering in
  the CLI, no store-interface change.
- **Harness compatibility: unaffected.**
- **Capabilities: no delta.** `taxonomy/list-the-taxonomy` specifies no ordering
  rule, so its wording is true before and after.
- **No documentation went stale**: grep for `[V]`/`[F]` across `README.md`,
  `skills/`, `commands/`, `docs/capabilities/` returns nothing, so no sample
  `list` output exists anywhere to have gone wrong.

## Deferred follow-ups

None opened. One known limitation recorded rather than fixed: an **orphaned
nested term** (`event/log-batch` with no `event/meta.yaml`) still renders
indented beneath no parent row. Pre-existing, not introduced here, unreachable
through `tcw taxonomy add` — which creates the parent chain — and an explicit
tree would face the same hoist-or-placeholder choice. Recorded in the spec's
Risks so it reads as considered rather than missed.

## Closeout choices

- **Route:** committed directly on `main`; no worktree, no PR. Commits
  `5948866`, `6b2422a`, `4c67477`, plus the outcome commit.
- **Version:** none cut at closeout; folded into the single **minor** bump
  covering this seven-item batch, per the user's decision on 2026-07-30.
- **Definition of Done:** `tests pass`, `docs synced`, `capabilities reconciled`,
  `reviewed`, `version offered` all satisfied.

  The sixth entry — *originating GitHub issue answered and closed* — **applies
  and is deliberately deferred, not missed.** This item resolves
  [GitHub #11](https://github.com/brocef/TCW/issues/11). Per the user's
  2026-07-30 decision, issues in this batch are answered only after the
  containing version is cut **and pushed**, so an issue is never closed while the
  fix is still uninstallable. The closing comment is drafted for approval after
  the push.

## Notes

Worth carrying forward when #11 is answered: the reply can state that the defect
was reproduced in TCW's own taxonomy, not merely in the reporter's synthetic
case. That is a stronger acknowledgement than "fixed", and it is true.
