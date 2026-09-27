# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Fixes

- **Re-running `tcw work init` or `tcw init` leaves your `work.path` exactly as you wrote it.**
  It used to rewrite `~/store` as the full path to your own home folder, which
  broke the setting for everyone else sharing the file.
