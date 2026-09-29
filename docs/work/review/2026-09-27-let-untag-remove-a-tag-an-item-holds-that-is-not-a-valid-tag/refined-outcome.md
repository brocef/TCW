# Refined outcome — Let untag remove a tag an item holds that is not a valid tag

## Decision

**Accepted**, 2026-09-29, during an unattended run: the decision is the
implementing agent's, taken in place of the user's at the user's request, on the
evidence below.

## Evidence

- `tcw:verifier` assessment: criteria 1–6 met, each on a test and a hands-on
  run in a scratch node; `tcw validate` still reports a held invalid tag.
- Full suite, run by the verifier from the item worktree with its private
  virtual environment: **4777 passed, 3 skipped** (exit 0), matching the
  implementer's run.
- Hands-on (mine): an item holding `['cli,docs', '!!!', 'cli']` loses
  `cli,docs` to `--untag 'cli,docs'` and `!!!` to `--untag '!!!'`, both exit 0,
  leaving `['cli']`; `--untag '???'`, which it does not hold, is refused with
  exit 1.

## Accepted deviations from the spec

- The spec was amended at implement (3754d663): the fix moved into
  `update_work` (`_validate_tags(held=...)`), because the original design could
  not meet criterion 1 — removing one invalid tag re-validated the other and
  was refused. The amendment also means a tag that is valid but no longer
  registered no longer blocks edits of an item holding it; `check` and
  `validate` still report it. This widens the request's scope; accepted
  because the one rule ("refuse an edit only for what it adds") covers both
  cases, and blocking every edit of an item over a tag it already holds is
  the same bug in another form.
- `--untag ''` now exits 1 ("names no tag") rather than 2; covered in the
  spec's Risks.
- A held non-string tag (YAML `true`) is written back as the string `'True'`
  when resent; recorded in `outcome.md`, nothing is lost.

## Closeout

- Capability reconciliation: none declared; nothing to reconcile.
- Documentation: `docs/guide/work.md`, `skills/work/references/tags.md`,
  changelog and release-note entry files.
- Not from a GitHub issue.
- Merge route: `tcw work complete` from the `bug-run` integration worktree,
  merging into `bug-run`; `main` is left for the user to merge.
- Follow-ups: none filed.
