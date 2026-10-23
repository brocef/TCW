# Implement round 2 — TCW-110

Answers review round 1 (rejected at `c1b1046d`). Built on the `v4` branch in
the worktree `.claude/worktrees/v4`, with the code under test run from its own
virtual environment (`.venv/bin/pytest`, `.venv/bin/tcw`), and scratch runs of
`.venv/bin/tcw` given their own `HOME`, `XDG_CONFIG_HOME` and
`XDG_CACHE_HOME`. The records were checked with the released CLI on PATH
(`tcw 3.0.2`), which reads this repository's root `tcw-config.yaml`. It gives
no verdict.

## What was done, for each item the review asked for

- **(a) The capability records** (`4644ac2d`). The nine records the review
  named now say only what the 4.0 code does; the 3.x sentences were replaced,
  not added to, and the "Since TCW 4.0" paragraph appended in round 1 was
  folded into the text above it or removed. Each claim was checked against
  the code or a scratch project before it was written:
    1. Records 1 to 3, `work/configure-the-work-store-location`,
       `taxonomy/configure-the-taxonomy-store-location` and
       `capabilities/configure-the-capabilities-store-location`: the key is in
       `.tcw/tcw-config.yaml`; a location is a path relative to the project's
       folder or a folder address, resolved from the project whose
       configuration holds it; an absolute path or one starting with `~` is
       refused (checked: `tcw init --work-path /tmp/x work` exits 2 with the
       Design 7.1 message); a chain of addresses that loops is refused
       (checked: `work.path: tcw://qq.work.path/x` in `qq` gives
       `store locations loop: qq work -> qq work`, exit 1); `tcw validate`
       fails a store that nests in or coincides with another (checked with a
       taxonomy store inside the work store). `tcw init --<component>-path`
       is described as scaffolding at a relative path only; see "Found while
       checking the records" for why.
    2. Record 4, `cli/rely-on-one-output-contract`: lists print full identifiers or
       project IDs; `"schema": 2`; records carry `full-id` and `owner`; any
       object is named by its full identifier, its address, its id-path in the
       project I am in, or for a Jira item its key, bare or as
       `<project>.work/<KEY>`; the 3.x `<project-id>/<folder>` and alias-prefix
       forms are not found (exit 4) with the Design 3.4 hint (checked:
       `tcw work show demo/2026-10-23-add-a-widget` exits 4 with
       `to name an object in project 'demo', write demo.work/2026-10-23-add-a-widget`).
    3. Record 5, `work/read-a-work-item`: the item is named by the 4.0 forms; the text
       form starts with `full-id` and `owner`; parent, blockers and children
       print as full identifiers; `--json` says `"schema": 2`.
    4. Records 6 and 7, `taxonomy/read-a-term` and `capabilities/read-a-capability`: the text
       form starts with `full-id:` and `owner:`; an inherited entry is named
       by the full identifier of the project it comes from; any locatable
       project's entry can be read; `"schema": 2`; the ambiguity advice now
       says to write the full identifier (see "Found while checking the
       records"); an unknown project ID exits 1. The tracker-key sentence,
       which does not apply to these namespaces, is gone.
    5. Record 8, `web/pick-references-and-known-values-from-suggestions`: links are
       inserted as `tcw://<project>.<namespace>/<id-path>`, checked against
       `tcwLinkOptions` in `web/client/src/model/reference-search.ts`;
       references and parent and blocker values are stored as full
       identifiers; another project's item is kept with the warning
       `otherProjectWarning` gives.
    6. Record 9, `work/declare-capability-changes-in-a-child-projects-ledger`: the
       examples are full identifiers; the project may be any project TCW can
       locate, not only one under `projects.children`; the first-segment and
       ambiguity rules are gone; what is refused follows
       `route_capability_path` (`tcw/work/gates.py:349-385`): not on this
       machine, no ledger, and the item's own project without a ledger are
       "could not be checked", an unknown project and a 3.x entry are wrong;
       an entry for an extended project is read through this project's view,
       and declaring it removed is refused. Reconciling is done inside the
       owning project, because `set`, `reset` and `rm` go through
       `find_tree_writable` and refuse another project's entry.

    The three weaker records: `work/view-the-board` says "full identifier"
    and `--parent <item>`, and its Jira sentence now says the warning names
    the tickets' keys; `work/manage-blocking-relations` and
    `work/decompose-a-work-item-into-children` say `<item>` for every
    `<slug>`, list the forms a blocker or parent can be given in, and say the
    full identifier is what is stored. Links inside the records stay in the
    3.x form, as the spec requires; commands that do not exist yet are not in
    backticks (`tcw migrate` is written without them).

- **(b) The Design 1.6 message** (`dd1491c6`). In `sort_input`
  (`tcw/ids.py`), command input that cannot reach a folder whose name breaks
  the identifier rule now names the rule and the rename by hand, and offers
  no other form to write:
    - `'cli/has.dot' names no capability: the id-part 'has.dot' breaks the rule: letters, digits, '-' and '_', starting with a letter or digit, at most 128 characters; no command can be given a folder whose name breaks that rule: rename it by hand`
    - `'has.dot' names no term: it is not a full identifier (<project>.taxonomy/<id-path>), and an id-path holds no '.' (each id-part is …); no command can be given a folder whose name breaks that rule: rename it by hand`
    - `'demo.capabilities/cli/has.dot' is not a full identifier: the id-part 'has.dot' breaks the rule: …; no command can be given a folder whose name breaks that rule: rename it by hand`

    A typing slip that no folder could have (`cli//x`, an empty part) gets
    the rule alone, without the rename. Messages use the noun of each
    namespace, "term", "capability" and "work item" (`NOUNS`), in place of
    "<namespace> object", including the wrong-namespace message
    (`names a capability; this command takes a term (taxonomy namespace)`).
    Tests: `tests/test_ids.py` gains three message tests (12 cases);
    `test_ac18_a_hand_made_folder_breaking_the_rule_is_listed_and_reported`
    (`tests/test_tree_full_identifiers.py`) now runs `show`, `set` and `rm`
    of such a capability folder and `show` and `rm` of such a taxonomy
    folder, and asserts exit 2, the rule, the rename, no "or its id-path"
    advice, and that the folders are still there. One match in
    `tests/test_capabilities_rm.py` followed the new noun.

- **(c) The AC 12 fixture** (`2224ccb0`). `app_and_server` in
  `tests/work/test_gates.py` names its projects with
  `connect_projects(app, "children", "server")` and
  `connect_projects(server, "parent", "app")`. The two projects are
  siblings, so the search finds them without the manifest the older helper
  wrote; the "not on this machine" test still gets `Unchecked`, because the
  `projects.children` entry names `server` after its folder is removed.
  `tests/work/test_gates.py`: 53 passed.

- **(d) The fixture errors that depend on how pytest is given the files.**
  Not caused by this repository: it is a pytest change in 9.1.0. When the
  file arguments visit a folder two levels below another folder whose
  `conftest.py` defines fixtures, then a file elsewhere, then that folder
  again, the second visit does not see that `conftest.py`'s fixtures.
  `tests/work/jira/test_jira_full_identifiers.py tests/test_ids.py
tests/work/jira/test_jira_list.py` reproduces it (17 errors), and the same
  three in an order that keeps the two Jira files together passes. A
  four-file project outside this repository (`tests/w/j/conftest.py` with
  one fixture, two test files beside it, one test file in `tests/`)
  reproduces it as well: with the arguments
  `tests/w/j/test_one.py tests/test_b.py tests/w/j/test_two.py` it gives
  "2 passed, 1 error" under pytest 9.1.0 and 9.1.1 (the version this
  repository's `.venv` has, and the newest; `pyproject.toml` does not pin
  it) and "3 passed" under 8.3.5, 8.4.2, 9.0.0 and 9.0.2. It predates this
  item: at `426c3a3f~1`, in a throwaway detached worktree (since removed),
  `tests/work/jira/test_jira_list.py tests/test_refs.py
tests/work/jira/test_jira_validate_remote.py` gave 28 errors and
  `tests/serve/test_records.py tests/test_refs.py
tests/serve/test_work_write.py` 52 errors, every one a fixture not found
  at setup; the review's 25-file list, cut to the 15 files that exist
  there, happens to keep each folder's files together and shows no fixture
  errors. Nothing was changed: the fix belongs to pytest, and a
  contributor avoids it by listing the files of one folder next to each
  other, or by passing the folder. The full suite, which passes `tests`,
  is not affected.

## Found while checking the records

- **The ambiguity message gave TCW 3.x advice** (`3f1bd826`). A bare
  id-path held by more than one inherited project raised `AmbiguousRef`
  saying "qualify it with an alias prefix", a form that 4.0 reads as an
  id-path and does not find. It now says
  `more than one project this one inherits from holds it; name it by its full identifier, <project>.<namespace>/<path>`
  (`tcw/store/base.py`). `test_cli_rm_ambiguous` asserts the new advice and
  that `show base-a.capabilities/auth/login` then works. Folded in as small:
  it is the message the two read records describe.
- **`tcw init --<component>-path` does not take a folder address.** Not
  fixed in this round. `run_init` (`tcw/cli.py:70-73`) makes a `Path` of the
  option's text, which collapses `tcw://` to `tcw:/`, so
  `tcw init --id qq --work-path tcw://qq.path/board work` writes
  `work.path: tcw:/qq.path/board` and creates the folder `tcw:/qq.path/board`
  under the project, as a plain relative path. Keeping the text as text is
  not enough: the address then goes to `store_location`, which locates the
  named project through the registry, and a project being initialized has
  no configuration yet to be found by, so the command fails with
  "no .tcw/tcw-config.yaml here". A correct fix has to resolve an address
  naming the project being initialized against its own folder and against
  the paths given in the same command, which is larger than this round's
  scope. A folder address written into `.tcw/tcw-config.yaml` by hand works
  (`tcw work path`, `tcw work new` and `tcw validate` checked with
  `tcw://qq.path/board` and `tcw://qq.work.path/terms`). The three records
  say only that `tcw init` scaffolds at a relative path. For the
  dispatching session to decide: fix it here, or file it.
- `tcw validate <path>` still says `no such <axis> object` for a target
  that names nothing (`tcw/validate.py:467`). That predates this item, and
  was left alone.

## Mutation checks

- With `tcw/ids.py` put back to `HEAD` before (b), the new tests in
  `tests/test_ids.py` and the AC 18 test fail (10 failed); with the change,
  they pass.
- `test_a_typing_slip_is_not_called_a_folder_to_rename` passes against the
  old message too, as it should: it guards the new message against adding
  the rename where no folder could exist.

## Checks run

- The files changed in this round: `tests/test_ids.py`,
  `tests/test_tree_full_identifiers.py`, `tests/test_capabilities_rm.py`,
  `tests/test_taxonomy.py` and `tests/test_capabilities.py` (274 passed, 10
  skipped); `tests/serve` (366 passed); `tests/work/test_full_identifiers.py`,
  `tests/work/test_cli_items.py`, `tests/test_cli_contract.py`,
  `tests/test_locate.py`, `tests/test_validate.py` (185 passed, 11 skipped);
  `tests/test_capability_ref_wording.py`, `tests/test_ledger_3_0.py`,
  `tests/test_literal_store_names.py`, `tests/test_identifier_sweep.py`,
  `tests/test_environment_hardness.py` (117 passed, 6 skipped).
- `.venv/bin/pytest -q -p no:cacheprovider tests/test_documented_cli_surface.py`:
  `454 passed in 4.60s`.
- The released `tcw validate` (`tcw 3.0.2`):
  `0 errors, 0 warnings, 0 unresolved`.
- `pnpm exec prettier --check` over the twelve changed records, run from
  the worktree root, which holds `.prettierrc.json`:
  `All matched files use Prettier code style!`

## Not done

- The `tcw init` folder-address defect above.
- The full suite is the dispatching session's to run.

## The suite

SUITE_RESULT
