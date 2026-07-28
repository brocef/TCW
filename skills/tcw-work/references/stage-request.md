# Stage: request

## Purpose

Record what is being asked for and why, in the requester's terms, before anyone
decides what to build. This stage exists to capture intent that would otherwise
be lost between a conversation and a spec.

## Inputs

`initial-request.md` as it stands — `tcw work new` and `tcw work inbox accept`
both seed it.

Repository discovery is unrestricted.

## Produce

`initial-request.md`, at the item's folder root. It is the always-present body
and overview surface, so it is never absent — this stage makes it *say something*.

Required: a title, and enough of the request that someone resuming cold knows
what was wanted. For an epic it also carries the coordination goal and is the
managed target for `tcw work reconcile`'s rollup.

Optional `## Notes`: anything worth keeping that has no home in the request
itself.

## Steps

1. Run `tcw work lifecycle --stage request` and honor any binding it reports.
   — agent `[judgment]`
2. **Ask the user what is unclear.** This stage is not delegable to a subagent
   for exactly this reason: it exists to obtain input only the user has.
   — agent `[judgment]`
3. Write the request in the requester's terms. Resist specifying a solution;
   that is the `spec` stage's job and pre-empting it here hides the alternatives.
   — agent `[judgment]`
4. Record constraints, deadlines, and anything explicitly out of scope.
   — agent `[judgment]`
5. Commit `initial-request.md` on its own. — agent `[judgment]`

## Exit

**Well:** the request states a problem and its constraints, and `spec` can start
without re-interviewing anyone.

**Badly:**

- *The request contradicts something already true of the codebase.* Say so and
  ask, rather than writing down a request that cannot be satisfied.
- *The work is larger than one item.* Say so now. Splitting after a spec is
  written wastes the spec.
- *There is no user to ask.* Write the request from the available evidence and
  mark the assumptions in `## Notes`, so the `spec` stage knows which parts are
  inference.
