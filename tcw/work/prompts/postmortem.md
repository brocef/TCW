# Stage: postmortem

**Purpose.** Find which stage first missed a problem. Not blame and not a
summary — the question is _where would this have been cheapest to catch_.

**Inputs.** The whole artifact spine, read **backwards**: `refined-outcome.md`
and any `rework.md` first, then `outcome.md`, `plan.md`, `spec.md`,
`initial-request.md`. **`## Notes` across the spine is the primary trail** —
where each stage recorded what it knew at the time, and usually where the miss
is visible in hindsight. Discovery is unrestricted, including git history.

**Produce** `post-mortem.md`, in the item's folder wherever that folder
currently lives. Required: what went wrong; which stage could first have caught
it; what would have had to be different; and whether that change is worth
making. A post-mortem that recommends "be more careful" has not finished.
Optional `## Notes`.

## This stage is out-of-band

It **never changes status**, and it is never a gate — nothing waits on it. It
is legal on an item in `review` and on one already `completed`, where it is the
single permitted write into a folder that is otherwise immutable. It is not
legal on a discarded item. Both timings are deliberate: the need for a
post-mortem is often only obvious after the work has shipped.

## Steps

1. Read the spine backwards and locate the earliest artifact that could have
   surfaced the problem.
2. Distinguish _nobody could have known_ from _nobody checked_. Only the second
   is actionable, and conflating them produces process nobody needs.
3. Write `post-mortem.md` and commit it.
4. Create follow-up work items for anything worth changing.

## Exit badly

- _The artifacts needed are missing._ Say so — a spine with no `outcome.md` is
  itself the finding.
- _The problem is a one-off._ Record that and stop. Manufacturing a process
  change for a non-recurring miss costs more than the miss.
