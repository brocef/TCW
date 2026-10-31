# Implement round 3 — TCW-110

Answers review round 2 (rejected at `c06881ad`). Built on the `v4` branch in
the worktree `.claude/worktrees/v4`, with the code under test run from its own
virtual environment (`.venv/bin/pytest`, `.venv/bin/tcw`), and scratch runs of
`.venv/bin/tcw` given their own `HOME`, `XDG_CONFIG_HOME` and
`XDG_CACHE_HOME`. It gives no verdict.

## What was done, for each item the review asked for

- **(a) `init`'s refusal of an absolute or `~` path.** `store_location_problem`
  (`tcw/config.py`) takes a new argument, `address`, true by default. With it
  false, the message leaves out the "or a tcw:// .path address" clause and is
  otherwise the same text, built from the same lines. `run_init`
  (`tcw/cli.py`) and the store layer's `init` (`tcw/store/fs.py`) pass
  `address=False` for a path given on the command line, since `init` refuses
  a `tcw:` value there. A location read from `.tcw/tcw-config.yaml` keeps the
  full message, in `init` too, and so do `tcw validate` and every other
  reader. Checked by hand in a scratch project:
    - `tcw init --id rr --work-path /tmp/x work` (exit 2):
      `tcw init: work.path must be a path relative to the project; a folder that sits elsewhere on this machine is placed by an entry in .tcw/tcw-manifest.local.yaml`
    - `tcw init --id rr --capabilities-path '~/x' capabilities` (exit 2): the
      same, for `capabilities.path`.

    Test: `test_ac24_init_refuses_an_absolute_or_home_location_and_writes_nothing`
    (`tests/test_store_addresses.py`) asserted the old text, `tcw://`
    included, and now asserts that the message does not hold `tcw://` and
    still names the local manifest. It gains `--capabilities-path`, so it runs
    all three options with `/abs/store` and `~/store`.
    `test_ac24_an_absolute_or_home_location_stops_every_command`, beside it,
    still asserts that `tcw work list` and `tcw validate` offer the address.

- **(b) The address form of a folder that breaks the rule.** In `sort_input`
  (`tcw/ids.py`), a `MalformedId` from `parse_address` now gets the Design 1.6
  rename by hand when the address is an object address, `tcw://<project>.<namespace>/<id-path>`
  with a valid project ID and namespace, whose id-path has a part that a
  folder could be named but an id-part cannot (`_address_rename`, which uses
  the same `_breaks_part_rule` as the other forms). An empty part (`//`) gets
  the rule alone, as before. Checked by hand with a `cli/has.dot` folder on
  disk: `tcw capabilities show` and `rm` of
  `tcw://demo.capabilities/cli/has.dot` print the same message, exit 2, as
  `show demo.capabilities/cli/has.dot`:
  `'demo.capabilities/cli/has.dot' is not a full identifier: the id-part 'has.dot' breaks the rule: letters, digits, '-' and '_', starting with a letter or digit, at most 128 characters; no command can be given a folder whose name breaks that rule: rename it by hand`

    Tests: `test_input_naming_a_folder_that_breaks_the_rule_says_to_rename_it`
    (`tests/test_ids.py`) gains the address of a capability, a term and a work
    item, and a term's address given where a capability is expected;
    `test_a_typing_slip_is_not_called_a_folder_to_rename` gains
    `tcw://demo.work/x//y`. `test_ac18_a_hand_made_folder_breaking_the_rule_is_listed_and_reported`
    (`tests/test_tree_full_identifiers.py`) now also runs `show`, `set` and `rm`
    of the capability's address and `show` and `rm` of the term's address, and
    asserts exit 2, the rule and the rename.

- **(c) The namespace in the `AmbiguousRef` message.** `AmbiguousRef`
  (`tcw/store/base.py`) takes the namespace, and its two raisers in
  `tcw/store/fs.py` pass `taxonomy` and `capabilities`. The message now ends,
  for example, `name it by its full identifier, <project>.capabilities/auth/login`;
  `<project>` stays a placeholder, since the user chooses which project.
  Tests: `test_cli_rm_ambiguous` (`tests/test_capabilities_rm.py`) asserts
  `<project>.capabilities/auth/login`; `test_resolution_ambiguous_errors`
  (`tests/test_taxonomy.py`) asserts the message ends `<project>.taxonomy/Term`.

- **The capability records.** None quotes these messages. The three
  store-location records say that an absolute or `~` path is refused and that
  the refusal names the local manifest, which stays true of both messages;
  the two read records say only that the ambiguity advice is to write the
  full identifier.

## Mutation checks

Each change was put back to `HEAD` with the new tests in place:

- (a) `6 failed, 35 passed` in `tests/test_store_addresses.py` (the six init
  cases, each finding `tcw://` in the message); with the change, `41 passed`.
- (b) `5 failed, 117 passed` in `tests/test_ids.py` and
  `tests/test_tree_full_identifiers.py` (the four address cases and the AC 18
  test); with the change, `122 passed`.
- (c) With `base.py` and its two raisers put back, `2 failed, 113 passed, 1
  skipped` in `tests/test_capabilities_rm.py` and `tests/test_taxonomy.py`,
  each showing the literal `<project>.<namespace>/`; with the change,
  `115 passed, 1 skipped`.

## Checks run

- `tests/test_ids.py`, `tests/test_tree_full_identifiers.py`,
  `tests/test_capabilities_rm.py`, `tests/test_init_configured_tree_path.py`,
  `tests/test_documented_cli_surface.py`, `tests/test_config_edit_writers.py`,
  `tests/test_config_edit.py`, `tests/test_configuration_text_home.py`,
  `tests/test_store_addresses.py`, `tests/test_taxonomy.py`:
  `973 passed, 6 skipped in 26.80s`.
- `tests/work/test_init_provision.py`: `7 passed in 0.79s`.
- `tests/test_capabilities.py`, `tests/test_capabilities_federation.py`,
  `tests/test_capabilities_reset.py`, `tests/test_capability_ref_wording.py`,
  `tests/test_validate.py`, `tests/test_cli_contract.py`:
  `249 passed, 20 skipped in 37.20s`.

## Not done

- The full suite is the dispatching session's to run.

## The suite

`.venv/bin/pytest -q -p no:cacheprovider`, run in full as CI runs it, at `d04642af`
(2026-10-23): `5759 passed, 114 skipped in 516.12s`.
