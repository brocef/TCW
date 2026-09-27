# Refined outcome — Resolve a cross-node external blocker against the node that owns it

**Accepted** (unattended run, 2026-09-27).

- A blocker recorded as `<project-id>/<slug>` settles against the project that
  owns the item, anywhere in the registered graph; `start`, `complete`, `list`,
  the strict tracker check and `reconcile`'s Next line agree. A blocker on a
  finished local item — as `slug:` now, or as an older `external:` entry — no
  longer blocks forever. `reconcile`'s Next line no longer mixes up equal slugs
  in two nodes.
- Verified: the verifier found criteria 1–5 met by test and by hand (including
  sibling, parent and routing-node targets); the full suite on the branch merged
  with main (4710 passed, 3 skipped); the report's reproduction driven through the CLI.
- Review: four findings fixed in this change (machine-dependent answer for a
  bare entry, prose judged by an error message's text, copied `list` labels not
  removable, a trap default in `_render`), each with a test.

## Deferred

- **GitHub #28 stays open until publication.** This repository closes an
  originating issue only after the version carrying the fix is cut and pushed,
  and the earlier reply on #28 needs correcting then — nothing is posted
  without the exact text approved first.
- Follow-up filed:
  `2026-09-27-refuse-a-blocker-that-names-its-own-item-by-qualified-ref-and-settle-status-path-blockers`.
- Not done, recorded in `outcome.md`: the goal 4 note and the goal 5 cache.
