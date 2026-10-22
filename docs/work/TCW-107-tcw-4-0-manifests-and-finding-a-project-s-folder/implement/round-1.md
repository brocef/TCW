# Implement round 1 — TCW-107

Built on the `v4` branch in the worktree `.claude/worktrees/v4`, with the code
under test run from its own virtual environment (`.venv/bin/pytest`,
`.venv/bin/tcw`). The records of step 11 were written with the released 3.x
CLI on PATH, which reads this repository's root `tcw-config.yaml`. This is the
first implement round, so it answers no rejection. It gives no verdict.

## What was done, step by step

- **Step 0 — the macOS permission check.** Step 0 not run: no terminal without
  that access is available to the implementing agent, and running it risks a
  system dialog on the user's machine; the belief was not checked. See "The
  folders macOS protects" below for what the code does instead.
- **Step 1 — the manifest files and their parser** (`3fe4a61e`).
  `tcw/store/manifest.py` holds `ManifestEntry` and `parse_manifest`;
  `tcw/project_files.py` gains the two manifest names, `SKIP_VARIABLE`,
  `personal_files_skipped()`, and `validate_project_id` with its pattern and
  reserved IDs, moved from `tcw/store/project.py`. Any problem in a manifest
  means it gives no entries (Design 1.8). 48 tests in `tests/test_manifest.py`.
- **Step 2 — test helpers, and test folders kept apart** (`32c510f0`).
  `tests/projectfiles.py` gains `manifest_file`, `write_manifest`,
  `write_connected_config` and `write_connected_config_file`;
  `tests/conftest.py` overrides `tmp_path` with a folder `w` alone in its
  parent. 15 tests in `tests/test_projectfiles_helper.py`, including the one
  that goes red without the override.
- **Step 3 — finding a project's folder from its ID** (`89af3e64`).
  `FsProjectRegistry.project_folder`, `found`, the lookup (`_locate`,
  `_answer`, `_family`, `_manifests_of`, `_entry_answer`, `_search`), the
  walk order parent, children, upstreams, `ProjectGraphError` and
  `UnknownProject`, and `Unreachable`'s `project` and `repository`.
  `parse_connected_entry` accepts `{}` and a `jira`-only mapping. 43 tests in
  `tests/test_project_lookup.py`, including the except-order test.
- **Step 4 — what a person sees** (`bae01a58`). `found` in
  `tcw projects list --json`; Design 6.2's message in `tcw validate`,
  `unreachable_project_note` and `open_project`; `manifest_findings` (rows a
  to e of Design 5.1, a committed entry overridden on this machine as a
  warning); the tracked personal manifest warning; the second ignore rule in
  `tcw init` and this repository's `.tcw/.gitignore`. 42 tests in
  `tests/test_manifest_cli.py`. **Process gap:** in this step the production
  code was written before the CLI tests, not after a red run. The tests were
  then mutation-checked one change at a time (below), which is the evidence
  that each can fail; one mutation survived and a test was added for it.
- **Step 5 — one registry per command** (`f52c934f`). `_OPEN`,
  `begin_command`, `end_command` and `forget_registries` in
  `tcw/store/project.py`, wired to `tcw.config.begin_command` and
  `end_command`; a registry is kept only once `_load_graph` finished;
  `_atomic_write_all` drops the registries after writing a
  `tcw-config.yaml` or either manifest, in a `finally` so a failed promote
  drops them too. Tests: AC 27, the drop after a write, a write of another
  file keeping the registry, outside a command every open reads afresh, a
  load that raised is not kept.
