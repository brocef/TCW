---
verdict: accepted
judges: 2
---

# Review round 2 — TCW-114

Reviewed by a separate read-only agent (the `tcw:reviewer` agent) on
2026-10-24 in a frozen worktree at `390b4b35`, against review round 1's
items (a) to (c) and the change in `0e36adb9..390b4b35`. Round 1 checked
every acceptance criterion; its results are carried forward.

## Checks run

- The full suite as CI runs it, run by the dispatching session at `76f053fc`
  in two halves by folder: `2068 passed, 2 skipped` and `4750 passed,
  111 skipped`, recorded in `implement/round-2.md`. `pnpm test`
  `198 passed`; `tsc --noEmit`, `pnpm lint`, `pnpm check:build` clean.
- By the reviewer: `tests/serve/test_work_write.py` and
  `tests/test_procedure_config.py`, `56 passed`;
  `tests/work/jira/test_jira_recorded.py`, `23 passed`. The four new tests
  fail with `0e36adb9`'s `tcw/serve/work.py`, each because a `wrote` or
  `created` line came back as a warning.
- By hand under `tcw serve`, through the guarded wrapper: a files-mode
  priority edit answers 200 and a plain create 201, neither with warnings; a
  nested create under another project's parent answers only the "does not
  check" and `not nested` warnings; the `created` and `wrote` lines go to the
  server's standard error. In Jira mode with the suite's stand-in, a create
  with another project's blocker answers the recorded-reference sentence
  with `where: blocked-by` and nothing else.

## Round 1's items

- (a) Met. Only the lines naming a parent or a blocker are answered as
  warnings. The `not nested` note goes beyond the sentence Design 3.3 names;
  the spec does not forbid it, it is the only way the person learns the
  nesting asked for was not done, and implement round 2 records it as the
  implementing agent's decision. The changelog line matches the code.
- (b) Met. `tcw/work/config.py:77-78` names `tcw -C <folder> work new
  "<title>" --parent <full id>`, `tests/test_procedure_config.py:60` checks
  it, and nothing repeats the old message.
- (c) Met. One wording slip: round 2 says the message is the wording
  `skills/work/SKILL.md` uses, where the skill writes the shorter
  `tcw -C <folder> work new --parent`; the meaning is the same.

No finding belongs to this change.

## Needs a separate change

Round 1's three follow-ups stand. Also kept on the 4.0 run's list, decided
by the dispatching session: a recorded-reference warning can show an
absolute path to the state file when that file is outside the server's
current folder (the `shown()` helper, older than this round).
