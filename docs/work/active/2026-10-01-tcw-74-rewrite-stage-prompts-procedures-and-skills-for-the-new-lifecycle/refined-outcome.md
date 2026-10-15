# Refined outcome — TCW-74: stage prompts, procedures and skills

**Accepted** on 2026-10-15 under the TCW 3.0 epic's rule: a child item is
approved at verify when it passes a bounded adversarial review (the owner,
2026-10-02, restated 2026-10-13: "I'm going to do my own review and
verification after all slices are completed, not after each one"). The
confirming round ended `NOT DONE` on two narrow points, both settled without a
further round (below).

## What was accepted

Everything in `outcome.md`:
- **Prompts:** the eight stage prompts, read by a strict loader, with the
  generated header and footer around a prompt and the item's slug filled in
  throughout.
- **Backend passages:** text a prompt or procedure meant for one backend only.
- **Procedures:** the 3.0 set of seven. Four are removed, and a configuration
  that still names one is told where it went.
- **Skills, agents and the plugin manifest:** rewritten for the 3.0 lifecycle.
- **Guards:** checks on the shipped text, covering no git grants, no 2.x
  vocabulary, and commands that exist.
- **Records:** the capability records.
- **Eval harness:** moved onto the 3.0 stages.

## Reviews

**Round 1** used three Claude reviewers, split by area: the code and the
prompts it loads; the skills, procedures and records; and the eval harness.
The code reviewer ended `DONE`, and the other two `NOT DONE`. Codex and the
local model were not run.

The fixes are in `outcome.md`'s "Review round 1" section (branch
`ed5e2eb4`, `e411e681`, `a55d9662`). The ones that mattered most:

- **Eval runs measured the wrong code.** A real eval run would have measured
  the installed 2.8.1 `tcw` on the agent's PATH, not this checkout. The runner
  now pins the PATH, records where the agent's `tcw` imports from, and grading
  fails a run with isolation problems.
- **A failed command still passed.** "The agent ran `tcw work stage prompt`"
  passed even when the command failed. It now requires the prompt's header in
  that call's result.
- **A check left over from 2.x.** One case checked for a word that a correct
  3.0 run never types.
- **An instruction that fails.** The create-work procedure told the agent to
  comment on an unadopted Jira ticket, which fails.
- **Records that overstated.** Eight capability records, and the matching
  release lines, claimed behavior the code lacks.
- **A missing warning.** Switching an existing project to Jira hides items kept
  as files, without warning.
- **A silent misspelling.** A misspelled pair of backend markers passed
  silently.
- **Stale 2.x text.** Descriptions of the 2.x `tcw serve` (Node.js, commits,
  moves) were still in the setup and work skills.

**One decision taken in place of the owner:** dropping "under both harnesses"
(spec Design 11). The runner launches only Claude. Adding Codex is a project of
its own, and criterion 12 does not require it, so it is a recorded cut, filed
as a follow-up, not a fix.

**Confirming round:** every round-1 finding was fixed except that E4 (the cut
above) was not recorded. It also found one new defect introduced by the N1 fix:
any comment line that mentioned "backend" was rejected, so a project prompt
file with an ordinary header comment would make `stage prompt` fail. I (the
orchestrator) fixed it directly: only a comment that *opens* with `backend` is
a misspelled marker (`0e30fca5`, with a test that goes red under the old
check). I also recorded E4 and added the rule to spec Design 3.3 (`c2f088b2`).
Both points were narrow enough that a fourth round was not run.

## Follow-ups

- `docs/work/inbox/2026-10-15-tidy-what-tcw-74-s-reviews-left-for-the-eval-harness.md`:
  - the Codex harness;
  - B9's prompt and seeded defect disagreeing;
  - `transcript_absent` on an empty transcript;
  - A7 having no control arm;
  - an unclear message when the spawned `tcw`'s interpreter is unknown;
  - one more pairing test.
- `docs/work/inbox/2026-10-15-tidy-what-tcw-74-and-tcw-77-s-reviews-left-elsewhere.md`:
  - commands wrapped across lines go unchecked;
  - `advance` checks no stage document;
  - unattended runs have no rule for the request stage.
- Notes for TCW-75 and TCW-76, in their folders.
  - **TCW-75:** `procedure prompt` and the deleted procedure ids are still
    named in README, the guides and the configure reference; the dead
    allowance entry; the configure skill's Jira reference, which the skills
    already point to. **A version must not be cut between TCW-74 and TCW-75.**
  - **TCW-76:** the eval section of `AGENTS.md` is already done.

## Deferred, by the owner's instructions for this epic

- **The full suite** runs near the end of the epic. Here: the standing guard
  files, `tests/work/`, the shipped text, prompt, procedure, skill and manifest
  tests, and every `tests/test_eval_*.py`. `pytest --collect-only -q` is
  clean.
- **No real eval run** was made; the dry run reports the agent's `tcw` as this
  checkout.
- **This repository's `tcw-config.yaml` is still 2.x**, so the board is driven
  with the installed 2.8.1 until TCW-76.
- **Node.js check:** on this branch alone, `tcw serve` still checks for
  Node.js while the setup skill says nothing needs it. TCW-77 removes the
  check, and both land in `epic/tcw-3.0` before any release.

## Capabilities

The records were written on the branch and pass the records gate there. They
reach `main`'s ledger only when the epic merges, so the item is completed by
hand, as TCW-69 to 73 were.

## Closeout route

The branch `work/2026-10-01-tcw-74-…` fast-forwards `epic/tcw-3.0`, and its
worktree and branch are then removed. TCW-77, built in parallel, rebases onto
it, and the combined change gets one more review. `main` receives 3.0 only when
the epic ends. No GitHub issue originated this item.
