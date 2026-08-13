As a user, I run `tcw work reconcile <epic>` to refresh the epic's own account of
its slices. TCW walks the registered descendants, collects every item whose
`initiative` points at this epic, and rewrites a managed block in the epic's
`initial-request.md` between `<!-- tcw:rollup -->` markers. Everything outside
those markers is mine and is never touched.

The block holds a slice table — node, slug, status, blockers — grouped by project
and ordered so a slice appears after whatever blocks it; the capability deltas the
slices declared; and either a **Next:** line naming the slices that are ready to
work, or **Ready to close** with the exact `complete` command once every slice is
resolved. An epic nothing points at yet says so rather than rendering an empty
table.

It is **idempotent**. A rollup that has not changed is not rewritten, so
re-running produces no commit and no churn — safe to run on a schedule or before
every status meeting.

It is **read-only on the capabilities ledger**. The rollup surfaces the deltas
slices declared so I can see them in one place; it never flips a capability's
status. That stays with
[Complete a work item](tcw://C/work/complete-a-work-item).

Two flags extend it:

- `--commit` also commits the refreshed rollup, in the repository that holds the
  work store — which is not necessarily the code repository, when the project
  configures [a work-store location](tcw://C/work/configure-the-work-store-location).
  The commit is scoped to the work store, so unrelated staged changes are left
  alone.
- `--complete-when-ready` auto-completes the epic when every slice is resolved,
  after refreshing the rollup so the persisted text reflects the closed state
  rather than a stale "ready to close" instruction. The Definition-of-Done and
  capability-reconciliation gates still run, so this cannot close an epic whose
  declared capabilities are unreconciled.

One slice with a malformed or unreadable `capabilities.yaml` does not take down
the rollup: it is reported as a skipped row. This is a display surface, so it
degrades rather than failing closed — unlike the completion gate, which must.

See [Coordinate a cross-node epic](tcw://C/work/coordinate-a-cross-node-epic) for
the relation this summarizes.
