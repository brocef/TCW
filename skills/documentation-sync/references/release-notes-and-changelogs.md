# Release Notes & Changelogs

Load this reference when the project uses the opt-in `docs/release-notes/` + `docs/changelogs/` structure **and** you're writing into those files (appending entries, rotating `upcoming.md`, migrating an existing `CHANGELOG.md`, or evaluating version drift before an append).

**This structure is opt-in.** The `docs/release-notes/` and `docs/changelogs/` layout described below applies only when the project's `## Documentation Sync` section explicitly lists `upcoming.md` files (or when the user asks you to set the structure up — read `setup.md`). Don't create `docs/release-notes/upcoming.md` or `docs/changelogs/upcoming.md` in a project that hasn't adopted them. Some projects use only GitHub Releases, only a root `CHANGELOG.md`, or have no version-history files at all — that's a valid choice.

For monorepos, each package may carry its own `docs/release-notes/` and `docs/changelogs/` directories, or the repo may share a single set at the root. Follow whatever the project's `## Documentation Sync` section points to; don't infer a structure that isn't listed.

## Directory Structure

```
docs/
  release-notes/
    upcoming.md        # Working file for the next unreleased version
    v1.2.3.md          # Finalized release notes for v1.2.3
  changelogs/
    upcoming.md        # Working file for the next unreleased version
    v1.2.3.md          # Finalized changelog for v1.2.3
```

File names follow the pattern `v{version}.md`. The `upcoming.md` files hold content for the next version, whose number is not yet known (could be a patch, minor, or major bump).

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
- `docs/release-notes/upcoming.md` [Public-API] — User-facing release notes; plain language, no jargon
- `docs/changelogs/upcoming.md` [Any-Code-Change] — Developer changelog with commit hash ranges
```

The trigger system determines when these files get updated — release notes fire on public-facing changes, changelogs fire on any code change.

## Version Cross-Check

Before writing to `upcoming.md`, cross-check the project's current version (from `package.json`, `pyproject.toml`, `Cargo.toml`, `version.txt`, or whatever the project uses) against existing versioned files in `docs/release-notes/` and `docs/changelogs/`.

Two scenarios surface drift:

- **Version bumped, no `v{version}.md` exists yet:** the content currently in `upcoming.md` likely belongs to that version. **Tell the user what you found and confirm before renaming.** Do not silently rotate files.
- **`v{version}.md` exists but `upcoming.md` has older content that predates the bump:** the `upcoming.md` content needs to be merged into the versioned file. Again, confirm with the user before merging — losing or relocating an entry without acknowledgment is worse than asking.

After confirmation, the rotation is:

1. Rename `upcoming.md` to `v{version}.md` in both directories
2. Start a fresh `upcoming.md` for subsequent work

Always run the cross-check before appending — never silently lose content that should be attributed to a released version, and never silently rename files the user didn't ask you to rename.

**The rotation itself is part of the project's version-cut process.** Many projects automate the bump + rotate + commit + tag steps behind a single command or script — follow whatever the project's `CLAUDE.md` / Versioning section documents rather than rotating by hand when such a process exists.

## Existing Project Migration

**Migration is always offered, never executed unilaterally.** Do not rewrite, move, or delete a project's existing CHANGELOG, release notes, or version-history files without explicit user approval. The table below lists _suggestions you can offer_ — not a script to run.

When first working in a project, check whether it already has release notes or changelogs in a different format or location (e.g., a single `CHANGELOG.md` at the root, a `CHANGES.txt`, release notes embedded in `README.md`, GitHub Releases only, or a `docs/` subfolder with a different naming scheme).

If something similar exists but does not match the structure described above, describe what you found, explain how it differs, and ask whether the user wants to migrate. Frame it as a recommendation:

> "This project has a `CHANGELOG.md` at the root. Want me to migrate it to the per-version structure under `docs/changelogs/` and `docs/release-notes/`?"

Only after the user agrees, follow the suggestion below. Always preserve the original content during migration — either by incorporating it into the new structure, or by keeping the original file with a note that it has been superseded. Never silently overwrite or delete.

**Suggested migrations to offer:**

| What you find                                                                        | Migration to propose                                                                                      |
| ------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------- |
| Single root `CHANGELOG.md`                                                           | Split into `docs/changelogs/` per-version files; extract user-facing entries into `docs/release-notes/`   |
| Release notes in `README.md`                                                         | Extract into `docs/release-notes/` per-version files; remove or replace the README section with a pointer |
| Flat `docs/changelog.md` or similar                                                  | Restructure into per-version files under `docs/changelogs/` and `docs/release-notes/`                     |
| Per-version files with different naming (e.g., `1.2.3.md` without `v` prefix)        | Rename to `v{version}.md`                                                                                 |
| Only GitHub Releases (no files in repo)                                              | Pull release content into `docs/release-notes/` and `docs/changelogs/` per-version files                  |
| Correct structure but missing one side (e.g., changelogs exist but no release notes) | Generate the missing side from the existing content                                                       |

## Common Mistakes

| Mistake                                                           | Fix                                                                              |
| ----------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| Silently rotating `upcoming.md` during version cross-check        | Tell the user what you found and confirm before renaming                         |
| Acting on a migration without explicit user agreement             | The migration table lists _offers_ — never execute one unilaterally              |
| Rotating files by hand when the project has a version-cut process | Use the project's documented version-cut process; it rotates as part of the bump |
