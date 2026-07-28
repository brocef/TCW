# Stage: implement

## Purpose

Build it, and record what actually happened — including where the plan turned out
to be wrong.

## Inputs

`spec.md`, `plan.md`, and `rework.md` if one exists.

**`rework.md` is what makes a second pass different from a first.** It is the
input that keeps a stale `outcome.md` from reading as "implementation complete":
re-implementation is driven by what verification rejected, not by which files
happen to be present.

Repository discovery is unrestricted. This is the largest stage by context, and
the most valuable to delegate.

## Produce

`outcome.md`, in the item's folder, plus the code itself. Code is not a lifecycle
artifact; `outcome.md` is.

Required: what shipped, task by task, with commit references; the test result;
and **anything the plan or spec got wrong**, corrected in place with the
correction recorded. Optional `## Notes`.

## Steps

1. **`tcw work start <slug>` before the first code edit.** If you are editing
   code while the item is still in `backlog`, you skipped this — stop and start
   it. The tool refuses if a blocker is unresolved or the initiative epic is not
   active, and commits the move itself. — agent `[gated]`
2. Run `tcw work lifecycle --stage implement` and honor any binding it reports.
   — agent `[judgment]`
3. Work the plan's tasks in order, committing each. — agent `[judgment]`
4. On any capability change, run contradiction detection. **REQUIRED SUB-SKILL:
   Use tcw-capabilities.** — agent `[judgment]`
5. **When the code disproves the plan, fix the plan and say so.** A spec claim
   the implementation contradicts is the most valuable thing this stage produces;
   silently working around it is how documentation starts lying. — agent
   `[judgment]`
6. **Once every plan task is done and the suite is green — and not before —**
   invoke the `documentation-sync` skill once over the whole change: evaluate
   every trigger in `AGENTS.md` against the finished diff, not against the task
   you just committed. Docs written
   task-by-task describe a shape the work no longer has by the end. Commit the
   doc updates separately from the code. **REQUIRED SUB-SKILL: Use
   documentation-sync.** — agent `[judgment]`
7. Write `outcome.md` and commit it. — agent `[judgment]`

Step 6 is the lifecycle's documentation gate: the last thing implementation does
before it reports done. `verify` inherits docs already current, so the user is
reviewing the change and its documentation together rather than being asked to
accept a diff whose docs are still pending. The version cut is **not** part of
this — it belongs after `tcw work complete`; see `stage-verify.md`.

This stage is **delegable**, and is where delegation pays: the coordinating
session ends up holding `outcome.md` rather than an entire diff. See
`delegation.md`.

## Exit

**Well:** the suite is green, every fired Documentation Sync trigger has been
answered, `outcome.md` records what shipped and what the plan got wrong, and
`submit` is the next move.

**Badly:**

- *The plan is unworkable.* Return to `plan`. Do not improvise a different design
  and leave the plan describing the abandoned one.
- *A task is blocked externally.* Record the blocker on the item
  (`tcw work edit --blocked-by`), finish everything that does not depend on it,
  and say explicitly what was left out.
- *Scope grew.* Ship what was specified, and create a follow-up item. Widening
  scope mid-implementation is how an item stops being reviewable.
