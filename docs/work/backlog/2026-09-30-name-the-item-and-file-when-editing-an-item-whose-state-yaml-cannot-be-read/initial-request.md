# Name the item and file when editing an item whose state.yaml cannot be read

## What is wanted

When `tcw work edit` meets an item whose `state.yaml` cannot be parsed, it should
say which item and which file it could not read, and that `tcw validate` lists
such items, rather than printing only the YAML parser's message.

Reproduction from the entry: overwrite an item's `state.yaml` with
`key: [unclosed`, then run `tcw work edit <slug> --blocked-by <other>`. It
fails with only `tcw: while parsing a flow sequence …`.

Refusing is correct; only the message is wrong. Moves already give the wanted
kind of message through `_require_readable_state`, which is the model to match.

## Notes

- Found reviewing
  `2026-09-29-see-a-blocker-cycle-that-runs-through-an-item-whose-state-yaml-cannot-be-read`.
- Whether other verbs besides `edit` give the same bare message is for spec to
  find out.
- Reference material: asked; none provided beyond the entry.
- Written at triage from the entry; the maintainer raised no questions on it.
