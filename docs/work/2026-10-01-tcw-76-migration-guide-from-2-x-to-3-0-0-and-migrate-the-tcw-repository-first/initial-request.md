# Migration guide from 2.x to 3.0.0, and migrate the TCW repository first

TCW 3.0.0 (epic [TCW-68](https://proposit.atlassian.net/browse/TCW-68)) changes the
work axis so deeply that 3.0 cannot read a 2.x project at all: no status
directories, no `state.yaml`, no `graveyard.yaml`, no Definition of Done, a new
`work.*` configuration shape and, in Jira mode, Jira as the single owner of status
and the request. 3.0 ships no code that detects or converts a 2.x project. Every
existing project therefore needs a written way across, and TCW's own repository is
the first project that has to make the move.

## What is wanted

1. **A migration guide** at `docs/migration-guide-2.8-to-3.0.0.md`, the only
   migration tool 3.0 has. It is written for an agent to follow with a user:
   - ordered steps, each ending with a check the agent can make by looking at the
     files, without trusting its own memory of what it did;
   - explicit points where the agent stops and asks the user, with one
     consolidated plan to approve rather than a question per item;
   - both backends: a project that stays on the filesystem and a project that
     moves to Jira mode;
   - every piece of 2.x a project can carry: status folders, item fields, lifecycle
     documents, the inbox, `graveyard.yaml`, `dod.yaml`, every configuration key,
     hook variables, prompt and hook bindings, templates, and the project's own
     scripts and agent guides.

   Projects older than 2.8 upgrade to 2.8 first.
2. **TCW's own repository migrated with that guide, before 3.0.0 is released.** It
   is a Jira-mode migration of TCW's real board. Following the guide as written,
   rather than improvising, is what proves the guide works; where it does not, the
   guide is fixed.
3. **TCW's own 3.0 configuration**, which this item owns: the opt-in git example
   from TCW-75 (pull as prompt text, commit as a `post` hook that tolerates
   nothing to commit, push as the owner chooses), a project-defined completion gate
   that replaces `dod.yaml`, and its documentation entries rewritten for 3.0.

The ticket also lists what TCW-69's spec added to the guide's scope: the hook
variable renames, `work.hooks`, `artifacts` templates becoming conditional `prompt`
bindings, a `skill` in `pre` and `when: {type: …}` becoming errors, the fate of the
capability `Planning doc` field, and `capabilities.yaml` staying at the item root.

## Constraints

- **The guide is the only tool.** No 2.x detection or conversion code ships in 3.0,
  and `tcw validate` knows only the 3.0 layout.
- **Sequencing.** 3.0 cannot read a 2.x board, and `CLAUDE.md` forbids driving the
  lifecycle with the `tcw` CLI while `tcw/` is changing. So TCW's migration is done
  with the 3.0 code frozen, uses the working-tree CLI only for the final
  `tcw validate`, and lands in the same change that switches TCW to 3.0, so TCW's
  own gates never see a half-migrated board.
- **Done last.** This slice follows TCW-69 to TCW-75 and TCW-77; it describes the
  layout and commands they settle and must not redefine them.
- **Nothing is posted to Jira or GitHub without the exact text being approved
  first** (`CLAUDE.md`).
- **The guide works under both Claude and Codex**, with whatever Jira access the
  agent has.

## Out of scope

- Any 3.0 code. The model, backends, personal configuration, CLI, prompts and
  skills, documentation and web viewer are TCW-69 to TCW-75 and TCW-77.
- Recreating items that 2.x retention already deleted; they stay deleted.
- Rewriting old slugs in historical text (changelogs, finished documents). Only live
  references are rewritten.

## Notes

- **Written without a user to ask.** This stage normally asks the requester what
  is unclear and for reference material. This item was written from the imported
  ticket (`intake.md`) and the epic's reference material, with no one available to
  ask, so everything beyond the ticket's own words is inference for `spec` to check.
- **Assumption: the ticket's board numbers are out of date.** It says 25 items (17
  bound to tickets), 10 inbox entries and a 310-entry `graveyard.yaml`. TCW-68 to
  TCW-77 were imported onto the board after it was written, and the graveyard has
  shrunk since. `spec` recounts against the tree, and the guide recounts again at
  migration time, since the board keeps changing until then.
- **Assumption: the ticket's "Update from TCW-69's spec" section wins** over its own
  artifact table where they disagree, as the epic's reference pack says. That makes
  `capabilities.yaml` stay at the item root, not move to `spec/capabilities.yaml`.
- **Open questions the ticket leaves to `spec`:** what happens to the capability
  `Planning doc` field; whether 2.x acceptance records (`refined-outcome.md`,
  `rework.md`) become `qa` rounds (the ticket) or `review` rounds (the epic's
  decision record); and how this epic's own board is tracked while TCW-70 to TCW-75
  and TCW-77 land and neither the 2.x nor the 3.0 CLI can be used on it.
- **Self-hosting.** From implementation onwards, this repository's board is driven
  by editing files, not through the CLI, as `CLAUDE.md` requires.

## References

- [TCW-76](https://proposit.atlassian.net/browse/TCW-76): the ticket, imported as
  `intake.md`; the agreed decisions for this slice.
- [TCW-68](https://proposit.atlassian.net/browse/TCW-68): the epic, and its attached
  decision record `TCW-68-design-decisions-2026-09-30.md`, whose "Migration" section
  is this slice's first draft.
- TCW-69's `spec.md`
  (`docs/work/backlog/2026-10-01-tcw-69-core-work-model-stage-table-item-folders-that-never-move-and-advance/spec.md`):
  the 3.0 layout, stage table, `work.*` configuration and hook variables the guide
  migrates to. It must not be redefined here.
- [TCW-70](https://proposit.atlassian.net/browse/TCW-70) and
  [TCW-71](https://proposit.atlassian.net/browse/TCW-71): the storage details the
  guide converts into (`item.yaml`, folder names, the inbox, Jira fields and
  statuses).
- [TCW-72](https://proposit.atlassian.net/browse/TCW-72),
  [TCW-73](https://proposit.atlassian.net/browse/TCW-73),
  [TCW-74](https://proposit.atlassian.net/browse/TCW-74),
  [TCW-75](https://proposit.atlassian.net/browse/TCW-75): `inherit: true`, renamed
  commands and config keys, the procedures that survive, and the opt-in git example
  TCW adopts.
- `docs/migration-guide-1.X-to-2.0.0.md` and the other `docs/migration-guide-*.md`
  files: the house style of earlier migration guides.
- `tcw-config.yaml`, `docs/work/`, `scripts/require_artifact.py`,
  `docs/procedures/create-work.md`, `CLAUDE.md` and `AGENTS.md`: what TCW's own
  migration changes.
