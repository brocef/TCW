# Stage: postmortem

## Purpose

Find which stage first missed a problem. Not blame and not a summary — the
question is always _where would this have been cheapest to catch_.

## Inputs

The whole artifact spine, read **backwards**: `refined-outcome.md` and any
`rework.md` first, then `outcome.md`, `plan.md`, `spec.md`,
`initial-request.md`.

`## Notes` across the spine is the primary trail. It is where each stage recorded
what it knew at the time, and it is usually where the miss is visible in
hindsight.

Repository discovery is unrestricted, including git history.

## Produce

`post-mortem.md`, in the item's folder wherever that folder currently lives.

Required: what went wrong; which stage could first have caught it; what would
have had to be different; and whether that change is worth making. A post-mortem
that recommends "be more careful" has not finished.

Optional `## Notes`.

## Steps

1. Run `tcw work lifecycle --stage postmortem` and honor any binding it reports.
   — agent `[judgment]`
2. Read the spine backwards and locate the earliest artifact that could have
   surfaced the problem. — agent `[judgment]`
3. Distinguish _nobody could have known_ from _nobody checked_. Only the second
   is actionable, and conflating them produces process nobody needs. — agent
   `[judgment]`
4. Write `post-mortem.md` and commit it. — agent `[judgment]`
5. Create follow-up work items for anything worth changing. — agent `[judgment]`

This stage is **delegable** to a read-only subagent.

## Exit

**Well:** the earliest catchable point is named, and either a concrete change is
proposed or the conclusion is explicitly "this was not knowable".

**Badly:**

- _The artifacts needed are missing._ Say so — a spine with no `outcome.md` is
  itself the finding.
- _The problem is a one-off._ Record that and stop. Manufacturing a process
  change for a non-recurring miss costs more than the miss.

## This stage is out-of-band

It **never changes status**. Running it does not reopen a completed item, and
there is no `completed → …` edge anywhere in the model.

Before `complete` it is an ordinary stage in `review`. After `complete` it is the
single permitted write into a `completed/` item, which stays immutable in every
other respect. It is never a gate: `complete` does not wait on it.

Both timings are deliberate — the need for a post-mortem is often only obvious
after the work has shipped.
