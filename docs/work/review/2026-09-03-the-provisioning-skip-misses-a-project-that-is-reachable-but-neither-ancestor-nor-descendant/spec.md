# Spec — The provisioning skip misses a reachable project

## Capability changes

None. `cli/provision-declared-stores` already claims a project it can reach is
never fetched; this makes the claim true in a case it does not currently cover.

## Problem

`_provision_nodes` in `tcw/cli.py` builds the "already have" set as:

    have = {registry.current.id,
            *(p.id for p in registry.ancestors()),
            *(p.id for p in registry.descendants())}

Three relations, chosen because they covered the case in front of the author. A
project that is a **sibling of an ancestor** is in neither, and is exactly what a
workspace looks like: in the Proposit graph, `proposit-core` is a child of the
orchestration node, so from `apps/server` it is a child of a grandparent.

Reproduced with the whole workspace present on disk — the layout where nothing
should be contacted at all:

    → proposit-core: https://github.com/Proposit-App/proposit-core.git at main → …
      proposit-core: would obtain into …

`registry.get("proposit-core")` resolves it. The registry knows; the caller
reconstructed a worse answer.

## Goals

- The skip covers every project the registry can resolve.
- The check is a single question to the registry, so no future relation can be
  forgotten.
- An absent project is still obtained, unchanged.

## Non-goals

- `--refresh`, which still bypasses the skip.
- Any change to what is fetched when a project genuinely is not here.

## Design

Replace the enumerated set with `registry.get(project_id) is not None`, evaluated
against the registry opened at the starting node, plus the ids the walk has
obtained so far. One question, asked of the object whose job it is to answer it.

Keeping the obtained-ids set alongside is still necessary: a project obtained
during this run is not in the starting registry, which was read before it
existed.

**Litmus test.** "Is this project in the graph" is the registry's own
storage-neutral operation. This removes a reconstruction rather than adding
anything.

## Acceptance criteria

1. In a graph where a project is a child of the current node's grandparent and
   present on disk, `tcw provision` reports it already available and clones
   nothing.
2. A project genuinely absent in the same graph is still obtained.
3. `tcw provision` in a workspace holding every repository contacts nothing and
   creates no cache directory.
4. `--refresh` still contacts the remote for a present project.
5. The existing skip test passes unchanged.

## Risks

- **A project in the graph but unusable** would now be skipped. The registry
  contains only nodes it could open — an unreachable one is recorded separately
  and `get()` answers `None` for it — so this inherits that guarantee, as the
  previous item's spec already reasoned.
