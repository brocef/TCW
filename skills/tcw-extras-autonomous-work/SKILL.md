---
name: tcw-extras-autonomous-work
description: Use when asked to work TCW items autonomously, unattended, or "without asking me" — drives one or more items to completion via the tcw-commands-drive-work-to-completion skill, consulting read-only advisors in place of every human checkpoint (by default Codex and an Opus subagent; a project can name its own).
allowed-tools: Bash(tcw *), Bash(codex *), Bash(git merge *), Agent, SendMessage
compatibility: Declares what TCW's shipped procedure needs — the Codex CLI (`codex`) on PATH and a harness with subagents (Agent, SendMessage). A project that replaces it under `work.procedures.unattended-work` may need other tools. Requires a `tcw` with `tcw work procedure prompt`.
dynamic_skill: true # which skills a project may override, and why: ../README.md
---

# Autonomous TCW work

Drive the named items through the `tcw-commands-drive-work-to-completion`
skill, back to back.
Wherever the lifecycle would ask the human — a review, an open question, the
verify decision, a closeout choice — ask **the advisors** instead and decide
yourself. Stop only on a hard blocker.

**Ask once, at the start:** confirm the item set (the user's list, or pick from
`tcw work list --status backlog`) and the order. After that, no more questions
until the run ends or a hard blocker hits.

## What an advisor must be

Whoever this project names as advisors, each one is:

- **Independent of this session** — a separate agent or program that does not
  share your context and sees only the brief you give it. Otherwise it is you
  agreeing with yourself.
- **Read-only** — it reads and answers. It never edits, commits, runs a
  transition or pushes; you act on what it says.
- **Heard, not assumed** — an answer is text you read. Silence, or a report you
  did not read, is no answer.

**Two advisors are wanted**, as different from each other as the harness allows
— another model, another tool — so they do not share the same blind spots.

An answer is an argument, weighed, never counted, whatever the number of
advisors. With one, weigh its answer against your own reading of the code; with
three, two that agree do not outvote a third with the better argument. You are
never bound by an advisor.

## This project's procedure

The advisors, how to consult them and what to do at each checkpoint come from
this project's `unattended-work` procedure. TCW ships a default; a project
replaces it under `work.procedures.unattended-work`. This skill's `allowed-tools`
and `compatibility` describe TCW's default only — a replacement may need other
tools, and the harness asks before running one not declared.

The text was read without a work item. If
`tcw work procedure prompt unattended-work --no-exec` reports a binding
`skipped (condition)`, re-read it with each item's slug before working that
item.

!`tcw work procedure prompt unattended-work || true`

## Hard blockers — stop, report, wait

- Credentials, MFA, or any human-gated console: package publishing, app-store
  submission, production database access.
- Unrecoverable: data deletion, force-push, rewriting main, remote branch
  deletion, production migrations.
- Product direction: what a feature should *be*, pricing, copy that speaks for
  the product.
- Spend on the user's paid accounts.
- Advisors split on an irreversible choice, or all of them call the item's
  premise wrong.
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

## Document command summary

The command below is automatically executed by the Claude Code harness where
"This project's procedure" says, and its output belongs there.

```sh
# The project's unattended-work procedure: advisors, checkpoint map, closeout
tcw work procedure prompt unattended-work
```

If your harness did not run it, run it yourself and read its output as that
section before starting. To see whether any of the project's bindings depend on
the work item, run it with `--no-exec`; to read it for one item, add the item's
slug.
