---
name: commands-pause-work
description: Stop the work in hand gracefully, write down what resuming needs, and wait for the user.
when_to_use: Use when a user asks to pause, stop for now, hold off, or stand down mid-task — including when they say they are about to lose their connection, reboot, or pick the work up on another machine. Not for finishing work (commands-drive-work-to-completion), abandoning it (tcw work drop), or recording a blocker.
allowed-tools: Bash(tcw *), Bash(git *), Read, Edit, Write
metadata:
    author: Brian Cefali
license: Apache-2.0
dynamic_skill: true # which skills a project may override, and why: ../README.md
---

Use the `work` skill for anything about the item itself. This skill covers
**stopping**: it runs no lifecycle stage and **no transition**, so the item keeps
the status and the claim it already had.

You do not know how long the pause will last. It may be five minutes with this
session still open, or a reboot, or the work resumed on another machine from a
fresh clone. Leave it so that either works.

## 1. Reach a coherent resting point

Finish the edit in hand or back it out. Start nothing new.

Coherent means **the checkout parses and the change is intelligible** — not that
it is complete, and not that the suite is green. Trying to reach green is how a
pause takes ten minutes while the user is already offline.

## 2. Ask whether to commit and push

Ask once, in one message: **commit and push**, **commit only**, or **leave the
tree alone**. The user is the only one who knows whether this is five minutes or
a different machine, so do not guess.

**No answer is a yes.** If the reply does not come, commit and push: a user who
has already gone is the case that most needs the work to survive without this
checkout.

## 3. Commit and push, if that was the answer

A work-in-progress commit on the branch you are working, marked as such in the
message. Push it.

## 4. Write the handoff

One file per work item in flight, in that item's folder — `tcw work path <slug>`
gives you the folder; never compose the path:

```
<stage-id>.handoff.md
```

`<stage-id>` is the **lifecycle stage** you were running (the repository also
uses stage ids for declared plan documents at `plan/<id>.md`; this is not that).
One of `request`, `spec`, `plan`, `implement`, `verify`, `postmortem`. Between
stages, use the one that would run next — the first missing artifact, which is
the `work` skill's "Finding your place" rule.

**`inbox` is not on that list.** At the inbox stage there is no item and no
folder to write into, and a file left inside a folder-shaped inbox entry is swept
into `attachments/` on acceptance under a name nothing looks for. An inbox-stage
pause writes no handoff: the raw entry is already the durable record. Say so in
your report instead.

Three rules about the file:

- **Delete any handoff already in the folder first.** The name is keyed to the
  stage, so a pause in `spec` followed by one in `implement` would otherwise
  leave two, one of them describing a position the work has left.
- **No `tcw://` links.** `tcw validate` resolves those links in every Markdown
  file under the work store, and a project may gate `tcw work complete` on it —
  a dangling reference in a handoff would refuse the completion. Name other
  items by bare slug.
- **Write it after the commit**, so it can name that commit.

Write for a reader with no memory of this session, possibly on another machine
from a fresh clone:

- the stage you were in, and what within it is done and not done;
- **the branch and the last commit** — nothing else records them; an item's
  `branch` field is set only for `--worktree` items;
- decisions already taken, and why — the part a diff cannot show;
- anything deliberately left broken, and what it was going to become;
- the immediate next action.

If you are working inside a git worktree, say so and name it: the item's store
there may be the worktree's own copy, so someone resuming from the primary
checkout will not see this file unless they know where to stand.

## 5. Commit and push the handoff

On the same answer from step 2. This is a **second** push, not covered by step 3:
the handoff is written after that commit, and a work store can live in a
different repository from the code, with a different remote.

Nothing pushes the store for you. TCW publishes only when a transition runs, and
this skill runs none.

Commit narrowly, in the repository that holds the store:

```bash
git -C <store folder> add -- <absolute path>
git -C <store folder> commit -m "<why the work paused>" -- <absolute path>
```

## 6. Report, then stop

One short message: the item(s), the branch, whether the work reached the remote,
and what to type to resume. If the user declined the commit, say plainly that the
handoff exists only in this checkout.

Then **fall silent**. No further tool calls, no scheduled check-in, no background
task left running that would wake you. Waiting is the deliverable.

## Scale the effort to what is in flight

Nothing uncommitted, and nothing held only in your head, is a pause that writes
**no handoff at all** — say that and stop. The value here is convenience;
ceremony for its own sake spends the time the user was trying to save.

## What the status does

Nothing: no transition runs.

| Paused during | The item is | On resuming |
| --- | --- | --- |
| `request`, `spec`, `plan` | `backlog` | `tcw work start` runs normally; the claim is taken then |
| `implement` | `active` | already claimed by you; no `--take-over` needed |
| `verify`, `postmortem` | `review` | unchanged |

One exception worth knowing on a node with a tracker configured: its ticket
commands compare the item's owner against the local identity, and refuse or skip
when they differ. A cold resume under a different identity hits that and is told
to use `--take-over`. Resuming as the same identity does not.
