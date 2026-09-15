# Registered project graph and stable project IDs — specification

## Capability changes

- `cli/host-multiple-projects-in-one-repo`: replace directory-descendant
  discovery and path-qualified identity with an explicitly connected graph whose
  nodes have stable project IDs and may live anywhere on the filesystem.
- `cli/scaffold-the-doc-trees`: require `--id` for new nodes, reuse the
  configured ID when omitted on existing nodes, reject conflicting IDs, and
  backfill an existing marker without discarding other configuration.
- `cli/validate-a-node`: validate the current project graph on every invocation,
  including narrowed file/directory validation, while retaining bounded
  component-store checks.
- `cli/reference-a-tcw-object`: interpret cross-project namespaces as canonical
  project IDs. Work targets are limited to registered descendants; taxonomy and
  capability targets are limited to each axis's explicit inheritance list.
- `taxonomy/federate-shared-vocabulary`: replace alias-to-path mappings with an
  explicit list of registered project IDs; the project ID is the inherited
  namespace.
- `capabilities/federate`: make the same explicit project-ID inheritance change
  for capabilities, independently of taxonomy.
- `work/view-the-board`: group descendant boards by project ID and qualify every
  descendant item as `<project-id>/<slug>`, including deep descendants.
- `web`: use project IDs in routes and cross-project navigation, and source
  hosted descendants only from the registry.
- Create the `connected-project-registry` taxonomy Feature over `node`,
  `namespace`, and `reference`, then associate all eight changed capabilities
  with it.

## Problem

TCW currently mixes node selection with several filesystem-discovery mechanisms.
Nearest-sentinel upward lookup correctly selects the active node, but topology
operations in `tcw/store/fs.py` recursively inspect descendants, consult git
state and ignore rules, and treat relative paths or federation aliases as
identity. The work CLI, reference resolver, federation stores, validation, and
web server build on those assumptions.

That behavior is not storage-abstracted, cannot represent connected projects
outside a directory tree, can visit large unrelated trees, and makes identity
change when a project moves. It also permits a configured path or inferred
filesystem relationship to stand in for explicit project membership.

## Goals

1. Give every TCW node one canonical, validated, human-chosen project ID.
2. Represent direct parent/child connections through an abstract registry with
   opaque locators and reciprocal declarations.
3. Derive ancestors and descendants transitively from registered edges only.
4. Make every cross-project consumer use project IDs and registered resolution.
5. Preserve explicit, per-axis taxonomy and capability inheritance.
6. Fail closed with actionable migration errors for every legacy, missing, or
   inconsistent configuration.
7. Prove that topology resolution neither walks directories nor invokes git.

## Non-goals

- Automatic ID inference, compatibility aliases, or legacy path-qualifier
  support.
- Automatic registration by scanning the filesystem or git metadata.
- Environment-variable or `~` expansion in filesystem locators.
- Remote registry adapters, URL locators, version pinning, or automatic project
  relocation.
- Inferring taxonomy or capability inheritance from a parent/child connection.
- Supporting general graph joins or multiple parents; connected projects form a
  rooted tree.

## Current-state findings

- `tcw/store/fs.py` owns nearest-sentinel selection (`find_node_root`) alongside
  `child_nodes`, `descendant_nodes`, and `resolve_qualified_work_ref`. The latter
  operations currently derive topology and identity from filesystem structure,
  git worktrees, ignore rules, and path segments.
- `FsWorkStore.child_stores()` and work CLI coordination consume discovered
  child/descendant stores for boards, epics, delegation, escalation, and
  reconciliation.
- `FsTaxonomyStore` and `FsCapabilitiesStore` read `extends` as alias-to-path
  maps, recursively open those paths, and expose the alias as `origin`.
- The abstract stores in `tcw/store/base.py` expose component federation
  mutations but no project-registry abstraction.
- `tcw/cli.py` initialization writes the sentinel without a canonical identity;
  component init mirrors share the same behavior.
- `tcw/validation.py` resolves `tcw://` namespaces through component aliases and
  filesystem descendant paths.
