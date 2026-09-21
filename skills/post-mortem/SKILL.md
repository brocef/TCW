---
name: post-mortem
description: Use when a TCW work item surfaced a problem worth understanding — verification rejected the work, a spec claim turned out false, or something shipped that should not have. Finds which lifecycle stage could first have caught it.
arguments: [item]
allowed-tools: Bash(tcw *)
dynamic_skill: true # which skills a project may override, and why: ../README.md
---
**Version check.** Under Claude Code, skip this: the session-start hook already ran it. Under any other harness, once per session before your first `tcw` command, run `bash "<plugin>/scripts/check_versions.sh"`, where `<plugin>` is two folders above the folder holding this `SKILL.md`, and pass on anything it prints to the user.

# Running a post-mortem on a work item

**The contract lives elsewhere.** The `postmortem` stage — invoke the `work-stage` skill with `postmortem` and the item's slug —
defines the inputs, the `post-mortem.md` artifact, its required content, and the
rule that this stage never changes status. Read it once and do not restate it.
This skill is the part that document deliberately does not cover: **how to
actually find the answer.**

The question is always the same, and it is narrower than "what went wrong":

> **Which stage could first have caught this, and at what cost?**

## Read the spine backwards

`refined-outcome.md` and `rework.md` → `outcome.md` → `plan.md` → `spec.md` →
the body the item started from, `initial-request.md` or the `intake.md` beneath
it. Backwards, because you know the outcome and are looking for the earliest
point it was already determined.

## Producing the artifact

Write `post-mortem.md` per the `postmortem` stage's `Produce` section. Then create
follow-up work items for anything worth changing — a recommendation with no item
behind it will not happen.

**Never change the item's status.** A post-mortem is legal in `review` and after
`completed`, and it reopens nothing. Writing into a `completed/` item's folder is
the single exception to that folder's immutability.

## The procedure

!`tcw work procedure prompt post-mortem $item || tcw work procedure prompt post-mortem || true`

## Document command summary

The command below is automatically executed by the Claude Code harness, in the
place shown above.

```sh
# Get the investigation procedure for the item: TCW's own text unless this
# project replaced it
tcw work procedure prompt post-mortem $item
```

If your harness did not run it, run it yourself, using the work item named in
the request in place of `$item`, and follow its output as the procedure.
