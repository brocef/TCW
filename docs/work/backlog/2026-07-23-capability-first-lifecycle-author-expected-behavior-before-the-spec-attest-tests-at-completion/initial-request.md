# Capability-first lifecycle: author expected behavior before the spec, attest tests at completion

## Origin

GitHub issue [#5](https://github.com/brocef/TCW/issues/5), filed 2026-07-18.

## Problem

The capabilities axis is front-loaded in tooling but not in practice. `tcw work
new` has the `## Capability changes` planning gate and `tcw work complete` fails
closed on a declared `new:` capability still reading `Missing` — but both gates
check that a capability *exists* and that its *status* flips, never that its
**behavior description** was authored first and drove the work. So a capability
reads as documentation of what was built rather than the spec that shaped it.

Second gap: the completion gate checks capability status, not substance. Nothing
prompts a check that the implementation's tests actually exercise the behavior
the capability describes.

## Product changes

Two lightweight refinements. No new objects, no CLI-breaking changes.

1. **Reorder: capability expected-behavior becomes the first authored artifact.**
   For any item with a product delta, author the capability's `description.md`
   expected behavior (a few plain bullets) *before* `spec.md`. The artifact spine
   for product items reads `capability-behavior → spec.md → plan.md → …`. This is
   guidance in the `tcw-work` and `tcw-capabilities` lifecycle docs — no
   enforcement change.

2. **Fold a capability-vs-tests attestation into the existing completion
   verification.** One added prompt in the verify-before-complete step: re-read
   each declared capability's behavior, confirm the item's tests exercise it, note
   any gap in `outcome.md`. Judgment-based attestation, deliberately not a
   mechanical check. May surface as a non-blocking DoD acknowledgment line in the
   `complete` gate and the web-complete modal.

## Technical changes

Mostly none — this is skill and lifecycle guidance. The only possible mechanism
change is the extra DoD acknowledgment line, which is data in the existing
checklist, not new machinery.

## Meta changes

Establishes the capability as the genuine source of truth for agentic work: plan
*from* the capability behavior, implement, then attest the tests match it.

- Explicitly **not** in scope (rejected in the issue as too heavy): structured or
  executable acceptance-criteria fields, and test-ID traceability tags.
- Docs to sync: `skills/tcw-work/SKILL.md` and its lifecycle references,
  `skills/tcw-capabilities/SKILL.md`, `README.md` if the DoD checklist is
  documented there, changelog + release notes.

## Open questions for spec

- Does the reordering apply to every product delta, or only to items declaring a
  `new:` capability (as opposed to a `changed:` one)?
- Should the attestation be a distinct DoD line, or folded into the existing
  "capabilities reconciled" acknowledgment? A sixth checkbox has an ongoing cost
  on every completion.
- Does the web-complete modal need the same line to stay in parity with the CLI
  gate?
