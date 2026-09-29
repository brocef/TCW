# Refuse to take over a claim that may still be in flight

Recovering an interrupted claim — `tcw work start <slug> --take-over` from the
CLI, or the web app's Recover button — acts at once on whatever it finds in the
store's claim staging area. A claim whose claimant is still alive, between the
two renames that publish it, can therefore be "recovered" out from under it. If
the claimant's publishing rename lands first, the item ends up active under the
recoverer's name while the claimant's own command reports that it started the
item, and the recoverer's command then fails (a server error in the web app).

What is wanted: recovery must not take a claim that may still be in flight. A
claim counts as interrupted only once it has sat unpublished for the same
500 ms window that an ordinary read already uses before it calls a claim
interrupted.

The window is microseconds wide in practice, and the defect predates the
recovery work that exposed it.

## Notes

- Written during an unattended run (the user asked for as many bugs fixed as
  possible, 2026-09-29) with nobody to ask; everything here comes from
  `intake.md`, which the code review of
  `2026-09-15-make-start-take-over-recover-an-interrupted-claim-from-the-cli-and-the-web-app`
  filed. Reference material: asked; none beyond the intake's own.
- The intake suggests checking how recently the claim's `state.yaml` changed.
  That is one way to do it, not a requirement; `spec` decides.

## References

- `tcw/store/fs.py` `FsWorkStore.start` (the take-over and recover branch) and
  `get` — the code with the race, and the 500 ms window to match.
- `tcw/serve/__init__.py` — the web app's Recover, which calls
  `start(..., recover=True)`.
- `tests/test_interrupted_claim.py` — how the existing tests make an
  interrupted claim.
