# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

**This is the release v2.5.0 was meant to be.** v2.5.0 was tagged but never
reached PyPI, because a test that only failed on the build server stopped the
upload. Nothing else changed: everything described in the
[v2.5.0 notes](v2.5.0.md) (making Jira tickets with `tcw work tracker create`,
and moving `extends` into `tcw-config.yaml`) arrives with this version.
**Read those notes before upgrading if you use inheritance**, because that part
needs a migration step.

## Your comments in `tcw-config.yaml` are kept

The commands that add a setting to `tcw-config.yaml` used to rewrite the whole
file, which deleted every comment, re-wrapped long lines and changed the
indentation. That hit `tcw taxonomy extends add`, `tcw capabilities extends`
(the easy route in the v2.5.0 migration guide) and `tcw work tags add`. Now they
change only the lines of the setting they write — and so do their removal
counterparts and `tcw init` — and leave the rest of the file exactly as you
wrote it, down to the line endings.

If a file is laid out in a way the command cannot edit safely — for example a
section written on one line in braces, like `taxonomy: {path: docs/taxonomy}` —
it stops without changing anything and tells you the exact edit to make by hand.

Three hand-written shapes that used to be quietly overwritten now get that
message instead: a `work:` line holding a single value rather than settings
beneath it (when registering tags or running `tcw init --work-path`), a `tags:`
that is not a list, and the same single-value shape for `taxonomy:` or
`capabilities:` when `tcw init` sets its location.
