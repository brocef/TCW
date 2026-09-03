# Plan — `tcw provision` fetches a project the checkout already has

Compressed planning, agreed for a change of this size: one task, one test file.

## Tasks

### 1. Skip a declaration for a project already reachable here

**Modifies** `tcw/cli.py`.

In `_provision_nodes`, build the reachable-id set from the starting node's
registry (`current`, `ancestors()`, `descendants()`) before the queue is worked,
and add each obtained node's id as the walk learns it. Before obtaining, skip a
queued entry whose id is in the set and print the same `already available` line
a present store prints. `--refresh` bypasses the skip.

**Proves it:** `tests/test_store_provisioning.py` — a three-node graph where an
obtained node declares a repository for a project the starting checkout already
has: nothing is cloned for it, the run reports it available, and one cache
directory exists rather than two. A genuinely absent sibling in the same run is
still obtained. `--refresh` still contacts the remote for a present project.

### 2. Documentation Sync

- **`docs/changelogs/upcoming.md`** — [Any-Code-Change]. Fires. Fixed: the node
  walk skips a project the checkout already has.
- **`docs/capabilities/cli/provision-declared-stores/`** — recorded as changed;
  its "running it again does nothing" promise extends to projects.
- **`README.md`** — [Public-API]. Fires only if it states the walk's skip rule;
  the transitive paragraph should say a project already here is not fetched.
- **`docs/release-notes/upcoming.md`** — folded into the existing entry for
  connected-project declarations rather than given its own; the two ship
  together and a user reading the notes never saw the intermediate behavior.

## Verification

Re-run the real reproduction: `tcw provision --dry-run` in `apps/server` of a
`proposit-app`-only checkout, with the orchestration node's merged configuration
in place, and confirm `proposit-app-repo` is reported available rather than
planned for cloning. That is the case this exists for, and a fixture is not a
substitute for it.
