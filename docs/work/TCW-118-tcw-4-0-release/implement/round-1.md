# Implement round 1 — TCW 4.0: release

Steps 5, 7, 8 and 9 of the plan, carried out by an agent in a worktree of
`v4` at `34739ce5`. The dispatching session adds the other steps' records.

## Step 2 — the small follow-ups (Decided 1)

Made by four agents, each in its own worktree from `v4` at `af55f473` (the
fourth on `v4` itself, from `d4dab8a3`), then rebased onto `v4`; the hashes
below are `v4`'s. One commit per fix, test first. Before each commit
`grep -rnF '<old text>' docs skills README.md` was run (leaving out
`docs/work/`, `docs/changelogs/`, `docs/release-notes/`), and every line it
printed was changed in that commit or found still true. No `tcw` was run
against this repository or Jira; hand checks ran the worktree's `tcw` in
scratch projects.

| Fix | Commit | Test | Red line (short) | Outcome |
| --- | --- | --- | --- | --- |
| 1 (F:1) | `a3c8d46e` | `tests/test_ids.py::test_ac2_each_refusal_names_its_rule`, case `tcw://p1.foo/x` | `assert 'tcw://p1.foo/x is not' in "'p1.foo/x' is not a full identifier: …"` | the refusal quotes the whole address |
| 2 (F:2c) | `16568ae6` | `tests/test_store_addresses.py::test_a_location_with_an_uppercase_scheme_is_a_refused_address_not_a_folder`; `tests/test_run_in_folder.py::test_an_uppercase_scheme_is_a_refused_address_not_a_folder` | `work.path is not a directory: …/TCW:/app.path/other`; `cannot run in TCW://demo.path/: no such folder` | `has_scheme` at the eight places; parsers and Markdown link readers left case-sensitive, as the row says |
| 3 (F:3, F:18) | `082d4467` | `tests/test_legacy_store_config.py::test_a_moved_store_that_cannot_open_is_reported_once_instead` | `.tcw/tcw-config.yaml: taxonomy: /…/consumer/.tcw/tcw-config.yaml: 'taxonomy.extends' was removed …` | the config file named once |
| 4 (F:5) | `55bbdb73` | `tests/test_capabilities_federation.py`, two `test_set_refuses_a_parent_…` tests | `Failed: DID NOT RAISE TcwError` | `set --parent` refuses itself and a loop, exit 2, nothing written |
| 5 (F:6, F:55) | `1402faa0` | `tests/work/test_validate_work.py::test_an_inbox_folder_is_a_reserved_name`, new `test_a_2x_item_under_a_stage_folder_names_the_guide` | `+ 'inbox' is reserved in the work store` (no guide named) | the work store's reserved-name finding names the 2.8-to-3.0 guide; three tests pinning the old message updated |
| 6 (F:10) | `80f16c2d` | `tests/config/test_config_edges.py::test_a_scalar_over_an_inherit_list_leaves_no_places_behind` | `Left contains 2 more items, first extra item: ('work', 'tags', 0)` | the list places cleared |
| 7 (F:11) | `bd91f61a` | `tests/test_config_environment.py::test_ac23_only_the_variable_whose_prompt_is_used_is_named` | `'TCW_WORK_STAGES_SPEC__APP' != 'TCW_WORK_STAGES_SPEC_PROMPT__APP'` | the note names only the variable used |
| 8 (F:14) | `167d4f56` | `tests/test_taxonomy.py`, `tests/test_capabilities_rm.py`, `tests/test_override_references.py` (10 cases) | `… still referenced by billing/refund (Blocked by)` (no project) | referrers named by full identifier |
| 9 (F:15) | `51bf28bf` | `tests/test_capabilities_rm.py::test_remove_refuses_a_target_another_capability_names_as_its_parent` | `Failed: DID NOT RAISE TcwError` | `rm` refuses while another capability names it as `parent`; three lines listing the fields `rm` checks gained `parent` |
| 10 (F:16, F:44) | `2bd6ed82` | `test_cli_rm_removes_the_organising_folder_it_empties`, `test_cli_reset_removes_the_organising_folder_it_empties`, `test_rm_removes_the_organising_folder_it_empties` | `assert 'removed docs/capabilities/billing' in [… only the two files …]` | `rm` and `reset` remove and name the emptied folders; four "and nothing else" lines changed |
| 11 (F:23) | `2b3036c0` | `tests/test_tree_move.py::test_a_rename_onto_a_case_variant_names_the_folder_as_spelled` | `'tcw taxonomy rename: docs/taxonomy/PAY already exists'` | the folder named as spelled on disk |
| 12 (F:30) | `54a342ce` | `tests/test_project_provision.py::test_ac32_the_refusal_names_each_project_with_a_problem` | `assert 'bb: fetched into <tmp>/bb' in "… aa: fetched into <tmp>/aa, …"` | each fetched project with a problem named |
| 13 (F:33) | `4414fc49` | none (docstrings only) | none | five docstrings describe the own-scope list |
| 14 (F:45) | `72a3cac6` | `tests/work/test_drift_work.py::test_an_inherited_capability_never_ruled_on` | `'… still the upstream default; …' != '… still the one it inherits; …'` | the line and the guide line quoting it changed |
| 15 (F:48) | `1f97fc42` | none (help text; no test pins it) | none | `--origin`'s help says an inherited setting a parent cannot give stops it |
| 16 (F:51, F:74) | not committed | written, red then green, reverted | — | **stopped; moved to a new item** (below) |
| 17 | `4a9dbeb6` | `tests/migrate/test_migrate_manifests.py::test_a14_names_the_ancestor_s_file_an_entry_came_from` | none expected (test only); checked by breaking `tcw/migrate/config.py:666`: `assert 0 == 1` | the test holds |
| 18 | `c23a0353` | `tests/migrate/test_migrate_monorepo.py`, two tests | `+ taxonomy.extends: 'mono' is already inherited through parents` (last line; no stop line) | `check after the run stopped: …` added; **narrowed**: set only for a 3.x finding, since another graph problem is already an A12 |
| 19 | `aa106ea1` | `tests/migrate/test_migrate_extends.py::test_a8_in_a_workspace_lists_a_parent_before_its_child` | `'  A8 …/ws/sub/deep' != '  A8 …/ws/sub'` | parents first; **larger than the row**: links predicted on demand, and the blocker list restored after each prediction so ordering never refuses a run (about 30 lines) |
| 20 (F:59, F:77) | `2a3ef2ff` | `tests/migrate/test_migrate_command.py::test_a_count_of_one_is_singular` | `+ changed: 1 files written, 0 moved, 0 deleted; 1 tickets edited` | singular for 1; the guide's template says so |
| 21 | `c0e83c2a` | `tests/migrate/test_migrate_overrides.py::test_each_b9` | `would write docs/capabilities/ov/login/tcw-capability.yaml: C9, C12` | no C12 or D7 for a refused override; the test is `not data.get("overrides")`, as `tcw/migrate/overrides.py:83` uses |
| 22 (F:63) | `332564ee` | `tests/test_store_addresses.py::test_project_new_refuses_an_address_naming_itself_not_init` | `--work-path 'tcw://x.path/board': init takes a path …` | names `tcw project new` |
| 23 (F:64) | `9f299af4` | `tests/config/test_config_show.py::test_credential_names_from_a_variable_name_the_variable` | `(… only in a Jira-mode project, )` | names the variable |
| 24 (F:66) | `0666cc8e` | `tests/test_taxonomy.py`, two `test_cli_a_missing_store_…` tests | `run `tcw project new taxonomy --id <id>` in the project folder` (in a project with an ID) | `--id <id>` only where no project with an ID is found |
| F:67 | `0a373c84` | none (text); checked by running | none | the guide says a Jira dry run needs the credentials, or `--no-jira` |
| F:68 | `fd8c8e5c` | none (text); checked by running | none | the guide gives a finished Jira project's re-run lines and exit codes |
| F:69 | `1c93fd56` | none (text); checked by running | none | the guide says a move changes no `parent`, and how to set it |
| F:70 | `6de632aa` | none (text); message checked by running | none | the template reads `its parent is <full identifier, or not set>` |
| F:71, F:75 | `1301066f` | `tests/test_project_provision.py::test_ac34_a_project_alone`, `tests/test_manifest_cli.py`, `tests/test_store_provisioning.py` (three) | `'Nothing to provision: no component declares a home repository …' != 'no store to fetch: …'` | the new line |
| F:72 | `0236c1e8` | none (a plan line) | none | Step 39 checks the work skill's link resolves on GitHub's `main` |
| F:73 | `0978f549` | none pins the text | none | exit 1's meaning covers something TCW was told to read; no exit code changed; the code itself is a new item |

