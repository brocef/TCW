# Refined outcome — Fix `tcw work new` hanging on inherited stdin

**Accepted.** The user approved closeout on 2026-08-19, after being told the
rework's stated justification had been disproved and choosing to keep the change
on the corrected one.

## The decision

Accepted after one rework. The original hang is real and fixed. The rework —
closing stdin on every `subprocess` spawn — was authorised on a premise that
turned out to be false, and the user was asked again before it was kept.

## Evidence

- **The reported hang, measured.** Three arms with a per-call timeout: `tcw work
  new` with a held-open pipe as stdin blocked indefinitely before, and completes
  promptly after. The first probe measured nothing — it used `tcw work init`
  without `--id`, giving rc=1 in all three arms, the same trap the original
  report fell into — and was redone as `tcw init --id … work`.
- **All five intake entry points** share one implementation (`tcw/stdin.py`) and
  are pinned by `tests/test_stdin.py` (22, real descriptors — pipe, devnull,
  regular file, socketpair, closed fd) and `tests/test_stdin_cli.py` (9, shelling
  out, because a parent holding a pipe's write end open is not reproducible
  in-process).
- **The three-outcome rule** — EOF returns, a gap with no bytes proceeds with a
  note, a gap with partial bytes raises `StdinTruncated` — came from a codex
  finding reproduced as `('first', 'EXPIRED')`: an earlier gate made truncation
  **silent**, which is worse than the bug.
- **The guard test paid for itself.** `tests/test_subprocess_stdin.py` walks the
  AST of every module under `tcw/` and fails any spawn without an explicit
  `stdin=`. It found three `tcw serve` spawns neither review had looked at, one
  of them a genuine defect: `serve/runtime.py:169`'s long-running node server
  inherited fd 0 and competed with the supervising `tcw serve` for the terminal.
- Full suite green at closeout.

## Two false premises in this item

Both recorded rather than quietly corrected, because they are the item's most
useful output.

1. **The spec claimed "a hook steals the piped intake out from under `work
   new`".** `_new` runs no hooks at all. Corrected at `2d7768f`.
2. **The rework claimed a `pre-commit` hook reading stdin blocks a transition
   forever.** Executed with no TCW involved — a hook running `cat`, `git commit`
   handed a held-open pipe:

   ```
   git commit: rc=0 in 0.14s
     hook said: HOOK: drained fd0 and reached EOF
   ```

   **Git closes its hooks' stdin.** A TCW-level probe agreed: `tcw work start`
   completed in 0.28s **both before and after** the fix.

So the 21 git changes close **no known hang**. What they buy is explicitness
enforced by a test, which is a smaller and honest claim, and it is the claim the
user accepted. Goal 1 in `spec.md`, the `_git()` docstring, the changelog entry
and `outcome.md` were all rewritten to say that rather than the original story.

## Capability ledger

Reconciled: `tcw capabilities drift` reports **no capability drift**. The intake
capability's stdin behavior was recorded during implementation (`766e8af`).

## Closeout choices

- **Merge route:** none needed — all work landed directly on `main`.
- **Documentation:** `docs/release-notes/upcoming.md` and
  `docs/changelogs/upcoming.md` both carry entries; the changelog's "known gap,
  deliberately out of scope" bullet was replaced once the rework closed it, and
  the replacement states plainly that no known hang was fixed.
- **Version:** folded into the unpushed **v1.0.0**. Gate re-run immediately
  before: `STATUS: FOLDABLE`, exit 0.
- **Follow-up:** none filed. Timeouts on git subprocesses stay out of scope —
  nothing has been observed to hang, a speculative item is backlog weight, and
  the fix now has one obvious home (`_git()`) if it is ever seen.

## Notes

`bllm-review` produced nothing during this item: it waited 1440s on a workload
lock and exited **0** with no review. Filed to `/Users/brian/llama/docs/work/inbox/`
per the user's standing instruction — an exit code of 0 for "never ran" is
indistinguishable from "clean" to any caller that gates on it. The root cause was
found later the same release and filed separately: `llama-server` inherits the
lock file descriptor and never releases it. That is an fd-inheritance bug, the
same class this item was fixing.
