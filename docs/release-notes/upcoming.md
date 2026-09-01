# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

### Fixed

- **Working in a git worktree now finds the right store.** If you point a
  project's work, taxonomy or capabilities store somewhere else with a relative
  path, TCW resolves it correctly from inside a linked worktree. Previously a
  project that sits in a subfolder of its repository lost that subfolder along
  the way, so the store could not be found at all and every command reported
  there was no project here — the only workaround was to write an absolute path
  into a file that is checked into git.

  A relative path that points *outside* the checkout still resolves to the same
  store you get from your primary checkout, which is what it is for. A relative
  path that stays *inside* the checkout now belongs to the worktree you are
  standing in, the same way the default store always has. Absolute paths and
  default stores are unchanged, as is everything outside a worktree.
  (Reported in [issue #26](https://github.com/brocef/TCW/issues/26).)
