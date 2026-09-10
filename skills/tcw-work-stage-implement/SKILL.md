---
name: tcw-work-stage-implement
description: Read the TCW `implement` stage in one piece — the stage's own working document composed with the instructions this project resolves for it. Use when about to build a work item, instead of opening the stage document and running the CLI separately.
when_to_use: Use when about to work the `implement` stage of a TCW work item and you want the stage document and the project's resolved instructions together. Takes the work item reference, or nothing — without one the instructions still resolve, with `<slug>` where a reference would go. It composes the instructions only — it does not run `tcw work start`, does not write code, and runs no gate. `tcw work stage gate` is still what refuses, and it is what enforces that an item is active before the first edit.
arguments: [item]
allowed-tools: Bash(tcw *), Bash(cat *)
metadata:
    author: Brian Cefali
license: Apache-2.0
---

# The `implement` stage

Two blocks follow: **how to work this stage**, then **what this project asks
for at it**. They are different documents and neither replaces the other. Read
both before producing anything.

## How to work it

!`cat "${CLAUDE_PLUGIN_ROOT}/skills/tcw-work/references/lifecycle/stage-implement.md" || true`

## What this project asks for

!`tcw work stage prompt implement $item || true`

## Before you act on any of that

The second block came from `tcw work stage prompt`, the **reading** verb. It runs
no legality check and no `pre` bindings, so it answers for a stage the item is
not ready for — which is the whole reason it can be composed into a skill.

It carries its own reminder of that, at the top and bottom of the block: what to
run to gate the stage, and what to do when its output is written. Follow those.
This skill adds nothing to them beyond the one line below, because two copies
drift and the copy in the CLI's output is the one a Codex reader gets too.

**`tcw work stage gate implement $item` is what refuses.** If it refuses, the
refusal is the answer; do not proceed on the strength of having read the
instructions here.

If a block above is missing, empty, or shows a command error, this harness did
not run the injected commands. Nothing is lost — run them yourself, substituting
the work item reference for `$item`:

```sh
cat <plugin>/skills/tcw-work/references/lifecycle/stage-implement.md
tcw work stage gate implement $item        # may it run?
tcw work stage prompt implement $item      # what does it ask for?
```
