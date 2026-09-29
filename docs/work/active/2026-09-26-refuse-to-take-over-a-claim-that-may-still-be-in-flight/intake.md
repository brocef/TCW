# Refuse to take over a claim that may still be in flight

`FsWorkStore.start(..., take_over=True)` (and `recover=True`, which the web app's
Recover uses) recovers an item left in `.claiming/<slug>-<hex>`. It does so at
once, while an ordinary read (`get`) first waits 500 ms before calling a claim
interrupted. So a claim whose claimant is still between its two renames can be
"recovered": the recoverer writes `owner` into the claim's `state.yaml`, and if
the claimant's publishing rename lands before the recoverer's own rename, the
item is published active under the recoverer's owner while the claimant's command
reports "started"; the recoverer's rename then fails (a 500 from the web app).
The window is microseconds, and it predates the recovery work.

Refuse recovery of a claim whose `state.yaml` changed within the same 500 ms
window `get` uses, in both the take-over and recover branches.

## Origin

Found by the code review of
2026-09-15-make-start-take-over-recover-an-interrupted-claim-from-the-cli-and-the-web-app
(placed by the reviewer in "needs a separate change"). Bug.

## References

- tcw/store/fs.py `FsWorkStore.start` (take-over / recover branch) and `get`
