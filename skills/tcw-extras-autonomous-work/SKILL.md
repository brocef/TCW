---
name: tcw-extras-autonomous-work
description: Use when asked to work TCW items autonomously, unattended, or "without asking me" — drives one or more items to completion via the tcw-commands-drive-work-to-completion skill, consulting Codex and an Opus subagent in place of every human checkpoint.
---

# Autonomous TCW work

Drive the named items through the `tcw-commands-drive-work-to-completion`
skill, back to back.
Wherever the lifecycle would ask the human — a review, an open question, the
verify decision, a closeout choice — ask **the two advisors** instead and decide
yourself. Stop only on a hard blocker.

**Ask once, at the start:** confirm the item set (the user's list, or pick from
`tcw work list --status backlog`) and the order. After that, no more questions
until the run ends or a hard blocker hits.

## The advisors

Run both in parallel on the same brief:

- **Codex** — `codex -C <repo> exec -c sandbox_mode=read-only "<brief>"` as a
  background Bash call. Never bare `codex` (interactive TUI, hangs the call);
  `-C` goes *before* `exec`; without the sandbox flag it stalls on an approval
  prompt.
- **Opus subagent** — Agent tool, `model: opus`, read-only prompt.

The brief must stand alone: item slug, the files in play, the exact question,
the options you see, and which one you lean towards. A brief that only makes
sense with your context returns advice that only sounds right.

Adjudicate: agreement → act. Split → take the stronger argument, not a majority
(there is no majority of two), and record why. Both come back "not enough
information" on something irreversible → hard blocker. You are not bound by
either; they replace a second opinion, not your judgement.

**An agent that goes idle without reporting has not answered.** It happens
often, and silence reads exactly like "nothing to say". `SendMessage` it for the
conclusion, restating what the answer must cover. Never write down a verdict you
did not read. Codex is the reliable half — when an answer is load-bearing, do
not let the run wait on the subagent alone.

## Checkpoint map

| The lifecycle asks for      | Do this instead                                                                                                       |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Sequential vs. subagents    | Decide yourself. Sequential unless the slices are genuinely independent.                                                |
| Open question in spec/plan  | Consult, then write the answer into the artifact with the assumption stated in the text.                                |
| Code review                 | A read-only adversarial review subagent — the `adversarial-code-reviewer` agent where the project has one. Apply what you agree with; write down what you reject and why. |
| Verify assessment           | The `tcw-verifier` agent, **plus** your own hands-on exercise of whatever the project actually produces.                |
| Verify decision             | Yours. Green → `tcw work submit`. Red → rework and loop; the same criterion failing three loops is a hard blocker.       |
| Hands-on QA                 | Drive the real thing yourself, however this project is run — see the `run` skill, or whatever the repo's own guidance says. Agent reports and green suites are testimony, not evidence. |
| Capability reconciliation   | The `capabilities` sub-skill, unchanged.                                                                            |
| Version choice              | Never cut one. Accumulate into `upcoming.md` and move on.                                                               |
| Closeout route              | `tcw work complete`, then merge the feature branch into main **locally**. Never `git push`.                             |

## Hard blockers — stop, report, wait

- Credentials, MFA, or any human-gated console: package publishing, app-store
  submission, production database access.
- Unrecoverable: data deletion, force-push, rewriting main, remote branch
  deletion, production migrations.
- Product direction: what a feature should *be*, pricing, copy that speaks for
  the product.
- Spend on the user's paid accounts.
- Advisors split on an irreversible choice, or both call the item's premise
  wrong.
- The spec contradicts the code and no reading makes both true.

Not blockers: ugly code, a missing fixture, one flaky suite, an unfamiliar lint
rule, or any disagreement you can settle by reading the code.

## Leave the audit trail

Append an `## Autonomous decisions` section to the item's `outcome.md`: one line
per consult — the question, what each advisor said, what you chose, why. This is
what makes an unattended run reviewable afterwards. The run is not finished
without it.

Close with one block per item: slug, resolution, decisions taken, review
findings rejected, follow-ups filed, and anything you would have asked about if
you could.
