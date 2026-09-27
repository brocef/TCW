# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Fixes

- **The web app shows why a save was refused.** It used to say "Stale write
  detected" for any refused save, even when the reason was something else, such
  as a file that only a `tcw` command may write. It now shows the actual reason,
  which names the command to run instead.