The plan (`a1cd7754`), `capabilities.yaml` (`8db0f873`, the three records
fixes 9 and 10 changed) and the entry files (`d34ca274`) followed. F:74 is
fix 16's defect, F:77 fix 20's, and F:76 and F:78 became new items; none was
dropped.

**Fix 16, stopped.** The row would make `tcw validate` report an
`_UncheckedProblem` as `unresolved` (exit 0) instead of an error. That
answer covers more than "the project is not on this machine": also an entry
naming a project, the item's own or another, that keeps no ledger, and a
ledger that cannot be read. Two guide lines say today's behaviour is meant
(`docs/guide/linking-and-validation.md:241-243`,
`docs/guide/taxonomy-and-capabilities.md:391-392`), and `tcw validate
--remote` has a third site with the same pattern (`tcw/work/jira/remote.py:576`).
Which cases are unresolved is a design choice, so it is a new item.

**After the suite.** The full suite run after the four groups found three
tests outside the modules each group ran, each pinning what a fix changed;
`34739ce5` updates them: `tests/test_ownership_sweep.py` lists fix 19's
`_parents_first` (it removes from a list it made itself, not a store),
`tests/test_taxonomy_rm_gaps.py` expects fix 8's full identifier, and
`tests/test_tree_store_files_only.py` expects fix 10's emptied folder.
Later, `11a47ddb` reworded `version_problem`'s docstring in
`tcw/project_files.py`, which cr1's fix 2 below had made name the 3.x state
files `meta.yaml` and `item.yaml`; the sweep of shipped text for 3.x forms
refuses those names, so it now says "its state files had other names".

