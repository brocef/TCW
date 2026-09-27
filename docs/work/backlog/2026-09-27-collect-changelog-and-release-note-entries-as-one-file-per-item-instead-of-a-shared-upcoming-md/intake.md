# Collect changelog and release-note entries as one file per item instead of a shared upcoming.md

Today every finished piece of work appends its changelog and release-note entries
to `docs/changelogs/upcoming.md` and `docs/release-notes/upcoming.md`. Agents on
different branches all edit the same two files, so parallel branches collide with
merge conflicts in them.

Replace each `upcoming.md` with a folder (for example `docs/changelogs/upcoming/`
and `docs/release-notes/upcoming/`). An agent finishing work adds its own uniquely
named file to that folder — named after the work item's slug, or similar — rather
than editing a shared file. Because no two branches write the same file, they no
longer conflict. At release-cut time, all the files in each folder are combined
into that version's `v{version}.md`, and the folder is emptied for the next cycle.

## Origin

Requested by the user in chat, 2026-09-27. Not a bug; a change to how
documentation-sync collects entries, to reduce merge conflicts between agents
working on separate branches.

## References

- `scripts/cut_version.py` and `tests/test_cut_version.py` — rotate `upcoming.md` into `v{version}.md` today; this becomes "combine the folder's files".
- `skills/documentation-sync/SKILL.md`, `references/release-notes-and-changelogs.md`, `references/cut-version.md` — tell agents to write into `upcoming.md`; shipped to every TCW user, so the new convention is user-facing.
- `tcw/work/procedures/documentation-sync.md`, `tcw/work/procedures/unattended-work.md`, `skills/configure/references/docs-sync.md` — also name `upcoming.md`.
- `tcw-config.yaml` (`work.documentation` entries), `CLAUDE.md`, `AGENTS.md` — this repo's own configuration and guide describe the `upcoming.md` rotation.
- `tests/test_documentation_config.py`, `tests/test_documentation_prompt.py`, `tests/test_repo_lifecycle.py`, `tests/test_unattended_work_skill.py`, `tests/test_eval_fixture.py`, `tests/cli/scenarios/13-release-integrity.md` — assert on `upcoming.md` wording or behavior.
- 2026-09-17-stop-offering-a-version-cut-after-every-completed-work-item (completed) — last change to when a version cut happens; background only.

Open questions for the spec: the order entries appear in once combined (by file
name, by date, grouped by kind of change); how a file is named when work was not
done under a work item; and what existing projects with an `upcoming.md` see
after upgrading.
