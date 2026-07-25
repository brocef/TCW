# Outcome — superseded

Closed on 2026-07-23 (backlog audit): the verification gap this item recorded has
been closed by the automated Playwright suite that shipped with
`2026-07-22-modularize-and-standardize-the-tcw-web-client`.

## Coverage check

`web/e2e/parity.spec.ts` (12 scenarios) drives the real browser against a
throwaway fixture node and covers the item's checklist:

| Requested | Covered by |
| --- | --- |
| Work create form, edit fields + body | "creates and edits Work with live Markdown and dirty navigation protection" |
| Edit a lifecycle artifact | "edits lifecycle artifacts and preserves a draft across a stale write" |
| Edit the `capabilities.yaml` sidecar | same scenario (`.sidecar-edit-btn`, sidecar PUT/GET round-trip) |
| Work start / complete, incl. the complete modal's DoD acknowledgments | "runs Work start and complete lifecycle controls" (checks every dialog checkbox) |
| Complete modal's capabilities reconciliation reminder | assertion added on `.reconciliation-reminder` in that scenario (this closeout) |
| Drop a work item | "drops a backlog Work item through the confirmation modal" |
| Taxonomy create Vocabulary/Feature, edit fields | "creates and edits Taxonomy and Capability objects" |
| Capability create + edit metadata/body | same scenario |
| Surfaced check failures | "shows validation errors without dropping a Work draft"; "searches references and surfaces targeted validation warnings" |
| Markdown live preview | "creates and edits Work with live Markdown…" |
| Dirty-nav guard | same scenario |
| 409 stale-write recovery, draft kept | "edits lifecycle artifacts and preserves a draft across a stale write" |

The item's open question — "is a lightweight automated frontend smoke worth
standing up, or does a manual pass suffice?" — was answered by that work in
favour of automation, which is the better outcome than the one-off manual pass
this item scheduled.

## Note for the next runner

The suite needs a Chromium binary. The recorded `lifecycle-dialog-darwin.png`
golden was captured against Playwright's chromium build 1187; running against a
different local build (e.g. 1217 via
`PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`) fails that one screenshot comparison on
rendering differences alone. This is environmental, pre-existing, and unrelated
to any assertion — re-baseline deliberately, not reflexively.

## Resolution

`superseded` — by `2026-07-22-modularize-and-standardize-the-tcw-web-client`.
