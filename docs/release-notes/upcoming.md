# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Fixed

Projects that keep their work in another repository (a configured `work.path`)
now have that setting honored everywhere, not just in some commands:

- Requests sent down to a child project or up to a parent now arrive in that
  project's real inbox. They used to be written into a `docs/work/inbox` folder
  that was created on the spot and that nobody ever read, so the request was
  silently lost. If the target's work store can't be reached, the command now
  stops with an error instead of reporting success.
- Reconciling an epic now updates and commits the rollup in the repository that
  actually holds the work, instead of failing with a raw Git error.
- `tcw capabilities drift` now finds the completed planning items that back a
  capability, so shipped-but-still-Missing capabilities are reported instead of
  quietly passing.
- Starting an item with `--worktree` now saves the item's own state in the work
  repository and the ignore-rule change in the code repository, and only then
  creates the worktree. Nothing is left half-saved, and if one of those saves is
  refused the command says which one and stops without creating a worktree.
- A leftover `docs/work` folder no longer masquerades as a project's work store
  when the project has been configured to keep its work somewhere else.

A project whose default `docs/work` folder is missing one of its status folders
is now treated as having no work store at all, rather than half-working. Run
`tcw work init` in that project to restore the missing folders.

Completing a work item that was started with `--worktree` no longer reports a
merge failure that did not happen. If the item moved through its lifecycle while
its branch was open — the usual case, since submitting it for review relocates its
folder — finishing it used to stop and claim the merge had failed, leaving you to
resolve by hand. It now completes on its own, while a genuine conflict between two
edits still stops exactly as before, with the branch and worktree left intact.

One behavior change comes with that fix, worth knowing if you rename directories:
when the merge-back runs, files your work branch added under a directory that has
since been renamed on the main branch now follow the rename into its new location.
That applies to code directories too, not only to the item's own folder.
