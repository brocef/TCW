# Rework: broaden Playwright coverage for lifecycle document tabs

The implementation is not yet accepted. Add browser-level regression coverage
for the new flows beyond the existing present-document rendering and Spec edit
path.

## Required coverage

- Verify Initial Request editing from its tab and persistence after save.
- Verify Implementation Plan editing from its tab and persistence after save.
- Verify a work item without Spec or Implementation Plan keeps both tabs
  visible, shows the correct not-yet-present state, and offers no edit action.
- Verify selecting another work item resets the active document tab to Initial
  Request and does not retain the prior item's rendered content.
- Preserve the existing browser assertions for tab order, default selection,
  Spec/Plan rendering, Spec editing, sidecar editing, and stale-write handling.

Run the focused Playwright scenarios independently of the known unrelated
taxonomy-fixture failure in the full serial suite, then update `outcome.md` with
the added coverage and results before resubmitting.
