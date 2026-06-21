# Spec — Show priority in the list board

## Behavior

`tcw work list` rows gain a priority column between `phase` and `title`:

```
<slug>  <status>  <phase|->  <priority|->  <title>[\tblocked-by: …]
```

Priority shows the integer, or `-` when unspecified (mirrors the `phase`
column's `-` default). Ordering is unchanged (already priority-then-topo).

## Where

CLI presentation only (`_list` in `tcw/work/cli.py`). No store/model change.
No positional parsers consume `list` output (grep-confirmed), so adding a
column is safe.

## Capability delta

- **Changed:** `work#view-the-board` — the row now includes priority.
