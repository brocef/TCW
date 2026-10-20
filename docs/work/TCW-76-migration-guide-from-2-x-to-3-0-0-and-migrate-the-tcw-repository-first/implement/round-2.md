# Implement round 2 (TCW-76, Task B22): review round 1's findings

Review round 1 (`review/round-1.md`) rejected round 1. This round fixes what
it accepted. Each finding was checked against the code or the files before
anything changed; the verdict on each, and the fix, are below. Only `docs/`,
`tests/`, `AGENTS.md` (and so `CLAUDE.md`, a link to it) and the migration
log changed. Nothing under `tcw/`, `skills/`, `agents/` or `web/` changed;
two mutations below edited `tcw/work/prompts/spec.md` for one test run each
and restored its bytes.

The lifecycle was driven with the 3.0 CLI (the private environment
`tcw76/venv`, installed from the epic worktree), since this round changes no
code under `tcw/`.

`guide` is `docs/migration-guide-2.8-to-3.0.0.md`, `log` is
`docs/tcw-3.0-migration-log.md`.

## The guide's reviewer

- **G1. Accepted.** `hook_env` (`tcw/work/advance.py`, 164-179) sets
  `TCW_REASON` only when `force` is true, and `discard()` (308-312) calls
  `advance` without `force`; the reason goes into the trace comment the move
  writes, and `tcw work show` prints comments (`tcw/work/cli.py`, `_show`).
  The `TCW_RESOLUTION` row now says the reason is in the comment the discard
  writes, that `TCW_REASON` is set only on a forced move, and that
  `tcw work discard` does not force.
