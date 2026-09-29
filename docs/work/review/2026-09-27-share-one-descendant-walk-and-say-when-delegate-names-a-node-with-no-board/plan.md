# Plan — Share one descendant walk, and say when delegate names a node with no board

## Tasks

1. **Failing tests** — `tests/test_boardless_delegate_and_slices.py`, reusing
   `tests/test_routing_nodes.py`'s `node` and `slice_of`. Criteria 2 and 3 red
   today; 1 and 4 green today (guards) and mutation-checked.
2. **Code** — `tcw/store/fs.py` (`initiative_slices`, `initiative_children`);
   `tcw/work/recursion.py` (`_label`, `_node_stores`, `_tasks_for`, `delegate`).
3. **Full suite.**

## Documentation Sync

- `docs/changelogs/upcoming/<slug>.md` [Any-Code-Change].
- `docs/release-notes/upcoming/<slug>.md` [Public-API]: the `delegate` message.
- Not firing: README, guides, skills, configure references (no command, key or
  file changes; a refusal's wording only).

## Verification

Each criterion by its test; hands-on: the reproduction through `tcw work
delegate` in a scratch graph.
