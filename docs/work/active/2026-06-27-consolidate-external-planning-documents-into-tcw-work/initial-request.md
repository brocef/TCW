# Initial request — Consolidate external planning documents into TCW work

## Requested outcome

Add a new `tcw work consolidate-plans` command that examines planning documents
that are not already inside the TCW work system and migrates them into TCW work
items. The user can optionally pass one or more folders to search for older plan
documents. After TCW work items have been created successfully, the old documents
can be deleted.

## Constraints and non-goals

- Preserve TCW's storage abstraction. Discovery of arbitrary local files is a
  filesystem CLI concern; the abstract work model should stay expressed in work
  items, statuses, lifecycle artifacts, references, and transitions.
- Do not import files already under `docs/work/` as new work.
- Do not delete source documents before successful work item creation.
- Do not require a remote tracker adapter now, but avoid APIs that would make
  one impossible.
- Planning should stop before implementation; do not run `tcw work start` yet.

## Open questions

- Should deletion be opt-in with a flag such as `--delete`, or should the command
  only print deletion commands for review first?
- Should the first implementation only support Markdown, or also recognize plain
  text and other common planning document extensions?
- Should migrated items always enter `backlog`, or should inbox-style ambiguous
  imports be possible later?

## Decisions already made

- Command name: `consolidate-plans`.
- Optional search folders are part of the user-facing shape.
- Old documents may be deleted after migration.
