# Plan: store names are names, never patterns

## Tasks

1. **Tests first** in `tests/test_literal_store_names.py`: criteria 1-4, the
   serve case through a real server.
2. **Claim lookup**: the segment check in `_claiming_dirs`.
3. **Git**: a `_literal(path)` helper in `tcw/store/fs.py`; apply it to each
   pathspec argument (not `git mv`); drop the `--literal-pathspecs` flags it
   replaces; route the graveyard `status` and `cli.py`'s `diff --cached`
   through it.

## Documentation Sync

- Changelog and release notes (fixes).
- No guide documents naming rules for these characters; checked
  `docs/guide/capabilities.md` and `docs/guide/work.md`.

## Verification

Hands-on: the reproduction from the spec with the worktree's `tcw`, and a curl
against `tcw serve` for `%2Fetc%2Fpasswd`.
