# Detect a blocker cycle that runs across nodes

A blocker cycle through two nodes — `A/x` waits on `B/y`, `B/y` on `A/x` — is not
detected: `_check_new_blocker` and `_reaches` follow only `slug:` entries within
one store, and a cross-node blocker is stored as `external: <project-id>/<slug>`.
Both items then block each other forever and `start` needs `--force`.

Split out of
2026-09-27-refuse-a-blocker-that-names-its-own-item-by-qualified-ref-and-settle-status-path-blockers
(2026-09-29), which fixed the local half: a reference qualified with this node's
own id is now recorded as `slug:` and so meets the checks.

## References

- tcw/store/base.py `_check_new_blocker`, `_reaches`; tcw/store/fs.py
  `external_blocker_state`, `resolve_qualified_work_ref`
