# Release Notes & Changelogs

Load this reference when the project uses the opt-in `docs/release-notes/` + `docs/changelogs/` structure **and** you're writing into those files (adding an entry file, combining entries at a version cut, migrating an existing `CHANGELOG.md`, or evaluating version drift before adding an entry).

**This structure is opt-in.** The `docs/release-notes/` and `docs/changelogs/` layout described below applies only when the project's documentation entries explicitly list `upcoming/` entry files (or, in a project set up before folders, a single `upcoming.md`) — from `tcw work docs`, or from a `## Documentation Sync` section when `source` is `agent-guide` (or when the user asks you to set the structure up — read the `configure` skill's `docs-sync.md`). Don't create `docs/release-notes/upcoming/` or `docs/changelogs/upcoming/` in a project that hasn't adopted them. Some projects use only GitHub Releases, only a root `CHANGELOG.md`, or have no version-history files at all — that's a valid choice.

For monorepos, each package may carry its own `docs/release-notes/` and `docs/changelogs/` directories, or the repo may share a single set at the root. Follow whatever the project's documentation entries point to; don't infer a structure that isn't listed.

## Directory Structure

```
docs/
  release-notes/
    upcoming/
      README.md              # How to write an entry; never combined
      <work-item-slug>.md    # One file per change, for the next version
    v1.2.3.md                # Finalized release notes for v1.2.3
  changelogs/
    upcoming/
      README.md
      <work-item-slug>.md
    v1.2.3.md                # Finalized changelog for v1.2.3
```

Released files follow the pattern `v{version}.md`. The `upcoming/` folders hold entries for the next version, whose number is not yet known (could be a patch, minor, or major bump).

### One file per change

Every change adds **its own file** to each `upcoming/` folder whose entry fires, rather than editing a shared file. Two branches that each finish a change then write different files, so merging them cannot conflict over the notes.

- **Name it after the work item:** `<work-item-slug>.md`. Work done outside any item uses `<YYYY-MM-DD>-<short-description>.md`, the same shape. Because slugs start with a date, file-name order is roughly the order the work happened.
- **Edit only your own file.** A second pass on the same item (rework) edits that item's file. Never edit another change's file, even to fix a typo in passing.
- **No `#` title.** Put entries under `##` headings. The changelog uses `## Added`, `## Changed`, `## Fixed`, `## Removed`, `## Internal`. Release notes use whatever headings the project uses; reuse one another entry already has when yours belongs with it. A `###` heading belongs to the `##` section above it. Never start a line with `## ` inside a code block: the cut reads every such line as a section heading.
- **Keep `README.md`.** It carries the drafting guidance, it is never combined into a release, and it keeps the folder in git when no entries are waiting.

At a version cut, the files are combined into `v{version}.md` — see `cut-version.md`, Step 2.

## Release Notes vs. Changelogs

| Aspect       | Release Notes (`docs/release-notes/`)                          | Changelog (`docs/changelogs/`)                               |
| ------------ | -------------------------------------------------------------- | ------------------------------------------------------------ |
| Audience     | End-users                                                      | Developers (contributors, dependents)                        |
| Tone         | Plain language, understandable by anyone familiar with the app | Technical, precise                                           |
| Content      | User-facing changes only                                       | All changes including internals, refactors, dependency bumps |
| Detail level | What changed and why it matters to the user                    | What changed, where, and how                                 |

**Release notes guidance:**

- Write in plain language — no jargon, no internal module names
- Focus on outcomes: what can the user now do, what was fixed, what changed
- Group by category when useful (e.g., "New Features", "Bug Fixes", "Breaking Changes")
- Omit purely internal changes (refactors, dev tooling, test-only changes)

**Changelog guidance:**

- Include everything: features, fixes, refactors, dependency changes, CI/CD updates, test additions
- Reference file paths, function names, or modules where helpful
- Group by category (e.g., "Added", "Changed", "Fixed", "Removed", "Internal")
- Be specific enough that a developer can understand the scope without reading the diff

## Recommended Documentation Sync Entries

Projects using this structure should include these entries in their CLAUDE.md `## Documentation Sync` section:

