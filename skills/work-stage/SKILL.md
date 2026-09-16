---
name: work-stage
description: Read a TCW lifecycle stage in one piece — the stage's own working document composed with the instructions this project resolves for it. Use when working a lifecycle stage (inbox, request, spec, plan, implement, verify, postmortem) for a work item, instead of opening the stage document and running the CLI separately.
when_to_use: Use when about to work a TCW lifecycle stage and you want the stage document and the project's resolved instructions together. Takes the stage id and, for every stage but `inbox`, the work item reference. It reads only — `tcw work stage gate` is still what refuses.
arguments: [stage, item]
allowed-tools: Bash(tcw *), Bash(cat *)
metadata:
    author: Brian Cefali
license: Apache-2.0
---

## Skill invocation validation (Claude-only injection)

Under any harness other than Claude Code, run `tcw work stage validate` with this skill's arguments before reading on.

!`tcw work stage validate -- $stage $item 2>/dev/null || true`

# The `$stage` stage

Two blocks follow: the **lifecycle stage contract**, then the **stage
instructions** this project resolves for it. They are different documents and
neither replaces the other. Read both before producing anything.

## Lifecycle stage contract

!`cat "${CLAUDE_PLUGIN_ROOT}/skills/work/references/lifecycle/stage-$stage.md" || true`

## Stage instructions

!`tcw work stage prompt $stage $item || true`

## Stage pre-checks

Run `tcw work stage gate $stage $item` if you have not done so already. If it
refuses, the refusal is the answer.

## Document command summary

The commands below are automatically executed by the Claude Code harness and
listed in order that they execute in the document.

```sh
# Validate the skill's arguments
tcw work stage validate -- $stage $item
# Get lifecycle stage description
cat <plugin>/skills/work/references/lifecycle/stage-$stage.md
# Generate prompt instructions for stage
tcw work stage prompt $stage $item
```

Not run automatically — run it yourself (see Stage pre-checks):

```sh
# Run pre-stage transition checks
tcw work stage gate $stage $item
```

If your harness did not run them, run them yourself, using the stage and work item named in the request in place of `$stage` and `$item`.
