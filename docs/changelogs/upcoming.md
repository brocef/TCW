# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Changed

- **A `connected-projects` locator naming nothing on this machine is no longer a
  graph problem.** `ProjectRegistry` now separates *unreachable* projects from
  *problems*: the project drops out of the graph, `require_valid()` accepts, and
  the commands that do not need it keep working. Everything else the registry
  refused still fails closed — invalid or duplicate project IDs, cycles,
  unparseable YAML, a registered key disagreeing with its target's ID.
- **Reciprocity is no longer disproved by an absent counterpart.** Two nodes
  naming each other at paths belonging to different machines validate; a
  counterpart that is present and points elsewhere still fails.
- **`tcw validate` reports unreachable connections** on every run — named,
  located, and not counted toward the exit status.
- **`extends`, a qualified work ref, and `tcw capabilities extends` name a
  declared-but-absent project** instead of reporting it as never registered.
- **The `start` gate distinguishes an unresolvable initiative epic from an
  inactive one**, and names the connected projects this checkout is missing.

## Added

- `ProjectRegistry.unreachable()` and `UnreachableProject` on the
  storage-neutral store interface; `FsProjectRegistry.unreachable_project(id)`
  for the message sites.

## Added (connected-project declarations)

- **`connected-projects` entries accept `{path, repository}`** beside the bare
  locator string, parsed by `parse_connected_entry` and resolved through the
  same ladder a component store uses. `ConnectedProject` is the parsed form;
  `_Config.parent`/`.children` now hold it.
- **`tcw provision` obtains declared connected projects, transitively.** The walk
  terminates on the resolved checkout path — keyed on `(url, ref)` — so one
  working copy serves every entry naming the same repository and a cycle
  revisits nothing. `--dry-run` covers the queue and reports that an unobtained
  node's own declarations cannot be listed yet.
- `declared_connected_projects()` reads the entries straight from the config, as
  `declared_repository()` does, so it can answer for a graph that will not load.
- `NODE_TARGET` extends the provisioner to a node: availability is a sentinel
  file, and a repository carrying none at the declared path is refused before
  anything is put in place.
- `UnreachableProject.declaration` carries the declaration, so every message that
  named an absent project now names its remote and says to run `tcw provision`.

## Internal

- `tcw/store/checkouts.py` holds the `(url, ref)` → working-copy-directory
  computation, which `fs.py` and `project.py` both need and neither may import
  from the other.

## Fixed (routing nodes)

- **`nearest_work_ancestor()`** replaces `parent_node()` in every upward walk —
  `FsWorkStore.initiative_epic`, the descendant board's ownership walk, and
  `escalate`. One `registry.ancestors()` traversal rather than repeated single
  hops, so a filter cannot truncate it.
- **`FsWorkStore.initiative_children`** uses `descendant_nodes` instead of
  `child_nodes`, so a slice below a storeless node is found. The two directions
  had disagreed about whether such a node is passable.
- **`registered_parent()`** exposes the direct parent without the store filter;
  `tcw work nodes` prints `parent: <id> (no work store)` and `escalate` refuses
  with "no registered ancestor keeps a work store" rather than claiming the node
  is the root.
- `parent_node()` is unchanged and still means the direct parent that keeps a
  board.

## Added (resolved-item retention)

- **`work.retain`** — a mapping of resolved status to boolean, parsed by
  `parse_retention`. Defaults every status to `True`. Unlike the repository
  parser it does **not** fail closed to "nothing declared": a malformed setting
  returns the safe value *and* a problem, which `tcw validate` surfaces.
- **Auto-delete writes two commits.** `FsWorkStore.delete_resolved` removes the
  folder and records the *previous* commit as the tombstone's `location` — the
  record points back one commit rather than at itself, since a SHA cannot
  contain itself. Re-runnable, and treats an already-absent folder as done.
- **`Tombstone.location`** is a new opaque field, absent on every existing
  record. `FsWorkStore.describe_location` resolves it before display, so a
  handle that no longer exists is reported rather than printed.
- **The interlock**: a resolving transition with `retain: false` into a
  gitignored folder is refused before the move, naming the rules to remove.
- **`tcw work show <slug>`** answers from the graveyard when the item is gone.
- `tcw work init` writes no ignore rules for a status named in `retain`;
  `resolved_ignore_rules(statuses=…)` takes the subset.
- `WorkStore.transition` returns the settled item, or the moved item where
  retention deleted it — re-reading would report it missing, which is true of
  the store and false of the transition.
