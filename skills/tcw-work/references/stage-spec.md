# Stage: spec

## Purpose

Decide _what_ to build and why, before deciding how. A spec that describes an
implementation has skipped its own job.

## Inputs

`initial-request.md`, including its `## References` section when present — the
starting set for research, not the limit of it. With neither that section nor an
"asked; none provided" note in `## Notes`, nobody asked: research from scratch
rather than reading the silence as "there was nothing to point at".

Repository discovery is unrestricted, and this stage depends on it: a spec
written without reading the code it changes is a guess.

## Produce

`spec.md`, in the item's folder.

Required sections: **Capability changes** (planned ledger deltas only — no
records are written here), **Problem**, **Goals**, **Non-goals**, **Design**,
**Acceptance criteria**, **Risks**. An epic's spec replaces Design with the child
boundaries and their ordering constraints.

Optional `## Notes`.

**Ground every claim about current behavior in the code**, with file and line.
Claims recalled rather than checked are how a spec starts lying.

## Steps

1. Run `tcw work lifecycle --stage spec` and honor any binding it reports.
   — agent `[judgment]`
2. **Product-first.** If there is any product delta, check the taxonomy for
   Vocabulary and Feature entries first, then run the tcw-capabilities planning
   check, then write the technical design. **REQUIRED SUB-SKILL: Use
   tcw-capabilities.** — agent `[judgment]`
3. Read the request's references first, then the code the change touches, and
   record what is actually true, with file and line. — agent `[judgment]`
4. Write acceptance criteria that are _checkable_. "Works correctly" is not a
   criterion; "an item in `review` still blocks its dependents" is.
   — agent `[judgment]`
5. State what is out of scope, especially anything adjacent enough to drift in.
   — agent `[judgment]`
6. **A sweep for defects sibling to the reported one is repo-wide by default**,
   or the spec says why it was narrowed. A scope inherited from the report — or
   from the previous stage — is a scope nobody chose; re-derive it from the
   criterion the fix is meant to satisfy. — agent `[judgment]`
7. Commit `spec.md` on its own, before planning. — agent `[judgment]`

This stage is **delegable** to a subagent. `Inputs` above is its context brief
and `Produce` is its return contract; the coordinating session re-reads the
artifact and checks the required sections before moving on.

## Exit

**Well:** every acceptance criterion could be handed to someone else and checked
without asking you what you meant.

**Badly:**

- _Reading the code contradicts the request._ Stop and return to `request`. A
  spec that quietly reinterprets the request is worse than one that refuses.
- _The change is too large for one item._ Say so and decompose — see
  `decompose.md` for nested pieces, `epic-deltas.md` for independently scheduled
  ones.
- _You cannot ground a claim._ Mark it as an assumption in `## Notes` rather than
  stating it as fact.
