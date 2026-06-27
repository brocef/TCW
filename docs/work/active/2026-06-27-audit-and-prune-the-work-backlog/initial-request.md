# Initial request — Audit and prune the work backlog

## Requested outcome

Add a new `tcw work audit-work-backlog` command that reviews each backlog item
and recommends cleanup actions. The audit should help identify tasks that are
stale, outdated, improperly located, or otherwise no longer useful as backlog
items.

## Requested review tasks

- Determine whether a backlog task is stale because it appears to have already
  been completed outside the TCW lifecycle; recommend completing it when so.
- Detect outdated plans with broken references, incorrect code references, or
  references to architecture/frameworks that have been deprecated, removed, or
  replaced.
- Detect work items that are in the wrong repository, especially in multi-repo
  projects; recommend moving the item or breaking it into per-repo work items.
- Offer additional cleanup checks to keep the backlog relevant and pruned.

## Additional suggested checks

- **Duplicate or overlapping intent:** detect items that appear to cover the same
  outcome as another backlog, active, or completed item and recommend merge,
  supersede, or duplicate resolution.
- **Actionability and scope:** flag items whose request/spec/plan is too vague,
  too large, missing acceptance criteria, or missing a clear next implementation
  step.
- **Blocked-without-next-action:** flag items with unresolved blockers that do
  not identify an owner, external wait, or follow-up action.
- **Capability drift:** flag items whose declared capability deltas no longer
  match the capability ledger.

## Constraints and non-goals

- The first implementation should report recommendations, not silently mutate
  the backlog.
- Keep multi-repo movement compatible with TCW nodes and the storage abstraction.
- Planning should stop before implementation; do not run `tcw work start` yet.

## Decisions already made

- Command name: `audit-work-backlog`.
- Primary scope is backlog items.
- Cleanup should include stale, outdated, and improperly located items.