## Step 3 — `cut_version.py` cuts a version the files already hold (Design 3.2)

Commit `6d7ce890`. Three tests first (an untagged current version cut by
name; a tagged one refused, `v4.0.0 is already tagged`; `patch`, `minor`,
`major` refused naming `cut_version.py 4.0.0`, with HEAD, tags and status
unchanged). Before the change:

```
5 failed, 17 passed in 3.36s
```

After:

```
22 passed in 3.49s
$ grep -n 'already hold\|no tag yet' docs/releasing.md
15:When the version files already hold the version to release, as on a major
19:current version has no tag yet, `patch`, `minor` and `major` are refused,
```

**What the plan got wrong.** The new paragraph moves the lines the spec cites
as `docs/releasing.md:29-31` (spec `:131`, `:999`) down by eight, to `:37-39`.
The spec is not edited.

## Step 4 — the plugin installs the CLI of its own version (Design 3.9)

Commit `d4dab8a3`. Tests first (`test_install_pins_the_plugin_version`,
`test_failed_pinned_install_names_the_version_and_retries`,
`test_no_version_line_installs_nothing`, and the unpinned assertions
changed to `==9.9.9`, `==2.4.0`). Before: `9 failed, 57 passed`. After:

```
66 passed in 14.27s    (bootstrap and check_versions)
88 passed in 19.23s    (with test_cut_version.py)
636 passed             (with test_shipped_text, test_docs_describe_4_0, test_plugin_manifests)
```

The three greps of "Proves it" (`pipx upgrade` in `check_versions.sh`;
`floats|newest release|pipx upgrade` in the four paths;
`"install --force tcw-cli"` in the bootstrap tests) print nothing.

**What the plan got wrong.** `OLDER_ADVICE = "pipx install --force tcw-cli=="`
cannot work: the tests check that the other direction's advice is absent, and
the newer-CLI message already says `pipx install --force tcw-cli==<skills>`.
It is `"match the CLI to the skills: pipx install --force tcw-cli=="`, the
older-CLI message's own words, with a comment saying why. Left alone:
`docs/migration-guide-3.X-to-4.0.0.md:37`'s `pipx upgrade tcw-cli` (a
person's own upgrade to 4.0, not the plugin's install).

## Step 5 — TCW-118's own entry files (Design 3.3)

