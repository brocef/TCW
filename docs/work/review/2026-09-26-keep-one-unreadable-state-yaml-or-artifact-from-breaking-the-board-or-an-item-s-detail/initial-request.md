# Keep one unreadable state.yaml or artifact from breaking the board or an item's detail

One item with a damaged file should be that item's problem, not everybody's.
Today a single item whose `state.yaml` is not valid UTF-8 (or is a folder), or
whose request text is not valid UTF-8, makes `tcw work list` fail for the whole
board, and makes that item's detail fail in the web app. The same failure was
fixed for `capabilities.yaml` in
`2026-09-15-make-the-capability-gate-honor-a-configured-ledger`; this is the rest
of it.

Wanted: the board still lists every item, the damaged item's own views still
load, and the damage is reported rather than crashing.

Also asked: decide whether a web save guarded by a revision may replace a file
that is not valid UTF-8. Today the detail view gives such a sidecar a revision
from a tolerant read, but the save checks it with a strict read, so a guarded
save fails with the decoder's byte-offset message while an unguarded one
succeeds.

## Notes

- Written during an unattended run (2026-09-29) with nobody to ask; everything
  comes from `intake.md`. Reference material: asked; none beyond the intake's.
- Reproduced on 2026-09-29 against the released CLI in a scratch node: a
  non-UTF-8 `state.yaml`, a folder named `state.yaml`, and a non-UTF-8
  `intake.md` each make `tcw work list` fail for every item. The last one is not
  in the intake — the board reads each item's request text too.

## References

- `tcw/store/fs.py` `FsWorkStore._safe_yaml`, `_read_item`, `_resolve_body`,
  `_present`, `_detail_snapshot`, `write_sidecar`, `write_artifact` — the readers
  and the revision guards involved.
- `tcw/store/fs.py` `_read_capabilities_sidecar` — the pattern the
  `capabilities.yaml` fix used.
