## Changed

- `FsWorkStore.initiative_slices(epic)` returns `(node root, item)` for every
  slice here and below; `initiative_children` (the completion gate) and
  `recursion._tasks_for` (the `reconcile` table) both read it, so the two can no
  longer drift apart. `_tasks_for` loses its `stores` parameter; row
  labels come from one `_label` helper.

## Fixed

- `delegate` to a node below this one that keeps no board says "'<ref>' keeps
  no board" and names the nodes with a board below it, instead of "no child
  node"; to one that configures a board this checkout cannot open (declared and
  not provisioned, or a broken `work.path`), it says the board "is not
  available here" with the reason. An ancestor or sibling still gets "no child
  node".
