# Filesystem work backend on the new model, wired into `tcw work`

TCW 3.0 needs a filesystem backend that is a first-class way to use TCW, not a
fallback: everything that Jira keeps in Jira mode, this backend keeps in the
repository. It is the second slice of the redesign (epic
[TCW-68](https://proposit.atlassian.net/browse/TCW-68)) and builds on the core work
model ([TCW-69](https://proposit.atlassian.net/browse/TCW-69)), which lands as a
library that no command uses yet. This slice is where 3.0 first becomes something a
user can run.

## What is wanted

1. **A filesystem implementation of TCW-69's backend operations** (create, read,
   list, update properties, set stage, comment, rename, look up a backend name),
   covering what Jira owns in the other mode:
   - an item's properties and stage in `item.yaml`, with only `title` and `stage`
     required and `priority` defaulting to `medium` when an item is created;
   - item folders named `YYYY-MM-DD-<title words>`, where the date prefix is the
     creation date and there is no separate `created` field. A name that already
     exists is refused;
   - the request in `request/request.md`;
   - comments as one file each, `comments/<UTC timestamp>.md`. Forced moves and
     discards write their reason there;
   - the inbox as items at the inbox stage. `list` shows them by default and
     `list --stage inbox` shows only them. This replaces `tcw work inbox`;
   - rename as a plain move of the folder that keeps the date prefix, rewrites
     `parent` and `blocked-by` in this project's items, and prints any other
     mentions it finds on stderr. No `renames.yaml`, no lock, no old-name alias;
   - delegation into a filesystem-mode project (`tcw work new --project <id>`,
     and `edit --blocks` writing another project's item), allowed only when the
     project's path resolves, its work store is present, and the store has no
     uncommitted changes. Otherwise it is refused, naming the condition that
     failed. A delegated item lands at the inbox stage, and files written in
     another repository are left uncommitted and named on stderr.
2. **The model wired into the `tcw work` commands** through this backend.
3. **The 2.x work store removed.** Status directories, `graveyard.yaml`,
   `dod.yaml` and `renames.yaml` are no longer part of a work store, and the code
   that kept them, and the tracker integration that belongs to that store, goes.

Work stores kept in a separate repository stay supported: `tcw provision` still
clones them, and keeping them current is the project's own job through hooks.

## Constraints

- **A project uses exactly one work backend.** Filesystem mode and Jira mode never
  mix.
- **Each branch carries its own `stage`.** Status is whatever the checked-out tree
  says. With no history list, two branches conflict only when both moved the same
  item, which is a real disagreement. Teams that want one shared view commit and
  push stage changes themselves (TCW-75's opt-in example).
- **TCW never changes git state.** It writes files, names them on stderr, and may
  read git for checks (for example, whether a store has uncommitted changes).
- **TCW-69 is not redefined here.** The folder layout, stage folders, rounds,
  handoffs and `path` are TCW-69's shared layer, used by both backends; this slice
  uses them.
- **Breaking changes are expected** (3.0.0). No 2.x compatibility code; migration
  is a written guide (TCW-76).
- **Every operation passes the abstraction litmus test**
  ([`docs/lifecycle/abstraction.md`](../../../lifecycle/abstraction.md)).

## Out of scope

- The Jira backend, `tickets list` / `tickets adopt`, and delegation into a
  Jira-mode project: TCW-71.
- Personal configuration and identity (`user.name`, `list --mine`,
  `--assign-me`, `inherit`): TCW-72.
- The final command surface across all three axes, `--help` text, the
  "node" to "project" rename, and the user-facing description of the
  stdout/stderr/exit-code contract: TCW-73. Where exactly the line between this
  slice and TCW-73 falls is for `spec` to decide; the ticket does not draw it.
- Stage prompt and skill text: TCW-74. Documentation: TCW-75. Migrating this
  repository's own board and config: TCW-76. The web viewer: TCW-77.

## Notes

- **No user was available to ask.** This request was written from the ticket
  ([TCW-70](https://proposit.atlassian.net/browse/TCW-70), held as imported in
  `intake.md`), the epic and its decision record, the sibling tickets, and
  TCW-69's finished spec, whose decisions the owner confirmed on 2026-10-01.
  Reference material was not asked for; the references below are the ones the
  epic pack supplied.
- **Assumption:** "wire the model into `tcw work`" includes every surface that
  today reads the 2.x work store and would otherwise stop working once it is
  removed: `tcw validate`'s work checks, `tcw://` work references,
  `tcw capabilities drift`, `tcw init`/`tcw provision` for the work component, and
  `tcw serve`'s work routes. The ticket names none of them; the owner confirmed
  only that TCW-70 "wires it into the CLI with the filesystem backend and removes
  the 2.x work store".
- **Assumption:** the ticket's line "Removed from the store root" means the code
  stops reading and writing those files. Deleting this repository's own copies is
  TCW-76's migration.
- **This repository's own board cannot be read by 3.0 until TCW-76 migrates it.**
  Its `tcw-config.yaml` uses keys TCW-69's parser rejects (`work.tracker`,
  `work.retain`, `work.lifecycle`) and its board uses status directories. How this
  slice is tested, and how the board is driven meanwhile, is for `spec` to settle.
- **The ticket lists no open questions.** The questions this request leaves to
  `spec` are the boundary with TCW-73, the testing approach above, and which other
  surfaces must be rewired rather than removed.
- **Self-hosting.** This changes `tcw/` itself, so the repository's board is driven
  by editing files, not through the CLI, as `CLAUDE.md` requires.

## References

- [TCW-70](https://proposit.atlassian.net/browse/TCW-70): the ticket; the agreed
  decisions for this slice.
- TCW-69's `spec.md` and `plan.md`
  (`docs/work/backlog/2026-10-01-tcw-69-core-work-model-stage-table-item-folders-that-never-move-and-advance/`):
  the model, layout and backend interface this slice implements, and the list of
  2.x imports the plan says TCW-70 must keep.
- [TCW-68](https://proposit.atlassian.net/browse/TCW-68) and its attached
  `TCW-68-design-decisions-2026-09-30.md`: the vision and the original decision
  record.
- [TCW-71](https://proposit.atlassian.net/browse/TCW-71),
  [TCW-73](https://proposit.atlassian.net/browse/TCW-73),
  [TCW-76](https://proposit.atlassian.net/browse/TCW-76),
  [TCW-77](https://proposit.atlassian.net/browse/TCW-77): the slices that share a
  boundary with this one (the other backend, the command surface, the migration,
  and the viewer that calls the same operations).
- `tcw/store/fs.py` (`FsWorkStore`) and `tcw/work/cli.py`: the 2.x work store and
  commands this slice replaces.
- `CLAUDE.md`, "Exception": how the board is driven while `tcw/` is being changed.
