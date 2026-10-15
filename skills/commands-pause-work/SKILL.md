---
name: commands-pause-work
description: Stop the work in hand gracefully, write down what resuming needs, and wait for the user.
when_to_use: Use when a user asks to pause, stop for now, hold off, or stand down mid-task — including when they say they are about to lose their connection, reboot, or pick the work up on another machine. Not for finishing work (commands-drive-work-to-completion), abandoning it, or recording a blocker.
allowed-tools: Bash(tcw *), Read, Edit, Write
metadata:
    author: Brian Cefali
license: Apache-2.0
dynamic_skill: true # which skills a project may override, and why: ../README.md
---
**Version check.** Under Claude Code, skip this: the session-start hook already ran it. Under any other harness, once per session before your first `tcw` command, run `bash "<plugin>/scripts/check_versions.sh"`, where `<plugin>` is two folders above the folder holding this `SKILL.md`, and pass on anything it prints to the user.

Use the `work` skill for anything about the item itself. This skill covers
**stopping**: it works no stage and **moves nothing**, so each item stays at
the stage it was at. You do not know whether the user is back in five minutes
or resuming on another machine — leave the work so both work.

## 1. How to pause

How to reach a resting point and what a handoff holds come from this project's
`pause-work` procedure, TCW's own text unless the project replaced it:

!`tcw work procedure pause-work || true`

If nothing appears above, run `tcw work procedure pause-work` yourself (see
the summary at the end) and follow what it prints. If the project wants
anything more when work pauses, such as saving the work somewhere, its
procedure says so; this skill adds nothing of its own.

## 2. Where the handoff goes

One handoff per item in flight, placed by the stage the item is at:

- **The stage has a folder:** write the handoff to the file
  `tcw work path <slug> <stage> --handoff` prints. Never compose the path;
  each call names a new file, and the newest one is what resuming reads.
- **The backend keeps the stage** (`tcw work path` exits 3 for it; in Jira,
  request and qa): post the handoff as a comment with
  `tcw work comment <slug>`, the text on stdin, whose first line is
  `Handoff`.
- **The item is at inbox, or there is no item:** write nothing. Triage keeps
  nothing worth resuming; say what you were doing in the report instead.

Handoffs are never deleted: a later one supersedes an earlier one by being
newer.

## 3. Report, then stop

One short message: each item, its stage, and where its handoff is. End it with
the exact words the user can give a new session to pick the work back up,
filled in with the real slug, one line per paused item:

```
To resume in a new session, tell the agent: "Resume work on <slug> from its
newest handoff."
```

With no handoff written, name what the new session should start from instead:
the slug, or what you were doing when there was no item.

Then **fall silent**. No further tool calls, no scheduled check-in, no
background task left running that would wake you. Waiting is the deliverable.

## Document command summary

The command below is automatically executed by the Claude Code harness, in the
place shown above.

```sh
# Get the pause procedure: TCW's own text unless this project replaced it
tcw work procedure pause-work
```

If your harness did not run it, run it yourself and follow its output as the
procedure.
