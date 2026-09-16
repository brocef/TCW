---
name: work-create
description: "Turns an idea for a piece of work into a tracked TCW work item, or adds it to the item or inbox entry that already covers it, after checking the board and the work inbox and recording blockers, references and origin."
when_to_use: "Use when you notice in passing, in the middle of other work, something that should outlive this session — a bug found while doing something else, a follow-up or deferred cleanup a task or review leaves behind, a 'we should also…' — or when a user asks to file, track, open or log a work item, or to add something to the backlog. Also when handing such an idea to a subagent. Do not use it for children of an item already being planned (tcw work new --parent), GitHub issues (the `extras-triage-issues` skill), triaging the work inbox (the `work` skill), a bug in TCW itself (the `extras-report` skill), or asking which stage should have caught a problem (the `post-mortem` skill)."
allowed-tools: Bash(tcw *), Bash(git *), Bash(grep *), Read, Edit, Write
metadata:
    author: Brian Cefali
license: Apache-2.0
dynamic_skill: true # which skills a project may override, and why: ../README.md
---

# Turning an idea into a work item

One idea goes in. Exactly one outcome comes out (step 5): a new item, an
existing item or inbox entry with the idea added, or nothing, because the work is
already tracked. Check what exists **before** running `tcw work new`. A duplicate
item splits the history of one piece of work across two places.

## 2. Find overlap

Follow [`find-overlap.md`](references/find-overlap.md). It is read-only and
returns one line per candidate. In an Interactive run, dispatch it to a
read-only subagent where you can and act on the lines it returns; otherwise run
it yourself.

!`tcw work procedure prompt create-work || true`

## Document command summary

The command below is automatically executed by the Claude Code harness, and its
output is the rest of this procedure.

```sh
# Get the procedure for filing the idea, composed with this project's text
tcw work procedure prompt create-work
```

If your harness did not run it, run it yourself and follow its output in place
of the line above. The opening paragraph and step 2 on this page still apply,
whatever that output says.
