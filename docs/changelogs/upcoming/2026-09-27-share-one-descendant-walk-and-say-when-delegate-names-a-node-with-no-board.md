## Changed

- `FsWorkStore.initiative_slices(epic)` returns `(node root, item)` for every
  slice here and below; `initiative_children` (the completion gate) and
  `recursion._tasks_for` (the `reconcile` table) both read it, so the two can no
  longer drift apart. `_tasks_for` loses its unused `stores` parameter; row
  labels come from one `_label` helper.

## Fixed

- `delegate` to a registered node that keeps no board says "'<ref>' keeps no
  board" and names the nodes with a board below it, instead of "no child node";
  to one whose board is declared but not provisioned, it says the board "is not
  available here" with the provisioning reason.
