# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

### New

- Work you decide **not** to do no longer sits next to work you shipped. Closing an
  item as "won't fix", "duplicate", or "superseded" now files it under `discarded`
  instead of `completed`, so `completed` answers "what did we ship?" all by itself.
  You can also discard an item straight from the backlog — previously you had to
  start it first, just so you could abandon it.
- Discarding is deliberately lighter than completing. There's no Definition-of-Done
  checklist to tick (confirming that tests pass in order to abandon something never
  made sense), an unreconciled capability warns instead of blocking, and an item
  that's blocked by something else can be discarded freely — waiting forever on a
  dependency is one of the better reasons to give up on a piece of work. You still
  have to confirm, because closing an item is permanent. If the item had its own
  work branch, TCW cleans up the working copy but keeps the branch, and tells you its
  name — abandoning an idea shouldn't quietly delete code you never merged.
- Keeping documentation in step with code is now built into TCW. When you plan or
  finish a piece of work, TCW checks the docs your project has asked it to watch —
  README, changelog, release notes, and more — and flags the ones that need updating.
  This used to rely on a separate plugin; it now comes with TCW itself, so there's
  nothing extra to install.

### Upgrading

Any item already closed as "won't fix", "duplicate", or "superseded" is still filed
under `completed`. Move those folders into `discarded` so one rule holds across your
whole history — `tcw validate` tells you which items disagree. See
[`docs/migration-guide-0.14.X-to-0.15.0.md`](../migration-guide-0.14.X-to-0.15.0.md).
