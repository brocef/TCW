---
description: Declare the project's documentation entries — in tcw-config.yaml under work.documentation, or as a Documentation Sync section in its CLAUDE.md — then create any tracked files (and parent directories) that don't yet exist.
---

Use the `documentation-sync` skill.

Read `skills/documentation-sync/references/setup.md` and follow it: ask which
files to track, which trigger applies to each (the base vocabulary is in
`SKILL.md`'s Trigger Reference; projects may define their own), and what
description guides updates — then write the section into `CLAUDE.md` **including
the opening directive line**, and create the tracked files and their parent
directories.

In a TCW project, don't add a `docs/FOLLOWUPS.md` — deferred code work is tracked
as `tcw work` backlog items.

Codex has no slash commands; invoke the skill directly there — nothing here is
available only one way.

$ARGUMENTS
