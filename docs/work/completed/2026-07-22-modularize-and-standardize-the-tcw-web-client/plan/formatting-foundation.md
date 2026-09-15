## Objective

Establish deterministic formatting with a deliberately bounded repository
surface and commit the first formatting pass separately from behavioral work.

## Pre-stage checks

- Confirm planning artifacts are committed and run `tcw work start` as its own
  commit before changing implementation files.
- Inventory the existing `.prettierrc.json`, `package.json`, lockfile, theme,
  and generated-bundle changes without discarding or staging them early.
- Inspect package scripts and the current Prettier file discovery behavior.

## Implementation

- Add `.prettierignore` for dependencies, package-manager files, generated web
  bundles, build/test/cache output, logs, worktrees, completed work items, and
  versioned changelog/release-note archives.
- Keep maintained source/configuration, capabilities, taxonomy, backlog/active
  work, `README.md`, and upcoming notes eligible.
- Retain the existing Prettier config, package scripts, dependency, and lockfile
  changes.
- Run the formatting write script and commit the mechanical pass by itself.

## Post-stage checks

- Run `pnpm prettify:check` and `git diff --check`.
- Inspect the formatted file set for ignored historical/generated content and
  accidental semantic changes.
- Commit the formatting foundation before modular source edits.
