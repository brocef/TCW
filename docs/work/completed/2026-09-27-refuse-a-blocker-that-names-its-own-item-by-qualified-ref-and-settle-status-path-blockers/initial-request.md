# Refuse a blocker that names its own item by qualified reference, and settle status-path blockers

Two ways a blocker is recorded as external text when it names an item of this
very node, so it never resolves:

1. **A reference qualified with this node's own project id.** In node `pa`,
   `tcw work edit <s> --blocked-by pa/<s>` is recorded as `external:`, so the
   item blocks itself and `start` needs `--force`; the self-block check never
   sees it. The same for `pa/<other>`: recorded as text rather than as the local
   item.
2. **A status-path locator** — `backlog/<slug>`, `completed/<slug>` — is stored
   as external text and never resolves.

Wanted: both are recorded as the local item they name, so the existing
self-block and cycle checks apply and they resolve like any local blocker.

## Notes

- Unattended run (2026-09-29); from `intake.md`, filed by the review of
  `2026-09-09-resolve-a-cross-node-external-blocker-against-the-node-that-owns-it`.
  Reference material: asked; none beyond the intake's.
- The intake also names a cycle *across* nodes (A/x waits on B/y, B/y on A/x)
  as undetected, calling recording own-qualified refs "the cheap half". The
  cross-node cycle is filed as its own follow-up rather than folded in.
- Reproduced 2026-09-29 in a scratch node `pa`: `--blocked-by pa/<self>` and
  `--blocked-by backlog/<other>` are both stored as `external:`.

## References

- `tcw/store/base.py` `WorkStore._entry_for`, `_normalize_ref`,
  `_check_new_blocker`; `tcw/store/fs.py` `external_blocker_state`.
