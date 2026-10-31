# Implement round 1 — TCW-117

Built on the branch `impl-117`, from `029455f8` on `v4`, in the worktree
`.claude/worktrees/impl-117`, with its own virtual environment
(`.venv/bin/pytest`). Hand runs of the 4.0 `tcw` went only through the
session's wrapper, which unsets every `TCW_*` variable and gives each run its
own home, configuration and cache folders, against scratch projects; never
against this repository, and never against Jira. The released 3.0.2 `tcw` was
run only inside scratch folders, to make 3.x projects for the migration
guide's examples, and once on a copy of this repository (Step 27). No
lifecycle command was run, no `git pull`, and no ticket was moved or written:
the dispatching session makes every move. This is the first implement round;
it gives no verdict.

TCW-116 (`tcw migrate`) was still in review while this round ran. Every
passage that describes `tcw migrate` describes the code at `029455f8`, and is
listed under [Passages that describe tcw migrate](#passages-that-describe-tcw-migrate),
so a later change to it can be followed.

## Commits

| Commit     | Steps                                                                                                                              |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `749d4b55` | 0b: prettier over the 26 documents this item rewrites                                                                              |
| `7a28e17c` | 1 to 4: `THREE_X_PATTERNS` and `scan`'s `flags`, the scan's tests, the migration guide's test, the guide, the README index line    |
| `a8c88208` | fix to 0b: the `--origin` listing in `skills/configure/references/personal.md` restored as tcw prints it, marked `prettier-ignore` |
| `1b59bebf` | fix to 0b: the blank line prettier put after each skill's front matter removed (six skills)                                        |
| `a7290540` | 6 to 17: the README, the eight guides, the use cases, `AGENTS.md`, the lifecycle documents, the TCW-99 design's amendments         |
| `a10e1226` | fix to 1: the 3.x fixture guard names the new scan test's `overrides:` sample                                                      |
| `eadf8e37` | 26: the evals                                                                                                                      |
| `49c921a5` | 19: the `work` skill                                                                                                               |
| `6ea6e437` | 20, 21: the `taxonomy` and `capabilities` skills                                                                                   |
| `fd563698` | 22: the `configure` skill, `KEY_PATHS`, the one `GIT_ALLOWED` phrase                                                               |
| `a0ab58d7` | 23 to 25: the `setup` skill, `skills/README.md`, the agents, the procedures, the remaining live documents                          |
| `b35e3a37` | 27: the ledger's prose, and `capabilities.yaml`                                                                                    |
| `7a5e4607` | 28: the live-document scan                                                                                                         |
| `bc5f848d` | 29: the changelog and release-note entries                                                                                         |
| `d4726761` | follow-up folded in: the test docstrings that named `--local`                                                                      |
| `7e031269` | a note from TCW-113 answered: each command's words for what an unavailable project leaves out, in the command-line guide           |
| `98487393` | 3, a correction: the way past a provisioning refusal needs a `repository` in the entry, as the Related projects guide says         |

Steps were combined where one commit could not be split without leaving a red
commit: Part 1 ships the guide with the test that reads it; Part 2's
documents link each other's new headings, so they land together. Each skill
has its own commit; Steps 23 to 25 share one, because they are the same kind
of small text change across many files.

## What was done

- **The migration guide**, `docs/migration-guide-3.X-to-4.0.0.md`, in spec
  2.2's eight sections: before you start (the 2.8 guide linked, both
  `tcw-cli` and the plugin upgraded together, CI held below 4); one project
  (the dry run, every line form, the three lists, the exit table, Jira and
  `--no-jira`, the order for a Jira project, a stopped run, the second person
  and old branches); related projects (parents first, the A8 line, a planning
  workspace's stores, B5, what each 3.x link becomes); the mapping tables;
  the epic-parts table, rows a to f; personal settings and the override
  variables; where provisioning may place a clone; scripts, hooks and agent
  instructions. Every quoted line was copied from a scratch run or from the
  source with the test that proves it (below).
- **Part 2**: every guide under `docs/guide/` rewritten for 4.0, the
  multi-repo guide rewritten whole as "Related projects"; the README's
  overview, command table, axis tables, cloud section and index;
  `docs/use-cases.md`; `AGENTS.md` and the lifecycle documents' comment
  lines; `docs/lifecycle/implementation.md`'s layout and its walk-functions
  bullet, which named a function that no longer exists
  (`descendant_projects`) and a gitignore prune 4.0 does not do; the seven
  amendments to the TCW-99 design, each with its dated line.
- **Part 3**: the five skills and their references, `skills/README.md`, the
  reviewer agent, the `search` and `pause-work` procedures,
  `docs/procedures/create-work.md`, `tests/migrate/data/README.md` (words
  only), the evals, the ledger's prose, the live scan, the upcoming entries.

## Checked on v4

Each line: the scratch run (exit code, the line quoted) or the source and the
test that proves it.

- A 3.x project under 4.0: `tcw work list` exits 1, "<folder> is a TCW 3.x
  project (tcw-config.yaml at its root, no .tcw/ folder); run 'tcw migrate'
  in it to move it to TCW 4".
- `tcw migrate --dry-run` on a 3.x project: exit 0; the change lines, the
  `needs attention:` list (A4, A5), the `reads differently in TCW 4:` list
  (D5), "would change: 6 files written, 0 moved, 4 deleted; 0 tickets
  edited" and "tcw validate's findings on the converted project are known
  only after a real run". A B8 blocker: exit 3, `refused:`, the line ending
  "rename the folder by hand, then run 'tcw migrate' again". The real run:
  exit 0, "changed: …"; again: "nothing to migrate", exit 0.
- After the run, `tcw validate` exits 1 on the user-wide file's `not_tags`
  (A5 leaves it); after it is changed to `not-tags`, "0 errors, 0 warnings,
  0 unresolved".
- `.tcw/tcw-migration.yaml` holds `tcw-version` and `capability-ids`;
  `.tcw/.gitignore` lists the progress record and both personal files.
- A stopped run (a capability folder made read-only): exit 1, "stopped: …",
  "not done:", "run 'tcw migrate' again to finish" and "do not save these
  files in version control until 'tcw migrate' finishes"; the progress
  record is present and ignored by git; the re-run finishes, exit 0, and the
  record is gone.
- A 4.0 package below a 3.x root: every command, own-scope listings
  included, exits 1 naming the root (also
  `tests/migrate/test_migrate_monorepo.py::test_a_package_migrated_before_its_root`).
  A8 reads "'mono' is still a TCW 3.x project; migrate it with 'tcw -C
  <folder> migrate'"; `tcw -C ../.. migrate` worked.
- `--no-jira` on a Jira package: the two summary lines quoted in the guide.
- From the source, each with its test: `NOTHING_WRITTEN` and `NOTHING_MORE`
  (`tcw/migrate/cli.py:46-49`;
  `test_a_failure_while_planning_writes_nothing`,
  `test_the_rerun_writes_nothing_more_when_jira_fails`); the cross-device
  message (`tcw/migrate/execute.py:56`;
  `test_a_move_across_filesystems_is_refused_and_finished_by_hand`); B17
  (`test_a_file_changed_after_a_stop_is_b17`); B10
  (`test_a_capabilities_entry_with_no_ledger_is_b10`); A12
  (`test_a12_lists_what_tcw_validate_finds_and_no_report_predicts`); a
  configuration problem does not refuse a run
  (`test_a_configuration_problem_does_not_refuse_it`); a parent's Jira
  settings change nothing
  (`test_a_parent_s_jira_fields_change_nothing_the_run_asks_jira`);
  `--no-jira` builds no client (`test_no_jira_builds_no_client_or_backend`);
  B5's `git clone` line (`tcw/migrate/family.py:78`); "left in another
  repository:" (`tcw/migrate/stores.py:253`).
- The four removed commands each exit 2 with "`tcw init` is now `tcw project
new`" and the three like it; the mistyped `new` and `list` suggestions.
- The override variables, by `tcw project config --origin`:
  `TCW_USER_NAME__MY_PROJ` and `TCW_WORK_JIRA_CREDENTIALS_TOKEN_ENV__APP`
  are applied and labelled; `TCW_WORK_JIRA_SITE__APP` is refused as a shared
  key. These are the examples of design amendments 8.6 and 8.7.
- `tcw work list --json`: `"schema": 2`, `full-id`, `owner`.
  `capabilities show`: `full-id:`, `owner:`, `overrides:`, `Status:`; under
  `--scope down`, `overridden by:` and `status by project:`; the `--json`
  records carry `statuses` and `overridden-by`. A plain listing shows no mark
  and no summary (amendments 8.1 to 8.3).
- `tcw -C ../app work new "Part" --parent plan.work/… --nest` exits 0 and
  prints "not nested: … belongs to project 'plan', so the item's folder is
  made at the top of this project's work folder".
- Changing another project's item: exit 3, "<full id> belongs to project
  'lib'; run the command there: tcw -C <folder> …".
- A store in the enclosing planning workspace, written `../docs/core/work` or
  `tcw://workspace.path/docs/core/work`: both work
  (`docs/lifecycle/implementation.md`'s layout).
- `tcw project new --id my-project`, with and without components: exit 0,
  `.tcw/tcw-config.yaml` and the `docs/` folders (README's adoption example).
- The quoted messages added by Part 2 were matched against `tcw/` by a script
  that compares each code span of 40 characters or more with the source;
  every one it could not match whole was found by hand as a message built
  from parts (for example `tcw/ids.py:215`, `tcw/store/base.py:613`,
  `tcw/work/jira/backend.py:1297`).

## Decisions

Each decided by the implementing agent.

1. The guide's one link into the Related projects guide by anchor
   (`#where-a-clone-may-be-placed`) was written as a file-only link in Part
   1 and given its anchor in Part 2, once the heading existed, so no commit
   has a broken link.
2. The epic-parts table's row a and the work skill write the part's command
   without `--nest`, since `--nest` has no effect when the epic is in
   another project (above); the guide says so in one sentence.
3. The mapping tables' rows for `--project` and `--blocks` name the 3.x
   command in the form the test's names use
   (`tcw work new --project <id>`, as in …), and every placeholder after
   `-C` is one word (`<folder>`, `<b-folder>`), as `tcw -C` takes one token.
4. The table of removed command lines sits at the end of its section, not
   inside a list item: the command check does not read an indented table's
   first column as exempt.
5. The ledger records whose prose describes how a 3.x form is refused link
   the migration guide in the same paragraph, rather than losing the
   description; a removed flag is described in words (as "the 3.x option
   that …"), so the spec's grep stays empty.
6. The upcoming release note names the migration guide by its path rather
   than linking it: the entry is combined into `docs/release-notes/v4.0.0.md`
   at the cut, where a relative link from `upcoming/` would break.
7. The ledger records keep their own formatting: they were not in the
   formatting commit, and formatting them would put unrelated lines in the
   diff.

## Adaptations of the plan

Each decided by the implementing agent, with its reason.

- **Step 0b's formatting changed content in two ways the word diff did not
  show**: prettier formats YAML inside fenced blocks (re-indenting and
  collapsing the two spaces before a comment), and puts a blank line after
  front matter. The first broke a quoted `tcw project config --origin`
  listing in `personal.md` (tcw prints two-space indents and two spaces
  before `#`), which `tests/test_shipped_text.py` caught; the second broke
  `tests/test_check_versions.py` for six skills. Both were fixed in their
  own commits (`a8c88208`, `1b59bebf`); the other fenced blocks prettier
  changed (ledger examples, the TCW-99 design's sketch, one JSON object) keep
  their meaning and were left. CI does not run prettier, so a `SKILL.md`
  stays without that blank line; every Part 3 helper was told to remove it
  after formatting.
- **`docs/lifecycle/implementation.md:41-44`**: the plan asked for the walk
  functions as they are on `v4`; `descendant_projects` and the gitignore
  prune no longer exist, so the bullet now names `find_project_root` and
  `_search` (`tcw/store/project.py`) and keeps the rule for any future walk.
- **Step 27's `tcw validate`** was run with the 3.0.2 `tcw` on a copy of the
  worktree in the scratchpad, not on the worktree itself: the brief allows
  the released `tcw` only inside scratch folders. It printed "0 errors, 0
  warnings, 0 unresolved".
- **`tests/test_no_3x_inheritance.py`** gained one allowance: the new scan's
  test writes `overrides: core/billing` as the sample P12 must catch.
- **The live-scan test** is parametrized over `DOC_FILES`, whose entries are
  absolute paths, so it passes each path relative to the repository's root.

## Mutation checks

- `tests/test_docs_describe_4_0.py`: red on import before `THREE_X_PATTERNS`
  existed; P7's and P12's patterns broken in turn, each red for its sample;
  the live scan red for one `item.yaml` added to `docs/guide/work.md`, and
  red in 48 ledger files with the `UNMIGRATED_RECORDS` exclusion removed.
- `tests/test_migration_guide_4_0.py` (each red for the reason named): a
  section heading renamed (order, links); the `not_tags` row removed (its
  name and P10's row); a hidden flag in a second column (the command check);
  a broken link to the 2.8 guide (links, and the 2.8 test); epic row f
  relabelled; exit row 5 relabelled; a second cell emptied; the pointer to
  related projects removed from the first paragraph; the blank-cell
  exemption turned off (the command check fails on the 3.x first cells);
  the help-surface check removed (all three hidden-flag tests fail, so only
  the surface refuses them).
- `test_the_documentation_index_links_the_guides_it_must`: red before the
  README line.
- The anchor checker used over every live document: red for one broken
  anchor in the README.
- The two Step 22 test changes, checked here after the helper that wrote
  them first gave no report: the phrase `` `<url>#<branch>` `` taken out of
  `projects.md` makes `test_every_git_allowance_is_still_needed` red; the
  allowance taken out makes `test_no_shipped_text_names_git[…projects.md]`
  red; a `projects.*` key put back in `KEY_PATHS` makes the count, the
  heading and the table tests red; the `parents` heading renamed makes its
  heading test red. The helper's own red-before-green run is not on record.

## Suite

The full suite as CI runs it, bare `.venv/bin/pytest -q -p no:cacheprovider`,
every `TCW_*` variable unset, in a scratch clone checked out at each commit:

- at `749d4b55` (0b): `2246 passed, 2 skipped`; and `9 failed, 5152 passed,
111 skipped` with `tests/migrate` apart (`314 passed`). The failures: the
  wheel test (the `node_modules` link), and the eight that 0b's formatting
  caused, fixed by `a8c88208` and `1b59bebf`.
- at `a7290540` (Part 2): `2246 passed, 2 skipped`; `2 failed, 5606 passed,
111 skipped`: the wheel test, and `test_no_fixture_sets_up_3x_inheritance`,
  fixed by `a10e1226`.
- at `d4726761` (Part 3): `2246 passed, 2 skipped`; `1 failed, 5832 passed,
111 skipped`, the one failure the wheel test.

`tests/test_shipped_prompts.py::test_the_wheel_carries_exactly_the_prompts_and_procedures`
fails in this worktree only, because `node_modules` is a link here; it was
not fixed. After `7e031269` and `98487393` the document tests (`test_documented_cli_surface`,
`test_cli_guide`, both document scans) pass: `932 passed`.

Other checks: the spec's 9.3 grep prints nothing; the 3.x scan over every live
document prints nothing outside the ledgers, and over the ledgers only P8
hits; every `tcw -C` in a live document has a one-word target; every anchor
in a live document resolves; the 43 fenced YAML blocks in the changed
documents parse, but one that is front matter, and none holds `upstream:`,
`extends:`, `not_tags`, a `cap-` pointer or a 3.x `projects:` block;
`python -m evals.run_evals --axis a|b --dry-run` print every arm and an
"agent's tcw:" line naming this worktree, spending nothing;
`~/.config/tcw/config.yaml` is still absent and `~/.cache/tcw/stores` still
empty, as before the round.

## Documentation sync

Every entry of `work.documentation` fires for this item, and each is
answered: the README; `docs/guide/jira.md` and every other guide; the
upcoming release note and changelog, named by the item's folder; every
`skills/<component>/SKILL.md`; every `skills/configure/references/` document
whose keys 4.0 changed; `docs/use-cases.md`.

## Earlier children's notes, and how each was answered

- **TCW-106** (`.tcw/`, `tcw-version`): every live document names
  `.tcw/tcw-config.yaml`, `.tcw/tcw-config.local.yaml` and `not-tags`; a 3.x
  project's refusal names `tcw migrate` (guides, skills, `AGENTS.md`, the
  lifecycle documents).
- **TCW-107** (manifests, finding a folder): the Related projects guide, the
  configure skill's `projects.md`, and the use cases UC-1, UC-3, UC-6, UC-8
  and S-5.
- **TCW-108** (parent links): parents, children and `inherit` in the Related
  projects guide, the README and `projects.md`; the work skill's exit-code
  passage.
- **TCW-109** (inherited configuration, personal settings, variables): the
  configuration guide and `personal.md`; design amendments 8.5 to 8.7.
- **TCW-110** (full identifiers, addresses): the linking guide, the command
  line guide, every skill; the six deferred entries.
- **TCW-111** (object folders, state files): the work guide's folder rules
  and `resources/`; the linking guide's findings.
- **TCW-112** (inheritance and overrides by path): the taxonomy and
  capabilities guide and skills; amendment 8.1.
- **TCW-113** (`--scope`, `--project`): the command-line guide (with the
  three endings of the `--project` refusal, and each command's words for what
  it left out, `7e031269`), the web viewer guide (pickers, the scope control,
  another project's read-only page), the Jira guide (one search needs the
  same email and token, and a write makes the next search ask again), the
  work skill's backlog audit (by full identifier and `tcw -C`, already in
  the `audit-backlog` procedure), the capabilities skill (`--project` with no
  `statuses` and no `overridden-by`); amendments 8.2 and 8.3.
- **TCW-114** (owning project, move and rename): the work skill's
  description and delegation passage, the epic-parts table, the work guide's
  move and rename.
- **TCW-115** (`tcw project`): every passage its Step 3 renamed now says what
  4.0 does: the README's command table has `tcw project path` and `tcw
project info`; the provisioning bound is in the Related projects guide in
  full and in the work, configure and setup skills in one sentence; UC-6's
  gap closed.
- **TCW-116** (`tcw migrate`): the line forms, `--no-jira`, the stopped run,
  the re-run without Jira, a package below a 3.x root, and the second person,
  in the migration guide; see the departures below for what the code does
  differently from the note.

## Follow-ups folded in, and left

Folded in: the `list --local` docstrings in `tests/test_tree_parent_missing.py`
and `tests/test_overrides_by_path.py`; `skills/work/SKILL.md`'s "filing"
description and its `projects:` delegation passage; Design 2.2's three
endings, in the command-line guide (TCW-113's spec itself is archival and
was not edited); `tcw config show`, now `tcw project config` everywhere; the
`projects:` passages in `projects.md` and the guides.

Left, as code changes or outside this item: every other line of the
follow-up list, which needs a change to code behaviour; among them, from this
round's own runs, that `tcw migrate` lists `write .tcw/.gitignore` twice,
and that a stopped run does not name its progress record by path.

## Departures found (code versus a spec)

1. A stopped `tcw migrate` does not name the progress record by its path;
   only B17's fix does. The guide says what the code prints, and names the
   file itself.
2. Spec 2.5 (b) expected exit 7 in a 4.0 package below a 3.x parent; every
   command exits 1 naming the parent, as TCW-116's test shows. The guide
   says exit 1.
3. `--nest` has no effect across projects (above); spec 5.1 (a)'s command is
   written without it.
4. `tcw migrate` prints `.tcw/.gitignore: C1` twice in a run (reported to
   TCW-116's review 2).

## Passages that describe tcw migrate

As written against the code at `029455f8`, for a later change to TCW-116 to
be followed: `docs/migration-guide-3.X-to-4.0.0.md` (all of it);
`docs/guide/linking-and-validation.md`, `jira.md`, `configuration.md`,
`cli.md`, `multi-repo.md` ("Moving from 3.x") and
`taxonomy-and-capabilities.md`; `docs/use-cases.md` (S-9 and five other
passages); `README.md`'s command table; `skills/setup/SKILL.md`,
`skills/setup/references/project.md` and `install.md`; `skills/work/SKILL.md`
and `references/commands.md`; `skills/configure/references/work.md` and
`projects.md`; `skills/README.md`; and the ledger records naming it (`git grep
-c 'tcw migrate'` lists each with its count).

## Handoffs for TCW-118

- Delete `UNMIGRATED_RECORDS` in `tests/test_docs_describe_4_0.py` once the
  repository is migrated; the live scan then reads the ledgers too, and
  their 3.x `tcw://C/…` links (P8) are what `tcw migrate` converts.
- `AGENTS.md` and the lifecycle documents already name
  `.tcw/tcw-config.yaml`; they are true only after the migration.
- `tests/migrate/data/README.md` describes the 3.x copy of this repository's
  configuration; its data was not touched.

## Not done

- The four Part 3 helpers and the eight Part 2 helpers each ended without
  delivering their report. Their files were checked here instead, by the
  scan, the grep, the document tests, the quoted-message check, the anchor
  check and spot reads; the per-claim "checked on v4" lines their reports
  would have given are not in this round.
- No paid eval run (spec 9.6 (c)). No cold read of the migration guide (qa).

## Added by the dispatching session

Rebased onto `v4` (TCW-116 completed after its review round 2, and TCW-118's
plan) with no conflict. TCW-116's round 2 added a report, A14, for an
absolute path a 3.x shared file held for everyone; the migration guide's
"Some of the reports need a word more" now says what it means and what every
other person must do, and its lead-in no longer says "Two". The document
tests (`test_docs_describe_4_0.py`, `test_migration_guide_4_0.py`,
`test_doc_vocabulary.py`, `test_documented_cli_surface.py`,
`test_cli_guide.py`) give `915 passed`. The full suite on the rebased branch
is recorded below once it has run.

The full suite as CI runs it, run by the dispatching session on the rebased
branch at `28e5f555` (2026-10-26) in two halves by folder, every `TCW_*`
variable unset: `2246 passed, 2 skipped` and `5839 passed, 111 skipped,
1 failed`; the failure is the worktree's `node_modules` link
(`test_the_wheel_carries_exactly_the_prompts_and_procedures`), which passes in
`v4`. `pnpm test` `247 passed`; `tsc --noEmit`, `pnpm lint`, `pnpm
check:build` clean.
