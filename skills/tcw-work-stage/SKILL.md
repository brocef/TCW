---
name: tcw-work-stage
description: Read a TCW lifecycle stage in one piece — the stage's own working document composed with the instructions this project resolves for it. Use when entering or reading a lifecycle stage (inbox, request, spec, plan, implement, verify, postmortem) for a work item, instead of opening the stage document and running the CLI separately.
when_to_use: Use when about to work a TCW lifecycle stage and you want the stage document and the project's resolved instructions together. Takes the stage id and, for every stage but `inbox`, the work item reference. It reads only — `tcw work stage begin` is still what enters the stage.
arguments: [stage, item]
allowed-tools: Bash(tcw *), Bash(cat *)
metadata:
    author: Brian Cefali
license: Apache-2.0
---

# The `$stage` stage

Two blocks follow: **how to work this stage**, then **what this project asks
for at it**. They are different documents and neither replaces the other. Read
both before producing anything.

## How to work it

!`cat "${CLAUDE_PLUGIN_ROOT}/skills/tcw-work/references/lifecycle/stage-$stage.md" || true`

## What this project asks for

!`tcw work stage prompt $stage $item || true`

## Before you act on any of that

The second block came from `tcw work stage prompt`, the **reading** verb. It runs
no legality check and no `pre` bindings, so it answers for a stage the item is
not ready for — which is the whole reason it can be composed into a skill. It is
not a licence to skip the gate.

**To enter the stage, run `tcw work stage begin $stage $item`.** That is the verb
that checks the stage is legal for the item's status and runs whatever the
project bound to it, and it refuses when either says no. If it refuses, the
refusal is the answer; do not proceed on the strength of having read the
instructions here.

If a block above is missing, empty, or shows a command error, this harness did
not run the injected commands. Nothing is lost — run them yourself:

```sh
cat <plugin>/skills/tcw-work/references/lifecycle/stage-$stage.md
tcw work stage prompt $stage $item
```
