# Implement round 1 — TCW-109

Built on the branch `impl-109`, made from `v4` at `0287fc4e`, in the worktree
`.claude/worktrees/impl-109`, with the code under test run from that
worktree's own virtual environment (`.venv/bin/pytest`). `.venv/bin/tcw` was
never run with this repository as the project; the hand run made was in a
throwaway project in the scratchpad, with `HOME`, `XDG_CONFIG_HOME` and
`XDG_CACHE_HOME` set there and `TCW_NO_PERSONAL_CONFIG=1`. The lifecycle was
not driven by any CLI: the dispatching session makes every move, so no ticket
was moved and nothing was posted. This is the first implement round, so it
answers no rejection. It gives no verdict.

## What was done, step by step

- **Steps 1 and 2 — the table of keys and reading the override variables**
  (`1c6b6e3c`). `tcw/config_keys.py`: `known_keys` (with `jira_keys`),
  `key_part`, `override_name`, `decode_key`, `project_of`, `Override`,
  `is_override`, `read_overrides`, `read_override`. `INHERITED_KEYS` and the
  `environment` layer in `tcw/config.py`; `Origin` gains `variable`,
  `project` and `position`; `_allowed` speaks for a variable. Not yet used.
- **Step 3 — the configuration editor writes an `inherit` entry**
  (`2c1ab089`). `SetList(inherit=True)`; a list holding one leading
  `inherit: true` entry is edited in place.
- **Step 4 — the configuration sources without raising** (`6de233ec`).
  `ProjectRegistry.source_entries`, `SourceEntry`, `unavailable` (the one
  builder of the exit-7 messages, with `subject`), and `sources` rewritten
  over them. An ancestor, or a project read only for a lookup, whose shared
  file cannot be read is placed with no parents and its links unreadable.
- **Step 5 — `inherit: true` in `work.tags` and `null` at an inherited key**
  (`cc23d798`).
- **Step 6 — what reads an inherited key reads it only when it uses it**
  (`4288eb89`). `Withheld`, `Config.withheld` and `require`;
  `project_facts`, `ProjectFacts`, `external_stages_of`, `item_folders`;
  `tcw work lifecycle`, `docs`, `path`, the stage and procedure prompts with
  no item, `_own` and `_personal_note` no longer open the store; references
  into a Jira-mode project answered from its folders; `validate_changes`
  reads the tags only when a tag is added; `open_backend` takes `registry=`
  and requires `work.jira`, then `work.tags`, in Jira mode.
- **Steps 7a, 7b and 7c — the fold** (`5bea9734`, and `cdd6be20`). See
  decision 1 for why they are one commit.
- **Step 8 — the environment layer** (`c19e7f2e`).
- **Steps 9, 10 and 11 — `tcw config show`, the tag commands, the web app
  summary** (`55956d9b`).
- **Step 12 — the records** (`5b7b61f4`).
- **Step 13 — the changelog and release-notes entries** (`ff3aba68`).

## Decisions

Each was decided by the implementing agent, with its reason. None
contradicts the spec.

