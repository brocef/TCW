Found by an adversarial review of the resolution ladder, 2026-09-04.
Reproduced.

`StoreLocationUnusable`'s docstring scopes it to "it is absent, it is not a
directory, or it lacks the component's layout". `FsWorkStore._open_at` also
raises it for `work.path is not inside a Git repository` — a directory that is
present, is a directory, and has the full six-folder layout. That is "present and
wrong", which the ladder's own contract says must surface rather than fall
through.

With a complete `work.path` store outside any repository and a `work.repository`
declared:

- before provisioning, the error is
  `… run \`tcw provision\`` and `work.path` is never mentioned;
- after `tcw provision` (exit 0), `FsWorkStore.open()` resolves to the cache
  clone rather than to `work.path`.

Every `tcw work` command then reads and writes a different store than the one
configured, and the user's items are invisible with no message anywhere.

The narrowing from `except ValueError` to `except StoreLocationUnusable` fixed
the federation half and did not catch this condition, which was already
mis-scoped before the class existed.
