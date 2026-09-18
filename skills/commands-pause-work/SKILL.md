---
name: commands-pause-work
description: Stop the work in hand gracefully, write down what resuming needs, and wait for the user.
when_to_use: Use when a user asks to pause, stop for now, hold off, or stand down mid-task — including when they say they are about to lose their connection, reboot, or pick the work up on another machine. Not for finishing work (commands-drive-work-to-completion), abandoning it, or recording a blocker.
allowed-tools: Bash(tcw *), Bash(git *), Read, Edit, Write
metadata:
    author: Brian Cefali
license: Apache-2.0
dynamic_skill: true # which skills a project may override, and why: ../README.md
---

Use the `work` skill for anything about the item itself. This skill covers
**stopping**: it runs no lifecycle stage and **no transition**, so the item keeps
the status and the claim it had. You do not know whether the user is back in five
minutes or resuming on another machine from a fresh clone — leave it so both work.

## 1. Reach a coherent resting point

Finish the edit in hand or back it out; start nothing new. Coherent means **the
checkout parses and the change is intelligible** — not that it is complete or
that the suite is green. Reaching for green is how a pause takes ten minutes
while the user is already offline.

## 2. Ask whether to commit and push

Ask once: **commit and push**, **commit only**, or **leave the tree alone**. Only
the user knows how long they will be gone. **No answer is a yes** — a user who has
already left is the case that most needs the work to survive this checkout.

## 3. Commit and push, if that was the answer

A work-in-progress commit on the branch you are working, marked as such. Push it.

## 4. Write the handoff

One file per work item in flight, in that item's folder — `tcw work path <slug>`
gives you the folder; never compose the path:

```
handoff-<UTC timestamp>.md      e.g. handoff-20260917T2115Z.md
```

**Write whatever context an agent would need to resume the work you were doing at
the time of the pause.** You have been working the item; you know what mattered.
Write it for a reader with no memory of this session, on a machine that may hold
nothing but a fresh clone.

Two requirements, because nothing else in the system covers them:

- **Name the branch**, and the last commit if you made one. An item's stored
  `branch` is set only for `--worktree` items, so this is otherwise the only
  pointer to where the work actually is.
- **No `tcw://` links.** `tcw validate` resolves those in every Markdown file
  under the work store and a project may gate `tcw work complete` on it, so a
  dangling one would refuse the completion. Use bare slugs.

Write it after the commit so it can name that commit. Resuming reads it and
deletes it — say so when you report; it is a message in flight, not a record.

With no work item, write no handoff and say so in your report instead. With
nothing uncommitted and nothing held only in your head, likewise: the value here
is convenience, and ceremony spends the time the user was trying to save.

## 5. Commit and push the handoff

On the same answer from step 2, and it is a **second** push — the handoff is
written after step 3's commit, and a work store can live in a different
repository from the code, with its own remote. Nothing pushes the store for you:
TCW publishes only when a transition runs, and this skill runs none. Commit it
narrowly, with `git -C <store folder> … -- <absolute path>`.

## 6. Report, then stop

One short message: the item(s), the branch, whether the work reached the remote,
and what to type to resume. If the user declined the commit, say plainly that the
handoff exists only in this checkout.

Then **fall silent**. No further tool calls, no scheduled check-in, no background
task left running that would wake you. Waiting is the deliverable.
