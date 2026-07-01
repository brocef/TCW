# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Added

- **See every nested project's work in one command.** If you keep several TCW
  projects as subfolders of one repo, `tcw work list --include-descendants` now
  lists them all at once — your current project's board followed by each
  sub-project's board, grouped under a heading for each folder. It respects the
  same options you'd normally pass, so `tcw work list --include-descendants --all`
  includes completed items across every project.
