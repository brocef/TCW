# Spec — Let a started item still pass its planning gates, or stop start from letting it past them

## Capability changes

- **changed:** `work/run-a-lifecycle-stage` — `request` is legal for an
  active item too, and a stage refused for the item's status says how to go
  on.
- **changed:** `work/start-a-work-item` — the warning at `start` also names a
  missing request.

## Problem

Work discovered mid-task is often made into an item after it was started.
The lifecycle still expects its planning documents, but on tcw 2.6.4:

```
$ tcw work stage gate request <slug>
tcw work stage gate: 'request' is not legal for an item in 'active'; it runs in backlog
```

Since 2.6.3, `spec` and `plan` are legal in `active`
(`STAGE_STATUSES`, `tcw/store/base.py`), because nothing moves an item back to
`backlog`. `request` was left behind, for no stated reason. So an item
started before its request was written has no gate for it, and agents write
it from `stage prompt` without the checks the gate runs. `start`'s own warning
names only a missing `spec.md` or `plan.md`, never the request. And the
refusal says where the stage runs, but not how to get there or what to do
instead.

## Goals

1. `request` is legal in `backlog` and `active`, as `spec` and `plan` are.
2. `start`'s warning names every one of `initial-request.md`, `spec.md` and
   `plan.md` that is missing, with the gate command for each, as today for the
   last two.
3. The hint after `start` follows the work skill's "Finding your place" order
   (`start_next_stage`): no `initial-request.md` → `request`, then `spec`,
   `plan`, and so on.
4. A stage refused for the item's status adds one line saying how to go on:
   - the item is past the stage and in `review`, while the stage is legal in
     `active` (`request`, `spec`, `plan`, `implement`): send it back with
     `tcw work rework <slug>`;
   - the item is before the stage (`backlog`, for `implement` or `verify`):
     start it with `tcw work start <slug>`;
   - the item is resolved: nothing runs on it. Only `postmortem` is legal on
     a completed item;
   - in every case where the item is open,
     `tcw work stage prompt <stage> <slug>` prints the instructions without
     the gate, and the hint says that the gate's checks will not run.
5. The existing refusal text stays word for word; the hint is added after it.

## Non-goals

- **`start` does not refuse** when planning documents are missing. The
  follow-up comment on #71 suggests refusing, or requiring `--force`. The
  accepted precedent (`994727fb`, 2.6.3) chose a warning: a project that skips
  planning small items is entitled to, and one that is not binds a `pre` check
  on `implement` (this repository does, with `scripts/require_artifact.py`).
- **Not `request` in `review`.** Going back from review is `rework`'s job.

## Design

- `STAGE_STATUSES["request"] = ("backlog", "active")`, with the comment
  above it extended.
- `_unwritten_plan` becomes `_unwritten_planning`, checking `initial-request`,
  `spec` and `plan`. An item with `intake.md` but no request still counts as
  missing the request: the `request` stage has not run.
- `start_next_stage` returns `request` first when `initial-request` is absent.
- `_stage` in `tcw/work/cli.py` adds the hint under the existing refusal.
- `tcw/work/prompts/request.md`'s footer, and `STAGE_NEXT_STEPS`, say that
  after `request` on an active item the next step is `spec`, as today. That is
  unchanged. Check it at implementation.

Litmus: lifecycle legality is model data (`STAGE_STATUSES`), which any store
reads the same way.

## Acceptance criteria

1. `tcw work stage gate request <slug>` on an active item passes its legality
   check (exit 0 in a project that binds nothing to `request`).
2. `tcw work start` on an item with only a title warns naming
   `initial-request.md`, `spec.md` and `plan.md`, and its next-step hint names
   `tcw work stage gate request`.
3. The same on an item with a request but no spec names `spec.md` and
   `plan.md` only, and points at `spec`, as today.
4. `tcw work stage gate spec <slug>` on an item in `review` exits 1, keeps
   today's text, and names `tcw work rework` and `tcw work stage prompt spec`.
5. `tcw work stage gate implement <slug>` on a backlog item names
   `tcw work start`.
6. The lifecycle baseline fixture and `tcw work lifecycle` output show
   `request` legal in `backlog, active`.
7. Existing tests pass, updated only where they pinned `request`'s old
   legality or the old start hint. The full suite passes as CI runs it.

## Risks

- **Changed `start` output** for items without a request: a new next step
  and a longer warning. Intended: it now matches the skill's own order.

## Notes

- No advisors were consulted. The question (legal, or only a better refusal)
  was settled by the accepted precedent `994727fb`, which made `spec` and
  `plan` legal in `active` for the same reason. Goal 4 answers the issue's
  other ask, a refusal that says what to do, for the cases still refused.
