# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Stable project IDs and explicit connections

TCW projects now have canonical IDs and an explicit, reciprocal project graph.
Connected projects can live anywhere on disk; moving one changes its locator,
not the work and reference addresses that use its ID. Descendant boards, work
commands, the web app, delegation, escalation, and `tcw://` links now use
`<project-id>/…`.

This is a breaking migration. New projects require `tcw init --id <project-id>`.
Existing markers must be backfilled, direct parent/child connections registered
on both sides, and taxonomy/capability `extends` maps converted to project-ID
lists. TCW fails closed instead of inferring IDs, scanning nearby folders, or
accepting legacy path qualifiers. See
[`docs/migration-guide-0.12.X-to-0.13.0.md`](../migration-guide-0.12.X-to-0.13.0.md).
