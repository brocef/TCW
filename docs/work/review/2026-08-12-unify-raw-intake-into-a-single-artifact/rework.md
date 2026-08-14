# Rework — Unify raw intake into a single artifact

Second rejection at `verify`. The first rejection's three items landed and were
re-verified (`38a79df`, `9e0de85`, `607a891`) — the web app's request tab, its
editor seeding, and the promotion notice. That history is recorded in
`outcome.md` under "After the rejection"; this document is now the **second**
pass's outstanding work.

## What still has to be done

### `tcw work reconcile` must stop creating the request

`recursion.py:197` composes `store.path(epic_slug) / "initial-request.md"` and
writes the rollup block into it, creating the file when absent. On a fresh epic
that is a code path producing an `initial-request.md` **without the `request`
stage running** — the exact thing criterion 4 asserts no longer happens. The
grep it uses (`"## Product changes"`) passes because reconcile writes real
content rather than a template, so the criterion reads clean while the property
behind it does not hold. Raised in the first pass and held out of the first
rework; the requester has now put it in scope.

Two defects, one cause:

1. **The board lies.** A reconciled epic shows `R` — "someone wrote this up" —
   when all that happened is that a machine wrote a table into the file. That is
   the letter this item exists to make meaningful.
2. **The path is composed.** `store.path(...) / "<filename>"` is a hardcoded
   filesystem reference of exactly the kind `CLAUDE.md` names under "Keep out of
   the model". No remote adapter can honor it, and the rollup is the one
   operation an external tracker would most obviously implement differently.

**Move the rollup to its own bounded resource.** `rollup.md` as a **sidecar** —
`WORK_SIDECARS`, `media_type: text/markdown`, no validation rule — not an
artifact:

- The rollup is **generated**, not authored. Every `WORK_ARTIFACTS` name is the
  output of a lifecycle stage a human or agent runs; the rollup is the output of
  a command. Registering it as an artifact would give it a board letter and place
  it in a lifecycle it has no position in.
- `write_sidecar` is already on the abstract `WorkStore`
  (`base.py:1166`) and already does the atomic write and the staging that
  `reconcile` currently hand-rolls. The whole change at the write site is calling
  it. That is the litmus test passing rather than being argued around.
- Sidecars are already in `_modified_timestamp`'s bounded name list
  (`fs.py:2491-2495`), so the epic's modified time keeps tracking its rollup.

**Migrate on write.** This repo's own epic has its rollup inside
`initial-request.md` today, and so will anyone else's. When `reconcile` finds a
`<!-- tcw:rollup -->` block there, strip it, write it to the sidecar, and leave
the request holding only what a human actually wrote. If stripping leaves the
request blank, do not leave an empty file behind pretending to be a document.

**Keep every property the current implementation defends.** They were each won
by a previous item and the comments at `recursion.py:203-226` say so:
idempotence (an unchanged rollup stages nothing), the unguarded commit (so a
retry after a refused commit still commits), and `git_commit_result`'s benign
non-commit handling rather than a traceback.

### Verification

- A fresh epic reconciles, gets `rollup.md`, and has **no** `initial-request.md`
  — asserted by listing the folder, the way criterion 1 is.
- Its board line shows no `R`.
- An epic whose rollup sits in `initial-request.md` migrates on the next
  reconcile: sidecar written, block gone from the request, human-written prose
  above it untouched.
- Migration where the request was *only* the rollup leaves no empty file.
- Idempotence: a second reconcile with nothing changed stages nothing.
- Criterion 4 re-run, and this time it means what it says.

### Documentation

`epic-deltas.md` declares `initial-request.md` the managed target for the rollup
and is now wrong. The reconcile capability, `commands.md`, the changelog, and the
release notes all follow.

## Notes

- **This is the third time the same fallacy has cost this item a pass.** Criterion
  8 was verified at the API and false in the client. Criterion 4 is verified by a
  grep for a template and false for a path that writes real content. Both times
  the criterion tested the mechanism the implementer had in mind rather than the
  property the user cares about. Worth carrying into C2's spec, which is written
  against a projection with the same shape.
- No new command surface, no new flag. `tcw work reconcile` behaves identically
  from the outside except in where it puts the file.
