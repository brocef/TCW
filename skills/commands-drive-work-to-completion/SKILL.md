---
name: commands-drive-work-to-completion
description: Drive a TCW work item from wherever it is through implement, review and qa, to completed where the agent may record the qa verdict, or to qa for a person where it may not.
when_to_use: Use when a user asks to drive, finish, or take a TCW work item to completion from wherever it stands — through implementation, review and qa, recording the qa verdict where the project lets the agent, and asking a person for it where the project or the backend says a person decides.
allowed-tools: Bash(tcw *), Read, Edit, Write
metadata:
    author: Brian Cefali
license: Apache-2.0
dynamic_skill: false # which skills a project may override, and why: ../README.md
---
**Version check.** Under Claude Code, skip this: the session-start hook already ran it. Under any other harness, once per session before your first `tcw` command, run `bash "<plugin>/scripts/check_versions.sh"`, where `<plugin>` is two folders above the folder holding this `SKILL.md`, and pass on anything it prints to the user.

Use the `work` skill. This skill covers **the current stage through qa**, and
the move to `completed` where the agent records the qa verdict.

**Find your place** as the `work` skill says: the item's stage from
`tcw work show <slug>`, then the newest handoff, then the stage prompt. Before
implement begins, ask the user whether to run the remaining stages in this
session or hand some to subagents, under the `work` skill's rules: stages may
go to a subagent, moves never do.

**Then, stage by stage:**

1. Run `tcw work stage prompt <stage> <slug>` and follow it.
2. When its output is written, run `tcw work advance <slug>`. On a refusal,
   read what it says, fix what it names, and run it again. Do not use
   `--force` without the user's agreement, given for that move.
3. A rejected review or qa round sends the item back to implement; the
   implement prompt says how to read the rejection. Keep going.

**Review** is done by a reviewer that did not write the code: a subagent
where you can start one (the `reviewer` agent where your harness has it),
otherwise a fresh read of the change against the spec, in this session, said
plainly in the round.

**Qa** depends on who decides its verdict:

- **TCW's own qa text on the filesystem:** run qa, write the round with its
  verdict, and advance; an accepted item reaches `completed`.
- **The project's qa prompt says a person decides:** run the scenarios, show
  the person the evidence, ask for `accepted` or `rejected` with a reason,
  and write the round recording their decision with `decided-by`, as the
  prompt says. Then advance.
- **The backend keeps qa** (in Jira, the ticket's move is the verdict): run the
  scenarios if the prompt asks, post the findings, and stop at qa for a person.

**Before reporting done,** say what changed, the documentation entries the
change fired and how each was answered, and any follow-up items created. A
stage that could not finish stops the run: report where the item is and why.
