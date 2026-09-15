# Make pnpm prettify:check pass on a clean checkout

## Origin

Split at triage (2026-09-15) from inbox entry
`2026-09-11-prose-defects-the-heading-sweep-found.md`, part 7, whose other parts
became the guide prose item. Kept on its own because it is a large mechanical change
to the formatting surface, not a documentation edit, and the entry itself says the
choice between reformatting and `.prettierignore` is a real decision.

Checked at triage: `pnpm prettier --check .` (the check without its cache) reports
**243 files** at `f9ee6b28`, up from the 168 the entry counted — roughly
`docs/capabilities` 68, `docs/work` 60, `docs/taxonomy` 43, `tests/fixtures` 29,
`tests/cli` 15, skills about 16, plus `README.md`, `tcw-config.yaml`, two guides, a
web client test and evals. `.prettierignore` exists and does not exclude the ledgers,
active work or `tests/fixtures`. `package.json`'s `typecheck` script runs
`prettify:check` first, so `pnpm typecheck` is red on a clean checkout too. The README
rewrite formats only `README.md`, `docs/guide/jira.md` and `docs/guide/work.md`.

## Folded in: from inbox entry `2026-09-11-prose-defects-the-heading-sweep-found.md` (Defects the heading sweep found that no heading can fix)

7. **`pnpm prettify:check` fails on 168 files at `3a063f6f`** — test fixtures
   under `tests/fixtures/` and sources under `web/client/` that are inside the
   formatting surface and are not formatted. This is the one entry here that is
   not a documentation change: a documented contributor command that is red on a
   clean checkout teaches contributors to ignore it, and the prose in item 4
   calling it deterministic is false while it stays that way.