1. **Steps 7a, 7b and 7c were built together.** The fold, a problem in an
   inherited value and a gap are three outcomes of one walk over the
   sources (`_Fold` in `tcw/config.py`), so the interim rules the plan
   describes (a gap withholds nothing; an ancestor's problem is the active
   project's) were never written. The full suite was run after the fold,
   before any new test, and every failure read: there were nine, all
   expected (below).
2. **No `parse_jira_config(undecided=)` and no `parse_work_config(withheld=)`.**
   The loader parses as today and then drops every parse problem whose key
   path is an undecided key or under one (spec 3.2), and puts the `Withheld`
   in `WorkConfig.tags` with `dataclasses.replace`. Same outcome, and the two
   parsers stay unaware of inheritance. The changelog says so rather than
   naming the keywords the plan proposed.
3. **Where a broken mark sits, and what clears it.** A problem marks the
   longest start of its key path that is a key in `known_keys()` under
   `work.tags` or `work.jira`; a later layer that replaces that key, or a key
   above it, whole clears the mark. "Later" compares `(position, layer)`, so
   a later layer of the same project counts too: an ancestor's local file
   fixing a bad credential name in its own shared file leaves nothing broken.
4. **A broken key that is also undecided gives no warning** (Design 1.6 treats
   it as undecided). A parse problem at an undecided key is dropped before it
   could mark anything; a problem found while checking a layer is kept off
   `inherited_problems` when the key is withheld as undecided.
5. **The gap a mapping's message names.** For `work.jira`, the earliest of the
   gaps its undecided keys name (choice 4's rule, key by key).
   `gaps_withholding` holds every gap at or after that one, so each finding
   for a gap that could have set the key gets the suffix.
6. **When the order cannot be had, for a project read for itself**, the
   withheld error is the error the registry raised, the loop's message, or
   that project's own link problem; never the command registry's
   `require_valid()` text, which describes the active project's graph. For
   the active project it is `require_valid()`'s text, as the plan says.
7. **A whole-file problem in an ancestor's `tcw-config.local.yaml`** marks
   `work.jira` broken in Jira mode and nothing otherwise, since only
   credential names can come from that file.
8. **The user-wide file applied at an ancestor** carries that ancestor's
   project and position, so it ranks correctly, but is never treated as
   another project's layer (choice 12); `tcw config show --origin` labels it
   `user: <path>`.
9. **TCW-107's lookup defers the problem of an unreadable target.** The plan
   built Design 1.6 in `_read_config`, but the lookup refused a manifest
   entry, or a search hit with a newer version, before `_read_config` saw the
   role. The answer now carries the problem unrecorded, with the folder; the
   walk places the project as unreadable in the `ancestor` and `outside`
   roles and records the problem everywhere else. `manifest_findings` skips
   an entry whose project the graph holds, at that folder, as an unreadable
   ancestor, so it is reported once (row d), as AC 15 requires.
10. **A file that is not valid YAML declares no ID the search can match**, so
    such a parent is found only through a manifest entry; AC 15's tests give
    one, which the spec's "as the layout makes obvious" allows.
11. **Spec defect, worked around in the test:** AC 23 writes
    `work.stages.spec.pre: [{blob: gate}]`, but a `pre` list takes only
    commands. The test uses `{command: gate}`; the criterion's point (a
    variable's mapping merges and keeps the `pre` binding) is unchanged.
12. **`tcw validate` in this repository and the records gate were not run.**
    Running the released 3.x CLI here was refused by the session's permission
    check (it reads the live Jira project). Instead the two ledgers were
    loaded with the worktree's library and checked locally: 310 findings, all
    the "TCW 3.x reference" ones TCW-116 converts, and none about the new or
    changed records.

## Tests changed by the fold

Only these, each for the design rule named:

- `tests/test_parent_links_cli.py`, the two AC 19 tests that compare the end
  of the finding: they gain `; could not check the configuration inherited
  from it` after the taxonomy suffix (Design 3.5, 3.6).
- `tests/test_manifest_cli.py::test_ac8_an_entry_that_is_wrong[True]`, its
  `newer` case: a parent whose shared file has a newer `tcw-version` is now a
  gap, one `unresolved` finding and exit 0, not a manifest error (Design 1.6).
- `tests/config/test_personal_merge.py::test_inherit_outside_a_chain_list_is_one_problem`
  uses `work.documentation`, since `work.tags` now takes the entry (Step 5).
- `tcw/store/config_edit.py`'s three new helpers renamed their parameter, which
  `tests/test_no_node.py` forbids naming `node`.

Every other test passed unchanged after the fold, including TCW-108's AC 31
and AC 20 tests, which check "contains".

## Mutation checks

Each was applied, run and reverted.

- Step 2: removing `read_override`'s early shared-key check left AC 21 green,
  because the allowlist walk refuses the same keys in the same words; the
  early check is a shortcut. Removing the sort by key parts turned AC 23's
  order test red.
- Step 3: the nine editor tests fail without `SetList(inherit=)`.
- Step 4: without the registry change, the unreadable-ancestor tests fail at
  `require_valid` with a graph problem.
- Step 5: without `_takes_inherit` and the `null` rule, the AC 7 and AC 8
  unit tests go red.
- Step 6: reverting `tcw/work/cli.py` turns the "no store opened" test red;
  reverting `validate_changes` turns the tag-read test red.
- Step 7: `_inherited_part` returning nothing turns 19 tests red (AC 1, 3-8,
  10-12, 16, 29, 33, the read-for-itself tests); the reasons read were the
  missing inherited value (no tags, `jira.site` absent, `email_env` not
  `CORE_EMAIL`). `Withheld` replaced by `()` for `work.tags` turns AC 13 and
  both AC 15 tests red, with exit 0 from `tags list` and exit 2 ("tag 't' is
  not registered") from `new --tag`. Removing the `parse_parents` trigger
  turns the unit test with a registry answering `[app]` red; the CLI test
  stays green because the registry records the refused `parents:` too.
  Reading the ID from the passed registry turns the own-ID test red.
  `reference_resolver` building the backend again turns the `lib` test red,
  with a false `unresolved` finding (not exit 7: the new `except` catches
  `InheritedUnavailable` as unresolved, so the folder answer is what the test
  guards). Skipping the "also undecided" rule turns its test red.
- Step 8: overrides read but never merged turns AC 11, 19, 22 and 23 red, and
  AC 20 and 21 stay green. The first AC 23 test used the words `one` and
  `whole`, which TCW's spec text holds, so it stayed green; its markers were
  made distinctive and it then went red. Putting variable problems into
  `personal=False` readings turns AC 28's second test red with a second
  error, on the `tcw://` link.
- Steps 9-11: `config show` ignoring withheld keys turns three AC 17 tests
  red; `tags add` without the `inherit` entry two AC 18 tests; `tags rm`
  refusing nothing the AC 18 child test; `/api/project` reading the tags
  directly the AC 32 summary test (500).

## Handoffs folded in

- TCW-110 had already made `resolve_work_input` take the active backend as a
  function; nothing more was needed.
- The plan's `tcw/refs.py:139` reference check now lives in
  `tcw/locate.py`, `Locator._read_work`; it uses `item_folders` there.

## Notes for the later children

For the dispatching session to post; each is what this item leaves for that
ticket.

- **TCW-99:** the spec's departures from the design: `work.backend` is not
  inherited; a variable's mapping merges; a project read for itself takes no
  personal file; the allowed list refuses the design's
  `TCW_WORK_JIRA_SITE__APP` and `TCW_WORK_PATH__MY_PROJ`; no collision check
  is built. AC 23's `pre: [{blob: gate}]` is not a valid `pre` list
  (decision 11).
- **TCW-112:** `source_entries(axis, project_id=None, *, root=None)` and
  `unavailable(project_id, gap_id, axis, *, subject=None, missing=None)` in
  `tcw/store/base.py` are the non-raising form of `sources` and the one
  builder of its messages; a `store_message=` keyword belongs on
  `unavailable`. The configuration's axis is `config`. `taxonomy.extends` and
  `capabilities.extends` are in `known_keys()` (marked with a comment) and
  come out when TCW-112 removes them. The loader reads only `work.tags` and
  `work.jira` from another project's file. An ancestor whose shared file
  cannot be read is unreadable in the `ancestor` and `outside` roles, the
  lookup defers its problem on the answer (`_Answer.unreadable`,
  `deferred`, `_settle`), and a descendant's stays a graph problem.
- **TCW-113:** a project read for itself is `load_config(root,
  personal=False, registry=<the command's registry>)`; without a registry,
  for a project with `parents:`, it raises `TypeError`. Its ID comes from
  `project_facts`, never from the registry's `current`. It applies the
  variables naming it and reports no variable problem. A gap in its sources
  is a `Withheld` in `Config.withheld`, which a scoped listing should turn
  into "unavailable" with the error's message, exit 0.
- **TCW-115:** `tcw project config` takes `tcw config show`'s rule
  (`tcw/config_cli.py`, `_show`): exit 7 for the first undecided key in
  `INHERITED_KEYS`' order, else exit 1 for a broken one, nothing printed.
  Each value's `Origin` carries `project`, `variable` and `position`;
  `Config.sources` gives the fold's order. `tcw project info` should show
  `work.backend` and `work.jira.project`, marking the latter inherited when
  its origin's `project` is another project's.
- **TCW-116:** report a 3.x configuration whose credential variable names
  start with `TCW_` and hold `__` (4.0 reads such a variable as an
  override), and a `null` at `work.tags` or `work.jira` in a 3.x file (it now
  removes an inherited value). This repository's two new capabilities and
  new taxonomy entry are in the 3.x form, like the rest.
- **TCW-117:** the documentation deferred to it, below.
- **TCW-118:** nothing beyond the release notes.

## Documentation entries

Evaluated with the plan's Step 13 table.

- **Written:** `docs/changelogs/upcoming/<folder>.md` and
  `docs/release-notes/upcoming/<folder>.md`, formatted with prettier.
- **Deferred to TCW-117**, which rewrites the user-facing documents for 4.0
  in one pass. What each must say:
  - `README.md`: a project takes its parents' `work.tags` and `work.jira`,
    never its backend; the override variables `TCW_<KEY>__<PROJECT>`, with
    one example.
  - `docs/guide/configuration.md` and `skills/configure/references/`: the
    inherited keys (`work.tags`, `work.jira` with every key under it); that
    `work.backend` is never inherited; mappings merge key by key, a list or
    value is replaced, `null` in a shared file removes an inherited value
    (and restores a default), and `inherit: true` is accepted in
    `work.tags`; the environment layer after `tcw-config.local.yaml`, the
    name rule with examples (`TCW_USER_NAME__APP`,
    `TCW_WORK_JIRA_CREDENTIALS_EMAIL_ENV__MY_PROJ`), values read by type, a
    variable's mapping merging, the more specific variable winning, and the
    allowed list (the personal keys; never `children` or a store location);
    `TCW_NO_PERSONAL_CONFIG=1` turning the variables off; exit 7 for a
    configuration setting and its two remedies, fetch the project or leave
    `config` out of that link.
  - `docs/guide/jira.md`: `work.jira` may come from a parent, key by key;
    `work.backend: jira` and the statuses are always the project's own; a
    credential name may come from a variable; a Jira-mode project whose
    `work.jira` could come from a missing parent cannot open its store
    (exit 7).
  - `docs/guide/multi-repo.md`: what a parent in another repository passes,
    and what happens in a clone without it (tags commands exit 7; the rest of
    a filesystem project works).
  - `skills/work/SKILL.md`: "On exit 7 naming a configuration setting
    (`work.tags`, `work.jira`), report which project it comes from and its two
    remedies, fetch the project or leave `config` out of that link; do not
    retry", and that `tcw work tags add` in a child writes `inherit: true`
    first.
  - `docs/use-cases.md`: S-5's "another project's personal file is never
    read" becomes "never read for a project read for itself; an ancestor's
    personal credential names reach its children"; UC-5 gains the inherited
    `work.jira` and the child's own `work.backend: jira`; UC-6 gains exit 7
    for an undecided setting; TCW-108 Design 6.1's "listing, reading and
    moving its own items still work" holds for a filesystem project, not for
    a Jira-mode project whose Jira settings come from a missing parent.

## Not done

- Plan Step 0's outcome comparison (`compare_outcomes.py` over junit records)
  and the assertion inventory were not built; instead the full suite was run
  after the fold, before any new test, and each of its nine failures was read
  and is listed above.
- `tcw validate` in this repository and `tcw work advance TCW-109 --dry-run`
  were not run (decision 12); the dispatching session should run them.
- AC 27's "no registry read" is checked by counting
  `FsProjectRegistry.open` calls, not TCW-107's `_read_text`.

## The web client

No file under `web/` or `tcw/serve/dist` changed (`git diff --stat 0287fc4e --
web tcw/serve/dist` is empty), so the web checks were not needed.

## The suite

At `ff3aba68`, from the worktree's root, with `-q -p no:cacheprovider`:

- `tests/work tests/serve`: 1915 passed, 2 skipped (202 s).
- `tests --ignore=tests/work --ignore=tests/serve`: 4190 passed, 111 skipped
  (338 s).

The baseline at `0287fc4e` was 1912 and 2, and 3987 and 111. The last commit
(`cdd6be20`) was followed by the config, validate and inherited-configuration
tests (369 passed, 11 skipped), not a second full run.
