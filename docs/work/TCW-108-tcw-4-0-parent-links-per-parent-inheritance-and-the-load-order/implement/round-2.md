# Implement round 2 — TCW-108

Built on the `v4` branch in the worktree `.claude/worktrees/v4`, with the code
under test run from its own virtual environment (`.venv/bin/pytest`). No hand
run of `.venv/bin/tcw` was needed. The lifecycle was not driven by any CLI:
the dispatching session makes every move. This round answers review round 1,
which was rejected with two findings belonging to this change. It gives no
verdict.

## What was done for each review item

- **(a) AC 35 and AC 36 in the `upcoming/` entries** (`573b109d`). The
  wording was checked against `tcw/store/project.py`
  (`FsProjectRegistry._search_conflict` and `_not_here`).
  - `docs/changelogs/upcoming/TCW-108-…md`, under "Changed": one line naming
    `_search_conflict` and `_recheck_search_answers` (the search finding a
    project in one folder while a manifest the lookup consults places it in
    another is a graph problem, exit 1, naming both folders and saying to add
    an entry to `.tcw/tcw-manifest.local.yaml` in the asking project), and
    one naming `_not_here` ("not on this machine" for a manifest entry names
    the full folder it was resolved to, `<manifest> places it at <folder>`;
    in a linked git worktree, the folder beside the main checkout).
  - `docs/release-notes/upcoming/TCW-108-…md`, under "A project that is not
    here": two paragraphs saying the same to a user, with an example entry
    (`lib: ../lib`) for the personal manifest.
- **(b) AC 9's command-line assertion** (`11b0633b`).
  `test_ac9_a_siblings_extends_is_read_from_its_own_load_order` in
  `tests/test_parent_links_cli.py` now asserts
  `"full-id: b.taxonomy/t" in shown.out` in place of `"t" in shown.out`.
- **(c)** This file.

## Checks run

- The changed test alone:
  `.venv/bin/pytest -q -p no:cacheprovider tests/test_parent_links_cli.py -k test_ac9_a_siblings`
  — `2 passed, 67 deselected`.
- Mutation: `tcw/taxonomy/cli.py:77` was changed by hand to print
  `full-id: a.taxonomy/t` whatever the term. The test went red at its new
  assertion, for the expected reason:
  `assert (0 == 0 and 'full-id: b.taxonomy/t' in 'full-id: a.taxonomy/t\nowner: b\nname: t\nkind: Vocabulary\n')`.
  The old assertion, `"t" in shown.out`, would have passed that output. The
  file was restored with `git checkout` (`git diff --stat tcw` empty) and the
  test passed again, `2 passed, 67 deselected`.
- The item's main test files:
  `.venv/bin/pytest -q -p no:cacheprovider tests/test_parent_links_cli.py tests/test_parent_links.py tests/test_parent_links_static.py tests/test_documented_cli_surface.py`
  — `570 passed`.

## The suite

`.venv/bin/pytest -q -p no:cacheprovider`, run in full as CI runs it by the
dispatching session at `6d25a69d` (2026-10-23), in two halves by folder:
`1912 passed, 2 skipped` (`tests/work`, `tests/serve`) and `3987 passed,
111 skipped` (the rest), `5899 passed, 113 skipped` in all. `pnpm test`
`190 passed`; `tsc --noEmit`, `pnpm lint` and `pnpm check:build` clean.
