# Stage: spec

## Purpose

Decide *what* to build and why, before deciding how. A spec that describes an
implementation has skipped its own job.

## Inputs

`initial-request.md`.

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
3. Read the code the change touches and record what is actually true, with
   references. — agent `[judgment]`
4. Write acceptance criteria that are *checkable*. "Works correctly" is not a
   criterion; "an item in `review` still blocks its dependents" is.
   — agent `[judgment]`
5. State what is out of scope, especially anything adjacent enough to drift in.
   — agent `[judgment]`
6. Commit `spec.md` on its own, before planning. — agent `[judgment]`

This stage is **delegable** to a subagent. `Inputs` above is its context brief
and `Produce` is its return contract; the coordinating session re-reads the
artifact and checks the required sections before moving on.

## Exit

**Well:** every acceptance criterion could be handed to someone else and checked
without asking you what you meant.

**Badly:**

- *Reading the code contradicts the request.* Stop and return to `request`. A
  spec that quietly reinterprets the request is worse than one that refuses.
- *The change is too large for one item.* Say so and decompose — see
  `decompose.md` for nested pieces, `epic-deltas.md` for independently scheduled
  ones.
- *You cannot ground a claim.* Mark it as an assumption in `## Notes` rather than
  stating it as fact.
