# Registered project graph and stable project IDs

## Capability changes

- Change `cli/host-multiple-projects-in-one-repo` to describe canonical project
  IDs, arbitrary filesystem placement, reciprocal registered connections, and
  descendant addressing by project ID.
- Change `cli/scaffold-the-doc-trees` so every new TCW node receives an explicit
  stable ID and existing markers can be backfilled without losing configuration.
- Change `cli/validate-a-node` so validation always checks the registered project
  graph and fails closed on invalid or unreachable registrations.
- Change `cli/reference-a-tcw-object` so cross-project `tcw://` namespaces are
  stable project IDs resolved only through registered graph or explicit
  component inheritance.
- Change `taxonomy/federate-shared-vocabulary` and `capabilities/federate` so
  inheritance is an explicit list of registered project IDs, independent for
  each axis and never implied merely by a project connection.
- Change `work/view-the-board` so descendant boards and qualified work items use
  canonical project IDs, including deep descendants outside the current
  filesystem tree.
- Change `web` so routes, rollups, and cross-project navigation use registered
  project IDs.
- Link all affected capabilities to a new `connected-project-registry` taxonomy
  Feature involving `node`, `namespace`, and `reference`.

## Requested outcome

Replace filesystem discovery with an explicit, storage-abstracted project graph.
Every TCW node has a canonical ID, direct parent/child connections are
reciprocal, and every cross-project traversal follows registered opaque locators.

The filesystem adapter stores the graph in `tcw-config.yaml`:

```yaml
id: this-project
connected-projects:
  children:
    child-a: /some/absolute/path
    child-b: ../or/a/relative/path
    child-c: ./or-just-a-child-folder
  parent:
    orchestrator-project: ../
```

Relative locators resolve from the config directory. `children` contains direct
children only; `parent` is absent or a one-entry mapping. Ancestors and
descendants are derived transitively.

## Constraints and decisions

- Apply the abstraction litmus test: the model exposes project identity,
  relations, opaque locators, lookup, ancestors, and descendants; only the
  filesystem adapter interprets paths and YAML.
- Project IDs match `^[a-z0-9]+(?:-[a-z0-9]+)*$`. Reserve `t`, `c`, `w`,
  `local`, and work-status names.
- IDs are human-chosen, immutable identifiers. Renaming is a coordinated manual
  migration with no compatibility alias.
- Connected projects form a rooted tree: each node has at most one direct
  parent, zero or more direct children, and reciprocal declarations.
- Keep nearest-sentinel upward lookup to select the current node.
- Do not scan directories, inspect git worktrees or ignore rules, infer IDs,
  accept legacy path qualifiers, or fall back to discovery.
- Paths are filesystem-adapter locators, not identity. Do not expand environment
  variables or `~`; absolute and config-relative paths are allowed.
- A registered connection does not imply taxonomy or capability inheritance.
  Each component explicitly lists the registered project IDs it extends.
- Work qualifiers resolve only among the current node's registered descendants.
  Taxonomy and capability references resolve only through their explicit
  inheritance lists. Bare references remain local.
- Invalid, ID-less, malformed, nonreciprocal, cyclic, duplicated, missing, or
  unreachable registrations fail closed with migration guidance.

## Scope

- Add an abstract project-registry interface plus an `FsProjectRegistry` that
  reads only declared configuration locators and caches each config once per
  process.
- Update initialization, all topology consumers, component federation,
  validation, `tcw://` resolution, work coordination, and web routing.
- Remove topology behavior based on child-directory scans, git ignore state,
  worktree discovery, path aliases, and filesystem-relative identity.
- Add comprehensive unit, CLI, integration, and web coverage for arbitrary
  layouts, invalid graphs, fail-closed migration, and proof that undeclared
  nodes and decoy trees are never visited.
- Update taxonomy, capability descriptions, public documentation, migration
  guidance, release notes, changelog, and the three driving skills.

## Lifecycle and release boundary

Checkpoint this request, `spec.md`, and `plan.md` in separate commits. Commit
`tcw work start` separately before implementation. After implementation,
verification, capability reconciliation, and documentation sync, pause for user
acceptance. Complete the item only after approval, then cut the selected breaking
release with `python scripts/cut_version.py major`.
