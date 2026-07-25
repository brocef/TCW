# Outcome

Work completed successfully. All seven planned phases landed; the full
verification matrix is green.

## What changed

**Core model** (`tcw/store/base.py`) — `WORK_STATUSES` gains `discarded`;
`RESOLVED_STATUSES` names the two terminal statuses; `resolution_status()`
derives the destination and raises on an unknown resolution.
`LEGAL_TRANSITIONS` gains `(active, discarded)` and `(backlog, discarded)`.
`complete()` derives its destination instead of hard-coding `"completed"`, and
the completable-epic backlog exception is narrowed to `done`.

**The resolved/shipped split** — the part that mattered. Four sites meant
_resolved_ and now use `RESOLVED_STATUSES`: `unresolved_blockers`,
`epic_completable`, `complete()`'s open-children check, and `_ready()` in
`tcw/work/recursion.py`. One site means _shipped_ and deliberately still reads
`completed` alone — `_shipped_but_missing` in `tcw/capabilities/cli.py`, now
carrying a comment explaining why, so a future reader doesn't "fix" it.

**Consistency detector** (`FsWorkStore._status_resolution_problems`) — three
cases, surfaced through `check()` and therefore `tcw validate`.

**CLI** (`tcw/work/cli.py`) — `list` hides `discarded`; `complete` branches on
the resolution for the DoD checklist, the capability gate, and the worktree
merge-back; help strings updated.

**Web** — `WORK_STATUSES` extended in both literals, `discarded` sorts last and
defaults to hidden, and the complete modal branches on resolution. The HTTP API
needed no change: it delegates destination choice to the model.

**Migration** — this repo's three non-`done` closures moved to `discarded/` in
their own commit (`43b27a8`), no `state.yaml` edits. `.prettierignore` gained
`docs/work/discarded/`.

**Docs** — README, release notes, changelog, `tcw-work` SKILL.md and its two
lifecycle references, plus `docs/migration-guide-0.14.X-to-0.15.0.md`.

**Capabilities** — `work/discard-a-work-item` flipped to `Supported`;
`work/drop-a-work-item`, `work/complete-a-work-item`, `work/view-the-board`, and
`web/editing` rewritten to shipped behavior.

## Verification

```
python -m pytest        733 passed   (568 before this item)
pnpm vitest run          43 passed
pnpm prettify:check      clean  (repo-wide, for the first time)
tcw taxonomy check       taxonomy OK
tcw capabilities check   capabilities OK
tcw capabilities drift   no capability drift
tcw validate             validate OK
git diff --check         clean
```

Commits: `0f7acd7` (core + CLI), `f7f80ef` (web), `43b27a8` (migration),
`f0e91a7` (docs + ledger), `404ebec` (follow-up fixes), `5d0b02a` (doc sync +
repo-wide format).

Tests specifically covering the resolved/shipped split, since a wrong call there
is the failure mode this item was most exposed to:

- a discarded blocker stops blocking (`test_discarded_blocker_no_longer_blocks`)
- a discarded child stops wedging its epic
  (`test_epic_completable_with_a_discarded_child`)
- the reconcile rollup counts it resolved
  (`test_reconcile_counts_a_discarded_child_as_resolved`)
- `capabilities drift` does **not** count it shipped
  (`test_cli_drift_ignores_a_discarded_planning_doc`)
- the worktree branch survives a discard
  (`test_discard_leaves_the_unmerged_branch_intact`)

## Deviations from the plan

**None behaviorally.** Two notes:

1. The plan's Phase 5 asked for an assertion that an invalid resolution over the
   API returns 422. That test already existed
   (`test_complete_invalid_resolution_422`) and still passes, so no new test was
   needed — the concern the reviewer raised was already covered.
2. `pnpm prettify:check` was failing on 25 files, all pre-existing drift in
   TCW's own generated `state.yaml` files and skill docs (verified by stashing
   all work: the failing set was byte-identical with and without my changes).
   Cleared by a repo-wide `pnpm prettify` at the user's instruction — see
   follow-up 2.
3. The blocker gate on a discard shipped as the spec described, then was
   reversed at verification — see follow-up 1. This is the one intentional
   divergence from the approved spec, made with the user's approval.

## Follow-ups — all three resolved in-item

Raised at verification and addressed on the user's instruction rather than
deferred to backlog items (`404ebec`, `5d0b02a`).

1. **Blockers no longer gate a discard.** The approved spec had them gating both
   routes; on review that was wrong. "Don't claim you shipped this while its
   dependency is unfinished" says nothing about giving up, and being blocked
   indefinitely is one of the most common reasons to abandon work — so requiring
   `--force` there was friction on the exact path this status exists to smooth.
   `complete()` now checks blockers only when `dest == "completed"`.

    The **epic open-children gate still applies to both routes**, and that
    asymmetry is deliberate: an initiative child cannot start until its epic is
    active, so closing an epic by either route strands its open children.
    Covered by `test_blockers_gate_a_completion_but_not_a_discard` and
    `test_epic_children_gate_applies_to_a_discard_too`.

2. **Repo-wide prettier drift cleared.** `pnpm prettify` across the whole repo;
   `prettify:check` now passes for the first time. The pre-existing failures
   were TCW's own generated `state.yaml` files and skill docs — formatted rather
   than prettier-ignored, per the user's call.

3. **Web `WORK_STATUSES` deduplicated** into `model/types.ts`.
   `model/tree.ts` keeps `WORK_STATUS_ORDER` as a separate export, since display
   precedence (live work first) is genuinely a different concern from the
   canonical vocabulary — with a test asserting the order map covers every
   status, so the two cannot drift when a fifth status appears.

    Deduplicating surfaced a bug this item had introduced: the sort's
    unknown-status fallback was a hard-coded `3`, which meant "after everything"
    with three statuses but tied with `discarded` once it took index 3. Now
    `WORK_STATUS_ORDER.size`.

## For the next items in this sequence

- `2026-07-23-capability-first-lifecycle-…` adds a capability/tests attestation
  to the completion gate. It should attach to the **`done` route only** — the
  discard route has no DoD checklist to extend.
- `2026-07-22-planning-agnostic-tcw-lifecycle-orchestration` freezes a
  `complete` checkpoint contract. That contract now has two destinations.
- `2026-07-23-emit-new-location-when-cli-commands-move-a-tcw-object` assumes in
  its `plan.md` that `complete` moves to `completed/`; that is now
  resolution-dependent.