Commit `073703dc` (`TCW-118: release notes and changelog entries`).
`docs/migration-guide-3.X-to-4.0.0.md` exists on `v4`, so the step ran.

- `grep -c '^## Upgrading' docs/release-notes/upcoming/TCW-118-tcw-4-0-release.md`
  prints `1`: the six points went under the heading Step 2 began, and Step 2's
  one point there ("holding the plugin at an older version now holds the CLI
  it installs at that version too") is folded into the fifth.
- The leading paragraph says 4.0 is a major release, that it changes where a
  project keeps its files (a `.tcw/` folder) and how projects relate (parents
  in place of `projects:` and `extends`), and that a 3.x project must be
  migrated with `tcw migrate`; that sentence names `tcw migrate`, so TCW-117's
  scan for 3.x forms would allow it even if it read the `upcoming/` entries.
  It also links the migration guide (see "What the plan got wrong" below).
- The six points against Design 3.3, criterion 7:
  1. the migration guide, linked as `../migration-guide-3.X-to-4.0.0.md`: present;
  2. automation that installs `tcw-cli` kept at `tcw-cli<4` until migrated: present;
  3. everyone upgrades together, 4.0 refusing a 3.x project's files except to
     migrate them: present;
  4. commit or back up before running `tcw migrate` for real: present;
  5. the plugin installs `tcw-cli==<the plugin's version>`; the harness
     paragraph of the plan's "The open items", item 1, copied word for word
     (Claude Code, Codex, Pi); then the first-install case with
     `pipx install --force 'tcw-cli<4'`: present;
  6. the branch `3.x` holds the last 3.x code, and a 3.x patch is cut there
     and published by pushing its tag: present.
- The changelog entry gains `## Removed` (`tests/test_repo_config_pair.py`
  and the root `.gitignore` line `/tcw-config.local.yaml`, both removed at
  Step 15) and, under `## Internal`, this repository migrated to 4.0 and
  `UNMIGRATED_RECORDS` deleted. `## Changed` already held the pinned install
  and `check_versions.sh`'s advice from Step 2, and the `cut_version.py` rules
  stay under `## Internal` (decided by the dispatching session: the script is
  contributor tooling).
- Every `upcoming/` file a `TCW-118:` commit has touched:

  ```
  073703dc docs/changelogs/upcoming/TCW-118-tcw-4-0-release.md
  073703dc docs/release-notes/upcoming/TCW-118-tcw-4-0-release.md
  ```

  (and `d34ca274`, Step 2, the same two files). No other item's entry file.

**What the plan got wrong.** A leading paragraph fails
`tests/test_upcoming_entries.py::test_an_entry_starts_at_a_level_two_heading`,
which allowed leading text only in TCW-75's 3.0.0 introduction. The same
commit changes that test so each major version's introduction is allowed:
TCW-75's for 3.0.0 and TCW-118's for 4.0.0, each checked, until its cut, to
exist in both folders, to link its migration guide from the introduction
itself, and to come first in the combined notes. To meet the last of those the
introduction links the guide as well as point 1. Checked by breaking it:
taking the link out of the introduction makes
`test_the_introduction_links_the_migration_guide[4.0.0]` fail.

## Step 6 — the combined review (Design 3.4)

### Round 1, at `d16c88ed`

Six `adversarial-code-reviewer` agents, one per slice of the plan, each
running `tcw` only in scratch folders. Each found HEAD and status unchanged
at its start and end (only the untracked `node_modules`). Every slice ended
`NOT DONE`. Each finding was checked against the code by the dispatching
session.

**Slice 1, the `.tcw/` folder and version stamps.** Every `tcw-*.yaml` a 4.0
writer made was in `.tcw/` or its object folder, stamped `tcw-version: 4.0.0`.

| # | Finding | Sort | Verdict | Fix |
| --- | --- | --- | --- | --- |
| 1 | an interrupted `tcw migrate` passes `tcw validate`, whose only warning says to delete the root `tcw-config.yaml` | belongs to 4.0 | accepted | `cfafa5b5` |
| 2 | a state file with no `tcw-version` is told to run `tcw migrate`, which converts nothing in it, so the advice loops | belongs to 4.0 | accepted | `b5d214bd` |
| 3 | the migration and progress records' stamps are never checked when read back | separate change | new item | — |
| 4 | a hand-quoted `"tcw-version"` key is rewritten unquoted, with the running version, on the next edit | separate change | new item | — |

**Slice 2, a project family together.** Diamonds, overrides in one branch,
`--scope down`, writes refused outside the owner, and Jira key lookup all
reproduced correct.

| # | Finding | Sort | Verdict | Fix |
| --- | --- | --- | --- | --- |
| 1 | a loop through a descendant's other parent is a warning with exit 0 from the ancestor (TCW-113's catch), against TCW-108 Design 4.7 "whichever project the loop is in" | belongs to 4.0 | **rejected** as a code change, under the user's delegation of TCW-99 design questions: covering a descendant whose own graph is broken is the case TCW-113 defines (left out with a warning naming the loop, while the project itself refuses), and validate checks only its own project (decided at F:65); 4.7 is read as every command run in a project whose own load order holds the loop. A spec wording note, no change | — |
| 2 | write commands trust that stores never share a folder, which only `tcw validate` enforces, so a child whose capabilities path is its parent's writes the parent's records | separate change | new item | — |

