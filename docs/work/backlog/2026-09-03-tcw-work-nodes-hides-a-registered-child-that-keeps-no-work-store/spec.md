# Spec — `tcw work nodes` hides a registered child that keeps no work store

## Capability changes

- **changed** — `work/inspect-the-node-topology`. Its body says a registered
  project whose work store cannot be opened is omitted, "so what this prints is
  the set of nodes the cross-node operations can actually reach". That was a
  reasonable contract when no legitimate node kept no board; now that a routing
  node is a supported shape, omitting it silently makes the command lie about the
  graph.

## Problem

`_nodes` in `tcw/work/cli.py` builds its children list from `child_nodes`, which
is documented as "direct registered children that contain a work store"
(`tcw/store/fs.py`). A routing node — registered, reciprocal, keeping no board —
is filtered out, and a node whose only child is one prints
`children: (none — leaf)`.

Reproduced at the orchestration root of the Proposit workspace with every
repository present: `proposit-app-repo` is a registered child and the command
reports the node as a leaf.

The parent line already handles this. `registered_parent` was added alongside
routing-node support so `parent: <id> (no work store)` could be printed instead
of `(none — root)`. The children line was left on the filtered helper.

## Goals

- Every registered child is listed, with the ones keeping no work store marked.
- `(none — leaf)` means no registered children.
- `child_nodes` is unchanged — the cross-node operations want the filtered set,
  and this is a display question.

## Non-goals

- Changing what `child_nodes`, `descendant_nodes` or `parent_node` mean.
- Listing anything not registered.

## Design

Add `registered_children(root)` beside `registered_parent`, returning the
registry's direct children unfiltered. `_nodes` lists those, appending
`(no work store)` to each that `_has_work_store` rejects — the same annotation
the parent line uses, so the two halves read alike.

**Litmus test.** A node relation query answered in ids by the registry.

## Acceptance criteria

1. A node whose only registered child keeps no work store lists that child,
   marked `(no work store)`, instead of `(none — leaf)`.
2. A node with a mix lists both, and only the boardless one is marked.
3. A node with no registered children still prints `children: (none — leaf)`.
4. The parent line is unchanged.
5. `child_nodes` still returns only children with a store, asserted by the
   cross-node tests passing unchanged.

## Risks

- **A reader may take the listing as "these can receive work".** That is what it
  meant before. The `(no work store)` marker is the whole mitigation, and it is
  the same one the parent line relies on — so the two are consistent, which is
  the best available answer.
