## Added

- `docs/migration-guide-3.X-to-4.0.0.md`, the guide for moving a TCW 3.x
  project, or a family of related projects, to 4.0, and
  `tests/test_migration_guide_4_0.py`, which checks its sections, its mapping
  tables, its links, and that every 4.0 command it writes is one `--help`
  shows. (TCW-117)
- `THREE_X_PATTERNS` in `tests/doc_vocabulary.py`, the 3.x commands, flags,
  keys, file names and name forms 4.0 removes, and
  `tests/test_docs_describe_4_0.py`, which fails a live document that names
  one outside a passage naming `tcw migrate` or linking the migration guide;
  `scan` gains a `flags` argument, so this table is matched case-sensitively.
  The two ledgers stay out of that scan until TCW-118 migrates them
  (`UNMIGRATED_RECORDS`). (TCW-117)

## Changed

- The README, every guide under `docs/guide/`, `docs/use-cases.md`,
  `AGENTS.md`, the lifecycle documents, the five skills and their
  references, the agents, the procedures and the evals describe TCW 4.0;
  `docs/guide/multi-repo.md` is rewritten as "Related projects". The TCW-99
  design gains the seven dated amendments its children decided. (TCW-117)
- `tests/test_configuration_text_home.py`'s `KEY_PATHS` lists `parents` and
  `children` in place of the 3.x `projects.*` keys, and `GIT_ALLOWED` in
  `tests/test_shipped_text.py` gains one phrase, `` `<url>#<branch>` ``, the
  written shape of a manifest entry's `repository`. (TCW-117)
