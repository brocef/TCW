# Refined outcome

## Verification decision

**Accepted**, under the standing decision to drive the epic to completion and
refine from use.

## Evidence

- 873 Python tests (from 851 at the start of this child); 44 web tests;
  `tcw validate` OK.
- A real repository with a configured `pre` hook, driven by hand: hook failing →
  stderr surfaced, exit 1, item still `backlog`; gate satisfied → started;
  `--directive` bound → one sentence, unbound → empty stdout with exit 0; the
  binding rewritten as a bare string → validate exit 1 naming
  `work.lifecycle.stages.spec[0]`.

## Capability and taxonomy reconciliation

- **New capabilities, both `Supported`:** `work/configure-the-work-lifecycle`,
  `work/inspect-the-lifecycle-contract`.
- **New taxonomy:** `work-item/lifecycle-stage` (Vocabulary) and
  `configurable-work-lifecycle` (Feature, involving `lifecycle-stage` and the
  existing `work-item/transition`).
- The epic spec also proposed a `lifecycle-transition` term. **Not added** —
  `work-item/transition` already exists and means exactly that. Adding a second
  term for the same concept to match a planning document would be the taxonomy
  drifting to fit prose rather than the other way round.

## Consequence: child 3 is superseded

`tcw work methodology <stage>` was scoped to do two things, and this child
resolved both:

1. **"Name the skill for this stage, harness-neutrally."** Already shipped, twice
   over: `tcw work lifecycle --stage <id>` reports it in human and `--json` form,
   and `--directive` emits the ready-to-follow instruction. The epic spec's own
   justification for child 3 — *"every stage document can carry one
   harness-neutral step"* — is satisfied verbatim by a command that exists.
2. **"Fall back to a shipped default binding per stage."** This one should not
   ship at all. A default binding means TCW naming a specific methodology skill
   for a specific stage, and the epic's own non-goals list *"built-in methodology
   presets"* first. Child 3 would have contradicted the spec it was drawn from.

Shipping a second command answering the same question would be the exact defect
this initiative exists to remove: two surfaces, drifting. Recorded here and acted
on at the epic level.

## Notes

Both of 2a's deferred items closed here, because they were the same surface: the
web complete modal now states that configured hooks do not run from the web app,
**and** that a refused auto-commit still moves the item while reporting to
`tcw serve`'s terminal.

**`pr` is still unconsumed** after two children that were each predicted to use
it. Child 4's stage documents are its last plausible consumer.

**Child 4 must read `LIFECYCLE_STEPS` before writing a single stage document.**
The objective, inputs, produced artifact, status move, and gates for every id now
live in one machine-readable table. A stage document that disagrees with it is
wrong by construction, and that is now checkable rather than a matter of two
prose documents happening to match.
