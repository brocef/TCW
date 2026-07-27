# Outcome

All six planned tasks shipped, one commit each, suite green at every boundary.

| # | Commit | Task |
|---|---|---|
| 1 | `f8f95d5` | Delete the dead `phase` field |
| 2 | `b0cfe81` | The `review` status, four edges, `submit`/`rework`, lazy folder creation |
| 3 | `a4085d5` | `tcw work submit` / `tcw work rework`; the verify-skipped warning |
| 4 | `c81d0f1` | The `pr` field |
| 5 | `4de80a2` | The TypeScript mirror and the parity guard |
| 6 | `563a02b` | Documentation sync |

767 tests pass (up from 733), plus 44 in the web suite. `tcw validate` is OK.

## What shipped

The state machine gained one status and four edges, including its first reverse
edge. `review` is deliberately *not* resolved: an item awaiting acceptance still
blocks its dependents and still holds its epic open, because verification can
reject it.

`rework` fails closed while `refined-outcome.md` is present. That document
asserts the work was verified; after a rejection it is false. TCW refuses rather
than deleting it, so forgetting is `[gated]` rather than silent. It is the only
transition that artifact gates — `complete` from `review` is unaffected on
either resolution.

`complete` from `active` still works and now warns that the verify stage was
skipped. `[prompted]`, not a gate: exit status unchanged, no second confirmation.

## Acceptance criteria

All 15 met. Each maps to a test in `tests/test_work_review.py`,
`tests/test_status_parity.py`, or `tests/test_work.py` except where noted.

Criteria 8 (lazy folder creation), 13 (the reserved-id collision), and 11 (the
parity guard) were the three the epic spec said must not be left to inference.
All three are covered explicitly.

## Verification performed beyond the suite

1. `tcw validate` → OK.
2. **A full end-to-end run in a scratch repo** with `docs/work/review/` deleted
   first, to stand in for a node that predates the status:
   `new → start → submit → rework (refused) → rework (allowed) → submit →
   complete`. The folder was recreated by the transition, `list` and `show`
   rendered the `review` item, and the refusal message named the file and the
   action.
3. **The parity guard broken by hand in both directions** — removing `review`
   from `types.ts` and from `WORK_STATUSES` — confirming it goes red each way
   and green on restore. A guard nobody has watched fail is not yet known to be
   a guard.
4. `npx vitest run` → 44 passed.

## Two corrections made during implementation

Both were claims the spec asserted and the code disproved. Recorded because the
epic's whole subject is documentation that drifted from behavior.

**`phase` is not erased from existing items.** The spec said the key would be
dropped on the next write. It is not: `set_field` is a read-modify-write over
the raw mapping, so unknown keys survive. The migration is that `phase` stops
being *read* and stops being *displayed* — the inert key persists in existing
`state.yaml` files. That is the right outcome; erasing it would mean touching
60+ files to delete an already-ignored value. Spec design section, criterion 9,
and the plan were corrected to match, and the test asserts the real behavior.

**`WORK_ARTIFACTS` is not inert.** Adding names to it would have crashed
`tcw work list` outright — `_render_board_item` indexed a letter map with `[]`,
so an unlabelled artifact name raises `KeyError`. Both new names got letters
(`W`, `M`) and the lookup became `.get(..., "?")`, so the registry can grow
without taking the board down.

## Notes

**The `pr` field remains the weakest part of this change, by its own admission.**
Two independent reviewers flagged it as speculative and they were right: nothing
in this child reads it. It is here because the epic plan assigned it here and
because child 2's `complete --already-integrated` is its consumer one child
later. If child 2's design moves away from it, `c81d0f1` is a clean single
revert.

**The parity test is a regex over another language's source.** Coarse, and it
breaks if `types.ts` is reformatted. That is the accepted cost of not requiring
Node.js in the Python suite. The `assert m, "declaration not found"` exists so a
reformat reads as a broken test rather than silently matching nothing and
passing — which would be the one failure mode worse than no guard at all.

**The skill and its reference docs were corrected, not rewritten.** Child 4
deletes `lifecycle.md`, `task-lifecycle.md`, and `epic-lifecycle.md` outright,
so they got the minimum needed to stop being wrong about the state machine.
Anything more would have been written to be deleted.

**One thing child 2 should not re-derive:** `submit` deliberately carries no
gate, even though the epic spec lists `outcome.md` as a "soft" check. Per the
epic's own terminology rule, soft means judgment, and the CLI must not refuse on
it. If child 2's hook layer makes it tempting to add a `pre` binding that
enforces artifact presence, that is a *user's* choice to configure, not a
default to ship.
