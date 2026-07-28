---
description: Cut a new version — choose the bump size, update every version-bearing file, rotate the upcoming.md working files, commit, and tag.
---

Use the `documentation-sync` skill.

Read `skills/documentation-sync/references/cut-version.md` and follow it.

**Check for the project's own version-cut process first** (its `CLAUDE.md`
Versioning section, usually a script) and run that instead of cutting by hand —
in this repo that's `python scripts/cut_version.py <patch|minor|major|X.Y.Z>`.

Write the release-note and changelog entries into the `upcoming.md` files
_before_ cutting; the cut rotates them. Publishing is a human step — ask before
pushing the commit or the tag.

Codex has no slash commands; invoke the skill directly there — nothing here is
available only one way.

$ARGUMENTS
