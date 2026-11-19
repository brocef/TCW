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
the stage it was at.

Assume nothing about what was going on beyond this: the user said to pause,
and may resume in a fresh session, possibly on another machine. Do what you
can to make that possible.

You know whether you report to the user directly or to another agent that
started you. That decides how you finish (section 2).

## When an agent you sent the pause to is interrupted

Other agents may be working under you: full interactive sessions you started,
ones the user started and you coordinate by message, or agents that message
each other. Each gets the pause as a message, and may not read it until its
current turn ends, which can take a while. A user who cannot wait that long
interrupts those agents by hand, so that each stops its turn and reads the
pause at once.

So **when an agent you sent the pause to shows as interrupted, assume the user
interrupted it**, and that it is now working through the pause: reaching its
own resting point and writing its own handoffs, with no further instruction
from you. Do not take its handoff over, and do not treat it as done and idle
**until more than ten minutes have passed with no message or confirmation from
it**. Until then, wait for its report; after that, count its work as
unconfirmed.

## 1. How to pause

How to reach a resting point, what a handoff holds, and where it is kept so a
fresh session can find it come from this project's `pause-work` procedure,
TCW's own text unless the project replaced it:

!`tcw work procedure pause-work || true`

If nothing appears above, run `tcw work procedure pause-work` yourself (see
the summary at the end) and follow what it prints. If the project wants
anything more when work pauses, its procedure says so; this skill adds
nothing of its own.

## 2. Report, then stop

Whoever you report to, first send the pause to every agent working under you,
however it was started, and wait for their reports as described above, so
that your own report covers their work too.

**If you report to another agent,** send it one report: each item you or the
agents under you were working, its stage, where its handoff is (or that none
was written, and why), and anything you know only from this session that the
handoff does not hold. Write no resume message: the agent you report to
writes the only one.

**If you report to the user,** you write the only resume message, however
many agents were working. Send one short message: what was paused and where
each handoff is. End it with a single resume message, in a fenced block, for
the user to paste into a fresh session:

```
Resume the paused work: <what was in progress, each item by its full
identifier and where its newest handoff is; what ran alongside what; any
work not confirmed as paused>. Where the work was split between agents,
start them again and give each its own instruction to resume.
```

Copying it is the one way certain to carry anything from this session to the
next, so it must be enough on its own to pick all of the work back up. Point
to what was saved somewhere a fresh session can reach, rather than repeating
it; anything saved nowhere else, or only on this machine, goes in the
message itself.

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
