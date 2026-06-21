# List hides completed items by default

## Product changes

- `tcw work list` with no `--status` filter no longer shows `completed` items —
  the board defaults to the live columns (inbox, backlog, active).
- `--status completed` still lists completed items (explicit filter is honored).
- New `--all` flag re-includes completed items in the unfiltered board (preserves
  the old "everything" view).

## Technical changes

- Filter completed out in the CLI `_list` presentation layer; `WorkStore.board()`
  / `query()` keep their full semantics (litmus: hiding a status is a list
  presentation default any store can apply, not a store-interface operation).

## Meta changes
