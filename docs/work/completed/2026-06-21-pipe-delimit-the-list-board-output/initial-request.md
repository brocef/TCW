# Pipe-delimit the list board output

## Product changes

- `tcw work list` separates fields with ` | ` instead of a tab, so field
  boundaries are visible and unambiguous (titles contain spaces).
  Row: `slug | status | phase | priority | title [| blocked-by: …]`.

## Technical changes

- Swap the `\t` separators in the `_list` row for ` | ` (and the blocked-by
  suffix). CLI presentation only.

## Meta changes
