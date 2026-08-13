# Outcome — Roll back or reorder the pre-move set_field writes on a lost transition

Reordered, not rolled back. Four commits, one per plan task; suite green at each.

## What shipped

### Task 1 — Field writes ride the transition (`d36941c`)

- `WorkStore.transition` and the abstract `_effect_transition` take
  `fields: dict | None = None`. `transition` merges its `owner`/`started`
  blanking over the caller's fields (`update`, not `setdefault`) and writes
  nothing before the move; `complete` passes `{"resolution": …}` on both routes,
  including the `from_backlog_epic` direct `_effect_transition`.
- `FsWorkStore._set_fields_at(dir, fields)` is the new one-write primitive;
  `set_field` is a one-line face over it.
- `FsWorkStore._effect_transition` applies the fields at `dst` after `_mv` and
  before `_commit_transition`, wrapped so a refused `git add` raises
  `TransitionCommitError` instead of an unhandled `CalledProcessError`.
- `start`'s take-over branch writes `owner`/`started` through one
  `_set_fields_at` so a move between them cannot tear the pair.
- Tests: `test_lost_complete_leaves_its_resolution_written` inverted in place;
  new `test_lost_submit_leaves_the_claim_intact`,
  `test_a_transition_that_wins_still_writes_its_fields`,
  `test_the_transition_commit_carries_the_field_write`,
  `test_a_refused_stage_after_the_move_is_a_transition_commit_error`.

### Task 2 — Comments the reorder falsified (`5079d40`)

The lost-race message now says "This process changed nothing";
`_status_resolution_problems`' docstring names the three ways a disagreement can
still arrive instead of claiming none can; both `pre`-hook comments in
`tcw/work/cli.py` and `git_mv`'s `-f` justification stopped citing a pre-move
staging that no longer happens. `test_a_failing_pre_hook_writes_no_field` passes
unmodified, as the spec required.

### Task 3 — Read-backs that lose the race (`9f68a34`)

`_require_detail` at all five sites (`create_work`, `update_work` ×2,
`update_term`, `update_capability`). Eight tests: five store-level, one for
`FsWorkStore.create`'s `.item` dereference, one for `tcw work new` (exit 1,
slug in the message, no traceback), one for `POST /api/work` (422, not 500).

### Task 4 — Documentation Sync (`becb070`)

Both predicted triggers fired and were answered: `docs/changelogs/upcoming.md`
and `docs/release-notes/upcoming.md`. `README.md` and `skills/tcw-work/SKILL.md`
did not fire — no command, flag, lifecycle, or guardrail changed. Re-evaluated
against the finished diff, not the prediction.

## Tests

`pytest -q` — **1294 passed**, from 1285 before (9 net new). No test was deleted
and none was weakened; the one inverted test asserts the opposite of what it did,
which is what its own docstring asked for.

`tcw validate` on this repository: OK. Working tree clean after every transition
commit, including this item's own `start`.

## What the plan and spec got wrong

1. **The take-over fix was not "one line for free."** The spec called
   `_set_fields_at` on the take-over branch a freebie. It also breaks
   `test_takeover_lost_at_the_commit_lookup_is_a_valueerror`, which hooks
   `set_field` and keys on `key == "started"` — a hook that never fires once the
   pair is written in one call. Rewritten to patch `_set_fields_at`; the test
   still pins the same thing. One line plus a test hook, not one line.
2. **Acceptance criterion 4's `git show HEAD:<path>` needed a committed
   baseline.** `_repo`/`init` leave the node uncommitted, so the test has to make
   an initial commit before the transition or `git show HEAD:` has no HEAD to
   read. Handled in the test; the criterion is unchanged.
3. Everything else the review verified held: the hook ordering, the commit
   inclusion at both tracked and gitignored destinations, and `FsWorkStore.start`
   being genuinely out of scope.

## Notes

- The targeted review (Claude + Codex + local LLM) ran between `plan` and
  `implement` at the user's request. Ten findings were accepted into the
  artifacts before any code was written — the load-bearing ones being the
  post-move `git add` failure mode (now `TransitionCommitError`, criterion 10)
  and `_require_detail`'s message being false at one of its five sites. One
  finding was refuted by the reviewer itself (ignored paths do not appear in
  `git status --porcelain`, so the gitignored-destination write breaks nothing).
- No behavior here is proven against a real race; every test forces the
  interleaving with `monkeypatch`, as the spec's Risks section says. A green
  suite means the handlers are right, not that the race was reproduced.
