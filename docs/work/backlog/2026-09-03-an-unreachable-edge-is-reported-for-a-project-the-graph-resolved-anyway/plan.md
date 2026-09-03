# Plan — An unreachable edge is reported for a project the graph resolved anyway

Compressed planning, for a one-function change.

## Tasks

### 1. Filter the accessor by what the graph holds

**Modifies** `tcw/store/project.py`.

`unreachable()` returns only entries whose `id` is not in `self._by_id`.
`unreachable_project` already reads through it. Recording is untouched, so the
order edges are walked in cannot matter.

**Proves it:** `tests/test_project_registry.py` — a graph where a child resolves
its parent while the parent's own locator for the child does not, asserting
nothing unreachable and `unreachable_project` `None`; the existing absent-project
tests unchanged.

### 2. Documentation Sync

- **`docs/changelogs/upcoming.md`** — [Any-Code-Change]. Fires. Fixed: an
  unreachable report is per project, not per edge.
- **`docs/capabilities/cli/host-multiple-projects-in-one-repo/`** — recorded as
  changed; its promise about naming unfollowable connections becomes true.
- **`README.md`** — [Public-API]. The paragraph added earlier says `tcw validate`
  names each connection it could not follow; reword to *project* so it does not
  promise per-edge reporting.
- **`docs/release-notes/upcoming.md`** — folded into the existing partial-graph
  entry; a user never saw the intermediate behavior.

## Verification

Re-run `tcw validate` in `apps/server` of the `proposit-app`-only checkout with
orchestration and core provisioned, and confirm the two false reports are gone
and the run is still clean.
