---
verdict: accepted
judges: 1
---

# Review round 1 — TCW-106

Reviewed by a separate `tcw:reviewer` agent, read-only, against the spec,
plan, `capabilities.yaml` and `implement/round-1.md`, over the change
`64042c2b..9f43d5f6` (outside `docs/work/`) and this item's folder. The
dispatching session checked its report and wrote this round.

## The suite, run as CI runs it

`.venv/bin/pytest -q -p no:cacheprovider` from the worktree root:
`5266 passed, 118 skipped in 547.33s`. The released 3.0.2 `tcw validate` in
the worktree: `0 errors, 0 warnings, 0 unresolved`.

## Acceptance criteria

Every criterion is met. The tests are in `tests/test_project_files_cli.py`
unless named otherwise.

- **AC 1, met:** `test_ac1_init_writes_the_versioned_configuration_in_the_tcw_folder`.
- **AC 2, met:** `test_ac2_init_writes_the_ignore_rule_in_the_tcw_folder_once`,
  `test_ac2_outside_a_repository_the_note_names_the_new_place`.
- **AC 3, met:** `test_ac3_a_subfolder_acts_on_the_project_above_it`,
  `test_ac3_in_a_monorepo_the_nearest_project_wins`.
- **AC 4, met:** `test_ac4_a_tcw_folder_without_the_file_is_not_a_project`,
  which compares exit code and both output streams with an empty folder's.
- **AC 5, met:** the four-command test (nothing written), the subfolder test,
  and `--version` and `--help` exiting 0. The reviewer also ran other
  commands by hand in a 3.x folder, and each was refused with the Design 4.1
  line. Every subcommand, `serve` included, goes through
  `refuse_legacy_project` first in `_dispatch`.
- **AC 6, met:** `test_ac6_a_4_0_project_nested_in_a_3x_one`.
- **AC 7, met:** ten refusal cases across rows a-d for both files, and the
  accepted versions `4.0.0`, `'4.0'`, `4.0.99` and an older 4.x minor.
- **AC 8, met:** `test_ac8_config_show_hides_the_version_and_the_allowlist_ignores_it`.
- **AC 9, met:** three tests, and every byte-comparison edit test in
  `tests/test_config_edit_writers.py` now checks the first line.
- **AC 10, met:** two tests, one with a decoy `.tcw/docs/x.md`.
- **AC 11, met:** twelve cases: four keys times three files.
- **AC 12, met:** three tests, covering `not-tags`, its JSON form, the hint,
  and a key that must be text.
- **AC 13, met:** the 3.x connection is reported. Its "not read" assertion is
  weak (F1).
- **AC 13a, met:** four tests.
- **AC 14, 14a, 14b, 14c, met:** tests named after them.
- **AC 15, met:** all five version fields read 4.0.0, and
  `tests/test_plugin_manifests.py` passes.
- **AC 16, met:** the suite result above.

The reviewer made nine breaks in memory, each to a different behavior, and
each one turned its criterion's tests red. They covered: `.tcw` read as 3.x,
the newer-version row, `Origin.folder`, `without_version`, the 3.x
connection check, the personal file's version check, `refuse_legacy_project`,
the line order in `plan_id`, and where the ignore rule is written.

## Other checks

- **Readers of `tcw-*.yaml`.** Every primary reader calls `version_problem`.
  Three secondary reads skip it, and none is a primary read:
  `tcw/validate.py` `_claims_work` and `_configured_path_problem` run after
  the version error is reported, and `tcw/store/project.py` `_worktree_copy`
  reads an `id` only to word a warning.
- **This repository's two configurations** stay in step through
  `tests/test_repo_config_pair.py`, and `tests/test_repo_lifecycle.py` loads
  the 4.0 copy with no problems.
- **Records.** Every capability and term named in `capabilities.yaml`
  exists and matches the code, except one sentence in `format-version` (F2).
- **Public repository.** No private project name in the diff, once the Jira
  site URLs that TCW itself writes are excluded.

## Documentation entries (`documentation-sync`)

The dispatching session ran the `documentation-sync` skill against
`tcw work docs`. The reviewer agent has no way to run a skill, so it checked
the entries by hand and reached the same conclusions.

- `docs/release-notes/upcoming/<folder>.md` [Public-API] and
  `docs/changelogs/upcoming/<folder>.md` [Any-Code-Change]: fired, and
  written for this item's folder.
- `README.md` [Public-API], `docs/guide/<topic>.md` [Guide-Topic-Change],
  `skills/<component>/SKILL.md` [Skill-Driven-Component],
  `skills/configure/references/<document>.md` [Configuration-Key-Change] and
  `docs/use-cases.md` [Project-Setup-Change]: fired. They are deferred to
  TCW-117 by plan step 8, and TCW-117's request names each of them. Nothing on
  `v4` is released before TCW-117 lands, ahead of the release item TCW-118.
- `docs/guide/jira.md` [Jira-Change]: did not fire. Nothing a command does to
  a ticket changed.

## Findings

None of these blocks the verdict. The small ones (F1-F8) belong to this
change and are folded in during qa, as this project does with small
follow-ups. Each fix is committed on `v4`, and the suite is run again before
the qa findings are posted.

- **F1.** AC 13's "not read" assertion always passes: the command exits 1,
  so the list it checks is empty. Assert it in a way that can fail.
- **F2.** `docs/taxonomy/format-version/description.md` says an older major
  version is refused. The code refuses only a major version below 4.
- **F3.** The changelog says `_resolve_override` checks `tcw-version`. It
  checks only the 3.x layout.
- **F4.** `implement/round-1.md` cites `d6efa7d7` for step 5a. The commit on
  the branch is `5dc09dd6`.
- **F5.** The 3.x wording for a `TCW_PROJECT_<ID>` that names a 3.x folder
  (`tcw/store/project.py`, around line 771) has no test.
- **F6.** `Origin.folder` (`tcw/config.py:80`) computes the root itself
  instead of calling `root_of`.
- **F7.** A `.tcw/` file with no version also gets naming-rule errors, and
  `when: {not_tags: …}` produces two errors. Report each problem once.
- **F8.** `test_an_empty_personal_file_is_an_empty_layer` now tests a file
  holding only the version line. Its name should say so.

Two need separate changes, and are recorded on the items that own them:

- **S1.** `tcw init` is refused anywhere inside a 3.x project, so no 4.0
  project can be created inside a partly migrated monorepo. For TCW-116.
- **S2.** Whether an empty `.tcw/` file should be exempt from the
  missing-version refusal is a spec question, which nothing here requires.
  For TCW-116.
