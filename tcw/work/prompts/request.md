# Stage: request

**Purpose.** Record what is being asked for and why, in the requester's terms,
before anyone decides what to build — intent a conversation otherwise loses.

**Inputs.** `intake.md` when the item has one: the raw input it started from.
Intake is not a request; this stage writes the first one. Repository discovery
is unrestricted.

**Produce** `initial-request.md`, at the item's folder root. Required: a title,
and enough of the request that someone resuming cold knows what was wanted.
Optional `## Notes` — anything worth keeping that has no home in the request
itself. Optional `## References` — material the requester considers relevant (a
link, a repo path, another work item), each with a one-line _why it matters_.
The `spec` stage reads that section; bare URLs with no reason save it nothing.

## Steps

1. **Ask the user what is unclear.** This stage exists to obtain input only
   they have.
2. **Ask the requester for reference material** — docs, a spec, an issue, prior
   art, an in-repo file, a related item — each recorded with a one-line reason.
   Do not fetch, validate, or summarize it here; a link is context for `spec`,
   not a decision it must accept. If they have none, write "asked; none
   provided" in `## Notes`, so `spec` can tell that apart from a stage that
   never asked.
3. Write the request in the requester's terms. Resist specifying a solution:
   that is `spec`'s job, and pre-empting it here hides the alternatives.
4. Record constraints, deadlines, and anything explicitly out of scope.
5. Commit `initial-request.md` on its own.

## Exit badly

- _The request contradicts something already true of the codebase._ Say so and
  ask, rather than writing down a request that cannot be satisfied.
- _The work is larger than one item._ Say so now; splitting after a spec is
  written wastes the spec.
- _There is no user to ask._ Write from the available evidence and mark the
  assumptions in `## Notes`, so `spec` knows which parts are inference.
