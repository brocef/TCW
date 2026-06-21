# Show priority in the list board

## Product changes

- `tcw work list` displays each item's priority (the integer, or `-` when
  unspecified) as a column, so the priority-driven ordering is legible.

## Technical changes

- Add a priority column to the `_list` row in `tcw/work/cli.py`
  (`slug  status  phase  priority  title  [blocked-by]`); `-` when None,
  mirroring the existing `phase` column. CLI presentation only.

## Meta changes
