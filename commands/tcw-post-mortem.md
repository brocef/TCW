---
description: Run a post-mortem on a TCW work item to find which lifecycle stage could first have caught a problem.
---

Use the `tcw-post-mortem` skill.

It covers the **`postmortem` stage**, which is out-of-band: it never changes an
item's status, and it is legal both while the item is in `review` and after it
has completed.

Read `skills/tcw-post-mortem/SKILL.md` for how to conduct the analysis, and
`skills/tcw-work/references/stage-postmortem.md` for the artifact contract.

The analysis is delegable to the read-only `tcw-post-mortem` agent under Claude.
Codex has no custom agents and no slash commands, so run it inline there and
invoke the skill directly — nothing here is available only one way.

$ARGUMENTS
