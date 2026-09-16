---
name: commands-process-inbox
description: Triage raw entries in the TCW work inbox into tracked work items.
when_to_use: Use when a user asks to process, triage, or clear the TCW work inbox — turning every raw entry into an accepted work item and running the request stage on its intake.
allowed-tools: Bash(tcw *), Bash(git *), Read, Edit, Write
metadata:
    author: Brian Cefali
license: Apache-2.0
---

Use the `work` skill. This skill covers the stage range **`inbox` →
`request`**.

Invoke the `work-stage` skill with `inbox`, and work through every entry
`tcw work inbox list` reports. For each one, decide whether it is one item or
several, choose its tags from the node's registered vocabulary, and accept it
with `tcw work inbox accept <entry> --title "<clear title>"`.

Accepting an entry writes it as the item's `intake.md`. Then invoke
the `work-stage` skill with `request` and the new item's slug, and run the `request` stage over that intake to
produce `initial-request.md` — asking the user whatever is unclear, since that
is what the stage exists for.

Commit each item as you create it. Do not carry an entry into `spec`; that is
the `commands-plan-work` skill.
