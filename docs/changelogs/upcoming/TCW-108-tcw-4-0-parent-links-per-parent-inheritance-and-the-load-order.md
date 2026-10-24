## Added

- `tcw/store/links.py`: `parse_parents` and `parse_children`, the readers of a
  project's `parents:` and `children:`, each giving its problems by entry.
  (TCW-108)
- `tcw/store/base.py`: `ParentLink` (a parent's ID and the axes it passes,
  from `AXES`), `LoadOrder` (the IDs, the missing and unreadable ones, and the
  fallback warning), `load_order_of` (C3 over the parent lists, depth-first
  with a warning when C3 finds no order), `find_loop`, `loop_message` and
  `passing`. (TCW-108)
- `ProjectRegistry`: `parents`, `load_order`, `sources(axis)` (the projects
  whose content reaches a project for an axis, in load order, raising
  `InheritedUnavailable` for one not available), `passing_in`,
  `inherited_unavailable`, `link_state`, `order_project`, `absent_note`,
  `link_problem` and `personal_child_ids`. (TCW-108)
- `InheritedUnavailable` and exit code 7, `INHERITED_UNAVAILABLE`, for a
  command that needs something inherited that is not available here.
  (TCW-108)
- `tcw projects list --json`: `inherit` on a parent row, `personal` on a child
  row, `read-only` on every row but the current one, and the top-level
  `load-order`, `load-order-complete` and `load-order-warning`. (TCW-108)
- `tcw serve`'s project answer gives each connected project's `readOnly`.
  (TCW-108)
- `tcw.config.LOCAL_ONLY_KEYS`: `children`, which only a project's own files
  may set. (TCW-108)

## Changed

- The registry walks up through `parents:` and down through listed
  `children:`, never to a sibling; a project read only to look another up is
  kept apart from the family. `ancestors`, `descendants`, `get`, `projects`
  and `read_only_reason` follow parent links; TCW-107's lookup order asks the
  manifests of every parent. (TCW-108)
- A listed child must name its parent; a parent need not list its child.
  (TCW-108)
- `_extended_component_stores` and both `extends_add` methods hold `extends`
  to the parent links, through the command's registry: an ID the links do not
  pass the axis from is refused (exit 1 when read, exit 2 when added), and one
  not available here raises `InheritedUnavailable`. (TCW-108)
- `tcw validate` (`_cmd_validate`): a load-order warning; one finding per
  project of the family that is not available, saying what could not be
  checked, including the taxonomy or capabilities a store check stopped at;
  `_run_check` and `validate` take an `unavailable` list. (TCW-108)
- `tcw.config._allowed` and `_merge`: `children` is allowed in
  `.tcw/tcw-config.local.yaml`, refused in the user-wide file, and the
  personal list is added after the committed one. (TCW-108)
- `unreachable()` keeps one record per project. (TCW-108)
- `tcw.projects_cli.connected` takes an optional registry. (TCW-108)
- The web client's `TConnectedProject` has `readOnly` in place of `upstream`,
  and the create form marks a project `(read-only from here)`. (TCW-108)

## Removed

- The `projects:` key and its `parent`, `children` and `upstream` relations;
  it is refused with the message that names `parents:`, `children:` and the
  manifest. `REMOVED_LINK_KEYS` and `retired_key_problem(config, keys)` give
  it. (TCW-108)
- The upstream relation and its bookkeeping, `parent()`, `declared_parent_id`,
  `declared_upstream_ids`, `entry()`, `ConnectedProject`,
  `parse_connected_entry`, and filing into a project not on this machine
  through a `jira` block. (TCW-108)
- The single-parent helpers `child_projects`, `_routed`, `routed_children`,
  `routed_unreachable_children`, `parent_project`, `registered_parent`,
  `registered_children`, `unreachable_parent`, `unreachable_children`,
  `descendant_projects` and `registered_project_id`. (TCW-108)
- `_validate_reciprocity` and `_validate_cycles`. (TCW-108)

## Internal

- Every fixture writes `parents:` and `children:`; `connect_projects(root,
relation, *ids, inherit=...)` in `tests/projectfiles.py` and `connect(a, b,
relation, *, inherit=...)` in `tests/work/projects.py` take what a parent
  passes. (TCW-108)
- `tests/test_parent_links_static.py` fails on any test that still writes
  `projects:` outside the tests of its refusal, and on any removed helper
  defined in `tcw/`. (TCW-108)
- `tests/test_parent_links.py` and `tests/test_parent_links_cli.py`; and
  `tests/test_load_order.py`, with a property test of the load order against
  Python's own C3. (TCW-108)
