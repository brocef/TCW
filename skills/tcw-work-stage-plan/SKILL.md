---
name: tcw-work-stage-plan
description: Read the TCW `plan` stage in one piece — the stage's own working document composed with the instructions this project resolves for it. Use when about to decide how to build a work item, instead of opening the stage document and running the CLI separately.
when_to_use: Use when about to work the `plan` stage of a TCW work item and you want the stage document and the project's resolved instructions together. Takes the work item reference, or nothing — without one the instructions still resolve, with `<slug>` where a reference would go. It is not `/tcw-plan-work` — that command drives request through plan and writes all three artifacts, while this composes the `plan` stage's instructions and writes nothing. It runs no gate either — `tcw work stage gate` is still what refuses.
arguments: [item]
allowed-tools: Bash(tcw *), Bash(cat *)
metadata:
    author: Brian Cefali
license: Apache-2.0
---

# The `plan` stage

Two blocks follow: **how to work this stage**, then **what this project asks
for at it**. They are different documents and neither replaces the other. Read
both before producing anything.

## How to work it

!`cat "${CLAUDE_PLUGIN_ROOT}/skills/tcw-work/references/lifecycle/stage-plan.md" || true`

## What this project asks for

!`tcw work stage prompt plan $item || true`

## Before you act on any of that

The second block came from `tcw work stage prompt`, the **reading** verb. It runs
no legality check and no `pre` bindings, so it answers for a stage the item is
not ready for — which is the whole reason it can be composed into a skill.

It carries its own reminder of that, at the top and bottom of the block: what to
run to gate the stage, and what to do when its output is written. Follow those.
This skill adds nothing to them beyond the one line below, because two copies
drift and the copy in the CLI's output is the one a Codex reader gets too.

**`tcw work stage gate plan $item` is what refuses.** If it refuses, the
refusal is the answer; do not proceed on the strength of having read the
instructions here.

If a block above is missing, empty, or shows a command error, this harness did
not run the injected commands. Nothing is lost — run them yourself, substituting
the work item reference for `$item`:

```sh
cat <plugin>/skills/tcw-work/references/lifecycle/stage-plan.md
tcw work stage gate plan $item        # may it run?
tcw work stage prompt plan $item      # what does it ask for?
```
