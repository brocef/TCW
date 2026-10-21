# Stage: spec

**Purpose.** Decide _what_ to build and why, technically, before deciding how.
A spec that describes an implementation has skipped its own job.

**Inputs.** The request, read as filed:

{{tcw:request}}`tcw work show <slug>` prints it.{{/tcw:request}}

Its References are where research starts, not where it ends; with neither
references nor an "asked; none provided" note, nobody asked. Repository
discovery is unrestricted.

**Resuming.** Read the newest `handoff-*.md` beside the file
`tcw work path <slug> spec` names, as a description of the work when it was
written, and check for anything newer before trusting it. To leave one, write
it to `tcw work path <slug> spec --handoff`.

**Produce** three things:

- The spec, at `tcw work path <slug> spec`, with seven sections: **Capability
  changes**, **Problem**, **Goals**, **Non-goals**, **Design**, **Acceptance
  criteria**, **Risks**.
- `capabilities.yaml`, in the folder `tcw work path <slug>` prints: the
  capability paths this work adds, changes or removes, under `new:`,
  `changed:` and `removed:`, and taxonomy terms under `taxonomy:` the same
  way. It declares; it writes no records. Implement changes the records.
- **The QA plan**, posted with `tcw work comment <slug>` (the text on stdin),
  for readers outside engineering. Its first line is `QA plan`. It gives one
  scenario per product change in the request, the expected behavior of each,
  the environment or accounts needed, and what is not tested. With no product
  changes, it says so and names what qa should confirm did not change. A
  revised spec posts a new QA plan whose second line names the one it replaces.

## Steps

1. **Product first.** For each product change, check the project's taxonomy
   and capabilities for the terms and capabilities it touches.
2. Read the request's references, then the code the change touches. **Ground
   every claim about current behavior in the code, with file and line.**
3. Write acceptance criteria someone else can check without asking what you
   meant. "Works correctly" is not one.
4. State what is out of scope, especially anything close enough to drift in.
5. **A sweep for defects like the reported one is repository-wide by default**,
   or the spec says why it was narrowed.
6. **Self-review.** Every file and line cited still shows what you claim;
   every criterion you can run against the code today has been run; any
   criterion two readers could check two ways is pinned to one.

## Exit badly

- _The code contradicts the request._ Stop and return to request. A spec that
  quietly reinterprets the request is worse than one that refuses.
- _The requester revises the request._ It stays at spec: record it as an
  amendment (a dated `## Added`; in Jira, an `Added` comment), and follow it.
- _The work is too large for one item._ Say so; plan decomposes it.
- _You cannot ground a claim._ Mark it as an assumption, not a fact.
- _`tcw work comment` failed._ Report the command and its exit code, do not
  advance, and leave the spec as written. Running this stage again posts the
  QA plan.
