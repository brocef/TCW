# Record the branch a work item is being implemented on

A work item should record the branch it is being implemented on, so that work
which is active but not yet completed is easy to find, and so that resuming it
does not depend on remembering where it lives.

## What already exists

`branch` is not a new concept. `WorkItem` (`tcw/store/base.py`) already carries
both `worktree` and `branch` as real fields, `tcw work start --worktree` writes
them, `FsWorkStore._read_item` reads them back, and `WORK_ITEM_SCHEMA`
(`tcw/work/projection.py`) emits both in the versioned JSON document.

Three gaps stop that from answering the question above.

- **Plain `tcw work start` records nothing.** The two fields are written only
  on the `--worktree` path, so an item implemented on an ordinary branch has
  an empty `branch`. `git_current_branch` already exists in the filesystem
  adapter and would answer for that case.
- **Nothing displays either field.** `_print_item` prints owner, started, tags
  and six other fields and skips these two, so `tcw work show --json` is the
  only surface that reveals them.
- **Nothing filters on them.** `tcw work list` takes `--status` and `--tag`
  and nothing else.

## Scope

This item is the branch half of a request that arrived carrying two asks. The
other half — letting a node declare its own state fields — is now
`2026-09-10-let-a-node-declare-its-own-work-item-state-fields`, and the two are
independent.

The request paired them on the premise that a project which does not want a
`branch` field needs an extension mechanism before the field can be recorded.
Reading the code broke that premise: `branch` is already in `WorkItem`, already
in the emitted schema, and already written on the `--worktree` path, so
recording it on a plain start adds no field to the model. Nothing here waits on
the other item, and nothing here should introduce an extension mechanism.

**The slug still names both halves.** It is the item's stable ID and is
deliberately not recomputed on a retitle, so it is left as it is; the title is
what describes the item.

## Notes

- Whether recording the branch should be suppressible by a node — a
  `work.record-branch: false`, or similar — is the one place the dropped half
  still touches this one. It is a question for the spec, and it is a
  node-configuration question, not a declared-field one.

## References

- `tcw/store/base.py` — `WorkItem`, where `worktree` and `branch` already live.
- `tcw/store/fs.py` — `git_current_branch`, `_read_item`, `_set_fields_at`:
  respectively what could supply the branch, what reads it back, and what
  writes it.
- `tcw/work/cli.py` — `_print_item` and the `list` parser, the two surfaces
  that would have to show and filter the result, and `_start`, which writes the
  fields today only under `--worktree`.
- `tcw/work/projection.py` — `WORK_ITEM_SCHEMA`, which already emits both
  fields, so this item does not move the schema version.
- `docs/lifecycle/abstraction.md` — the prime directive any new operation here
  has to pass.
- `2026-09-10-let-a-node-declare-its-own-work-item-state-fields` — the other
  half of the original request; independent, and not a blocker.
- `2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge`
  — adjacent, not a duplicate. That item syncs lifecycle state and branches to
  an external tracker; this one asks what the local model records in the first
  place.
