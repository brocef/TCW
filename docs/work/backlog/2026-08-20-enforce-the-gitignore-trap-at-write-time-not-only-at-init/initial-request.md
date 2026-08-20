# Enforce the gitignore trap at write time, not only at init

## The request

An item that TCW writes to disk but git never records is a silent data-loss
footgun: the work looks filed, `tcw work list` shows it, and it is absent from
every clone. `tcw work init` guards against that today, but only at configure
time. The guard cannot see a `.gitignore` written after `init`, a rule naming
one slug, or a rule arriving with a later `git pull` — and in any of those cases
the write goes ahead and the item quietly never enters version control.

Move the enforcement to where the write actually happens, so the user is told
at the moment a path is being dropped rather than discovering it later.

## Constraints

- **Warn on stderr and proceed — do not refuse the write.** The requester chose
  this explicitly over refusing. `completed/` and `discarded/` are ignored on
  purpose (that is how a resolved item leaves the tracked tree), and a node may
  legitimately ignore other status folders too; a hard refusal would turn those
  deliberate setups into a broken store.
- The two resolved statuses must stay **silent**. A warning that fires on every
  `complete` is noise the user will learn to ignore, which defeats the point.
- The item must still be written. The warning informs; it does not block.

## Out of scope

- Changing which paths TCW itself gitignores by default.
- The `init`-time guard's own probe shape — that is a separate item
  (`2026-08-20-the-init-ignore-guard-probes-fixed-path-names-that-a-rule-could-collide-with`).

## References

- `docs/work/completed/2026-07-30-fix-non-git-write-paths-work-new-and-init-fail-outside-a-git-repository/refined-outcome.md`
  — "Deferred, with the user's agreement" item 1 is this request, in the words of
  the review that found it.
- `intake.md` — the raw filing, including the observation that `git_stage`
  already computes which paths it is dropping.
- `tcw/store/fs.py` — `git_stage` and the `ponytail:` note on the `init` guard
  that names this gap as a known ceiling.

## Notes

Asked for further reference material; none beyond the above provided.

Batched with the other four `bug`-tagged items into a single patch release.
