# Plan — `tcw work nodes` hides a registered child that keeps no work store

Compressed planning, for a display change.

## Tasks

### 1. List registered children, marking the boardless ones

**Modifies** `tcw/store/fs.py`, `tcw/work/cli.py`.

`registered_children(root)` beside `registered_parent`, returning
`registry.children()` locators unfiltered. `_nodes` iterates those and appends
`(no work store)` where `_has_work_store` is false.

**Proves it:** `tests/test_multiproject.py` — using the existing `_routing_graph`
fixture, `tcw work nodes` at the top lists the routing child marked, and at the
routing node lists its board-keeping child unmarked; a leaf still prints
`(none — leaf)`.

### 2. Documentation Sync

- **`docs/changelogs/upcoming.md`** — [Any-Code-Change]. Fires; folded into the
  routing-node entry, which is where the parent half is recorded.
- **`docs/capabilities/work/inspect-the-node-topology/`** — recorded as changed;
  its "omitted, so this prints what cross-node operations can reach" sentence is
  what this changes.
- **`README.md`** — checked; it does not describe the children line's filtering.

## Verification

`tcw work nodes` at the orchestration root of the hierarchical Proposit
workspace, confirming `proposit-app-repo` appears.
