# Collect changelog and release-note entries as one file per item instead of a shared upcoming.md

## Request

Change how documentation-sync collects changelog and release-note entries.
Today every finished piece of work edits one shared file per kind —
`docs/changelogs/upcoming.md` and `docs/release-notes/upcoming.md` — and agents
working on different branches all edit those same two files, which produces
merge conflicts.

Instead, each of those becomes a folder. An agent finishing work adds its own
uniquely named file to the folder rather than editing a shared one. At release
cut, all the files in each folder are combined into that version's
`v{version}.md`, and the folder is left empty for the next cycle.

**Why:** fewer merge conflicts. Branches that never write the same file cannot
conflict over it.

## Decisions the requester made (2026-09-27)

- **Scope — both.** This repository switches to folders, *and* the shipped
  `documentation-sync` skill (plus the `configure` skill's setup guidance) teaches
  the folder layout to every project that uses TCW.
- **Grouping — merge by heading.** Each file uses the same section headings the
  combined document uses (Added / Changed / Fixed / Removed / Internal for the
  changelog; the release notes' own headings). At cut time every entry is
  gathered under a single heading of each kind, in a fixed order, rather than
  repeating headings once per file.
- **Tooling — no new CLI command.** This repository's `scripts/cut_version.py`
  does the combining here; agents in other projects follow the skill's written
  steps. The `tcw` CLI gains nothing.
- **File names — the work item slug.** `<slug>.md`. Work done outside any item
  uses a short descriptive name plus the date.

## Constraints

- `cut_version.py` must keep its existing guarantees: it aborts on version
  drift, commits and tags, and does not push.
- The released `v{version}.md` must still read as one document with the
  `# v{version}` title (the retitle and preamble-dropping `rotate_upcoming`
  does today).

## Out of scope

- A `tcw` command for combining entries (declined above).
- Rewriting already-released `v{version}.md` files.

## References

- `scripts/cut_version.py` (`rotate_upcoming`) — the code that becomes "combine the folder".
- `skills/documentation-sync/references/release-notes-and-changelogs.md` and `references/cut-version.md` — the shipped instructions that describe `upcoming.md`.
- `skills/configure/references/docs-sync.md` — tells projects how to set the structure up.
- `tcw-config.yaml` `work.documentation` — this repo's entries name the two `upcoming.md` paths.

## Notes

- Reference material was not asked for separately; the chat request named none,
  and the list above is what the `work-create` survey found.
- The current `upcoming.md` files hold unreleased entries (the
  `commands-pause-work` resume-line change); they must survive the switch.
- Open for `spec`: what projects that already have an `upcoming.md` see after
  upgrading the plugin.
