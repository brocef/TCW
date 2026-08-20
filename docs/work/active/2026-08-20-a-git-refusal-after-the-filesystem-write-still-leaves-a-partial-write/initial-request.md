# A git refusal after the filesystem write still leaves a partial write

## The request

TCW refuses a filesystem-store write before touching the disk when the
repository is *absent*. It has no answer for a repository that exists and
*refuses*: a held `index.lock`, a rejecting pre-commit hook, a permissions
error, a corrupt `.git`. Those surface only when staging fails — after the
content is on disk. The error message is legible (`tcw: git command failed`,
not a traceback), but the half-written item stays behind, and the user is left
to clean it up by hand without being told what to remove.

Make a git refusal leave the store as it was before the command ran.

## Constraints

- **Undo only what this call created**, then re-raise. The requester chose this
  over full write-to-temp-then-move atomicity: it covers the reported symptom —
  a half-created item left behind — at a fraction of the blast radius.
- **Never delete something that already existed.** An update to an existing item
  that fails at staging must leave the prior content alone; removing it would
  turn a recoverable failure into real data loss. This is the hard boundary on
  the request.
- The failure must still be reported. Rolling back silently and exiting 0 would
  be worse than today's behaviour.

## Out of scope

- Full atomicity under concurrent writers (write everything to a staging area
  and move into place once git accepts). Explicitly deferred by the requester as
  a much larger change across every write path in `tcw/store/fs.py`.
- Predicting a refusal with a new precondition. A precondition cannot see a lock
  acquired a millisecond later; this is a rollback request, not a guard request.

## References

- `docs/work/completed/2026-07-30-fix-non-git-write-paths-work-new-and-init-fail-outside-a-git-repository/refined-outcome.md`
  — "Deferred, with the user's agreement" item 3 states the deferral this item
  picks up.
- That item's Scenario 14, assertion 8 — pins the *message shape* of a git
  refusal and explicitly not the atomicity, so it is the existing contract this
  work must not break.
- `intake.md` — the raw filing.

## Notes

Asked for further reference material; none beyond the above provided.

Batched with the other four `bug`-tagged items into a single patch release.
