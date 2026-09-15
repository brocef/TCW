# Check the whole tracked tree, ledgers included, for removed skill names

## What is wanted

The tests that keep removed skill and command names from coming back, and that check no
live document still names a deleted lifecycle document, should look at every live file
in the repository — and only live files.

Today they do neither reliably:

1. **They walk the disk with hand-kept exclusion lists.** One test skips archives by
   path prefix and directories by name. A linked worktree under `.claude/worktrees/`
   holds a second full checkout whose archived changelogs did not match the prefix list,
   so the suite went red with nothing wrong. `.claude` was added to the name list, but the
   exclusion is still expressed twice, in two shapes, and only one works with nesting.
   Reading the tracked tree from `git ls-files` would need neither list.
2. **They skip live folders.** The removed-names check covers `skills/`, the two manifest
   folders, `README.md`, `docs/guide/` and `docs/lifecycle/`, but not `agents/`,
   `hooks/`, `scripts/`, `evals/`, `tests/`, `AGENTS.md`, `CLAUDE.md`,
   `docs/capabilities` or `docs/taxonomy`. All are clean today; nothing keeps them so.
3. **Three tests each parse skill frontmatter themselves.** The rule for what counts as a
   skill body lives in three places.

## Constraints

- `tcw://C/skills/...` links in the ledgers name skills on purpose and must not be
  reported.
- Names written without a leading slash (for example `tcw-audit-work-backlog`) must be
  caught; a one-off `git grep` for the slash form missed them before.

## Notes

- Merged at triage from three entries (the worktree note, parts 1 and 5 of the skill
  restructure guards, and §3 of the capability overlaps), because all change which files
  the skill-parity tests read. All kept verbatim in `intake.md`.
- Checked at triage on `main`: the parity test is the only whole-repository walk with a
  hand-kept exclusion list; five other tests already use `git ls-files`; `LIVE_ROUTES`
  lacks both ledger folders.
- Reference material: asked; none provided.

## References

- `tests/test_plugin_manifests.py`, `tests/test_committed_paths.py` — existing tests that
  already read the tree from `git ls-files`.
