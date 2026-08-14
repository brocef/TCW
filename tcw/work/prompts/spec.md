# Stage: spec

**Purpose.** Decide _what_ to build and why, before deciding how. A spec that
describes an implementation has skipped its own job.

**Inputs.** `initial-request.md` and its `## References` — the starting set for
research, not the limit of it. With neither that section nor an "asked; none
provided" note in `## Notes`, nobody asked: research from scratch rather than
reading silence as "there was nothing to point at". Repository discovery is
unrestricted; a spec written without reading the code it changes is a guess.

**Produce** `spec.md`, in the item's folder, with seven required sections:
**Capability changes** (planned ledger deltas only — no records are written
here), **Problem**, **Goals**, **Non-goals**, **Design**, **Acceptance
criteria**, **Risks**. Optional `## Notes`.

## Steps

1. **Product-first.** On any user-facing delta, check the project's taxonomy
   for the Vocabulary and Feature entries it touches, and the standing
   capability ledger, before writing the technical design.
2. Read the request's references first, then the code the change touches.
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

## Exit badly

- _Reading the code contradicts the request._ Stop and return to `request`. A
  spec that quietly reinterprets the request is worse than one that refuses.
- _The change is too large for one item._ Say so and decompose it.
- _You cannot ground a claim._ Mark it as an assumption in `## Notes` rather
  than stating it as fact.
