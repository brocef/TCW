# Migrating from 0.12.x to 1.0.0

Version 1.0 replaces filesystem project discovery and component path aliases
with a registered project graph. This is intentionally breaking and has no
compatibility aliases or scan fallback.

## 1. Assign every project an ID

Choose an immutable lowercase kebab-case ID for every TCW node:

```sh
cd /path/to/project
tcw init --id my-project
```

This backfills an existing `tcw-config.yaml` while preserving tags and other
configuration. IDs must match `^[a-z0-9]+(?:-[a-z0-9]+)*$`; `t`, `c`, `w`,
`local`, and work-status names are reserved.

## 2. Register reciprocal direct connections

Declare direct children on the parent and the one direct parent on each child:

```yaml
# parent/tcw-config.yaml
id: parent-project
connected-projects:
  children:
    child-project: ../child
```

```yaml
# child/tcw-config.yaml
id: child-project
connected-projects:
  parent:
    parent-project: ../parent
```

Locators may be absolute or relative to the config directory. Do not use `~` or
environment variables. Register only direct edges; TCW derives ancestors and
descendants. Both sides must name the target's actual ID and resolve back to one
another.

## 3. Convert component inheritance

Replace every alias-to-path map:

```yaml
extends:
  shared: ../shared-repo
```

with a list of registered project IDs:

```yaml
extends:
  - shared-project
```

Do this independently in `docs/taxonomy/config.yaml` and
`docs/capabilities/.config.yaml`. A connection alone does not imply inheritance.
The source project ID replaces the old alias as the inherited namespace.

The CLI now accepts one ID:

```sh
tcw taxonomy extends add shared-project
tcw capabilities extends shared-project
```

## 4. Replace path-qualified references

- Change descendant work addresses from `sub/path/<slug>` to
  `<descendant-project-id>/<slug>`.
- Change taxonomy/capability namespace aliases in `tcw://` links and structured
  refs to the source project ID.
- Keep bare references unchanged; they remain local.

Work qualifiers resolve only among registered descendants. Taxonomy and
capability qualifiers resolve only through that axis's explicit `extends` list.

## 5. Validate before continuing

```sh
tcw validate
tcw taxonomy check
tcw capabilities check
tcw work nodes
```

Validation fails closed on ID-less nodes, invalid or duplicate IDs, malformed or
duplicate YAML keys, missing targets, key/target mismatches, nonreciprocal
connections, multiple parents, cycles, legacy `extends` maps, and unreachable
inheritance targets. Fix the graph; TCW will not infer IDs, scan nearby folders,
or accept legacy path qualifiers.
