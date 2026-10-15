## Added

- `docs/guide/cli.md`: output streams, standard input, naming an item, and the
  exit code table, checked against `tcw/exit.py`.
- `skills/configure/references/personal.md`: personal configuration and which
  keys a person may set.
- `docs/guide/examples/commit-item-after-move.sh`: the opt-in git example, a
  `post` hook that commits an item's folder after it moves.
- Tests: `tests/test_docs_describe_3_0.py` (README structure, 2.x vocabulary
  scan, links and anchors, allowance names, owned set, inventory),
  `tests/test_cli_guide.py`, `tests/test_git_example.py`, and the work-guide
  verb check in `tests/test_documented_cli_surface.py`.
- `tests/test_doc_allowance.py`: every allowance entry must still be named by
  some live document.

## Changed

- Rewritten for 3.0: `README.md`; `docs/guide/work.md`, `jira.md`,
  `configuration.md` and `multi-repo.md`; `skills/configure/SKILL.md` and its
  references; `docs/lifecycle/abstraction.md`, `implementation.md` and
  `harness.md`; the worktree section of `AGENTS.md`.
- Edited for 3.0: `docs/guide/taxonomy-and-capabilities.md` and
  `docs/guide/linking-and-validation.md`.
- `tests/doc_allowance.py` holds only entries named by files TCW-76 rewrites;
  the flag, form and value lists are empty.
- `tests/test_upcoming_entries.py` exempts this item's release-notes entry,
  which carries the 3.0.0 introduction, from starting at a `##` heading.
- The `upcoming/README.md` files name entries after the item's folder name.
- The `configure` skill's capability record and taxonomy entry, and
  `evals/coverage.py`, follow the rewritten skill and its new references.
- `tests/test_shipped_text.py` scans the `configure` skill too.
  `tests/test_configuration_text_home.py` checks that each configuration key
  has one heading in the `configure` references, saying who may set it, and
  that the labels match `tcw.config.PERSONAL_KEYS`.
  `tests/test_check_versions.py` expects the fourteen skills left after TCW-74.

## Removed

- `docs/work-inbox-template.md`.
- `skills/configure/references/tracker.md`.