- **Step 6 — git worktrees** (`89ba8247`). `personal_file(root, name)` with
  the fallback to the main checkout; `Origin.root` so a borrowed
  `tcw-config.local.yaml` is read as though it sat in the worktree (its
  `file:` paths and `TCW_CONFIG_DIR` are the worktree's) and is named as the
  main checkout's file; Design 4.3's search candidates. 8 tests in
  `tests/test_manifest_worktree.py`: AC 16, 17 (manifest and configuration),
  18, 19 (two), 26, and `packages/a` finding `ws` through the main checkout.
- **Step 7 — `tcw provision` fetches no project** (`28224a47`). Removed
  `_declared_projects_in_graph`, `_provision_projects`,
  `declared_connected_projects` and the static-guard exemption; the help text
  and the "Nothing to provision" line name stores only; the comment of choice
  7 on `FsStoreProvisioner`. AC 22's first sentence in
  `test_ac22_provision_fetches_no_project` (a `git` wrapper records every
  call; no clone and no contact with the entry's repository). The tests in the
  plan's step 7 table were removed or kept exactly as the table says.
- **Step 8 — a store inside a project already here** (`55f4fac8`).
  `checkout_of` reads the manifests in `_manifest_order` and removes the
  entry's `subfolder`. The registry-rung section of
  `tests/test_store_provisioning.py` now writes the repository in a manifest
  entry; new tests for AC 22's rung sentences, the order, an entry for a
  project not found, and a sibling's manifest.
- **Step 9 — the fixtures move onto the lookup** (`ebce3fd6` by script,
  `910d6477` by hand). Details below.
- **Two fixes between steps 9 and 10.** `bf4aee2e`: an entry placing a 3.x
  project read "places it at <folder> is a TCW 3.x project"; it now reads
  "…, which is a TCW 3.x project", with a test of the exact text.
  `b2fa5810`: delegation (`tcw work new --project`, `--blocks`) refused a
  project not on this machine with "is declared but is not on this machine";
  it now gives Design 6.2's message, so the work skill's new rule for exit 3
  (step 12) has an instruction to pass on. Found while reading step 9's
  mutation failures.
- **Step 10 — `projects:` names IDs only** (`ee8c46ad`).
  `parse_connected_entry` refuses a string, `path` or `repository` with the
  manifest entry to write (`lib: ../lib`, or
  `lib: {path: <a folder>, repository: <url>#<ref>, subfolder: <path>}`);
  `ConnectedProject` keeps `id` and `jira`; `UnreachableProject` drops
  `declaration`; `_target_path`, `_points_elsewhere`, the two "does not point
  back" problems, `misdirected` and its `tcw validate` warning, and the
  `provisioned_root` import are gone; the `tcw provision` hint is gone from
  every project message. AC 15's tests are in `tests/test_manifest_cli.py`.
- **Step 11 — records** (`ec417aa9`), with the released CLI:
  `cli/record-where-other-projects-are-in-a-manifest` and
  `cli/find-a-projects-folder-from-its-id` (Supported, subjects `project` and
  `manifest`, feature `project-registry`); the eleven changed descriptions;
  the term `manifest`, related to `project`, and the descriptions of
  `project`, `project-registry` and `personal-configuration` (both features
  now list `manifest`). `tcw validate` with the released CLI: `0 errors,
  0 warnings, 0 unresolved`.
- **Step 12 — documentation entries** (`1ddf57ed`). See the table below.
- **Step 13 — the suite as CI runs it.** See the end.

## Decisions

- **The family walk consults only folders already known.** `_family` reads
  the manifests of a family member only once this command has found its
  folder, and makes no lookup of its own to find one. This keeps the walk
  finite and AC 25 working (a grandchild placed only by a manifest the
  current project cannot reach is not found from it), and it is the reading
  of Design 2.2 that needs no recursion.
- **The macOS guard was implemented, not raised first.** The spec's Risks say
  to raise the protected folders on TCW-99 before guarding them; the brief
  for this round said to guard them so a search never reads inside them. The
  guard is in place (below); this is flagged so the dispatching session can
  record it on TCW-99.
- **`UnreachableProject.repository`.** `open_project` needs the deciding
  entry's repository to put on `Unreachable`; a field on the record is used
  rather than a second lookup.
- **`checkout_of`'s order beyond Design 2.2.** The spec names the active
  project, its ancestors and its descendants. A project the graph follows
  that is none of those (a sibling, reached through the parent) is read after
  them, in the order the walk met it, so its manifest still counts and the
  answer stays fixed. Tested by `test_checkout_of_reads_a_siblings_manifest`.
- **Delegation's refusal uses Design 6.2's message** (`b2fa5810`). Design 6.2
  says "wherever 3.x reports" a project not here, and the skill line in step
  12 covers exit 3 for an absent project; the refusal said neither where the
  project is placed nor how to fetch it.
- **A manifest entry whose folder holds files and no project is an error**,
  as Design 2.6 says, and that changed two fixtures whose "absent" folder
  was really a folder with contents (`test_an_absent_parent_leaves_the_child_usable`
  now points at `../../../gone`; the override workspace's `core` places its
  parent at `../orchestrator`). Their assertions are unchanged.
- **AC 7, an overridden committed entry.** The committed entry that the
  personal manifest overrides still gives its own `unresolved` row when its
  folder is not here; only the problems of rows b to e turn into warnings.
  This is how Design 5.1's rows read, and is noted in case a reviewer reads it
  otherwise.

## Handoffs folded in

From the ticket's comments:

- **TCW-115 (1):** a folder holding only `.git` is "not on this machine", and
  its message says `<path> holds only .git; finish or remove it with git`
  before the fetch command (`_holds_only_git`, exempted in the static guard).
- **TCW-115 (2):** a manifest `repository` whose URL or branch begins with `-`
  is refused, so it can never be read as an option to git.
- **TCW-114:** `Unreachable` carries `project` and `repository`; the search
  starts no process, and the only process the lookup starts is
  `git rev-parse`, through `worktree_anchors`.
- **TCW-108:** needed nothing from this item beyond what the spec already
  gives.
- **TCW-115 (spec and plan, revised):** telling a git failure apart from a
  folder in no repository is not done here, as the dispatching session
  decided: `git_root` is unchanged and this item does not touch it. The `-`
  refusal from the same handoff is folded in, as TCW-115 (2) above.
- **TCW-115 (plan, final):** checked that this item adds no git call that
  bypasses `_git` (`tcw/store/fs.py`) or `_git_lines`
  (`tcw/store/project.py`). Every `+` line of
  `git diff 3fe4a61e~1 HEAD -- tcw` was searched for `subprocess`, `"git"`,
  `_git(` and `_git_lines`. The only git use is `personal_file_tracked`'s
  `git_root(root)` call, which was there before this item and runs through
  `_git`. The worktree code calls the existing `worktree_anchors`, which runs
  through `_git_lines`. Clearing git's location variables is left to TCW-115.

## The folders macOS protects

On macOS, `Desktop`, `Documents` and `Downloads` directly in the home folder
are never tested as folders next to a project (`_PROTECTED_NAMES`,
`_ON_MACOS`, `_protected`), including next to the main checkout of a linked
worktree. The enclosing folders are the current project's parents, so when
the current folder is outside those three none of them is inside one. A
search therefore never reads inside them when the current folder is outside
them; `test_the_search_never_reads_inside_a_protected_folder_next_to_it`
counts the reads to show it. A manifest entry or a `TCW_PROJECT_<ID>` that a person writes to
point inside one is read, since that is an explicit placement, not a search.

## Step 9 in detail

- **Inventory** (scratchpad, not the repository): 5549 test IDs at the start
  of step 9, and the count of `assert` statements and `pytest.raises` blocks
  in each test function.
- **Left on 3.x locators before the conversion**, each with the rule that
  changed or removed it at step 10:
  - `tests/test_project_registry.py`: `test_a_present_counterpart_pointing_elsewhere_still_fails`
    and `test_a_locator_that_misses_a_project_the_graph_has_is_reported`
    (Design 3.2, removed); `test_a_declaration_answers_when_the_locator_does_not`
    (where 3.x cloned a project, removed); `test_an_override_at_an_absent_path_falls_through_to_the_declaration`
    (rewritten as `…_falls_through_to_the_manifest`); `test_a_declared_project_says_to_provision_it`
    and `test_an_undeclared_absent_project_does_not_say_to_provision`
    (Design 6.2, rewritten as `test_a_project_placed_with_a_repository_names_the_command_that_fetches_it`
    and `test_a_project_placed_with_no_repository_does_not_say_to_provision`);
    `test_a_malformed_entry_is_an_error_naming_the_line` (Design 3.1, its
    cases now refusals).
  - `tests/test_store_provisioning.py::test_an_unresolvable_checkout_is_a_declaration_error_not_a_crash`
    and `tests/test_worktree_sibling_nodes.py::test_a_child_declared_only_by_repository_resolves_to_the_worktree`:
    a repository with no path or a `repository.checkout`, which the helper
    refuses; removed at step 10 (where 3.x cloned a project; TCW-116 decides
    how such entries migrate).
  - `tests/test_project_registry.py::test_a_locator_that_resolves_is_never_misdirected`
    and the `misdirected()` assertion in `tests/test_project_overrides.py`:
    removed with `misdirected` (Design 3.2).
- **Commit 1, by script** (`ebce3fd6`): `write_config(` and
  `write_config_file(` became their `write_connected_` forms in 33 files; the
  tests above were pointed back at the 3.x writers.
- **Commit 2, by hand** (`910d6477`): `connect()` in `tests/work/projects.py`;
  AC 13 and 13a in `tests/test_project_files_cli.py`; the text comparisons in
  `tests/test_config_edit_writers.py` (its fixture wrote bytes, which the
  helper leaves alone) and `tests/test_store_provisioning.py`; the two
  worktree tests in `tests/test_worktree_sibling_nodes.py` that edit a
  configuration's text, one of which now places `pkg-b` itself in a second
  repository, since an entry can no longer place a project under another ID;
  the two Jira block tests. A probe that refused every locator, run over the
  whole suite including its `tcw` subprocesses, found five files the grep had
  missed (they write `document["projects"] = …`): `tests/test_cli_contract.py`,
  `tests/test_capabilities_cli_contract.py`, `tests/test_routing_nodes.py`,
  `tests/test_store_nodes.py`, `tests/test_validate_target.py`. They were
  converted in this commit. `tests/test_environment_hardness.py`'s symlink and
  worktree tests passed after the script, with paths made relative, so they
  were not changed by hand.
- **Assertions changed, each for a rule the spec changed:**
  - Design 6.2 ("is not on this machine", where the entry places it):
    `tests/test_capabilities_federation.py` (two),
    `tests/test_project_overrides.py::test_validate_with_no_override_says_nothing_about_one`,
    `tests/test_upstream_projects.py::test_an_absent_upstream_is_a_warning_and_extends_says_unreachable`,
    `tests/test_validate.py::test_an_absent_connected_project_is_reported_and_not_fatal`,
    `tests/test_cli_contract.py::test_naming_projects_that_are_not_here`
    (its shared fixture was converted, so it changed here, not at step 10).
  - Design 2.6 (the folder an entry places is the entry's problem):
    `test_invalid_target_fails_closed` (two cases, so their test IDs changed),
    the two decoy tests in `tests/test_project_registry.py`,
    AC 13 and 13a, `tests/test_validate_target.py::test_graph_problems_precede_target_resolution`.
  - Design 3.1 (the configuration names the ID):
    `test_extends_add_writes_the_key_and_no_file_inside_the_store` now finds
    the path in the manifest.
- **Proofs.**
  1. The full suite, green with the 3.x ladder present: `5432 passed,
     118 skipped`.
  2. The search turned off (the source of `_search` edited for the run to
     find nothing, so every `tcw` subprocess saw it too, and restored after),
     over the suite without the three files whose subject is the search:
     green except two new step 8 tests that relied on the search for a
     project their subject was not; they were given the entries they lacked
     and the run was then green.
  3. Mutation check, the search off and `parse_manifest` returning no
     entries: 294 failed and 10 errors. Every converted file holding a test
     that asserts a connected project is present has at least one red test;
     the files with none (`tests/config/test_config_show.py`,
     `tests/config/test_personal_validate_init.py`,
     `tests/test_routing_nodes.py`, `tests/test_validate_moved_stores.py`)
     hold no such test, and `tests/test_capabilities_cli_contract.py` errors
     when run on its own. The reasons of 14 red tests across 14 files were
     read: each is the project not being found ("is not on this machine: no
     manifest lists it…", an empty children list, a `KeyError` on the
     project), none an unrelated crash.
  4. Inventory: no test ID disappeared in step 9 except the two renamed
     `test_invalid_target_fails_closed` cases; one test's assertion count
     dropped, `test_checkout_of_reads_a_siblings_manifest` (2 to 1), because
     its `found == search` check went when the test was given its entries.

## Tests removed across steps 3 to 10

Each against the rule that removed it:

- Step 3: the `{}` case of `test_a_malformed_entry_is_an_error_naming_the_line`
  (Design 3.1 accepts it; `test_an_entry_holding_an_empty_mapping_is_accepted`
  added).
- Step 7 (Design 6.3; what each covered is in the plan's step 7 table, for
  TCW-115): `test_a_declared_connected_project_is_obtained`,
  `test_provisioning_follows_a_declaration_inside_an_obtained_node`,
  `test_two_entries_naming_one_repository_share_a_working_copy`,
  `test_a_repository_with_no_node_at_the_declared_path_is_refused`,
  `test_an_occupied_checkout_is_refused_before_any_fetch`,
  `test_a_malformed_connected_declaration_refuses_and_names_the_line`,
  `test_a_declaration_on_a_sibling_is_followed_from_anywhere_in_the_graph`,
  `test_a_project_the_checkout_already_has_is_not_fetched`,
  `test_a_sibling_of_an_ancestor_is_recognised_as_already_here`,
  `test_a_present_project_is_still_read_for_its_own_declarations`,
  `test_dry_run_does_not_call_a_planned_obtain_already_available`,
  `test_a_declaration_error_on_an_obtained_node_fails_the_run`,
  `test_a_public_upstream_is_provisioned_into_a_reader_only_checkout`,
  `test_provision_does_not_follow_an_upstreams_own_connections`,
  `test_without_an_override_the_declared_repository_is_fetched`,
  `test_an_overridden_project_is_never_fetched`,
  `test_one_variable_set_serves_both_session_shapes`,
  `test_provision_refuses_the_2x_key_in_a_child`.
  `test_provision_refresh_is_a_usage_error` was kept and moved;
  `test_graph_readers_tolerate_what_the_loader_refuses` dropped its
  `provision` comparison.
- Step 10: the eight tests listed under "Left on 3.x locators" above that
  were removed rather than rewritten, and the four
  `test_a_malformed_entry_is_an_error_naming_the_line` cases, whose IDs
  changed with their expected text.

## Mutation checks

Each mutation was applied to the source, the named tests run, and the source
restored (`mutate.py` in the scratchpad). Every one went red unless said.

- Steps 1 to 3: the new tests were mutation-checked as they were written;
  one survivor in step 3 showed the `.tcw` exclusion of the search was
  enforced twice, and the duplicate was removed.
- Step 4: removing `found` (7 red), `manifest_findings` (7), the drop of
  records `manifest_findings` owns (5), the `open_project` message (1), the
  warning turned into an error (1), the second ignore rule (1), the tracked
  manifest warning (1). The `absent.message` branch in `_cmd_validate`
  survived; a validate line for a project with no entry anywhere was added to
  AC 7's test, and it then went red (1). `unreachable_project_note`'s branch:
  1 red.
- Step 5: `forget_registries()` not called (1 red); `open` returning a new
  registry each time (4 red).
- Step 6: no fallback to the main checkout's file (2), no worktree search
  (3), not listing next to the main checkout (2), not enclosing the main
  checkout (3), `Origin.root` ignored (1), a search match not passed through
  `_worktree_copy` (survived at first; `test_ac19_a_search_landing_in_the_main_checkout_is_the_worktrees_copy`
  added, then 1 red).
- Step 8: the `subfolder` not removed (2), an entry for a project not found
  ending the search (1), the order reversed (1), other followed projects not
  appended (survived at first; the sibling test added, then 1 red).
- Delegation's message (`b2fa5810`): 2 red.
- Step 10: the locator refusal off (7 red), the `subfolder` part of the
  suggested entry dropped (1), unknown keys accepted (1).
- Step 9's mutation check is under "Step 9 in detail".

## Documentation entries

| Entry | Answer |
| --- | --- |
| `README.md` [Public-API] | Fires (where a connected project's location is written, `tcw provision`). Deferred to TCW-117, which rewrites the user-facing documents for 4.0, as the plan says. |
| `docs/guide/jira.md` [Jira-Change] | Does not fire: nothing a command does to a ticket changes. |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | Fires (`multi-repo.md`, `cli.md`, `work.md`). Deferred to TCW-117. |
| `docs/release-notes/upcoming/<folder>.md` [Public-API] | Written: `docs/release-notes/upcoming/TCW-107-tcw-4-0-manifests-and-finding-a-project-s-folder.md`. |
| `docs/changelogs/upcoming/<folder>.md` [Any-Code-Change] | Written: `docs/changelogs/upcoming/TCW-107-tcw-4-0-manifests-and-finding-a-project-s-folder.md`. |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | `skills/work/SKILL.md`'s exit 5 rule changed to the plan's sentence. Everything else deferred to TCW-117. |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | Fires (`projects.md`, `stores.md`). Deferred to TCW-117. |
| `docs/use-cases.md` [Project-Setup-Change] | Fires (UC-1, UC-3, UC-6, UC-8, S-5, S-10). Deferred to TCW-117. |

## The suite

`.venv/bin/pytest -q -p no:cacheprovider`, run in full as CI runs it:

SUITE_RESULT
