---
verdict: accepted
judges: 2
---

# Review — round 1

Reviews branch `v4.0.1` at `a3848dca` (TCW-177's commits `309b452a` to
`a3848dca`, read together with TCW-119's and TCW-120's on the same branch).
The reviewer is a separate agent that did not write the code; it ran the
released `tcw` 4.0.0 only for the stage prompt, and this worktree's
`.venv/bin/tcw` and `.venv/bin/pytest` (which import this worktree's `tcw/`,
checked with `tcw.__file__`) for every check, since the released 4.0.0
refuses this branch's key-form item files.

## The code review's three findings, rechecked

1. **The release is 4.1.0.** Answered. The spec says why in Goal 7, Non-goals
   ("Old TCW reading new files"), S-9 and Risks: the item file's format
   changes, a patch release never changes a format
   (`docs/guide/configuration.md`), and TCW 4.0.0's `version_problem`
   compares major and minor, so a file stamped 4.1.0 gets "written by a newer
   TCW; upgrade TCW" instead of a misleading "is not on <site>". The restamp
   script (outside the repository, `restamp_items.py`) does what implement
   round 2 says. Run on a fresh clone of `a3848dca`:
   `117 item files stamped tcw-version: 4.1.0 (0 already were, 0 left)`;
   `git diff` held exactly 117 `-tcw-version: 4.0.0` and 117
   `+tcw-version: 4.1.0` lines and nothing else; a second run printed
   `0 item files stamped tcw-version: 4.1.0 (117 already were, 0 left)`. It
   touches only files whose `ticket:` line is a key, and keeps line endings.
2. **`tcw migrate` and the documents.** Answered. `_ticket_key`
   (`tcw/migrate/stores.py`) returns the key only when the 3.x value is
   exactly `<site>/browse/<KEY>`, `<KEY>` a Jira key and the folder's name
   starting with `<KEY>-`; anything else is carried over unchanged. Probed
   beyond the item's own tests, on F-single, each value carried over as
   written and then reported by `tcw validate` exactly as 4.0.0 would:
   a host in different case (`is not on`), another site with another key
   (`is not on`), the site with a different project prefix `OTHER-1`
   (`names OTHER-1`), `<site>//browse/APP-1` (`is not on`), a lowercase key
   (`names app-1`), a trailing query (`names APP-1?x`); a folder `APP-10-a`
   holding the link to `APP-1` kept the link. The project's configuration
   in `.tcw/tcw-config.yaml` instead of the root `tcw-config.yaml` converted
   (`ticket: APP-1`). A configured site with a trailing slash never reaches
   `_ticket_key`: migrate stops with B3 ("work.jira.site: must be
   https://<host>, with no path and no trailing /"), so the `rstrip('/')`
   in `_ticket_key` is harmless. `_jira_site` reads the project's own layers
   (`own_jira_layers`: shared, user-wide, personal; no parent, no
   environment variable), the reading TCW-116 settled for migrate's Jira
   half; a 3.x project could not take `work.jira.site` from a parent (a 3.x
   `projects:` entry's `jira` block names where to file, and is dropped as
   D6), so no 3.x site is missed by that. A 2.8 layout never reaches the
   stores step (B2, naming the 2.8 to 3.0 guide). `docs/guide/jira.md`, the
   capability description and the migration guide's new paragraph claim the
   key only for `tcw work new`, `tcw work tickets adopt`, and a 3.x link on
   `work.jira.site` naming the folder's key, which is what the code does.
3. **The release notes' Upgrading section.** Answered. The entry opens with
   `## Upgrading`: everyone on a Jira project, CI and automation included,
   moves to 4.1 together; 4.0.0's exact refusal line is quoted with an
   example folder; files 4.0.0 wrote stay valid.

No new defect found in the migrate code.

## Checks run

- **The suite as CI runs it**, on a fresh clone of the worktree at
  `v4.0.1`, by `ci-suite.sh` (bare `pytest` in a clean virtual environment
  with a scratch home, then the web build). Load averages before: `2.04 2.62 3.40`; after: `4.66 4.78 4.52`. Its lines: `HEAD a3848dca7eb72178d6892cd856132b4aebaa40f6`, `8311 passed, 115 skipped in 1386.59s (0:23:06)`, `suite and web build passed`, exit 0. No test failed, `tests/test_check_versions.py::test_a_hanging_cli_is_abandoned_silently` included. The latest `main` run on GitHub (41672125999, `test`, success) passed `tests/test_check_versions.py` on Python 3.11 and 3.14: `8256 passed, 128 skipped`.
- `tcw validate` (this checkout's): `0 errors, 0 warnings, 0 unresolved`.
  `tcw validate --remote`: `117 item folders checked against their tickets`,
  `0 errors, 0 warnings, 0 unresolved`.
- Red and green: the item's tests (`tests/work/jira/test_jira_validate_offline.py`,
  `test_jira_write.py`, `test_jira_tickets.py`, `test_jira_nested.py`,
  `test_jira_state_files.py`, `tests/migrate/test_migrate_stores.py`) run
  against `tcw/` as at `cf9279e9` (before the change): `11 failed, 148
  passed`, the failures being the key form clean, the four key-form and
  not-a-string messages, `test_a_new_item`, the adopt test, the missing-file
  message, `test_new_writes_the_version_and_the_ticket`, the migrate
  conversion and the key-form pair. Against `a3848dca`: `159 passed`.

## Acceptance criteria

| # | Criterion | Result | Evidence |
| - | --------- | ------ | -------- |
| 1 | Writer writes `ticket: TCW-1` alone; adopt writes the key | met | `JiraBackend._item_file` writes `f"{version_line()}ticket: {key}\n"`; `test_a_new_item` asserts the whole text; the adopt test (`test_jira_tickets.py:330`) asserts `ticket: {key}`; both red before, green after |
| 2 | Key form accepted, exit 0 | met | `test_the_key_form_is_clean`, red before, green after; this repository's 117 key-form files validate clean |
| 3 | Wrong key refused naming both, exit 1 | met | `test_each_error` row: `code == 1` and "ticket 'TCW-2' is not the folder's key, TCW-1"; red before |
| 4 | 4.0.0 link form accepted | met | `test_a_clean_tree_is_clean` (fixture writes `<SITE>/browse/<KEY>`), passes |
| 5 | Link form still checked | met | `test_each_error` rows "is not on" (another site) and "names TCW-2", exit 1 |
| 6 | Not a string refused, exit 1 | met | `test_each_error` row `ticket=7`: "ticket 7 is not the folder's key, TCW-1"; red before |
| 7 | Missing-file message | met | `UNMADE_MESSAGE = "is missing; it holds the ticket's key"`, used by `_item_file_problems`; `test_a_key_named_folder_with_no_state_file_is_no_item` asserts "ticket's key", red before |
| 8 | 2, 3, 6 red then green; 1 and 7 too | met | the red run above (`11 failed`) and the green run (`159 passed`) |
| 9 | This repository's item files | met | every `docs/work/**/tcw-work-item.yaml`'s `ticket:` equals its folder's key prefix (loop over 117 files, no mismatch); none holds `/browse/`; `validate` and `validate --remote` 0 errors |
| 10 | Documentation | met | `docs/guide/jira.md` (key, 4.0.0 link still valid); `docs/guide/linking-and-validation.md` (new message); capability description ("the ticket's key"); entry files named by the folder in `docs/release-notes/upcoming/` and `docs/changelogs/upcoming/`; the sites in the added lines are `example.atlassian.net`, `example.invalid` and the test fixtures' `acme.atlassian.net` (in implement round 1's quoted test output), none a real site |
| 11 | Full suite as CI runs it | met | `8311 passed, 115 skipped` on a fresh clone at `a3848dca`, bare `pytest` as CI runs it, and the web build passed |
| 12 | Migration | met | `test_a_jira_items_ticket_link_on_the_site_becomes_its_key` (red before), `test_any_other_ticket_value_is_carried_over_as_it_is` (four values), `test_a_ticket_pair_in_either_form_is_equal` (key form red before); probes above |

