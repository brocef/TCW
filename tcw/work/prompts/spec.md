# Stage: spec

**Purpose.** Decide _what_ to build and why, before deciding how. A spec that
describes an implementation has skipped its own job.

**Inputs.** {{tcw:body}}the item's body artifact{{/tcw:body}}, read as filed.
An `intake.md` is raw arrival: the `request` stage has not run, so work from the
intake itself, and expect no `## References` unless whoever filed it wrote one.
In an `initial-request.md` that section is the research starting set, not its
limit; with neither it nor an "asked; none provided" note, nobody asked — so
research from scratch, not from silence. Repository discovery is unrestricted.

**Produce** `spec.md`, in the item's folder, with seven required sections:
**Capability changes** (planned ledger deltas only — no records are written
here), **Problem**, **Goals**, **Non-goals**, **Design**, **Acceptance
criteria**, **Risks**. Optional `## Notes`.

## Steps

1. **Product-first.** On any user-facing delta, check the project's taxonomy
   for the Vocabulary and Feature entries it touches, and the standing
   capability ledger, before writing the technical design.
2. Read the body's references first, then the code the change touches.
   **Ground every claim about current behavior in the code, with file and
   line.** A claim recalled rather than checked is how a spec starts lying.
3. Write acceptance criteria that are _checkable_ by someone else without
   asking what you meant. "Works correctly" is not a criterion; "an item in
   `review` still blocks its dependents" is.
4. State what is out of scope, especially anything adjacent enough to drift in.
5. **A sweep for defects sibling to the reported one is repo-wide by default**,
   or the spec says why it was narrowed. A scope inherited from the report — or
   from the previous stage — is a scope nobody chose.
6. Commit `spec.md` on its own, before planning.

## Self-review, before committing

- Every `file:line` citation still resolves to what the spec claims it shows;
  a sibling change landing mid-spec moves lines.
- Every acceptance criterion executable against the tree today has been run,
  and one that fails is reworded or dropped rather than shipped.
- Any criterion two readers could check two different ways is pinned to one.

## Exit badly

- _Reading the code contradicts the request._ Stop and return to `request`. A
  spec that quietly reinterprets the request is worse than one that refuses.
- _The change is too large for one item._ Say so and decompose it.
- _You cannot ground a claim._ Mark it as an assumption in `## Notes` rather
  than stating it as fact.
