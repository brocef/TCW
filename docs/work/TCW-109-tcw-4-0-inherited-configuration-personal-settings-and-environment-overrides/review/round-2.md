---
verdict: rejected
judges: 2
---

# Review round 2 — TCW-109

Reviewed by a separate read-only agent (the `tcw:reviewer` agent) on
2026-10-24 in a frozen worktree at `61344857`, against review round 1's
items (a) to (d) and the change in `f798612e..61344857`. Round 1's results
for the acceptance criteria are carried forward. The dispatching session
checked the findings against the code before writing this round.

## Checks run

- The full suite, run by the implementer at `e604c39a` in two halves:
  `1915 passed, 2 skipped` and `4209 passed, 111 skipped`.
- By the reviewer: the item's eight test files, `473 passed, 3 skipped`;
  `tests/work/jira`, `729 passed, 2 skipped`.
- By hand, nine scratch projects with every `TCW_*` variable unset.

## Round 1's items

- (a) Met for the active project: round 1's scenario now exits 1 with the
  `timeout` and `email-env` errors and no "required"; an undecided key stays
  hidden; a parent after the gap with bad decided keys gets two warnings at
  its file; the same parent before the gap gets none. Not met for an
  ancestor's unknown key (finding 1).
- (b) Met. With two variables set, only the bad one is reported, starting
  with its name.
- (c) Partly met (finding 2).
- (d) Accurate, apart from the points below.

The implementer's decision to check a credential name when the other is
missing is allowed by Design 3.2 and stated in the changelog; no test or
record describes the old behaviour. The decision on unknown keys is sound,
apart from finding 3.

## Findings

1. `tcw/config.py:1269`: `_withhold` asks `fold.unknown(path)` with the
   mark's path, which `_broken_key` (`:1079`) cut to the longest known key,
   so `work.jira.bogus` becomes `work.jira` and `priorities.bogus` becomes
   `priorities`; neither was replaced whole, so the warning is dropped. A
   parent after the missing one that passes `jira: {bogus: 1, priorities:
   {bogus: x}}` gives no warning, though with no parent missing it gives
   both. The problem's own key path has to be kept with the mark (a
   variable's problem has `key_path=()`).
2. The release notes (line 56) say a variable that "holds a value that
   setting cannot take" stops commands in any project. A binding's shape is
   checked only when its project is loaded: `TCW_WORK_STAGES_SPEC_PROMPT__B=[1]`
   stops commands in `b` but not in `a`. The changelog's line 73 ("a warning
   at the parent's file when a parent does") is wrong in finding 1's case.
3. `tcw/config.py:1214`: an unknown key set to `{}` behind a gap is not
   reported, because `_replacements` records nothing for an empty mapping;
   with no gap it is.

## What implement must do

- (a) Keep the problem's own key path with each mark and decide "unknown" by
  it, with a test for finding 1's case.
- (b) Report an unknown key whose value is `{}` behind a gap, with a test.
- (c) Make the release notes say which value problems stop commands in any
  project, and correct the changelog line.
- (d) `implement/round-3.md`.
