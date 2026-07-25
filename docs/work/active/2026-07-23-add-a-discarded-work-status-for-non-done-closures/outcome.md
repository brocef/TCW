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
python -m pytest        732 passed   (568 before this item)
pnpm vitest run          42 passed
tcw taxonomy check       taxonomy OK
tcw capabilities check   capabilities OK
tcw capabilities drift   no capability drift
tcw validate             validate OK
git diff --check         clean
```

Commits: `0f7acd7` (core + CLI), `f7f80ef` (web), `43b27a8` (migration),
`f0e91a7` (docs + ledger).

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
2. `pnpm prettify:check` fails on 25 files. **This is pre-existing**, verified by
   stashing all work and re-running: 32 files failed before this item, and the
   failing set was byte-identical with and without my changes. The count dropped
   to 25 because I formatted the files this item touched. The remaining failures
   are TCW's own CLI-generated `state.yaml` files and skill docs across the repo
   — unrelated drift, deliberately not fixed here.

## Follow-up notes

Not TCW items yet — creating them is a closeout decision.

1. **The blocker gate on a discard is worth reconsidering.** The approved spec
   said blockers gate a discard exactly as they gate a completion, and that is
   what shipped (`test_discard_is_still_blocker_gated` documents it). But the
   reasoning behind the other gate removals arguably applies here too: "we've
   been blocked on this vendor for six months, so — wontfix" is close to the
   canonical reason to discard something, and requiring `--force` for it is
   friction of exactly the kind this item set out to remove. The gate on `start`
   means "don't begin work that can't proceed"; the gate on `complete --done`
   means "don't claim you shipped something whose dependency isn't done."
   Neither rationale covers a discard. **Raised for your decision** — it is a
   one-line change either way.
2. **Repo-wide prettier drift** (the 25 files above) deserves its own cleanup
   item, or a decision that CLI-generated TCW files should be prettier-ignored
   the way `completed/` and `discarded/` already are.
3. **The duplicated `WORK_STATUSES` literal** in `web/client/src/ui/app.tsx` and
   `content-views.tsx` was extended in place, as the spec scoped it. Worth
   deduplicating eventually.

## For the next items in this sequence

- `2026-07-23-capability-first-lifecycle-…` adds a capability/tests attestation
  to the completion gate. It should attach to the **`done` route only** — the
  discard route has no DoD checklist to extend.
- `2026-07-22-planning-agnostic-tcw-lifecycle-orchestration` freezes a
  `complete` checkpoint contract. That contract now has two destinations.
- `2026-07-23-emit-new-location-when-cli-commands-move-a-tcw-object` assumes in
  its `plan.md` that `complete` moves to `completed/`; that is now
  resolution-dependent.
