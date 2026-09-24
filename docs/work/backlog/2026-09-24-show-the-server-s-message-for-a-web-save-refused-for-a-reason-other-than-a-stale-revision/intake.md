# TCW-1 — The web client shows any 409 as a stale write

Imported on 2026-09-24 from [TCW-1](https://proposit.atlassian.net/browse/TCW-1) (jira-cloud).

## Desired outcome

When the local web server refuses a save for a reason other than a stale revision,
the web app shows the server's message instead of "Stale write detected".

## Context

Found by code review of
`2026-09-15-refuse-web-writes-to-sidecars-a-command-generates`.

`web/client/src/ui/app.tsx` treats every 409 from a resource save as a stale write:
it sets the conflict banner ("Stale write detected — The server version changed",
`content-views.tsx`) and drops `result.error`. The server also answers 409 for
strict-tracker-mode refusals and for a write to a generated sidecar, each with a
message naming the command to use. Not reachable from the UI today for sidecars
(no edit control is shown for generated ones), but reachable for the strict
refusals the app does offer controls for.

## Notes

- Either distinguish by the error body, or give non-stale refusals their own status.
