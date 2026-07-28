---
description: Triage raw entries in the TCW work inbox into tracked work items.
---

Use the `tcw-work` skill. This command covers the stage range **`inbox` →
`request`**.

Read `skills/tcw-work/references/stage-inbox.md` and work through every entry
`tcw work inbox list` reports. For each one, decide whether it is one item or
several, choose its tags from the node's registered vocabulary, and accept it
with `tcw work inbox accept <entry> --title "<clear title>"`.

Then read `references/stage-request.md` and shape each new item's
`initial-request.md` into an actual request — asking the user whatever is
unclear, since that is what the stage exists for.

Commit each item as you create it. Do not carry an entry into `spec`; that is
`/tcw-plan-work`.

$ARGUMENTS
