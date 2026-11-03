## Fixed

- `tcw migrate` (C16) converts an entry under `taxonomy:` in an item's
  `capabilities.yaml` whose first part is a listed child project's ID to
  `<child>.taxonomy/<rest>` (`legacy.route_term_entry_3x`, called from
  `references.Owners.owner_of`), as `route_entry_3x` already did for the
  capability lists. 3.x's reading is kept where it names an `extends` source
  or finds the whole path in the project's own or an inherited taxonomy.
  Where the child's ID is also a first folder of one of those taxonomies,
  the run is refused with B10; the `TermClash` it returns names each project
  that has the folder and offers one full identifier per reading. Before
  this, such entries became `<project>.taxonomy/<child>/<rest>`, which
  `tcw validate` reported as unresolvable in a project keeping no taxonomy.
  (TCW-119)

## Changed

- The 3.x to 4.0 migration guide says that in a Jira-mode project plain
  `tcw validate`, and the check `tcw migrate` runs after a real run, do not
  check what items' `capabilities.yaml` files declare; the Jira order gains
  a fourth step, `tcw validate --remote`. Its B10 bullet and "Names and
  addresses" section describe the child-prefixed entries. (TCW-119)
