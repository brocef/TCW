# The web server accepts writes to sidecars that a command generates

## Desired outcome

`PUT /api/work/<slug>/sidecars/<name>` refuses a sidecar whose `WORK_SIDECARS`
entry is marked `generated`, with a message naming the command that writes it,
so the only way to change one is the command that owns it.

## Context

Found while planning the external-tracker bridge epic
(`2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge`,
Risk 1), and filed as that epic's spec asked: separately, not absorbed into the
child that added `tracker.yaml`
(`2026-09-12-claim-an-external-tracker-ticket-and-bind-it-to-a-work-item`).

`generated` is honored only by the web client. The server reports it
(`tcw/serve/__init__.py:646`) so the client can hide its Edit button, but the
write route checks only that the name is registered and the item exists, then
calls `write_sidecar` (`tcw/serve/__init__.py:1281-1307`). Any request that passes
the loopback-origin and content-type checks can overwrite:

- `rollup.md`, which `tcw work reconcile` regenerates, so an edit is silently
  discarded on the next run;
- `tracker.yaml`, the binding between an item and a tracker ticket. An edit there
  does not grant a claim — every tracker command re-reads the ticket, and the
  binding is never taken as proof — but it can make `tcw work tracker import`
  report a ticket as already bound, or refuse because the binding is malformed.

## Notes

- The fix belongs in the server, not in `write_sidecar`: the commands that own
  these files write them through `write_sidecar` too.
- Not a security boundary in the strong sense. Both files live in the user's own
  repository and a text editor can change them. The point is that a surface
  which hides an edit button should not accept the edit.
