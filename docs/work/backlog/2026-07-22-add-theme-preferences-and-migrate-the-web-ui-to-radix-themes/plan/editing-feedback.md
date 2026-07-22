## Objective

Hard-convert editing, lifecycle, validation, and operational-feedback surfaces
to Radix, then remove the obsolete bespoke visual system without changing any
domain or API behavior.

## Pre-stage checks

- Confirm the browsing-shell stage is verified and committed.
- Run all create/edit/resource/lifecycle/dirty-state/validation/stale-write
  component and Playwright tests.
- Inventory each text field, select, textarea, checkbox, button, tag, editor
  header, lifecycle action, artifact control, modal, warning, notification, and
  reference-input presentation rule.

## Implementation

- Convert inputs, selects, text areas, checkboxes, buttons, tags, editor headers,
  lifecycle actions, artifact controls, and reference-input presentation to
  Radix components.
- Use Radix `Dialog` for Start and Complete workflows and `AlertDialog` for the
  destructive Drop confirmation. Preserve focus restoration, dismissal rules,
  validation, acknowledgments, and request payloads.
- Use `Callout`, `Badge`, and themed surfaces for validation errors, warnings,
  stale-write conflicts, reconciliation reminders, empty/error states, and
  notifications.
- Remove legacy theme variables, hard-coded light colors, and bespoke visual
  button/form/modal styling. Retain only layout/behavior CSS consuming Radix
  tokens.
- Preserve every API contract, route, create/edit/resource workflow, Markdown
  split editor, dirty-navigation guard, validation recovery, stale-write
  recovery, lifecycle transition, and accessibility contract.
- Add/update deterministic light/dark desktop/responsive screenshots for the
  editor, lifecycle dialog, validation warning, and conflict state.

## Post-stage checks

- Run typecheck, lint, Vitest, and all mutation/lifecycle/feedback Playwright
  tests plus the new screenshot matrix.
- Exercise dirty navigation, validation retry, stale-write recovery, reference
  input, Start, Complete, and Drop by keyboard in a live browser.
- Search for old variables, hard-coded light colors, native controls that should
  be Radix, and bespoke visual modal/form/button rules. Document any retained
  custom CSS as behavior/layout-specific.
- Commit the complete editing-and-feedback stage before rebuilding final assets
  or updating release documentation.
