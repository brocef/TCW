# Plan: collect changelog and release-note entries as one file per item

Spec: `spec.md`. No blockers. Work on `main` directly (no worktree); nothing
here changes `tcw/` Python code, so driving the lifecycle with the `tcw` CLI
stays safe throughout.

Each task ends with the full suite green (`pytest`, run bare, as CI does) and
one commit.

## Task 1 — Combine `upcoming/` folders in `scripts/cut_version.py` (test first)

Modifies `tests/test_cut_version.py`, `scripts/cut_version.py`.

1. Change `make_repo` to create `docs/changelogs/upcoming/README.md` and
   `docs/release-notes/upcoming/README.md` (short preamble text) plus one entry
   file in each (`a.md`: `## Added\n\n- changelog entry\n`), instead of the
   two `upcoming.md` files.
2. Write the new tests, and watch them fail against the current script:
   - `test_combine_merges_sections_by_heading` — spec criterion 4 exactly:
     `a.md` holds `## Fixed` then `## Added`; `b.md` holds `## Added` then
     `## Security`. Assert the shipped `docs/changelogs/v0.2.3.md` starts
     `# v0.2.3\n`; `count("## Added") == 1`; `a.md`'s Added entry precedes
     `b.md`'s; heading order is Added, Fixed, Security; no README text; `a.md`
     and `b.md` are deleted, `README.md` is byte-identical; tag `v0.2.3`
     exists; `git status --porcelain` is empty.
   - `test_combine_with_no_entries_ships_only_the_title` — criterion 5: only
     `README.md` in each folder → `v0.2.3.md` equals `"# v0.2.3\n"`.
   - `test_subheadings_stay_under_their_section` — criterion 6: a `### Detail`
     line inside `b.md`'s `## Added` appears after `b.md`'s Added entry and
     before the next `## ` heading.
   - `test_release_notes_keep_first_appearance_order` — release-notes folder
     with `a.md` (`## Zeta`) and `b.md` (`## Alpha`, `## Zeta`) → order
     Zeta, Alpha, one Zeta.
   - `test_text_before_the_first_heading_follows_the_title` — a file with no
     `## ` heading lands right after `# v0.2.3`.
   - Rewrite `test_main_end_to_end` to the folder layout (keeps the commit
     message, tag and clean-tree assertions).
   - Replace `test_rotation_drops_the_working_file_preamble` with
     `test_readme_guidance_never_ships`: README text never appears in
     `v{new}.md` and survives the cut unchanged.
3. Implement in `scripts/cut_version.py`:
   - `UPCOMING` becomes a mapping of folder → fixed section order:
     `{"docs/changelogs/upcoming": ("Added", "Changed", "Fixed", "Removed",
     "Internal"), "docs/release-notes/upcoming": ()}`.
   - `combine(texts: list[str], order: tuple[str, ...]) -> str` — pure; the
     Design §3 steps 1–4. Split on lines starting `## ` (not `###`).
   - `combine_upcoming(root, version) -> list[str]` replaces `rotate_upcoming`:
     for each folder, read `sorted(p for p in folder.glob("*.md") if p.name !=
     "README.md")`, write `<parent>/v{version}.md` as `# v{version}\n` + (`\n`
     + body if body), `git rm -q` the entry files, return the paths to stage.
   - `main` stages the version files and the new `v{version}.md` files; the
     `git rm`s are already staged. Update the module docstring.
   - Abort (`sys.exit`) if an `upcoming/` folder is missing, naming it —
     otherwise a cut run before Task 2 would silently ship empty notes.

**Proves it:** the new tests pass; they failed before step 3.

## Task 2 — Switch this repository to the folders

Creates `docs/changelogs/upcoming/README.md`,
`docs/release-notes/upcoming/README.md`,
`docs/changelogs/upcoming/2026-09-27-carried-over.md`,
`docs/release-notes/upcoming/2026-09-27-carried-over.md`. Deletes both
`upcoming.md` files. Modifies `tcw-config.yaml` (the two entries at lines
55–61), `tests/test_repo_lifecycle.py:101-109`.

1. `git mv` each `upcoming.md` to `upcoming/2026-09-27-carried-over.md`, then
   drop its `# Upcoming` title and preamble; change the changelog's
   `### Changed` to `## Changed` (the new convention). Entry text unchanged.