**Slice 3, identifiers and addresses.**

| # | Finding | Sort | Verdict | Fix |
| --- | --- | --- | --- | --- |
| 1 | `work move --into <KEY>` makes a new folder named like the key beside the item carrying it, and writes that path to the ticket | belongs to 4.0 | accepted | `c18d042b` |
| 2 | `--into` refuses a `tcw://` object address, which every other option naming an object takes | belongs to 4.0 | accepted | `64a8a8b6` |
| 3 | an upper-case `TCW://` in command input is told to rename a folder by hand | belongs to 4.0 | accepted | `c05b6ba8` |
| 4 | a Markdown link `](TCW://…)` is skipped by validate, by a move's rewrite and by the web app, as in 3.x | separate change | new item | — |
| 5 | a mistyped project or component part (`Demo.work/x`) is also told "rename it by hand" | separate change | new item | — |

**Slice 4, `tcw project` and `tcw migrate`.** Families migrated in both
orders, and a richer single project, all clean but one.

| # | Finding | Sort | Verdict | Fix |
| --- | --- | --- | --- | --- |
| 1 | an override with `Partial` and no `Gaps`, which 3.x never checked, is listed under A12, "a finding the project already had in 3.x" | belongs to 4.0 | **narrowed** to wording: A12's printed line makes no 3.x claim; the guide and `check_after`'s docstring did. No D report added | `42b397f2` |

**Slice 5, the release's own changes.** Bootstrap pinning, the version
warning, a simulated cut, and Step 2's fixes checked sound but two.

| # | Finding | Sort | Verdict | Fix |
| --- | --- | --- | --- | --- |
| 1 | the release note's stay-on-3.x step covers only a first install; 3.0.2's bootstrap installs the newest CLI whenever its saved record differs, so pinning back after 4.0 installs 4.0 again | belongs to 4.0 | accepted | `e9cf723e` |
| 2 | `capabilities set --parent` on an inherited capability accepts the capability itself, writing the original as its parent | belongs to 4.0 | accepted | `38fbb34c` |
| 3 | a folder `remove_emptied` removed can go unnamed when an unusual permission error stops it higher up | separate change | new item | — |

**Slice 6, the guides against the code.** About 65 quotations sampled,
almost all matching.

| # | Finding | Sort | Verdict | Fix |
| --- | --- | --- | --- | --- |
| 1 | the migration guide gives the wrong order of `tcw migrate`'s closing lines | belongs to 4.0 | accepted | `118ea30e` |
| 2 | the guide says every converted link is printed under `reads differently in TCW 4:`, but an `extends` already inherited through a parent is dropped with one uncoded line | belongs to 4.0 | accepted | `2f8ea7c0` |
| 3 | `docs/guide/work.md` gives `tcw work rename <item> <words>`; the command takes a lower-case hyphenated name (older than Step 2) | belongs to 4.0 | accepted | `dc6e2db1` (also `docs/guide/jira.md:316`) |

Each fix was test first where code changed. The red lines:

