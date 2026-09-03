# Plan — The provisioning skip misses a reachable project

Compressed planning, for a two-line change.

## Tasks

### 1. Ask the registry instead of enumerating relations

**Modifies** `tcw/cli.py`.

Keep the registry opened at the starting node and the set of ids obtained during
the walk. Before obtaining, skip when `registry.get(project_id)` resolves or the
id has already been obtained. Drop the `current`/`ancestors`/`descendants`
reconstruction.

**Proves it:** `tests/test_store_provisioning.py` — a four-node graph
(grandparent, parent, current, and a sibling-of-grandparent present on disk)
where the grandparent declares a repository for that sibling: nothing is cloned,
it is reported available, and no cache directory is created. An absent project in
the same run is still obtained. The existing skip test passes unchanged.

### 2. Documentation Sync

- **`docs/changelogs/upcoming.md`** — [Any-Code-Change]. Fires; fold into the
  existing skip entry rather than adding a second, since the two ship together.
- Nothing else fires: the README and capability wording already say "a project
  this checkout can already reach", which is what the code now implements.

## Verification

Re-run `tcw provision --dry-run` in `apps/server` of the hierarchical workspace —
every repository on disk — and confirm it plans nothing and creates no cache
directory. That is the case this exists for.
