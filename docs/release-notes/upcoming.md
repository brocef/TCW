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
- **A refused `tcw work edit` now changes nothing.** If one part of the command
  is refused (an unregistered tag, a blocker that would make items wait on each
  other in a loop), none of it is applied. Before, the blockers were saved and
  only then was the command refused.
- **The web app no longer lets you save an item as blocking itself**, or a
  blocker that would make items wait on each other in a loop.

## Fixes

- **Tag conditions in lifecycle settings work the way tags do everywhere else.**
  `when: { tags: [CLI] }` now matches items tagged `cli`; before, it silently
  never matched. If you used a differently spelled tag under `not_tags`, those
  items are now excluded as you intended. `tcw validate` reports a condition tag
  that is not registered, or several tags written as one (`"cli,docs"`).
- **`tcw validate` names a bad key instead of crashing** when a settings key is
  an unquoted number.
- **`tcw work list --tags` says when the tag you asked for is not registered**,
  so an empty list is not mistaken for "nothing has that tag".
- **`tcw validate` reports a `skill:` setting that cannot be a skill name**, such
  as one with spaces in it.
