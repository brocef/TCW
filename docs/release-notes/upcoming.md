# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Added

- **Install tcw as a plugin.** You can now add tcw to Claude Code or Codex as a
  plugin. It brings the tcw skills, and in Claude Code adds a `/tcw-init` command
  that installs the `tcw` command itself for you — no separate setup step. If a
  later update ever leaves `tcw` missing or out of date, `/tcw-doctor` checks the
  install and repairs it. (Tip: if you use `/tcw-init`, don't also install tcw a
  second way — keep the one copy.)
