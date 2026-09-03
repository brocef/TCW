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
