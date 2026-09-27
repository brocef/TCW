# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Fixes

- **Re-running `tcw work init` or `tcw init` leaves your `work.path` exactly as you wrote it.**
  It used to rewrite `~/store` as the full path to your own home folder, which
  broke the setting for everyone else sharing the file.

## Fixes

- **`tcw validate` checks a taxonomy or capabilities ledger wherever it lives.**
  A ledger moved out of `docs/` with a `path` setting, or kept in another
  repository, was never checked by `tcw validate`; it now is. Capabilities are
  also checked against a moved taxonomy, so a capability naming a term that does
  not exist is caught there too.
- **`tcw validate` lists a `taxonomy.path` that points nowhere** instead of
  stopping with an internal error.
