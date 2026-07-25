# Live browser test pass for the interactive web editor

## Origin

Verification gap on `2026-07-02-interactive-local-web-editor-for-tcw-objects`.
That work shipped with the full write stack verified via the test suite (436
tests) and a live write-API smoke, but the actual in-browser UI was never driven
end-to-end because the Chrome automation extension was not connected.

## Desired outcome

Drive the running `tcw serve` app in a real browser (against a throwaway node) and
confirm each axis' flows render and behave:

- Work: create form (all fields), edit fields + body, edit a lifecycle artifact and
  the `capabilities.yaml` sidecar, and start/complete/drop — including the complete
  modal's DoD acknowledgments + capabilities reconciliation reminder.
- Taxonomy: create Vocabulary/Feature, edit fields, surfaced check failures.
- Capabilities: create (incl. add-to-existing-collection), edit metadata/body,
  surfaced check failures.
- Cross-cutting: Markdown live preview, dirty-nav guard, and 409 stale-write
  recovery (edit in the browser, mutate via CLI, save → conflict banner, draft kept).

## Notes

- Plan item 5.11 originally scheduled this; capture it here so it isn't lost.
- Consider whether a lightweight automated frontend smoke is worth standing up, or
  whether a manual pass suffices.
