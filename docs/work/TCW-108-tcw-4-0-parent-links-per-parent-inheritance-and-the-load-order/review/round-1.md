---
verdict: rejected
judges: 1
---

# Review round 1 — TCW-108

Reviewed by a separate read-only agent (the `tcw:reviewer` agent) on
2026-10-23 in a frozen worktree at `87729a98`, over `3e6868fc..d908bb79`.
The dispatching session checked both findings against the repository before
writing this round.

The reviewer recommended accepting, with two small findings that belong to
this change. The user's rule for the TCW-99 children is that an item is
accepted only when the review finds no open finding belonging to the change,
so this round is recorded as rejected and both go back to implement.

## Checks run

- The full suite as CI runs it, `.venv/bin/pytest -q -p no:cacheprovider`,
  run by the dispatching session on `v4` at `e5c7ebee` (this item with
  TCW-110's last round on top), in two halves by folder: `1912 passed,
  2 skipped` and `3987 passed, 111 skipped`, `5899 passed, 113 skipped` in
  all, the same as implement's run at `393d2b54`. `pnpm test` `190 passed`;
  `tsc --noEmit`, `pnpm lint`, `pnpm check:build` clean; the end-to-end
  suite `15 passed`.
- By the reviewer: the item's main test files, `329 passed, 2 skipped`;
  `tests/work/test_errors.py` and `tests/serve`, `377 passed`.
- Three mutations in a scratch copy, each turning its test red: removing the
  `parents` skip in `_list_problems` (ten tests in
  `tests/test_parent_links_cli.py`), a records gate refusing every project
  `declared_child_ids()` does not list (`test_ac32_*`, so AC 32's test has
  force), and removing the nested-repository guard in `_worktree_copy`.
- By hand: AC 35 through the CLI (exit 1 naming both folders and
  `.tcw/tcw-manifest.local.yaml`; exit 0 with the personal entry), AC 32's
  two dry runs, AC 9's sibling read.
- `documentation-sync`: both `upcoming/` entries are present; the guides,
  `docs/use-cases.md`, README, the configure reference and the three skill
  passages are deferred to TCW-117 as the spec's non-goals allow, with the
  text each needs in implement round 1's notes.

## The dispatching session's questions

- `tests/test_config_edit_writers.py`: the indentation went from four spaces
  to two, and the writer did not change; the new fixture holds only a list,
  for which the writer uses two. Not a test bent to fit.
- `tests/test_worktree_sibling_nodes.py`'s `config` helper: no remaining
  caller passes an absolute path.
- The `_list_problems` fix is covered (the first mutation).
- The two dated spec decisions and AC 36's full folder agree with the
  Design and with TCW-107's messages.
- No decision of the implementing agent contradicts the spec.
- No git call was added under `tcw/`; no private name is in the change.

## Acceptance criteria

All 36 are met; AC 34 is the suite above. AC 9's CLI assertion is weak
(finding 2). AC 18's registry test uses a different layout from the spec's,
and the CLI test uses the spec's layout, which is enough.

All 14 changed or new capability paths and the five taxonomy entries were
changed in the range and say what the code does.

## Findings

1. The changelog and release-notes entries do not mention AC 35 or AC 36. A
   person whose parent's manifest places a project somewhere other than the
   folder the search finds now gets exit 1 from every command, and nothing in
   the notes says why or what to write in `.tcw/tcw-manifest.local.yaml`.
2. `tests/test_parent_links_cli.py:636` asserts `"t" in shown.out`, which
   almost any output passes.

## What implement must do

- (a) One line in each `upcoming/` entry for AC 35 (a manifest that places a
  project away from where the search finds it is an error, fixed by a
  personal entry) and AC 36 ("not on this machine" names the folder
  checked).
- (b) Assert the term's full identifier, `full-id: b.taxonomy/t`, in AC 9's
  CLI test.
- (c) `implement/round-2.md`.