- `cfafa5b5`: `assert 0 == 1` (validate exited 0 with only the delete-the-root-file warning).
- `b5d214bd`: each line ended `…, or, for a TCW 3.x file, run 'tcw migrate' in this project`.
- `c05b6ba8`: `'TCW://demo.work/x' names no work item: the id-part 'TCW:' breaks the rule: … rename it by hand`.
- `c18d042b`: `('TCW-1', 'created docs/work/TCW-1/ …`; in Jira, `set TCW-1's TCW Item to tcw.work/TCW-99/TCW-1-a`.
- `64a8a8b6`: `tcw work move: 'tcw://demo.work/2026-10-22-e' is not an id-path`.
- `38fbb34c`: `Failed: DID NOT RAISE TcwError` (three cases).
- `42b397f2`, `118ea30e`, `2f8ea7c0`, `e9cf723e`, `dc6e2db1`: text only, each checked by running.

The changelog lines for these are in `878dead0`. Two more cases from cr2
were left by the dispatching session: `tcw validate` reports no error for a
hand-written override whose parent is its own original (validate's rules are
TCW-111's and TCW-112's, unchanged here); and a key-shaped folder below the
top level, which round 2's fix below covers.

### Round 2, at `878dead0`

The touched slices reviewed again: `NOT DONE`. Ten of the eleven fixes hold.
Two findings, both "belongs to 4.0":

1. a hole in `c18d042b`: `--into <KEY>/<more>` still makes a top-level folder
   named like a key;
2. after `cfafa5b5`: a stale progress record left behind while the project
   was edited further leads `tcw validate` and `tcw migrate` to advice that
   would throw that work away.

Brought to the user with the split (Design 3.4). **The user chose
(2026-10-27):** fix (1) test first, with the guide sentence on key-shaped
folders and the two release-note wordings, checked by the dispatching session
without a third round; (2) becomes a new item after release.

The fix (cr3): `4c584555` (in the work store, a part of `--into` that does not
already exist and wholly matches a tracker key is refused with exit 2, at any
depth; an existing key-shaped folder may still be used as part of the path),
`976a038d` (the guides), `6f03e406` (the release note: pin the 3.x CLI once
the first 3.0.2 session has started), and the changelog line in `22da3ea8`.
The nine tests were seen red first, each exiting 0 and making the key-named
folder. The dispatching session ran the check script itself: the nine tests,
the reviewer's Jira reproduction, and the files reproduction by hand in a
fresh scratch project:

```
12 passed, 0 failed
```

### New work items to file after release

- Fix 16 (F:51, F:74): which `Unchecked` answers `tcw validate` reports as
  `unresolved`, and the two guide lines and the `--remote` site with it.
- F:73: whether an unknown project ID exits 1 everywhere or 2 everywhere.
- F:76: the Jira credentials message always names `.tcw/tcw-config.yaml`,
  though the names may come from the personal file or a variable.
- F:78: whether the user-wide file may hold `tcw-version`, and the message's
  "a shared key".
- Round 1, S1-3: check the migration and progress records' stamps on read.
- Round 1, S1-4: keep a hand-quoted `tcw-version` key as written on edit.
- Round 1, S2-2: write commands refuse a project whose stores share a folder
  with another project's.
- Round 1, S3-4: an upper-case `TCW://` Markdown link, in validate, rewrite
  and the web app.
- Round 1, S3-5: "rename it by hand" for a mistyped project or component part.
- Round 1, S5-3: a removed folder's line lost on a permission error in
  `remove_emptied`.
- From cr2: `tcw validate` and a hand-written override whose parent is its
  own original.
- Round 2, finding 2: a stale progress record and the advice it leads to.

## Step 7 — success criterion 1 and the Known gaps (Design 3.5)

Run at `073703dc`, which differs from `v4` (`34739ce5`) only in the two entry
files and the test above; `docs/use-cases.md` and the specs are `v4`'s.

```
UC-1 12
UC-2 12
UC-3 12
UC-4 12
UC-5 12
UC-6 12
UC-7 12
UC-8 12
S-1 5
S-2 6
S-3 9
S-4 12
S-5 9
S-6 8
S-7 7
S-8 10
S-9 12
S-10 12
S-11 12
```

Every id has a count of at least 1 (criterion 9).

The Known gaps, one line per row of TCW-117 Design 6.4's table
(`docs/work/TCW-117-…/spec/spec.md:1040-1059`), against `docs/use-cases.md`
(criterion 49):

