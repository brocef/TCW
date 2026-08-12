# Stage: request

## Purpose

Record what is being asked for and why, in the requester's terms, before anyone
decides what to build. This stage exists to capture intent that would otherwise
be lost between a conversation and a spec.

## Inputs

`intake.md` when it exists — the raw input the item started from, written by
`tcw work new` from piped stdin or by `tcw work inbox accept` from the entry.
Neither seeds a request; this stage writes the first one.

Repository discovery is unrestricted.

## Produce

`initial-request.md`, at the item's folder root. **It is this stage's own
artifact and absent until this stage runs** — that is what makes `R` on the board
mean something. Until then the item's body surface shows its `intake.md`, and
writing the request promotes the item off raw intake, leaving the intake itself
untouched.

Required: a title, and enough of the request that someone resuming cold knows
what was wanted. For an epic it also carries the coordination goal and is the
managed target for `tcw work reconcile`'s rollup.

Optional `## Notes`: anything worth keeping that has no home in the request
itself.

Optional `## References`: material the requester considers relevant — a link, a
repo path, or another work item — each with a one-line _why it matters_. The
`spec` stage reads it; bare URLs with no reason attached save it nothing.

## Steps

1. Run `tcw work lifecycle --stage request` and honor any binding it reports.
   — agent `[judgment]`
2. **Ask the user what is unclear.** This stage is not delegable to a subagent
   for exactly this reason: it exists to obtain input only the user has.
   — agent `[judgment]`
3. **Ask the requester for reference material.** Docs, a spec, an issue, prior
   art, an in-repo file, a related item — record each with a one-line reason. Do
   not fetch, validate, or summarize here; a link is context for `spec`, not a
   decision it must accept. If they have none, note "asked; none provided" in
   `## Notes`, so `spec` can tell that apart from a stage that never asked.
   — agent `[judgment]`
4. Write the request in the requester's terms. Resist specifying a solution;
   that is the `spec` stage's job and pre-empting it here hides the alternatives.
   — agent `[judgment]`
5. Record constraints, deadlines, and anything explicitly out of scope.
   — agent `[judgment]`
6. Commit `initial-request.md` on its own. — agent `[judgment]`

## Exit

**Well:** the request states a problem and its constraints, and `spec` can start
without re-interviewing anyone or re-finding the requester's sources.

**Badly:**

- _The request contradicts something already true of the codebase._ Say so and
  ask, rather than writing down a request that cannot be satisfied.
- _The work is larger than one item._ Say so now. Splitting after a spec is
  written wastes the spec.
- _There is no user to ask._ Write the request from the available evidence and
  mark the assumptions in `## Notes`, so the `spec` stage knows which parts are
  inference.