```markdown
- `docs/release-notes/upcoming/<slug>.md` [Public-API] — User-facing release notes; plain language, no jargon; one file per work item
- `docs/changelogs/upcoming/<slug>.md` [Any-Code-Change] — Developer changelog; technical, grouped under `##` category headings; one file per work item
```

The trigger system determines when these files get updated — release notes fire on public-facing changes, changelogs fire on any code change.

## Version Cross-Check

Before adding an entry file, cross-check the project's current version (from `package.json`, `pyproject.toml`, `Cargo.toml`, `version.txt`, or whatever the project uses) against existing versioned files in `docs/release-notes/` and `docs/changelogs/`.

Two scenarios surface drift:

- **Version bumped, no `v{version}.md` exists yet:** the entries waiting in `upcoming/` likely belong to that version. **Tell the user what you found and confirm before combining them.** Do not silently combine files.
- **`v{version}.md` exists but `upcoming/` holds entries that predate the bump:** those entries need to be merged into the versioned file. Again, confirm with the user before merging — losing or relocating an entry without acknowledgment is worse than asking.

After confirmation, combine the waiting entries into `v{version}.md` by the rules in `cut-version.md`, Step 2, and delete them.

Always run the cross-check before adding an entry — never silently lose content that should be attributed to a released version, and never silently combine or delete files the user didn't ask you to touch.

**Combining is part of the project's version-cut process.** Many projects automate the bump + combine + commit + tag steps behind a single command or script — follow whatever the project's `CLAUDE.md` / Versioning section documents rather than combining by hand when such a process exists.

## A project still on a single `upcoming.md`

Projects set up before the folder layout declare `docs/changelogs/upcoming.md` and `docs/release-notes/upcoming.md` — one shared file each. The project's documentation entries are authoritative, so **keep writing where they point**: append to `upcoming.md` under its existing headings, and at a cut rename it to `v{version}.md` and start a fresh one, as the project always has.

Then offer the folder layout — once in a session, not at every entry, and if the user declines, do not raise it again. It is a migration like any other below, never done unasked:

> "Every change here edits the same `upcoming.md`, so work finished on separate branches conflicts when it merges. Want me to switch to one file per change in `upcoming/` folders?"

If the user agrees: create each `upcoming/` folder with a `README.md` (the guidance above); move the current `upcoming.md` content, minus its title and preamble, into `upcoming/<YYYY-MM-DD>-carried-over.md`; change the documentation entries' paths to `upcoming/<slug>.md`; and update the project's version-cut script or instructions to combine the folder.

## Existing Project Migration

**Migration is always offered, never executed unilaterally.** Do not rewrite, move, or delete a project's existing CHANGELOG, release notes, or version-history files without explicit user approval. The table below lists _suggestions you can offer_ — not a script to run.

When first working in a project, check whether it already has release notes or changelogs in a different format or location (e.g., a single `CHANGELOG.md` at the root, a `CHANGES.txt`, release notes embedded in `README.md`, GitHub Releases only, or a `docs/` subfolder with a different naming scheme).

If something similar exists but does not match the structure described above, describe what you found, explain how it differs, and ask whether the user wants to migrate. Frame it as a recommendation:

> "This project has a `CHANGELOG.md` at the root. Want me to migrate it to the per-version structure under `docs/changelogs/` and `docs/release-notes/`?"

Only after the user agrees, follow the suggestion below. Always preserve the original content during migration — either by incorporating it into the new structure, or by keeping the original file with a note that it has been superseded. Never silently overwrite or delete.

**Suggested migrations to offer:**

| What you find                                                                          | Migration to propose                                                                                      |
| -------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Single root `CHANGELOG.md`                                                             | Split into `docs/changelogs/` per-version files; extract user-facing entries into `docs/release-notes/`   |
| Release notes in `README.md`                                                           | Extract into `docs/release-notes/` per-version files; remove or replace the README section with a pointer |
| Flat `docs/changelog.md` or similar                                                    | Restructure into per-version files under `docs/changelogs/` and `docs/release-notes/`                     |
| Per-version files with different naming (e.g., `1.2.3.md` without `v` prefix)          | Rename to `v{version}.md`                                                                                 |
| A single `docs/changelogs/upcoming.md` / `docs/release-notes/upcoming.md` working file | Switch to `upcoming/` folders with one file per change — see "A project still on a single `upcoming.md`"  |
| Only GitHub Releases (no files in repo)                                                | Pull release content into `docs/release-notes/` and `docs/changelogs/` per-version files                  |
| Correct structure but missing one side (e.g., changelogs exist but no release notes)   | Generate the missing side from the existing content                                                       |

## Common Mistakes

| Mistake                                                            | Fix                                                                               |
| ------------------------------------------------------------------ | --------------------------------------------------------------------------------- |
| Silently combining `upcoming/` entries during version cross-check  | Tell the user what you found and confirm before combining                         |
| Editing another change's entry file in `upcoming/`                 | Touch only your own `<work-item-slug>.md`; that is what keeps branches apart      |
| Acting on a migration without explicit user agreement              | The migration table lists _offers_ — never execute one unilaterally               |
| Combining files by hand when the project has a version-cut process | Use the project's documented version-cut process; it combines as part of the bump |
