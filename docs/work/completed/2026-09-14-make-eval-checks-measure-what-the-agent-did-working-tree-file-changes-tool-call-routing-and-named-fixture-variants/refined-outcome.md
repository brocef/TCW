# Refined outcome — Make eval checks measure what the agent did

## Decision

**Accepted.** On 2026-09-14 the requester handed acceptance of this item to the
coordinating agent. Approval means two things:
- a multi review (an adversarial code reviewer, Codex and the local model
  `bllm`) finds nothing real left that belongs to this change;
- the full test suite passes.

No human reviewed the item. Both conditions were met after two review rounds.

## Evidence

- **Full suite.** Bare `pytest` in the worktree at `be821183` gave **2841
  passed**, in 15 minutes 16 seconds.
- **After merging into `main`** (merge commit `ba84a70f`), the five eval test
  files gave 89 passed.
- **Acceptance criteria.**
  - ACs 1–5 are covered by tests in `tests/test_eval_files_changed.py`,
    `tests/test_eval_grading.py`, `tests/test_eval_runner.py` and
    `tests/test_eval_fixture.py`.
  - AC 6: the axis B `--dry-run` output is byte-identical before and after
    (`outcome.md`).
  - AC 7: the suite result above.
- **Mutation checks.** In round 2 the adversarial reviewer reverted each fix in a
  copy of the code outside the worktree, and confirmed that the matching test went
  red for the stated reason. The developer did the same for the original tests
  (`outcome.md`).

## Review round 1 (the diff `fe735d94..b8ef8ab9`)

**Adversarial code reviewer: NOT DONE.**
- *Accepted:* Python bytecode caches (`__pycache__/`, `.pytest_cache/`) counted
  as changes the agent made. The reviewer reproduced this in a seeded fixture.
- *Accepted:* a bare fixture case under a TCW project was refused only partway
  through a paid run.
- *Accepted:* re-seeding into a folder that had already been used silently
  produced a fixture that was not bare.
- *Accepted, though the reviewer filed it as separate:* the grading machine's
  global git ignore file changed the answer. It is one line in this change's own
  new call, so it was fixed here.
- *Moved to the inbox note:* `run_one` never writes `items` to `timing.json`.
  This predates the change and is outside the spec.
- *Moved to the inbox note:* whether `claude -p` writes into the fixture needs a
  paid run to answer.

**Codex (read-only sandbox confirmed from the session header; worktree unchanged
after the run): NOT DONE.**
- *Accepted:* a carriage return in a file name became a newline, because git's
  output was read as text.
- *Accepted:* the same missing up-front check for bare cases.
- Its other answers were "no defect", or submodules and B10's prompt, which are
  separate.

**`bllm`, three slices:**
- *Rejected:* "`git diff <commit>` misses unstaged edits". It compares the commit
  with the working tree, and a test proves it.
- *Rejected:* "the missing-`seeded_head` test passes against the old code". The
  old check sees the committed fix and passes, where the test expects a failure.
- *Narrowed, no fix:* a search text with a backslash or a quote doesn't match the
  JSON-escaped tool input. The cases search for POSIX paths.
- *Rejected:* an empty `text` passes `tool_input_contains`. The existing
  `transcript_*` checks behave the same way.
- *Rejected:* a crash on an event whose `message` is a string. The existing
  `_texts` reader has the same shape, and `stream-json` events carry a dictionary
  there.
- The seeder and runner slice had no defects.

Fixes: `7aa8ba3e`. Documentation and records: `a7546294`, `882e43a0`, `be821183`.

## Review round 2 (the fixes, `b8ef8ab9..be821183`)

- **Adversarial code reviewer: DONE.**
  - It re-ran both live experiments and confirmed that each fix closes its
    finding.
  - It found no regressions when seeding into a new or empty folder.
  - Each new test fails when its fix is reverted.
- **Codex (read-only confirmed; worktree unchanged): DONE.** It found no defects
  in the five fixes. One test, the valid-input companion to the bare check, passes
  with its fix reverted, which is what a companion test should do.
- **`bllm`: no answer.** It reported "temporarily disabled for maintenance", so
  round 2 rests on the other two reviewers and the suite.

## Deferred follow-ups

All are in `docs/work/inbox/2026-09-14-eval-runs-under-this-checkout-grade-and-behave-wrongly.md`:
- items 1–4, found by the developer's own review;
- items 5–6 from round 1;
- item 7 from round 2: reusing an `--out` folder can still stop a paid run
  partway, because only bare arms are checked up front.

The real `stream-json` tool-call shape is still unconfirmed. The note on
`2026-09-11-run-the-eval-harness-and-act-on-what-it-finds` says so.

## Closeout

- **Capability ledger:** no deltas. The spec's Capability changes section is
  "None", and there is no `capabilities.yaml`.
- **No GitHub issue** is attached.
- **Version:** this ships in the next patch release, which is cut after
  `2026-09-14-delete-a-capability-with-tcw-capabilities-rm` merges.