- UC-2, a library cannot warn before a breaking rename: kept, marked TCW-114
  (`:203-209`). Agrees.
- UC-3, `children:` on its own board only: gone (UC-3 reads "none recorded",
  `:272`). Agrees.
- UC-3, `--parent` when filing into another project: gone. Agrees.
- UC-3, TCW-98 and TCW-99 will change how a parent sees children: gone.
  Agrees.
- UC-4, two places rebuild a store's path from the project root: kept as one
  place, `tcw validate`'s fallback to `docs/work`, "No item yet" (`:342-344`).
  Agrees with the "otherwise kept" outcome: one place remains.
- UC-4, TCW-22, the backlog audit: gone. Agrees.
- UC-4, TCW-23, provision scoping: gone. Agrees.
- UC-5, a list fetches every ticket in the shared Jira project: narrowed,
  marked TCW-113 (`:382-387`). Agrees.
- UC-6, a missing project named in `extends` stops every command: gone (UC-6
  reads "none recorded", `:422`). Agrees.
- UC-6, `tcw://<id>/T/…` into a missing project: gone. Agrees.
- UC-6, TCW-23: gone. Agrees.
- UC-8, only `tcw validate` says where `TCW_PROJECT_<ID>` placed a project:
  narrowed, marked TCW-107 (`:473-475`). Agrees.
- S-7 (a move does not check the stage it was read at), S-8 (two gaps: a
  creation that loses its connection, and re-running `advance`), S-9 (unknown
  top-level keys): all kept, "No item yet" (`:636-638`, `:668-673`,
  `:708-710`). Agrees.
- S-9, a 2.x work store listed as empty: reworded, not removed, since
  `tcw migrate` does not refuse a 2.x store; kept with "No item yet"
  (`:702-707`). Agrees. One remark for the dispatching session, not a
  mismatch: since Step 2's fix 5, `tcw validate` names the 2.8-to-3.0
  migration guide for a stage-named folder; the gap says only that
  `tcw validate` "reports each folder as an error", which stays true.

No row goes back to TCW-117's area.

## Step 8 — the combined release notes, previewed (Design 3.6)

