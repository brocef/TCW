# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Fixed

- Fixed the plugin failing to load its startup hook in Claude Code with a
  "Duplicate hooks file detected" error, which stopped `tcw` from being installed
  automatically at the start of a session. Introduced in v0.17.0.
