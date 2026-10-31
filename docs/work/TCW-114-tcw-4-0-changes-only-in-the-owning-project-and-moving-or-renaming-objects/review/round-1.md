---
verdict: rejected
judges: 1
---

# Review round 1 — TCW-114

Reviewed by a separate read-only agent (the `tcw:reviewer` agent) on
2026-10-24 in a frozen worktree at `78c88809`, over `bab05f37..78c88809`.
The dispatching session checked both findings against the code before
writing this round.

## Checks run

- The full suite as CI runs it, `.venv/bin/pytest -q -p no:cacheprovider`,
  run by the dispatching session on `v4` at `78c88809` in two halves by
  folder: `2064 passed, 2 skipped` and `4750 passed, 111 skipped`. `pnpm
  test` `198 passed`; `tsc --noEmit`, `pnpm lint`, `pnpm check:build` clean;
  the end-to-end suite `18 passed`.
- By the reviewer: the new and central test files, `912 passed` and
  `149 passed`; 25 scratch tests of its own outside the repository.
- By hand, through a guarded wrapper with every `TCW_*` variable unset and
  scratch home folders: every work and tree write aimed at another project's
  object exits 3 naming `tcw -C <absolute folder>` with the other project's
  files unchanged; `tcw -C tcw://core.path/` writes in `core`; renaming an
  epic with nested items prints one `<old> -> <new>` line each and rewrites
  blockers, parents and a capability link, reporting the code and prose
  mentions; a stop on an unwritable folder writes nothing and a rerun
  finishes; refused moves change no file or folder; a Jira-mode create and
  edit keep another project's blocker with no issue-link request.

## Acceptance criteria

AC 1 to 27 are met (AC 4 and AC 11 also by hand); AC 28 is the suite run.
The 74 removed tests and 34 rewritten ones were sampled (17 and 10): each
removal tests `--project`, `--blocks`, delegation or the read-only rule, and
each rewrite keeps its assertion's force. The Step 1 record compared with
the final run covers what the per-step comparisons would have caught. The
implementer's decisions are reasonable; the `clash_advice` exemption is one
function returning text.

## Findings

1. `tcw/serve/work.py:406-426`: `reported()` collects every line the backend
   reports, not only the lines naming a parent or blocker. A files-mode
   `PATCH /api/work/<item>` that sets a priority answers with a warning
   `wrote docs/work/<item>/tcw-work-item.yaml`, and `POST /api/work` with
   `created …` and `wrote …` warnings, so every ordinary edit in the web app
   shows "Saved with 1 validation issue". No test checks that a plain edit
   answers with no warnings. The changelog describes this as intended.
2. `tcw/work/config.py:77-78`: a project still configuring the removed
   `delegation` procedure is told "delegating to another project is `tcw
   work new --project`", which now exits 2, and that its rule is "fixed text
   in the work skill", which is no longer true (Design 9.5).

## Needs a separate change

Kept on the 4.0 run's list of small follow-ups, decided by the dispatching
session:

- The web create form ignores the answer's warnings, so AC 7's "Jira shows no
  link for it" never reaches the person; the server half is met.
- `skills/work/SKILL.md:3` still says "filing work into another project",
  and its delegation passage says projects are declared under `projects:`
  (TCW-117's).
- `tcw taxonomy rename bill PAY` reports `docs/taxonomy/PAY already exists`
  when the folder that exists is `pay`.

## What implement must do

- (a) Answer only the reference lines (a parent or blocker) as warnings from
  a web write, with a test that a plain files-mode edit and create answer no
  warnings; correct the changelog line.
- (b) Change the `delegation` message to name `tcw -C <folder> work new` and
  drop the claim about the work skill.
- (c) `implement/round-2.md`.