`combine` from `scripts/cut_version.py` run on both `upcoming/` folders by
the plan's block, with nothing cut, written, deleted or tagged; the preview
(1,642 lines before this step's addition) is kept in the session's scratch
folder, not the repository. Read against Design 6.2 (e), one line each:

- `## Upgrading` is the release notes' first `##` section, after the
  introduction: found.
- The migration guide is linked (`../migration-guide-3.X-to-4.0.0.md`, in the
  introduction and the first point) and the file exists under `docs/`: found.
- Automation that installs `tcw-cli` kept below 4 until migrated: found.
- The `tcw project` group and the four 3.x commands, each with its
  replacement (`tcw init` → `tcw project new`, `tcw projects list` →
  `tcw project list`, `tcw config show` → `tcw project config`,
  `tcw provision` → `tcw project provision`): found (TCW-115's table).
- A clone placed by a manifest other than the project's own goes only
  directly beside that project, never at or above the home folder, never in a
  hidden folder below it: found (TCW-115).
- A folder holding only `.git` is refused: found (TCW-115).
- A project already on the machine is never fetched again, and a manifest
  fetched during the run that would place it elsewhere stops the run:
  **missing**; the nearest was TCW-115's "It never overwrites anything", as
  Design 3.6 expected. Added to TCW-118's entry under TCW-115's own heading,
  `` ## `tcw project provision` fetches connected projects ``, so the cut
  merges it into that section; the code it describes is `_changed_answer`
  (`tcw/provision.py:408-430`, called at `:549-553`), which refuses with
  `<id>: was at <folder> when this run started, but …` and exits 1
  (`test_ac35_a_kept_answer_that_changes_stops_the_run` asserts code 1). The
  preview made again shows it at its line 1543, inside that section.
- A store whose `ref` names no branch, tag or commit now fails: found
  (TCW-115).
- The pinned install, for each harness: found (TCW-118, Step 5).
- The `3.x` branch: found (TCW-118, Step 5).

Every statement is now in the preview; criterion 29 checks them again on the
shipped files.

## Step 9 — the user-wide personal file (Design 3.7), and the documentation entries

**The personal file (criterion 11).** `XDG_CONFIG_HOME` is not set, so both
paths are the same file:

```
$ ls "${XDG_CONFIG_HOME:-$HOME/.config}/tcw/config.yaml" ~/.config/tcw/config.yaml
ls: ~/.config/tcw/config.yaml: No such file or directory
ls: ~/.config/tcw/config.yaml: No such file or directory
$ ls -d ~/.config/tcw
ls: ~/.config/tcw: No such file or directory
```

Neither exists, so no file holds `not_tags` and nothing is changed. This is
a check on 2026-10-26; criterion 11 asks it again before Step 23.

**The documentation entries** (`work.documentation` in
`.tcw/tcw-config.yaml`, the same eight entries as the root file), each
against Phase A's changes:

| Entry | Fires? | How it is answered |
| --- | --- | --- |
| `README.md` [Public-API] | yes | Step 4 (`d4dab8a3`): `:78-80` say the session-start install takes the `tcw-cli` release of the plugin's own version. No change here. |
| `docs/guide/jira.md` [Jira-Change] | no | No command's effect on a ticket changed in Phase A. |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | yes | Step 2's two guide changes are in place: `docs/guide/taxonomy-and-capabilities.md:417-419` gives the `unreviewed` line as "its status is still the one it inherits", and `docs/migration-guide-3.X-to-4.0.0.md:173-174` says `file` and `ticket` for a count of 1. `grep -rn 'pipx\|tcw-cli' docs/guide/` finds nothing, so no guide says the install floats. No change here. |
| `docs/release-notes/upcoming/<folder>.md` [Public-API] | yes | TCW-118's entry: Step 2, Step 5 (`073703dc`) and Step 8 (`07f0e7fb`). |
| `docs/changelogs/upcoming/<folder>.md` [Any-Code-Change] | yes | TCW-118's entry: Step 2 and Step 5 (`073703dc`). |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | checked, no | No component's CLI changed. `grep -n -i 'newest\|pipx upgrade' skills/setup/SKILL.md` finds nothing, nor does `pipx upgrade` anywhere under `skills/`; `skills/setup/references/install.md:7` and `:40` give the pinned command (Step 4). |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | no | No configuration key added, removed or changed in meaning. |
| `docs/use-cases.md` [Project-Setup-Change] | yes | S-9 had no requirement that the plugin installs the CLI of its own version (TCW-117 had not written it), so this step adds it, citing `scripts/session_bootstrap.sh`. The Known gaps were confirmed at Step 7; the new line changes no heading, so Step 7's counts stand. |

One observation for the dispatching session, not changed here: `README.md:84`
and `skills/setup/references/install.md:31` still give `pipx install tcw-cli`,
unpinned, as the fix when `tcw` is missing. It gives the newest release, which
is the plugin's own for a user who follows `main`, and the version check
reports any difference at the next session start, but it is the one unpinned
install command left beside the pinned ones.

## Step 9a — the suite script proved on `v4` (Decided 7)

No commit: the release folder `~/.tcw-4.0-release/` only, with `load.sh` and
`ci-suite.sh` cut word for word from the plan's "Tools" and the step's block
as `step-9a.sh`. Run in the background; it did not hang, and the script
needed no change. Its first lines and its end:

```
== Mon Oct 26 20:39:43 UTC 2026 in ~/.tcw-4.0-release/suite-proof, HEAD af55f473e0fe3acdfa81f9d97b9d0fc3d261cace
== TCW_ variables inside the run (nothing below this line means none):
== HOME inside the run: <a scratch folder>/home
...
================ 8086 passed, 113 skipped in 894.82s (0:14:54) =================
10.14.0
== suite and web build passed
```

`step-9a.sh` exited 0; the clone `suite-proof` was deleted after the pass and
`suite-proof.txt` kept.

**What the plan got wrong.** The run proved `v4` at `af55f473`, before Steps
2 to 4 were merged into it, so it proves the script, not the release's
changes. The suite below is that proof.

## The suite at `22da3ea8`

Run by the dispatching session as CI runs it, in its two halves, with every
`TCW_*` variable unset:

```
2265 passed, 2 skipped
5889 passed, 111 skipped
```

`pnpm test`, `tsc --noEmit`, `pnpm lint` and `pnpm check:build`: clean.
