# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Fixes

- **Re-running `tcw work init` or `tcw init` leaves your `work.path` exactly as you wrote it.**
  It used to rewrite `~/store` as the full path to your own home folder, which
  broke the setting for everyone else sharing the file.

## Fixes

- **Recovering an interrupted start works.** If `tcw` stopped partway through
  starting an item, the advice to run `tcw work start <slug> --take-over` only
  repeated the same error. It now finishes the start. The web app shows such
  items above the work list with a **Recover** button.
