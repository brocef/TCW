# Make pnpm prettify:check pass on a clean checkout

## What is wanted

`pnpm prettify:check`, which the guides call "repository-wide and deterministic", should
pass on a clean checkout, and stay passing. Today it fails on 243 files, so contributors
learn to ignore it, and `pnpm typecheck` — which runs it first — is red too.

**Decided with the maintainer at triage:** reformat everything that is out of line, in
one change, so the check covers the ledgers, work items and test fixtures from then on,
rather than excluding them in `.prettierignore`.

## Constraints

- **Test fixtures are data.** Reformatting a fixture can change what a test measures; any
  fixture whose exact bytes a test depends on must keep passing.
- **Other sessions edit these files.** The ledgers and active work items are written
  constantly; a mass reformat should land when it will not collide with work in flight,
  and the README rewrite formats `README.md`, `docs/guide/jira.md` and
  `docs/guide/work.md` itself.

## Notes

- Split at triage from part 7 of the heading-sweep entry, and kept on its own because it is
  a large mechanical change, not a documentation edit.
- Checked at triage (`pnpm prettier --check .`, without the cache, at `f9ee6b28`):
  roughly `docs/capabilities` 68, `docs/work` 60, `docs/taxonomy` 43, `tests/fixtures` 29,
  `tests/cli` 15, skills about 16, plus `README.md`, `tcw-config.yaml`, two guides, a web
  client test and evals. `.prettierignore` already excludes resolved work, versioned
  changelogs and caches.
- Reference material: asked; none provided.

## References

- `package.json` — `prettify`, `prettify:check` and `typecheck` scripts.
- `.prettierignore` — what is excluded today.
