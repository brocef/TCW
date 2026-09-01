# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

### Fixed

- **A relative store path resolved to the wrong directory inside a linked git
  worktree.** `FsWorkStore._local_root` and `FsTreeStore._local_root` re-anchored
  a relative `<component>.path` at the **main worktree root**, which broke two
  things. A node nested inside its repository lost its own sub-path, so
  `apps/server`'s relative path was applied from the repository root and the
  store could not be found at all. And re-anchoring ran unconditionally, so a
  path that never leaves the checkout resolved to the primary checkout's store
  while the identical default (`docs/<component>`) did not — contradicting
  `cli/run-from-a-git-worktree`, which already documented the opposite.
  Both hooks now route through a new `anchor_configured_path`, which applies the
  rule `FsProjectRegistry._target_path` already used for `connected-projects`
  locators: re-anchor only on escape, and at this node's counterpart. Absolute
  paths, default stores, and anything outside a worktree are unaffected.
  ([#26](https://github.com/brocef/TCW/issues/26))

### Internal

- `tests/test_environment_hardness.py` gains a nested-node-in-a-linked-worktree
  fixture and coverage for every relative-path shape across all three
  components. The re-anchoring branch previously had no test at all — no test
  anywhere set a relative `<component>.path`.
