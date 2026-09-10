# Record a work item's branch, and let a node declare its own state fields

Two asks, raised together because the second is what makes the first
acceptable to a project that does not want it.

**A work item should record the branch it is being implemented on**, so that
work which is active but not yet completed is easy to find, and so that
resuming it does not depend on remembering where it lives.

**Not every project wants that field, and some want others** — a worktree
name, a machine name, whatever their process needs in order to say where a
piece of in-flight work actually is. So the field set should be extensible by
the node rather than fixed by TCW.

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

## What does not exist

There is no notion of caller-supplied metadata anywhere in the work model. The
field vocabulary is closed at three layers: the `WorkItem` dataclass, the
adapter read that populates it, and the JSON projection, which sets
`additionalProperties: false` and requires every declared key.

One thing that is true today but is not a contract: the filesystem adapter
writes state by read-modify-write over the whole mapping (`_set_fields_at`,
and the `edit` path), so a key added to a `state.yaml` by hand survives
subsequent edits and transitions. Nothing reads it, nothing shows it, nothing
can filter on it, and another adapter is free to drop it. It should not be
mistaken for support.

## Notes

- **An open per-item map is the wrong shape.** The abstraction litmus test
  names this case directly, under what to keep out of the model: "Globbing a
  store folder as an open namespace — bound it: body + named fields + named
  attachments." An operation defined as "set any key on any item" is one no
  shared interface can promise: Jira holds arbitrary custom fields, GitHub
  Issues holds none.
- **Tags are the precedent that does fit.** They are a node-declared
  vocabulary: registered in `tcw-config.yaml`, refused by the store when
  unregistered, and filterable from `list`. A declared set of named fields
  would follow the same rule, stay bounded, and let a non-filesystem adapter
  map each declared field onto a real custom field or refuse the declaration
  up front rather than silently dropping writes.
- **Machine name deserves scrutiny at the spec stage.** A branch is a property
  of the work. A hostname is a property of whoever last touched it, it goes
  stale with no event to correct it, and no store can verify it. `owner` and
  `started` already answer who holds an item and since when. This is an
  argument about that one field, not about the extension mechanism, which
  should not care what a node declares.
- **Open question for the spec stage: whether this is one item or two.** The
  branch half acts on fields that already exist and is small. The
  declared-field half touches the abstract store interface, the JSON schema
  version, and every adapter written afterwards. They are recorded together
  because the request arrived that way and the second is the reason the first
  is not simply hardcoded.

## References

- `tcw/store/base.py` — `WorkItem`, where `worktree` and `branch` already live.
- `tcw/work/projection.py` — `WORK_ITEM_SCHEMA`, the closed vocabulary any new
  field has to pass through, and the schema version that would have to move.
- `tcw/store/fs.py` — `git_current_branch`, `_read_item`, `_set_fields_at`:
  respectively what could supply the branch, what would have to read a
  declared field, and why unknown keys currently survive.
- `tcw/work/cli.py` — `_print_item` and the `list` parser, the two surfaces
  that would have to show and filter the result.
- `docs/lifecycle/abstraction.md` — the bounded-fields rule an open metadata
  map would break.
- `2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge`
  — adjacent, not a duplicate. That item syncs lifecycle state and branches to
  an external tracker; this one asks what the local model records in the first
  place, and would give that bridge a declared field to map.
