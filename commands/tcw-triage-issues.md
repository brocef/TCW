---
description: Sweep this project's open GitHub issues, triage them, and turn the ones worth doing into TCW work items.
---

Use the `tcw-triage-issues` skill.

It sweeps the **open GitHub issues on this project's own repo** — not TCW's; to
send a report upstream to the TCW project, that is the `tcw-report` skill.

Read `skills/tcw-triage-issues/SKILL.md` for the procedure, and
`skills/tcw-work/references/stage-inbox.md` for the intake judgment it defers to
— a GitHub issue is an inbox entry that happens to live on GitHub, and the
retitling, splitting, and tag choice are the same.

Triage decides before anything is created: only issues worth doing become work
items. Duplicates, non-starters, and reports too vague to act on do not. Every
reply to an issue is shown to the user for approval, one at a time, before it is
posted.

Codex has no slash commands, so invoke the skill directly there — nothing here
is available only one way.

$ARGUMENTS