`capabilities.yaml` names `changed: tcw.capabilities/work/keep-work-items-in-jira`;
its record is present and its description says what the code does (the key
written by TCW, the 4.0.0 link still accepted).

## Documentation entries (`documentation-sync`)

| Entry | Fires | Where |
| ----- | ----- | ----- |
| `docs/guide/jira.md` (Jira-Change) | yes | `309b452a`, `275a4004` |
| `docs/guide/<topic>.md` (Guide-Topic-Change) | yes | `linking-and-validation.md`, `work.md` in `309b452a`; `migration-guide-3.X-to-4.0.0.md` in `275a4004`, `fc3a54d7` |
| `docs/release-notes/upcoming/<folder>.md` (Public-API) | yes | `309b452a`, `275a4004` (Upgrading) |
| `docs/changelogs/upcoming/<folder>.md` (Any-Code-Change) | yes | `309b452a`, `275a4004` |
| `README.md` (Public-API) | no | it never describes the `ticket` line |
| `skills/<component>/SKILL.md` | no | no CLI surface, field or lifecycle change; no skill names the line |
| `skills/configure/references/` | no | no configuration key changes |
| `docs/use-cases.md` | no | UC-7's requirements and known gaps are unchanged; the spec names the cases |

## With TCW-119

TCW-119 changes how `tcw migrate` rewrites an item's `capabilities.yaml`
taxonomy entries (`route_term_entry_3x`, `Owners.replace` for
`capabilities-yaml` rows). TCW-177 changes the item's state file's `ticket`
line, which is not a reference field (`jira-item` has only `parent` and
`blocked-by`), by a `SetTop` edit after `Owners.replace` has run. Different
files, different code paths, different blockers (B10 there, B11's `also`
here). Both edit the 3.X to 4.0.0 migration guide, in separate sections, and
`tests/test_migration_guide_4_0.py` passes on the combined text. No
interaction found.

## Verdict

Accepted. Every criterion is met against the code, the capability record says what the code does, the suite passed as CI runs it, and `documentation-sync` found every entry that fires already updated in the item's commits, with no update outstanding.
