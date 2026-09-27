# Show the server's message for a web save refused for a reason other than a stale revision

## What is wanted

When the local web server refuses a save for any reason other than a stale
revision, the web app shows the server's own message, not "Stale write detected".

## Why

`web/client/src/ui/app.tsx` treats every 409 from a resource save as a stale
write: it raises the conflict banner ("Stale write detected — The server version
changed", from `content-views.tsx`) and throws away `result.error`. The server
also answers 409 for strict-tracker-mode refusals and for writes to a generated
sidecar, and each of those messages names the command the user should run
instead. Showing "stale write" for them tells the user to reload, which does not
help.

## Scope

- Reachable today through the strict-tracker refusals, because the app offers
  controls for them.
- Not reachable today for generated sidecars, because no edit control is shown
  for them. Fixing the general case covers them too.

## Notes

- From Jira TCW-1, filed after the code review of
  `2026-09-15-refuse-web-writes-to-sidecars-a-command-generates`.
- The ticket names two possible fixes: tell the cases apart by the error body, or
  give refusals that are not stale writes their own HTTP status. Choosing between
  them is the spec's job.
- Reference material: not asked. The request is written from the ticket alone,
  which was specific enough.
