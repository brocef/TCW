# Stage: implement

**Purpose.** Build it, and record what actually happened — including where the
plan turned out to be wrong.

**Inputs.** `spec.md`, `plan.md`, and `rework.md` if one exists; repository
discovery is unrestricted. **`rework.md` is what makes a second pass different
from a first**: it follows what verification rejected, not what files exist.

**Produce** `outcome.md`, in the item's folder, plus the code itself. Required:
what shipped task by task with commit references, the test result, and
**anything the plan or spec got wrong**. Optional `## Notes`.

## Steps

1. **`tcw work start <slug>` before the first code edit.** Editing code while
   the item is still in `backlog` means you skipped this — stop and start it.
2. Work the plan's tasks in order, committing each.
3. **Write the failing test first and watch it fail** before the code that
   makes it pass. A test that has never been red proves nothing.
4. On a bug or unexpected failure, **find the root cause before the fix**, and
   fix it where every caller routes through, not at the site that reported it.
5. Check any capability change against the standing ledger for contradictions.
6. **When the code disproves the plan, fix the plan and say so.** Silently
   working around it is how documentation starts lying.
7. **Once every plan task is done and the suite is green — and not before —**
   evaluate every Documentation Sync entry in the project's agent guide
   (`AGENTS.md` or `CLAUDE.md`) once, against the whole finished diff rather
   than the task you just committed. Commit the doc updates separately.
8. **No completion claim without output from a command you ran just now.**
9. Write `outcome.md` and commit it. **Self-review:** an empty "what the plan
   or spec got wrong" section is a claim, not an omission.

## Exit badly

- _The plan is unworkable._ Return to `plan`. Do not improvise a different
  design and leave the plan describing the abandoned one.
- _A task is blocked externally._ Record it (`tcw work edit --blocked-by`),
  finish everything that does not depend on it, and say what was left out.
- _Scope grew._ Ship what was specified and create a follow-up item.
