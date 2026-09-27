# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Fixes

- **Re-running `tcw work init` or `tcw init` leaves your `work.path` exactly as you wrote it.**
  It used to rewrite `~/store` as the full path to your own home folder, which
  broke the setting for everyone else sharing the file.
- **The web app tells a save that lost a race apart from any other refused
  save.** Only a save made against an out-of-date copy now shows "Stale write
  detected"; any other refusal shows the server's own reason, which names the
  command to run instead.
