# Refuse web writes to sidecars a command generates

## What is wanted

`PUT /api/work/<slug>/sidecars/<name>` should refuse a sidecar that a command generates,
with a message naming the command that writes it, so the only way to change one is the
command that owns it.

The server already tells the web client which sidecars are generated, so the client
hides their Edit button, but the write route never checks. Any request that passes the
loopback-origin and content-type checks can overwrite:

- `rollup.md`, which `tcw work reconcile` regenerates, so the edit is silently lost on
  the next run;
- `tracker.yaml`, the item's tracker binding. It grants no claim (every tracker command
  re-reads the ticket), but it can make `tracker import` report a ticket as already
  bound, or refuse because the binding is malformed.

## Constraints

- The refusal belongs in the server, not in `write_sidecar`: the commands that own these
  files write through `write_sidecar` too.
- Not a security boundary in the strong sense — both files are in the user's own
  repository and a text editor can change them. The point is that a surface which hides
  an edit should not accept it.

## Notes

- Filed separately at the tracker bridge epic's request (its Risk 1) rather than absorbed
  into the child that added `tracker.yaml`.
- Checked at triage on `main`: the route checks only that the name is registered, plus a
  strict-mode-only special case for `tracker.yaml`; nothing reads the `generated` marker.
- Reference material: asked; none provided.