- **G2. Accepted.** `_parse_stage` starts from `enabled = True`
  (`tcw/work/config.py`, 361), and a Jira-mode configuration needs a status
  for every enabled flow stage (406-414). Step 1's plan entry, step 3's
  rewrite, and a new Configuration row ("an optional stage the 2.x
  configuration does not name") now say an optional stage is on unless
  `work.stages.<stage>.enabled: false` turns it off, and that each flow stage
  left on needs a status in Jira mode (`postmortem` is a side stage and needs
  none). The new row's first cell names the stages without backquotes, so
  step 12's coverage test does not read them as 2.x names.
- **G3. Accepted.** v2.8.1's `_parse_tracker_statuses`
  (`git show v2.8.1:tcw/store/base.py`, 1733-1744) accepts `discarded` as a
  mapping of `wontfix`, `duplicate` and `superseded`; 3.0 refuses two stages
  on one status (`tcw/work/config.py`, 415-419). The statuses row now says the
  plan picks the one discarded status and what becomes of tickets at the
  others, that a shared status means a new Jira status made at step 2 and
  listed in the plan, and points step 1's plan entry at the row.
- **G4. Accepted.** v2.8.1's `_same_status` trims, collapses spaces and
  case-folds; 3.0 compares status names with `==` and dictionary lookups
  (`tcw/work/jira/backend.py`, 744, 954, 997, 1078; `tickets.py`, 164, 425).
  The statuses row says names are compared exactly, and step 3 says to spell
  each status as Jira does and correct the spelling before deciding Jira
  lacks a status.
- **G5. Accepted.** The old check, `grep -rnF -f`, matched substrings, and
  the rewrite had no order or chain rule. Step 9 now keeps pairs (old name, a
  tab, new name), follows each chain to its end, and requires a rewrite that
  matches whole names (no letter, digit, `_` or `-` on either side), works
  longest first, and is tried on a sample with a prefix case first. Its
  check builds one whole-name pattern per old name with `sed`, escaping the
  characters `grep -E` reads specially, and searches with `grep -rnE -f`.
  The builder was tried on a sample under macOS's `sed` and `/usr/bin/grep`:
  it found `2026-09-30-run-ci` in a path, left `2026-09-30-run-ci-extra`
  alone, and matched `old.name+x` but not `oldXname+x`. The test below runs
  it under the test machine's own `sed` and `grep`. This run's step 9 used
  the substring search, which finds everything the whole-name search does,
  and printed nothing, so its result stands.
- **G6. Accepted.** Checked on a scratch fixture: macOS's `/usr/bin/grep`
  (`grep (BSD grep, GNU compatible) 2.6.0-FreeBSD`) skips every link under
  both `-r` and `-R`, even one named on its command line, unless given `-S`;
  ugrep (the session's `grep`) and GNU grep follow only links named on the
  command line. There is no GNU grep on this machine, so its behavior is
  taken from its manual and stood in for by ugrep. Neither `-R` nor `-S` is
  common to both, so the guide does not change the search's flags: the list
  of places now follows the links itself. After amendment 7's loop, a second
  loop finds every link inside a listed folder (`find <place> -mindepth 1
  -type l`) and adds what it points to, unless a listed place already holds
  it; targets that are folders are searched for links in turn, and a link
  that points nowhere is skipped. On the fixture, the old snippet found 1
  line under both greps, and the new one 3 (the two linked files added), the
  same under both. The log's sentence now says amendment 7 covered only
  places that are links, and that links inside folders were still skipped.
- **G7. Accepted.** The private files are now
  `~/.tcw-3.0-migration-$ID-expected-names.txt` and
  `~/.tcw-3.0-migration-$ID-check.txt`, with `ID` the project's `id`. The
  real file was renamed to `~/.tcw-3.0-migration-tcw-expected-names.txt`,
  since the new name requires it (TCW's `id` is `tcw`), and the log's step 12
  section names it, saying it was renamed. The saved check output of the
  re-check below was deleted afterwards.
- **G8. Accepted, untested against Jira.** "Talking to Jira" now says the
  same rule holds for an existing ticket that step 6 would give a parent:
  Jira accepts a parent only one level up, so any other pair is listed in
  the plan rather than attempted. This run created or re-parented no ticket
  across levels, so nothing in it changes.
- **G9. Accepted.** `FsCapabilitiesStore.reset` refuses with
  `Refused` (exit code 3) when `_nested_entries` finds anything under the
  override (`tcw/store/fs.py`, 2562-2570;
  `tests/test_capabilities_cli_contract.py`, 162-165, asserts code 3); v2.8.1
  removed the folder (`git show v2.8.1:tcw/store/fs.py`, 3410-3425). The
  command has its own Commands row, "unchanged in shape; it now refuses …",
  and a "Behavior that changed" entry; the test's list names it.
- **G10. Accepted.** Tests below.
- **G11a. Accepted.** A filesystem comment's file holds the text and nothing
  else (`tcw/work/fs_backend.py`, `_write_comment`), named by the time, so a
  rerun writes a second file. Step 5 now says to look first, with a command
  that counts the comment files already beginning with the first line, tried
  on a scratch folder (`1` for an item with it, `0` for one without).
- **G11b. Accepted.** Step 9's pairs now include the inbox entries step 8
  converted. In this run, neither entry's name appears in any file but the
  log (searched with `/usr/bin/grep -rln` over the epic worktree), so the gap
  changed nothing here.
- **G11c. Accepted.** Step 12's check now says a second run records the step
  under `### Agent instructions` below its `## Run <N>` heading, as step 1
  does, and the `awk` reads only the `expected-names` blocks after the line
  `$RUN`. A redundant condition was dropped from the `awk` when its mutation
  survived (see Mutations).
- **G11d. Accepted.** Step 9 now says the log's lists of old and new names
  resolve an old name left in Jira, and git history does where the project
  committed each step (rule 5).
- **G11e. Accepted.** Step 3's scratch folder copies `tcw-config.local.yaml`
  when it exists, and its `grep` reads it too. Rule 7 now says any check's
  line from a file git does not track reaches the log only as a path and line
  number (steps 3, 10 and 12), and step 10's check says so for
  `tcw-config.local.yaml`.
- **G11f. Accepted, narrowed.** The reviewer suggested writing `~`. A line
  from a file outside the repository never reaches the committed block
  (rule 7), so only a target inside the project matters: the list of places
  now adds such a target by its path from the project's root, and anything
  else keeps its absolute path, which only the private file holds.

## The combined reviewer

- **C1. Accepted.** The guide's line 38 and the release note now add "and,
  in Jira mode, `jq`" (the release note says "for a Jira project"); the
  "Before you start" list already required `jq` 1.6.
- **C2. Accepted.** In `tcw-config.yaml`, `inbox` binds only a status; every
  stage from `request` on (postmortem included) binds the pull text, and
  every stage after `inbox` but the side stage binds the commit hook.
  `AGENTS.md` now says "from `request` on"; the changelog says the pull
  prompt is on every stage from `request` on and the hook on every move to a
  stage after `inbox`. The configuration is unchanged.
- **C3. Accepted.** `AGENTS.md` now says "Claude Code, Codex and Pi".
- **C4. Accepted.** The log's summary gains amendment 7 and, under a note
  that they came from this review, amendments 8 to 13, one per group of
  corrections above.
- **C5. Accepted, with one correction to the brief.** Pi's own documentation
  (`@earendil-works/pi-coding-agent/docs/configuration.md` under this
  machine's Node installation) lists `<agent-dir>/AGENTS.md` (or
  `AGENTS.override.md`, `CLAUDE.md`), `SYSTEM.md`, `APPEND_SYSTEM.md`,
  `skills/` and `prompts/`, and the project's `.pi/` equivalents; the
  `settings.json` keys `skills`, `prompts` and `packages` add more, with
  paths relative to `~/.pi/agent`, npm packages under
  `~/.pi/agent/npm/node_modules/`, and git ones under `~/.pi/agent/git/`.
  Step 12 names them and the snippet searches the fixed ones; a package's
  folders are added by hand, as linked files are. The brief said
  `~/.pi/agent/settings.json` lists only the TCW checkout; it lists three
  packages: the TCW checkout, `npm:@juicesharp/rpiv-ask-user-question` (an
  extension only, nothing to search) and `npm:pi-subagents` (skills and
  prompts, searched). The log's step 12 section records, with paths only,
  that the Pi places were searched and hold no 2.x instruction.
- **C6. Accepted.** `docs/lifecycle/harness.md` now says a skill may instruct
  delegation directly as long as it also says what a session that cannot
  delegate does, pointing at the Pi paragraph and the rule "a subagent is
  permitted, never required", which `skills/work/SKILL.md` (77-78) states.

## The tests' reviewer

- **T1. Accepted.** `tests/test_repo_lifecycle.py` now reads the section
  names from the "with … sections:" sentence of
  `tcw/work/prompts/spec.md`'s "**Produce**" list, inside the test, so a
  change to the prompt reaches it. It does not pin the count at seven, which
  would defeat reading it. The test is renamed
  `test_a_template_carries_every_spec_section`; the log's B17 and B20
  records keep the old name, as they record what ran then.

## The board's reviewer

- **B-B. Accepted.** `docs/lifecycle/review.md` now says the item's qa
  findings (on this project a comment on its ticket, since qa is kept in
  Jira) say that the closing waits, as `AGENTS.md` does.
- **B-C. Accepted.** The step 6 record never claimed the search; the
  evidence line for criterion 31 did. It now says the rerun was checked by
  the call log, and that the search cannot be run now because later steps
  and Task B21 wrote to the same tickets.
- **B-D. Accepted.** `git cat-file -t tcw-2.x-final` prints `commit` (a
  lightweight tag), it names `8b5a212b`, its ref file in the primary
  checkout dates from 2026-10-16, and `git ls-remote --tags origin
  tcw-2.x-final` prints nothing. The log records it under "Run 1, after the
  approved plan".
- **B-E. Accepted.** `implement/round-1.md`'s title and opening now say it is
  the first implement round, which the plan meant to be the log as well, and
  that the log is elsewhere.
- **B-F. Accepted.** `_items` (`tcw/work/jira/backend.py`, 373-375) lists as
  untracked only the parent key and blocker keys with no item. The log now
  says TCW-68's children are listed nowhere, and marks the correction.
- **B-G. Accepted.** The account ID is gone from the log; it was the only
  file in the repository holding it.

## Step 12 re-checked on this machine

The amended snippet was run from the epic worktree with the run's bound files
and `pi-subagents`' two folders added by hand: 24 places. The one link
inside a listed folder, `~/.claude/skills/pi`, points into
`~/.agents/skills`, so nothing more was added. The first `diff` printed the 7
lines of `pi-subagents` that match `NAMES`, all in files that never name
`tcw`; after reading them, and each of the 14 files the broad search prints,
they were added to the private file. The second `diff` printed nothing; the
search printed 77 lines, the same under `/usr/bin/grep` and ugrep. Recorded
in the log.

## Tests

New or changed in `tests/test_migration_guide.py`:

- `test_no_check_before_step_8_needs_the_inbox_gone` now also requires every
  loop over `docs/work/*/` in steps 4 to 7 to step over the inbox, and step 6's
  listing to except it; `test_the_checks_of_steps_4_and_6_step_over_the_inbox`
  names both exceptions.
- `test_steps_9_and_10_check_only_their_scope` now requires step 10's
  variable search to be exactly the non-recursive `grep -nE` over
  `<hook files>`.
- `test_each_stricter_behavior_is_named` gains `tcw capabilities reset`;
  `test_capabilities_reset_is_not_listed_as_unchanged`.
- Amendments 4 to 6: `test_step_3_copies_every_bound_file_and_composes_every_prompt`
  (also G11e's local configuration), `test_step_9_leaves_text_already_in_jira_as_written`
  (also G11d), `test_step_12_reads_files_someone_else_installed_where_they_match`.
- G5 and G11b: `test_step_9_rewrites_whole_names_longest_first_to_the_end_of_each_chain`,
  and `test_step_9s_patterns_find_a_whole_old_name_and_not_a_longer_one`,
  which runs the check's own pattern builder on a sample.
- Amendment 7, G6 and G11f: `test_step_12s_places_follow_links_and_keep_the_project_relative`
  runs the guide's own list-of-places snippet with `bash` in a scratch
  repository and home folder holding a `CLAUDE.md` link, links inside
  `.claude/skills/` to a file in the project, to the listed `AGENTS.md`, to
  nothing, and to a folder outside.
- G7: `test_step_12s_private_files_carry_the_projects_id`. G11c:
  `test_step_12s_check_reads_only_this_runs_expected_names` runs the check's
  own `awk` on a two-run log. G11a: `test_step_5_skips_a_filesystem_comment_already_written`.
  G1: `test_a_discards_reason_is_in_its_comment_not_in_tcw_reason`. G2:
  `test_optional_stages_are_on_unless_turned_off`. C5: Pi's five places
  added to `PLACES`, so `test_step_12_names_each_place` covers them.

`tests/test_repo_lifecycle.py`: T1 above.

Runs, with bare `pytest -p no:cacheprovider` from the epic worktree and the
private environment first on `PATH` (`import tcw` resolves to the epic
worktree):

- the guide's and the lifecycle tests, the three cross-scan files, every
  test file that names a changed file or reads under `docs/` (a broad
  `grep -rlE` over `tests/test_*.py`), and the standing guards
  (`test_cli_contract`, `test_cli_help_standard`, `test_static_guards`,
  `test_cli_handler`, `test_tree_store_raises`, `test_no_node`,
  `test_ledger_3_0`, `tests/work/test_model_guards`): 92 files in sorted
  order, **3312 passed, 78 skipped**;
- after this round was written, the document scans again
  (`test_docs_describe_3_0`, `test_documented_cli_surface`,
  `test_migration_guide`, `test_repo_lifecycle`, `test_shipped_text`,
  `test_upcoming_entries`, `test_validate`, `tests/work/test_validate_work`):
  1066 passed, 11 skipped;
- `pytest --collect-only -q`: 5275 tests, no errors (5255 at Task B20, and
  the 20 added here);
- `tcw validate`: `0 errors, 0 warnings, 0 unresolved`, exit 0; the `spec`,
  `implement` and `review` prompts compose (exit 0) and carry the new
  `harness.md` and `review.md` text.

The full suite was not run (the epic's rule: targeted tests per child, the
full suite near the epic's end).

## Mutations

Each applied alone, the named tests run with bare `pytest`, and the file's
bytes restored afterwards. All went red except M11's first form:

| Mutation | Red |
| --- | --- |
| M1 step 4's check loses `[ "$d" = docs/work/inbox/ ] \|\|` | `…inbox_gone[4]`, `…steps_4_and_6_step_over_the_inbox` |
| M2 step 6's check loses `[ "$n" = inbox ] && continue` | `…inbox_gone[6]`, `…steps_4_and_6_step_over_the_inbox` |
| M3 step 10's search over `.` instead of `<hook files>` | `test_steps_9_and_10_check_only_their_scope` |
| M3b step 10's search made `grep -rnE` | the same |
| M4 the reset row says `unchanged` | `test_capabilities_reset_is_not_listed_as_unchanged` |
| M4b the reset behavior entry removed | `test_each_stricter_behavior_is_named[…reset…]` |
| M5 step 3's procedure loop removed | `test_step_3_copies_every_bound_file_and_composes_every_prompt` |
| M5b step 3 copies no templates | the same |
| M5c step 3 does not copy `tcw-config.local.yaml` | the same |
| M6 amendment 5's sentence removed | `test_step_9_leaves_text_already_in_jira_as_written` |
| M6b "the step 6 commit" put back | the same |
| M7 "that someone else installed" removed | `test_step_12_reads_files_someone_else_installed_where_they_match` |
| M8 the pattern loses its boundaries | `test_step_9s_patterns_find_a_whole_old_name_and_not_a_longer_one` |
| M8b the pattern stops escaping | the same |
| M8c the chain rule removed | `test_step_9_rewrites_whole_names_longest_first_to_the_end_of_each_chain` |
| M8d the inbox entries left out of step 9 | the same |
| M9 the loop over links inside folders reads nothing | `test_step_12s_places_follow_links_and_keep_the_project_relative` |
| M9b targets added by absolute path | the same |
| M9c a place that is a link is kept | the same |
| M9d `held` always says no | the same |
| M10 the private file's name without `$ID` | `test_step_12s_private_files_carry_the_projects_id` |
| M11 first form: the `awk`'s last `r&&` removed | survived: that condition was redundant, since `f` is set only after the run's heading. Dropped from the guide |
| M11 the `awk` sets `f` before the run's heading | `test_step_12s_check_reads_only_this_runs_expected_names` |
| M12 "look before writing" removed | `test_step_5_skips_a_filesystem_comment_already_written` |
| M13 the `TCW_REASON` claim put back | `test_a_discards_reason_is_in_its_comment_not_in_tcw_reason` |
| M14 step 3 loses `enabled: false` | `test_optional_stages_are_on_unless_turned_off` |
| M15 Pi's project places removed from the snippet | `test_step_12_names_each_place[.pi/skills/]`, `[.pi/prompts/]` |
| M16 `## Risks` renamed in `docs/lifecycle/templates/spec.md` | `test_a_template_carries_every_spec_section[…spec.md]` |
| M16b `tcw/work/prompts/spec.md` asks for an eighth section | both templates' cases |
| M16c the prompt's "with seven sections:" reworded | both templates' cases |
