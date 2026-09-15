# Spec — Pipe-delimit the list board output

## Behavior

`tcw work list` rows use ` | ` as the field delimiter (was a tab):

```
<slug> | <status> | <phase|-> | <priority|-> | <title>[ | blocked-by: …]
```

## Where

CLI presentation only (`_list` in `tcw/work/cli.py`). No store/model change.
No positional parsers consume `list` output (grep-confirmed earlier), so the
delimiter swap is safe; the one test that splits the row updates to ` | `.

## Capability delta

- **Changed:** `work#view-the-board` — the row is now `|`-delimited.
