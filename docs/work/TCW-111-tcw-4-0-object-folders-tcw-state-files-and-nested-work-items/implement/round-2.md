# Implement round 2 — TCW-111

Made on `v4` in the worktree `.claude/worktrees/v4`, with the code under test
run from that worktree's own virtual environment (`.venv/bin/pytest`). No
lifecycle command was run: the dispatching session makes every move. This
round answers review round 1, which asked for (a), (b) and (c) under "What
implement must do". It gives no verdict.

## What was done, item by item

- **(a) "exit 1." on one line.** The changelog entry for `left_out` is
  rewrapped so that "exit 1. (TCW-111)" starts its line and no line starts
  with "1.". Both upcoming entries, the changelog and the release note, were
  searched for any other line beginning with a number and a full stop; there
  is none (line 78 of the changelog starts "3.x names", which is not a list
  marker).
  - Check: `grep -nE '^\s*[0-9]+\. '` over both entry files. Result: no lines.
- **(b) The 3.x removal refusal names the removal.** `_blocked_removal`
  (`tcw/store/fs.py`) builds both of its refusals itself from the `id_path`
  it is given, and the nested-state-file one already began
  `cannot remove '<id-path>': `; the 3.x one now begins the same way, in the
  same function, so the prefix is added in one place and never doubled. It
  reads, as spec 2.5 gives:
  `cannot remove '<id-path>': <path> holds a TCW 3.x <file>; run 'tcw migrate'
  in this project first`. `_blocked_removal` is the one route for both
  `tcw taxonomy rm` and `tcw capabilities rm`.
  - `tests/test_removal_blockers.py`: the term test now asserts the whole of
    standard error, `tcw taxonomy rm: cannot remove 'invoice': invoice/old
    holds a TCW 3.x meta.yaml; run 'tcw migrate' in this project first`; a
    new test does the same for a capability with a 3.x `item.yaml` below it
    (`tcw capabilities rm: cannot remove 'cli/x': cli/x/old holds a TCW 3.x
    item.yaml; …`). Both compare the full text with `==`, so a doubled prefix
    would fail them too, and both check that the tree is unchanged.
  - Mutation check: with the prefix removed from the 3.x refusal, both tests
    failed (2 failed, 4 passed); restored, all 6 passed.
- **(c)** This document.

## Checks run

- `.venv/bin/pytest -q tests/test_removal_blockers.py`. Result: 6 passed.
- `.venv/bin/pytest -q tests/test_removal_blockers.py
  tests/test_capabilities_rm.py tests/test_taxonomy.py
  tests/test_taxonomy_rm_gaps.py tests/test_taxonomy_cli_contract.py
  tests/test_partial_removal.py tests/test_object_folder_shape.py
  tests/test_object_folders.py tests/work/test_nested_items.py` (the removal
  tests, and the files that hold the text "holds a TCW 3.x", which are
  `validate` findings and were not changed). Result: 224 passed, 1 skipped.

## The suite

`.venv/bin/pytest -q -p no:cacheprovider`, run in full as CI runs it by the
dispatching session at `ec858dd6` (2026-10-24), in two halves by folder:
`1982 passed, 2 skipped` (`tests/work`, `tests/serve`) and `4126 passed,
111 skipped` (the rest). `pnpm test` `191 passed`; `tsc --noEmit`,
`pnpm lint` and `pnpm check:build` clean.
