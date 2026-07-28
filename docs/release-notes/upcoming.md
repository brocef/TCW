# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Two new commands for keeping docs in step with code

- **`/tcw-docs-sync-setup`** walks you through adding a Documentation Sync
  section to your project's `CLAUDE.md` — which files to keep current, when each
  one needs updating, and how updates should be written — then creates the files
  and folders it lists.
- **`/tcw-cut-version`** cuts a new release: it helps you pick how big the
  version bump should be, updates every file that carries the version number,
  files the pending release notes and changelog under the new version, commits,
  and tags. If your project already has its own release script, it runs that
  instead. Pushing stays your call.

Both are also available by asking for the `documentation-sync` skill directly,
so Codex users get the same behavior without slash commands.

## Documentation now updates at a fixed point in the work lifecycle

Documentation used to be something an assistant might touch at any point while
working an item. It now happens at one place: **once all the work is finished
and the tests pass, before the item is handed back to you.** Planning still
lists the documents a change is expected to touch — now grouped at the end of
the plan, where they'll actually be written.

The upshot is that when you're asked to review finished work, its documentation
is already part of what you're reviewing. And you're offered a version bump
after the item closes, not in the middle of it.
