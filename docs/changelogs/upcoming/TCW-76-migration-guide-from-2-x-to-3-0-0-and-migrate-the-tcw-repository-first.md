## Added

- `docs/migration-guide-2.8-to-3.0.0.md`: the 2.8 to 3.0.0 migration guide
  (TCW-76). Steps 0 to 12, each with a check; the mapping tables from every
  2.x key, stage, transition, `state.yaml` and `tracker.yaml` field, document,
  store-root file, hook variable, skill and agent to its 3.0 form; the 2.x
  behavior that had no key; Jira's REST form of every write; and step 12's
  search of agent instructions and memories.
- `docs/lifecycle/review.md`, bound to the `review` stage's prompt.
- `docs/tcw-3.0-migration-log.md`: the record of TCW's own migration.
- Tests: `tests/test_migration_guide.py` (the guide against its acceptance
  criteria, and that the documentation allowance stays gone; it runs the
  guide's own step 9 pattern builder, step 12 list of places and step 12
  `expected-names` reader on scratch fixtures),
  `tests/test_require_artifact.py`, `tests/test_repo_lifecycle.py` (TCW's own
  3.0 configuration, its bound files, the spec templates against the
  sections `tcw/work/prompts/spec.md` asks for, and the documentation
  entries; it replaces the 2.x file TCW-70 deleted), and
  `tests/work/removed_2x.py`, the permanent list of 2.x commands the code
  tests check stay gone.

## Changed

- TCW's own repository is on 3.0: `tcw-config.yaml` uses `work.backend: jira`
  with the project `TCW`, `work.stages` with a status per stage, a
  `git pull --ff-only` prompt on `request`, `spec`, `plan`, `implement`,
  `review`, `qa` and `postmortem` (`inbox` is bound none, and `completed`
  and `discarded` take no prompt), the commit-after-move `post` hook on
  every move to a stage after `inbox`, and the `Tracker-Change`
  documentation trigger renamed `Jira-Change`; the board is flattened to one `TCW-<n>-<words>` folder per
  item with a one-line `item.yaml`, its documents in stage folders, and no
  inbox, `graveyard.yaml` or status folders. `AGENTS.md`, `.gitignore` and
  the capability records' `Planning doc:` lines were updated to match.
- `scripts/require_artifact.py` asks `tcw work path "$TCW_SLUG" <stage>`
  where the document lives instead of composing a path, and still fails
  closed.
- The spec templates say they are the outline for `spec/spec.md`;
  `docs/procedures/create-work.md` matches 3.0's `create-work` procedure.

## Removed

- `tests/doc_allowance.py` and `tests/test_doc_allowance.py`, the temporary
  list of removed commands, flags and keys documents could still name while
  TCW 3.0 was written, with every branch that read it in
  `tests/test_documented_cli_surface.py`, `tests/test_shipped_text.py` and
  `tests/test_docs_describe_3_0.py`. A document naming a removed command or
  a refused key now always fails.
