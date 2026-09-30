## Fixed

- A blocker edit whose cycle check cannot see through an item on the path is
  refused instead of accepted unchecked. The walk (`WorkStore._reaches`) now
  collects each item whose blockers are unknown — a damaged `state.yaml`
  (new hook `WorkStore.unreadable_reason`), or a slug more than one folder holds
  (`MultipleMatch`) — and one helper, `_refuse_blocker_walks`, decides after
  every walk: a cycle wins, otherwise the unknown items refuse the edit, named
  with their project id when in another project (new hook
  `WorkStore._item_label`). All the blockers one call adds
  (`_check_new_blockers`), and all of an item's blockers for `--blocks`, are
  decided together. The remedy is worded per reason. Interrupted claims and unreachable projects stay silent.
  Applies to `--blocked-by`, `--blocks`, `update_work` and `create_work`.
