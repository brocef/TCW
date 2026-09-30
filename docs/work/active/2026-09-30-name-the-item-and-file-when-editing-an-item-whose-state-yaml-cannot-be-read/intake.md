## Inbox manifest

- `2026-09-29-editing-a-damaged-item-gives-a-bare-yaml-error.md`

## Inbox body

# Editing an item whose state.yaml is damaged gives a bare YAML parser message

Found reviewing `2026-09-29-see-a-blocker-cycle-that-runs-through-an-item-whose-state-yaml-cannot-be-read`.

With an item's `state.yaml` overwritten by `key: [unclosed`,
`tcw work edit <slug> --blocked-by <other>` fails with only
`tcw: while parsing a flow sequence …` — it names neither the item nor the
file. The refusal is right; the message should say which item and which file
cannot be read, and that `tcw validate` lists it, as `_require_readable_state`
does for moves.
