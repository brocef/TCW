# Implement — round 2

Answers the code review of round 1 (branch `v4.0.1`, at `3ea000bd`, which
also holds TCW-119 and TCW-120), and the maintainer's decision that came with
it: this release is **4.1.0**, not 4.0.1.

The CLI under change is `tcw/`, so every check ran this worktree's
`.venv/bin/tcw` and `.venv/bin/pytest`; the item's stage was not moved.

## Findings and what was done

1. **The release is a minor one (finding 1, the maintainer's decision).**
   The item file's format changes, and `docs/guide/configuration.md` says a
   patch release never changes a format. TCW 4.0.0's `version_problem`
   (`tcw/project_files.py`) compares major and minor, so a file stamped
   `tcw-version: 4.1.0` makes 4.0.0 say it was written by a newer TCW and to
   upgrade, the message `docs/use-cases.md` S-9 designs for this; a file
   stamped 4.0.x would instead fail its `ticket` check with the misleading
   "is not on <site>".
   - The spec's claims that this was a patch release that S-9 permitted
     (Non-goals, Use cases S-9, Risks) now say 4.1.0 and why; Goals 7 and
     Design 4 record the release and the restamp. TCW-119's and TCW-120's
     documents that named "the 4.0.1 release" now name 4.1.0 (TCW-119
     spec's last note and review round 1; TCW-120's plan, spec and review
     round 1). Mentions of the branch `v4.0.1` and its worktree are names of
     that branch, and were left.
   - **The restamp.** The 117 item files stay `tcw-version: 4.0.0` in this
     branch: stamped 4.1.0 now, this branch's own code, which reports 4.0.0
     until the version is cut, would refuse them as newer. A script outside
     the repository sets `tcw-version: <version>` in every
     `docs/work/**/tcw-work-item.yaml` whose `ticket:` line is a key, changing
     nothing else, and prints the count; the maintainer runs it right after
     `scripts/cut_version.py` and folds it into the release commit. Checked on
     a clone of this branch with its uncommitted changes applied and
     `tcw/__init__.py` saying 4.1.0: `117 item files stamped tcw-version: 4.1.0
     (0 already were, 0 left)`; `git diff` showed 117 lines
     `-tcw-version: 4.0.0` and 117 `+tcw-version: 4.1.0` and nothing else;
     that clone's code ran `tcw validate`: `0 errors, 0 warnings, 0
     unresolved`. The released `tcw` 4.0.0 on the same clone: `117 errors`,
     each one like

     ```
     error: docs/work/TCW-10-check-the-tracker-s-workflow-against-the-statuses-mapping-in-tcw-validate/tcw-work-item.yaml: was written by TCW 4.1 (tcw-version 4.1.0), newer than this TCW (4.0.0); upgrade TCW
     ```

2. **`tcw migrate` kept the site's address (finding 2).** The Jira guide and
   the capability description said an item file "never" holds the site's
   address, but `tcw migrate` (`_plan_object` in `tcw/migrate/stores.py`)
   carried a 3.x `ticket: <site>/browse/<KEY>` over unchanged. Folded in, as
   the maintainer asked: the 3.x to 4 conversion now writes `ticket: <KEY>`
   when the 3.x line is exactly the link on the project's `work.jira.site`
   naming the folder's key (`_ticket_key`; the site from the project's own
   layers, read by `_jira_site` in `tcw/migrate/plan.py` as
   `tcw migrate --no-jira`'s summary reads it). Any other value is carried
   over, for `tcw validate` to report as before. A 3.x file left beside a
   4.0 file holding the key (this TCW's run stopped between the two) or the
   link (written by 4.0.0) is an equal pair, not B11 (`_both`'s new `also`).
   `_ticket_key` matches the key with its own pattern rather than importing
   `folder_key`, since `tests/migrate/test_migrate_jira.py` allows only
   `tcw/migrate/jira.py` to import the Jira backend (it went red on the first
   attempt, which did). Tests first, in `tests/migrate/test_migrate_stores.py`
   on F-single: `test_a_jira_items_ticket_link_on_the_site_becomes_its_key`,
   `test_any_other_ticket_value_is_carried_over_as_it_is` (another site,
   another key, a trailing `/`, a key already) and
   `test_a_ticket_pair_in_either_form_is_equal` (key, link). Red before the
   change:

   ```
   AssertionError: assert 'tcw-version:...rowse/APP-1\n' == 'tcw-version:...cket: APP-1\n'
     - ticket: APP-1
     + ticket: https://example.invalid/browse/APP-1
   B11 docs/work/APP-1-a/item.yaml: differs from docs/work/APP-1-a/tcw-work-item.yaml at ticket; ...
   assert 3 == 0
   2 failed, 5 passed, 25 deselected
   ```

   Green: `tests/migrate/test_migrate_stores.py` and
   `tests/migrate/test_migrate_jira.py`, `77 passed`.

   The documents now say exactly what holds: `docs/guide/jira.md` — TCW
   writes the key (for `tcw work new`, `tcw work tickets adopt`, and `tcw
   migrate` from a 3.x link on the site naming the folder's key); a file
   written by TCW 4.0.0 holds the link, which 4.1 still accepts, and can be
   changed to the key by hand. The `keep-work-items-in-jira` description says
   the same. `docs/migration-guide-3.X-to-4.0.0.md` gains a paragraph below
   its Files table on a Jira `item.yaml`'s `ticket:` line. (It was first a
   row of that table, which the full suite refused:
   `tests/test_migration_guide_4_0.py::test_the_names_search_finds_every_3x_file_name_and_name_form`
   reads each first-column name as a 3.x file name the guide's search must
   find, `AssertionError: ['ticket: <site>/browse/<KEY>']`; as a paragraph,
   `71 passed`.) The spec gains Goal 5, Design 5
   and criterion 12, and its sweep table's `tcw/migrate/` row and Non-goals
   say what migrate now writes.

3. **The release notes did not say who must upgrade (finding 3).** The
   TCW-177 release-notes entry now has an `## Upgrading` entry: existing files
   written by 4.0.0 stay valid and only new, adopted or migrated items get
   the key; everyone on the project, CI and other automation pinned to an
   older TCW included, should move to 4.1 together; and TCW 4.0.0 refuses a
   4.1 item file with the line above (shown with an example item folder).
   The changelog entry records the migrate change, the new message and the
   minor release.

4. **A key-form value printed bare (the cosmetic note).**
   `_item_file_problems`' key-form message was "ticket '<v>' names <v>, but
   the folder's key is <KEY>", whose second `<v>` was not quoted. It is now
   "ticket '<v>' is not the folder's key, <KEY>", the value shown with
   `!r` only, the same words as the not-a-string message. Test first, in
   `tests/work/jira/test_jira_validate_offline.py::test_each_error`: the
   `TCW-2` row's expected text changed, and rows for an empty value and a
   two-line value were added. Red:

   ```
   AssertionError: error: docs/work/TCW-1-x/tcw-work-item.yaml: ticket 'TCW-2' names TCW-2, but the folder's key is TCW-1
   AssertionError: error: docs/work/TCW-1-x/tcw-work-item.yaml: ticket '' names , but the folder's key is TCW-1
   AssertionError: error: docs/work/TCW-1-x/tcw-work-item.yaml: ticket 'TCW-1\nTCW-2' names TCW-1 TCW-2, but the folder's key is TCW-1
   3 failed, 25 passed
   ```

   Green: `28 passed`. The spec's Design 2.2 gives the new text.

5. **A real site's address in another item's spec.** TCW-76's spec named
   this project's Jira site in two places; both are now
   `https://example.atlassian.net`, nothing else changed. Three other files
   that hold the site's host name (TCW-9's and TCW-105's implement round 1,
   and `tests/work/jira/test_recorded_shapes.py`, whose `REAL_HOST` is kept
   by TCW-105's decision) were left unchanged.

## Checks

- Full suite, bare `.venv/bin/pytest` from the worktree root, at
  `a4fa56aa`: `1 failed, 8310 passed, 115 skipped in 1126.94s`, the one
  failure the migration guide's table row described in finding 2, fixed in
  the next commit. Run again after that fix: `2 failed, 8309 passed, 115
  skipped in 1773.43s`, both
  `tests/test_check_versions.py::test_a_hanging_cli_is_abandoned_silently`
  (`the check waited 5.9s on a hanging tcw`, limit 4s). That test times the
  session-start version check against a stub that never answers; it passed
  in the first run, nothing in this round touches that check, and it fails
  the same way on an unchanged clone run while the machine was under load
  (load average above 5), so it is a timing failure of the machine, not of
  this change; run alone straight afterwards, both passed (`2 passed`).
  Every other test passed.
- The release simulated on a clone: `scripts/cut_version.py 4.1.0`, the
  restamp script, `git add -u docs/work`, `git commit --amend --no-edit`,
  `git tag -f v4.1.0`; its suite gave `1 failed, 8303 passed, 116 skipped`,
  the failure the same guide-table one (the clone predates its fix): no test
  objects to the restamped files or to the version.
- `.venv/bin/tcw validate`: `0 errors, 0 warnings, 0 unresolved`.
- Each commit's added lines checked against the private-names list: no
  match.

## What the plan or spec got wrong

- The spec's Non-goals ruled out changing `tcw migrate`, which left the
  documents' "never" untrue for a migrated project; the conversion is now
  part of the item (Design 5).
- The spec called the release a patch release that S-9 allowed; a format
  change needs a minor release for TCW 4.0.0 to give its upgrade message.
