# Plan: make a refused tcw work edit change nothing

## Tasks

1. **Store guard for `update_work`.** Tests first in
   `tests/test_store_editor.py`: criterion 6's three cases (self-block raises,
   new cycle raises, unchanged list of an item already in a cycle succeeds).
   Then in `tcw/store/base.py` extract `_check_new_blocker(slug, entry)` from
   `add_blocker` (same messages), and in `tcw/store/fs.py` `update_work` call it
   for each entry not already on the item. Proof: new tests red → green;
   `tests/test_store_editor.py` green.
2. **`check_blocker_edits`.** Add the non-writing store method to
   `tcw/store/base.py` (declared on the abstract `WorkStore` with a concrete
   default, like `add_blocker`). Tests in `tests/test_store_editor.py` for each
   refusal it mirrors, including `add=[A], blocks=[A]` and remove-then-add.
3. **`_edit` ordering.** Tests first in the CLI edit tests
   (`tests/cli/` file that covers `tcw work edit`, found by grepping
   `"edit"` + `--blocked-by`): criteria 1-5, each asserting byte-identical
   `state.yaml` for every item involved via one helper
   `_assert_unchanged(before, after)`. Then reorder `_edit` in
   `tcw/work/cli.py`. Proof: red → green; full suite green (criterion 7).

## Documentation Sync

- `docs/changelogs/upcoming.md` [Any-Code-Change] — `### Fixed`: edit
  refusals write nothing; `update_work` refuses new self-blocks/cycles.
- `docs/release-notes/upcoming.md` [Public-API] — two plain lines: a refused
  `tcw work edit` changes nothing; the web app refuses a blocker that would make
  an item wait on itself.
- `skills/work/SKILL.md` and its references [Skill-Driven-Component] — check
  whether any text describes edit's partial-write behaviour; update if so.
- README, guides, configure references: expected not to fire; re-checked on the
  finished diff.

## Verification

Hands-on in a scratch repository with the worktree's `tcw`: run criteria 1-3 and
`git status --porcelain` / `git diff` after each to confirm nothing changed; then
a web-style save via `tcw serve` is not needed — the store test covers the
PATCH path, which calls `update_work` directly.
