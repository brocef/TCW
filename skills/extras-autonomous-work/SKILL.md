---
name: extras-autonomous-work
description: Use when asked to work TCW items autonomously, unattended, or "without asking me" — drives one or more items to completion via the commands-drive-work-to-completion skill, consulting read-only advisors in place of every human checkpoint (by default Codex and a read-only subagent on the strongest model the harness can start; a project can name its own).
allowed-tools: Bash(tcw *), Bash(codex *), Agent, SendMessage
compatibility: Declares what TCW's shipped procedure needs — the Codex CLI (`codex`) on PATH and a harness with subagents (Agent, SendMessage). A project that replaces it under `work.procedures.unattended-work` may need other tools. Requires a `tcw` with `tcw work procedure`.
dynamic_skill: true # which skills a project may override, and why: ../README.md
---
**Version check.** Under Claude Code, skip this: the session-start hook already ran it. Under any other harness, once per session before your first `tcw` command, run `bash "<plugin>/scripts/check_versions.sh"`, where `<plugin>` is two folders above the folder holding this `SKILL.md`, and pass on anything it prints to the user.

# Autonomous TCW work

Drive the named items through the `commands-drive-work-to-completion`
skill, back to back.
Wherever a stage would ask the human — an open question in a spec or plan, a
review, a qa verdict the agent may record — ask **the advisors** instead and
decide yourself. The one exception is what the requester wants, at request:
that is not the advisors' to know, so do not ask them; write the request from
the evidence available, marking each assumption (where the backend keeps the
request, as Jira does, post your questions with `tcw work comment <slug>`
instead and leave its text alone). Stop only on a hard blocker.

**A stage the backend keeps** (in Jira, request and qa) moves on only when the
person who decides tells you to. An advisor never stands in for that person.
Unless the user's own instruction for this run said to move those stages,
reaching one is a hard blocker: post what the stage asks for and stop that item.

**Ask once, at the start:** confirm the item set (the user's list, or pick from
`tcw work list`) and the order. After that, no more questions
until the run ends or a hard blocker hits.

## What an advisor must be

Whoever this project names as advisors, each one is:

- **Independent of this session** — a separate agent or program that does not
  share your context and sees only the brief you give it. Otherwise it is you
  agreeing with yourself.
- **Read-only** — it reads and answers. It never edits a file or moves an
  item; you act on what it says.
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
`tcw work procedure unattended-work --no-exec` reports a binding
`skipped (condition)`, re-read it with each item's slug before working that
item.

!`tcw work procedure unattended-work || true`

## Hard blockers — stop, report, wait

- Credentials, MFA, or any human-gated console: package publishing, app-store
  submission, production database access.
- Unrecoverable: data deletion, rewriting or deleting shared history,
  production migrations.
- Product direction: what a feature should *be*, pricing, copy that speaks for
  the product.
- Spend on the user's paid accounts.
- Advisors split on an irreversible choice, or all of them call the item's
  premise wrong.
- The spec contradicts the code and no reading makes both true.

Not blockers: ugly code, a missing fixture, one flaky suite, an unfamiliar lint
rule, or any disagreement you can settle by reading the code.

## Leave the audit trail

Give the round you write an `## Autonomous decisions` section: one line per
consult — the question, what each advisor said, what you chose, why. Decisions
made up to and during implement go in the implement round; decisions at review
or qa go in that stage's round, which is written after them. Where qa writes no
round, because a person decides its verdict or the backend keeps it, put the
section in the findings comment you post on the item, or in your closing
report if you post none. This is what makes
an unattended run reviewable afterwards. The run is not finished without it.

Close with one block per item: slug, the stage it ended at, decisions taken,
review findings rejected, follow-ups filed, and anything you would have asked
about if you could.

## Document command summary

The command below is automatically executed by the Claude Code harness where
"This project's procedure" says, and its output belongs there.

```sh
# The project's unattended-work procedure: advisors, checkpoint map, closeout
tcw work procedure unattended-work
```

If your harness did not run it, run it yourself and read its output as that
section before starting. To see whether any of the project's bindings depend on
the work item, run it with `--no-exec`; to read it for one item, add the item's
slug.