- `tcw/serve/` builds descendant routing and work aggregation on path-qualified
  nodes.
- Existing tests in `tests/test_nodes.py`, `tests/test_qualified_ref.py`,
  `tests/test_taxonomy.py`, `tests/test_capabilities*.py`,
  `tests/test_validate.py`, `tests/test_work.py`, and `tests/test_serve.py`
  encode the legacy scanning, alias-map, and path-qualification contracts and
  require deliberate breaking migration.

## Configuration contract

Each node's `tcw-config.yaml` has this top-level shape:

```yaml
id: this-project
connected-projects:
  children:
    child-a: /some/absolute/path
    child-b: ../relative/path
  parent:
    orchestrator-project: ../
work:
  tags:
    - existing-tag
```

- `id` is required for every command and matches
  `^[a-z0-9]+(?:-[a-z0-9]+)*$`.
- `t`, `c`, `w`, `local`, and every work status name are reserved.
- `connected-projects` is optional. When present it is a mapping containing only
  `children` and/or `parent`.
- `children` is a mapping of direct child project ID to opaque locator.
- `parent` is absent or a mapping with exactly one project-ID/locator entry.
- Mapping keys must be unique at every relevant YAML level.
- For the filesystem adapter, a locator is a nonempty string. Absolute paths are
  used directly; relative paths resolve against the directory containing the
  declaring `tcw-config.yaml`. No other expansion occurs.
- Tags, component settings, and unknown future top-level configuration survive
  ID backfill and connection edits.

Taxonomy and capability store configuration changes from an alias map to:

```yaml
extends:
  - shared-project
```

The listed ID must be reachable in the current node's registered graph. The
source project ID is also the inherited namespace and `origin`; there is no
independent alias.

## Abstract registry contract

Add a storage-neutral `ProjectRegistry` interface whose vocabulary is:

- the current project ID;
- a project record containing ID and opaque locator/handle;
- direct parent and direct children;
- lookup by project ID within the connected graph;
- ordered ancestors;
- ordered descendants.

The interface does not expose paths, directory traversal, YAML, git, worktrees,
or globbing. It may expose a validation result or fail with typed/value errors
that adapters translate into clear CLI diagnostics.

`FsProjectRegistry` realizes the interface from `tcw-config.yaml`. It starts at
the already-selected nearest sentinel, follows only declared locators, and
caches each canonical config path once for the registry instance/process-level
operation. No topology method invokes git or enumerates directory contents.

## Graph invariants and validation

Loading or validating the registry checks:

- the current and every reached node has a valid, nonreserved ID;
- each locator target exists and contains a `tcw-config.yaml`;
- each registration key equals the target config's `id`;
- a child's `parent` points back to the declaring node, and a parent's
  `children` points back to the declaring child;
- reciprocal locators resolve to the same canonical pair of configs;
- a node declares at most one parent;
- one project ID identifies only one reached config, and one config does not
  appear under multiple IDs;
- the connected graph contains no cycles;
- YAML contains no duplicate keys;
- `connected-projects`, `children`, `parent`, and locators have the documented
  shapes;
- component `extends` is a list of unique project IDs, not a legacy map, and
  each target is reachable.

Errors identify the config and relation involved and include migration guidance
for ID-less nodes, legacy `extends` maps, and path-qualified usage. All commands
fail before component behavior when the current graph is invalid.

## Initialization behavior

- `tcw init` and `tcw taxonomy|capabilities|work init` accept `--id <id>`.
- A directory without `tcw-config.yaml` requires `--id`.
- An existing configured node may omit `--id` and reuses its ID.
- Supplying the existing ID is idempotent; supplying a different ID fails.
- `tcw init --id <id>` backfills a legacy marker that has no ID, preserving
  tags, component configuration, and other keys.
- An invalid/reserved ID fails before scaffolding or writing.
- Initialization remains limited to a git work tree; nearest-sentinel selection
  remains unchanged after initialization.

## Cross-project behavior

### Work

- A bare work slug or status locator remains local.
- A qualified work reference is exactly `<project-id>/<slug>`. The qualifier
  must name a registered transitive descendant of the current project.
