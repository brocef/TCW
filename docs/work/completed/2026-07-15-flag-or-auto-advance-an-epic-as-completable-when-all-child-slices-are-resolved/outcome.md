# Outcome: flag / auto-advance a completable epic

Work completed successfully. Work-axis change; TDD; dual-reviewed (one real
Medium bug found and fixed). Full suite green (649 passed → +14 epic tests).

## What changed

- `tcw/store/base.py` — `WorkStore.epic_completable(item)` (concrete; `type: epic`,
  not completed, ≥1 initiative child, all completed; cross-node via
  `initiative_children`). `complete()` gains a scoped backlog exception: a
  completable epic may close directly from `backlog` (effected via
  `_effect_transition`, not by widening the global `LEGAL_TRANSITIONS`); non-epics
  and non-completable epics are still refused; the open-children + blocker gates
  still run.
- `tcw/work/recursion.py` — `reconcile(..., complete_when_ready=False)`: "Ready to
  close" rollup line when completable; with the flag, auto-completes the epic. The
  shared `capability_gate` was **moved here** from the CLI so both the manual
  `complete` path and reconcile auto-complete enforce it (see review). Auto-complete
  runs the gate first, then rewrites the rollup after the move so a completed epic
  keeps no stale "Ready to close" note.
- `tcw/work/cli.py` — board rows show `ready-to-close` for a completable epic (only
  evaluated for `type: epic`); `reconcile --complete-when-ready`; `_complete` now
  calls the shared `capability_gate`.
- Capabilities: `work/complete-a-work-item` + `work/view-the-board` bodies updated
  (both `changed:`, already `Supported`). Docs: README, release notes, changelog,
  `tcw-work` skill.

## Verification performed

- `pytest` — 649 passed; new `tests/test_epic_completable.py` (14): predicate
  true/false cases; complete-from-backlog allowed + the three refusals; the
  reconcile flag (complete / no-op / **blocked by a Missing capability**); the
  no-stale-rollup guard; and the cross-node open-child case.
- CLI end-to-end (throwaway repo): epic + resolved child → `list` shows
  `ready-to-close`; rollup shows "Ready to close" + the exact command; `complete`
  straight from `backlog` succeeds (DoD gate applied); `reconcile
  --complete-when-ready` auto-closes.
- `tcw validate` + `tcw capabilities check` clean.

## Review (dual)

1. **Subagent (targeted-code-reviewer)** — state-machine core sound (traced every
   non-completable case: none reaches the backlog exception; `_effect_transition`
   bypass equivalent to `transition()` minus the legality check; gates still run;
   cross-node source shared by board/reconcile/complete; reconcile error-handling +
   `--commit` correct; board perf guarded to epic rows). Found one **Medium bug**:
   `reconcile --complete-when-ready` called `store.complete()` directly, **skipping
   the capability gate** (which lived in the CLI handler) — contradicting the spec's
   "capability gate still runs" guarantee; an epic with a declared-Missing `new:`
   capability would auto-complete silently. Plus two Low notes (marker-vs-blocker
   signal precision; stale persisted rollup after auto-complete).
2. **`bllm-review-many` (qwen25)** — generic advisories only (TOCTOU, "add tests"),
   no concrete defect; did not catch the Medium.

**Applied:** moved `capability_gate` into `recursion.py` as the single source of
truth, called by both the CLI `complete` and reconcile auto-complete (fail-closed
before completing); added a test proving auto-complete refuses a Missing declared
capability. Fixed the stale-rollup Low by rewriting the rollup after completion
(+ regression test). **Dismissed** the marker-precision Low: `epic_completable`
stays "all child slices resolved" (the request's definition), and the docs already
frame `ready-to-close` as "children resolved"; the board prints any own-blocker on
the same row.

## Deviations from plan

`capability_gate` moved from `cli.py` to `recursion.py` (not in the plan) to close
the review's Medium finding without duplicating the gate — the abstract `WorkStore`
deliberately does not host it (it reaches into `FsCapabilitiesStore`; litmus).

## Follow-up notes

None.
