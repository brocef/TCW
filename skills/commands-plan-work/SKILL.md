---
name: commands-plan-work
description: Plan a TCW work item from an existing item or the user's chat request, writing its request, spec and plan.
when_to_use: Use when a user asks to plan a TCW work item, or to turn a chat request into a planned item — running the request, spec and plan stages and stopping once the plan is written, before any code.
allowed-tools: Bash(tcw *), Read, Edit, Write
metadata:
    author: Brian Cefali
license: Apache-2.0
dynamic_skill: false # which skills a project may override, and why: ../README.md
---
**Version check.** Under Claude Code, skip this: the session-start hook already ran it. Under any other harness, once per session before your first `tcw` command, run `bash "<plugin>/scripts/check_versions.sh"`, where `<plugin>` is two folders above the folder holding this `SKILL.md`, and pass on anything it prints to the user.

Use the `work` skill. This skill covers the stage range **`request` →
`plan`**.

**Planning from a chat request with no item:** run the `work-create` skill
first, in interactive mode. The chat request answers its references and origin
questions. If it reports `already tracked`, `amended` or
`already in progress`, stop and report that. If it reports `created` or
`revised`, go on with that item.

**Then, from the item's stage** (`tcw work show <slug>`), for each of request,
spec and plan that the project has enabled:

1. Read the newest handoff for the stage, as the `work` skill's "Finding your
   place" says.
2. Run `tcw work stage prompt <stage> <slug>` and follow it. Request asks the
   user; spec and plan write their documents and post what the prompt names.
3. When the stage's output is written and the stage is not plan, run
   `tcw work advance <slug>`. On a refusal, read what it says, fix what it
   names, and run it again; never `--force` past a gate here. When plan is
   disabled, stop at the last of the three stages the project runs.

**Where the backend keeps request** (in Jira, the request is the ticket), the
request prompt proposes changes as a comment, and the requester decides when
the item moves on. When they tell you in this conversation to move it, do what
the request prompt says: put any wording they adopted into the description,
read it back, and run `tcw work advance <slug> --reason "<who told you>"`, then
carry on to spec. A question, or an advisor's opinion, is not that
instruction. Without it, stop after the comment and report that the item waits
for its requester; pick the work up again with this skill once it is at spec.

**Stop once the plan is written**, leaving the item at plan. The plan
prompt's last line says to run `tcw work advance`; under this skill, do not.
That line is for `commands-drive-work-to-completion`. Moving it on and
writing code is the `commands-drive-work-to-completion` skill. Ask the user to
read the plan, and name its path, `tcw work path <slug> plan`.