- Deep descendants use their own ID, not an ancestry path.
- `work nodes`, `list --include-descendants`, web aggregation, epic rollups,
  inbox `from:` metadata, delegation, escalation, and reconcile display and
  persist project IDs.
- Registered ancestors support escalation; registered direct children support
  delegation. Consumers never infer a relationship from physical placement.

### Taxonomy and capabilities

- `extends add` accepts exactly one registered project ID; `extends rm` accepts
  that ID.
- Only IDs in the axis's explicit `extends` list participate in lookup.
- A connection alone grants no inherited visibility.
- Inherited objects qualify as `<project-id>/<object-path>`.
- Existing override semantics remain, with project ID replacing alias as
  `origin` and in override targets.
- Inheritance-cycle and ambiguity checks remain and operate on project IDs.

### References and web

- `tcw://T/...`, `tcw://C/...`, and `tcw://W/...` remain local when unqualified.
- Work namespaces resolve registered descendants only.
- Taxonomy/capability namespaces resolve only explicit axis inheritance.
- Web routes use project IDs as the node segment and reject unknown or
  unhosted IDs. Rendered foreign or dangling links remain inert.

## Validation behavior

`tcw validate [path]` always constructs and validates the current project
registry before applying path narrowing. Narrowing still bounds YAML, Markdown,
taxonomy, capability, and work-store checks to their existing scope; it never
narrows away graph validity. Component `check` commands validate their bounded
stores and explicit inheritance, including legacy shape and reachability errors.

## Acceptance criteria

1. Arbitrarily placed sibling, parent, child, and deep-descendant nodes resolve
   through relative and absolute registered locators.
2. Moving a registered project requires only locator updates; its ID-qualified
   references remain stable.
3. Unregistered valid nodes, copied worktree sentinels, ignored directories, and
   huge decoy trees are never opened or returned.
4. Registry instrumentation demonstrates one config read per reached node, no
   directory walk, and no git subprocess.
5. Every invalid graph/config case described above fails clearly and before
   normal command output.
6. New initialization, ID backfill, preservation, idempotence, and conflict
   behavior match the contract for top-level and component init commands.
7. Work CLI/web topology and coordination operate by project ID across arbitrary
   layouts.
8. Taxonomy and capability federation uses ID lists, preserves explicit
   selection/overrides/cycle detection, and rejects legacy maps.
9. `tcw validate`, component checks, reference resolution, and web navigation
   fail closed on unknown/unreachable IDs.
10. Public docs, migration guide, taxonomy, capabilities, release notes,
    changelog, and all three driving skills describe only the new model.

## Risks and dependencies

- This intentionally breaks every existing ID-less node, alias/path `extends`
  declaration, and path-qualified work or `tcw://` reference; migration
  diagnostics and documentation must land atomically with the code.
- `tcw init --id` must be usable to bootstrap migration even though normal
  commands fail on an ID-less node.
- Registry validation must avoid recursion ambiguity and preserve deterministic
  error ordering for tests and users.
- Worktree lifecycle operations still legitimately use git; only topology
  discovery must stop doing so.
- The registry should be passed or constructed consistently so component stores
  do not independently reread the same graph and defeat caching.

## Related work

- `2026-06-22-node-sentinel-tcw-config-yaml-and-sentinel-based-node-detection`
- `2026-07-01-aggregate-descendant-node-boards-in-work-list-include-descendants`
- `2026-07-04-subproject-qualified-slugs-for-descendant-work-items`
- `2026-07-08-child-nodes-walk-hangs-on-node-modules-epic-complete-nodes-reconcile`
- `2026-07-10-add-tcw-reference-protocol-tcw-validate-and-web-view-link-navigation`
- `2026-07-10-unify-folder-substrate-across-taxonomy-capabilities-work-and-add-capability-federation`
- `2026-07-01-transitive-taxonomy-inheritance` may be superseded in part by the
  registered-graph foundation but remains separately scoped unless explicitly
  reconciled during implementation.
