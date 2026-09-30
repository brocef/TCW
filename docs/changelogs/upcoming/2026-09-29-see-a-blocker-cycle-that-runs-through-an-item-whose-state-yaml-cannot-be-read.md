## Fixed

- A blocker edit whose cycle check cannot see through an item on the path is
  refused instead of accepted unchecked. The walk (`WorkStore._reaches`) now
  collects each item whose blockers are unknown — a damaged `state.yaml`
  (new hook `WorkStore.unreadable_reason`), or a slug more than one folder holds
  (`MultipleMatch`) — and one helper, `_refuse_blocker_walks`, decides after
  every walk: a cycle wins, otherwise the unknown items refuse the edit, named
  with their project id when in another project (new hook
  `WorkStore._item_label`). `--blocks` decides across all of the item's
  blockers together. Interrupted claims and unreachable projects stay silent.
  Applies to `--blocked-by`, `--blocks`, `update_work` and `create_work`.