2. Each `README.md`: `# Upcoming entries`, the old preamble sentence, and how
   to add an entry — one file per change, named `<work-item-slug>.md`
   (outside an item, `<YYYY-MM-DD>-<short-description>.md`), `##` section
   headings (the changelog's five, in order), no `#` title, edit only your own
   file; `scripts/cut_version.py` combines them.
3. `tcw-config.yaml` entry paths become `docs/release-notes/upcoming/<slug>.md`
   and `docs/changelogs/upcoming/<slug>.md`; descriptions add "one file per
   work item, named by its slug; never edit another item's file".
4. Update the expected path list in `test_repo_lifecycle.py`.

**Proves it:** criteria 1–3 — `ls` the folders; `git diff -M HEAD~1` shows
the carried-over entry lines unchanged; `tcw work docs` lists the new paths;
`tcw validate` is clean; suite green.

## Task 3 — Teach the folder layout in the shipped skills

Modifies `skills/documentation-sync/references/release-notes-and-changelogs.md`,
`skills/documentation-sync/references/cut-version.md`,
`skills/documentation-sync/SKILL.md`, `tcw/work/procedures/documentation-sync.md`,
`tcw/work/procedures/unattended-work.md`, `skills/configure/references/docs-sync.md`.

- `release-notes-and-changelogs.md`: directory layout (§1 of the Design), file
  naming, the in-file format, recommended entries with `<slug>.md` paths; the
  version cross-check rewritten for folders; a "Single `upcoming.md`" section —
  keep writing there when the entries name it, and offer once the migration;
  a new row in the migration table; Common Mistakes gains "editing another
  item's entry file".
- `cut-version.md`: Step 2 becomes "Combine the `upcoming/` folders" with the
  Design §3 rules as numbered steps (and "a project still on `upcoming.md`
  rotates it as before"); the intro's "`upcoming.md` file names" line; the
  TCW example sentence; the fold section's steps 2 and 4.
- `SKILL.md` line 41 example entry and the "working files" paragraph near the
  end, plus the Companion references row wording; the same paragraph and row in
  `tcw/work/procedures/documentation-sync.md` (lines 46, 84–90).
- `unattended-work.md:37`: "let entries accumulate in the `upcoming/` folders".
- `configure/references/docs-sync.md`: the YAML example path (line 18) and the
  "Create tracked files" bullet (line 43) — create `upcoming/` folders each with
  a `README.md`.

**Proves it:** criteria 7 and 8 — run the criterion 7 `grep` and read each
hit; `tests/test_unattended_work_skill.py` and the procedure/prompt tests stay
green.

## Task 4 — Repo guides, release scenario, eval fixture comment, capability

Modifies `CLAUDE.md` and `AGENTS.md` (Versioning), `tests/cli/scenarios/13-release-integrity.md`
row 8, `evals/seed_fixture.py:425-431` (comment only), and the capability
`skills/documentation-sync` via `tcw capabilities set` (using the
`capabilities` skill).

- Versioning text: "combines `docs/{changelogs,release-notes}/upcoming/*.md`
  into `v{version}.md`"; "add your entry file there *before* running it".
- Scenario 13 row 8: combine instead of rotate; `README.md` kept.
- Fixture comment: it stays on a single `upcoming.md` because eval B10 lists
  exact changed paths, and it exercises the older layout.
- Capability: append the spec's sentence (criterion 11).

**Proves it:** criterion 11 via `tcw capabilities show skills/documentation-sync`;
`tcw capabilities check` clean; `tests/test_eval_fixture.py` green.

## Task 5 — Documentation Sync (one pass over the finished diff)

- `README.md` [Public-API] — fires: the Releasing paragraph (lines 887–891)
  says the cut turns "the `upcoming.md` changelog and release notes" into the
  version's files. Rewrite for folders.
- `docs/guide/<topic>.md` [Guide-Topic-Change] — fires for
  `docs/guide/configuration.md:212`'s example entry path. `web-viewer.md:30`
  stays ("upcoming notes" is still true).
- `docs/release-notes/upcoming/<slug>.md` [Public-API] — fires: the skill tells
  every project's agents to use folders. Write
  `docs/release-notes/upcoming/2026-09-27-collect-changelog-and-release-note-entries-as-one-file-per-item-instead-of-a-shared-upcoming-md.md`.
- `docs/changelogs/upcoming/<slug>.md` [Any-Code-Change] — fires. Write
  `docs/changelogs/upcoming/2026-09-27-collect-changelog-and-release-note-entries-as-one-file-per-item-instead-of-a-shared-upcoming-md.md` (`## Changed`: cut script, skills,
  config; `## Internal`: tests).
- `skills/<component>/SKILL.md` [Skill-Driven-Component] — handled in Task 3.
- `skills/configure/references/<document>.md` [Configuration-Key-Change] — no
  configuration key changes meaning; `docs-sync.md` is already updated in
  Task 3 for its example.
- `docs/guide/jira.md` [Tracker-Change] — does not fire.

Criterion 9 (README and guide) is proven here.

## Verification (beyond the suite)

- Copy the repository to a temporary folder and run
  `python scripts/cut_version.py patch` there (scenario 13 row 8's method).
  Read both produced `v2.6.4.md` files: one title, sections merged, no README
  text, carried-over and this item's entries both present; `upcoming/` holds
  only `README.md`. Never run it in the real checkout.
- `pytest` bare — criterion 10.
- Read the rewritten `cut-version.md` Step 2 cold, as an agent in another
  project would, and check it can be followed without this repo's script.

## Notes

- Tests `test_documentation_prompt.py` and `test_documentation_config.py`
  use `docs/changelogs/upcoming.md` only as an arbitrary sample path for the
  parser; they are left alone.
- `docs/plan/phase-5-work.md` and `docs/superpowers/` are historical and not
  edited.
