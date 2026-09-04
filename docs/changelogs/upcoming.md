# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- `ProjectRegistry.unreachable()` and `UnreachableProject` on the
  storage-neutral store interface; `FsProjectRegistry.unreachable_project(id)`
  for the message sites.

### Connected-project declarations

- **`connected-projects` entries accept `{path, repository}`** beside the bare
  locator string, parsed by `parse_connected_entry` and resolved through the
  same ladder a component store uses. `ConnectedProject` is the parsed form;
  `_Config.parent`/`.children` now hold it.
- **`tcw provision` obtains declared connected projects, transitively.** The walk
  terminates on the resolved checkout path — keyed on `(url, ref)` — so one
  working copy serves every entry naming the same repository and a cycle
  revisits nothing. `--dry-run` covers the queue and reports that an unobtained
  node's own declarations cannot be listed yet.
- **A project the graph already resolves elsewhere is never obtained.** A
  declaration lives on whichever node knows about an edge, so an ancestor
  routinely names a repository the caller is standing inside, and the walk took
  that at face value and re-cloned it. Reachability is now settled by asking the
  starting registry for the project id — **asked**, not reconstructed from a
  chosen set of relations: an intermediate version enumerated
  current/ancestors/descendants and missed a sibling of an ancestor, which is
  the shape a workspace has — plus the ids the walk obtains as it goes. The skip
  holds whatever the flags say, `--refresh` included: refreshing means bringing
  a copy `tcw` itself provisioned back to the declared ref, a project resolving
  somewhere other than the copy the declaration would create has no such copy,
  and obtaining one anyway would put a second node in the graph under one id —
  which `require_valid()` then rejects as a duplicate.
- `declared_connected_projects()` reads the entries straight from the config, as
  `declared_repository()` does, so it can answer for a graph that will not load.
- `NODE_TARGET` extends the provisioner to a node: availability is a sentinel
  file, and a repository carrying none at the declared path is refused before
  anything is put in place.
- `UnreachableProject.declaration` carries the declaration, so every message that
  named an absent project now names its remote and says to run `tcw provision`.

### Resolved-item retention

- **`work.retain`** — a mapping of resolved status to boolean, parsed by
  `parse_retention`. Defaults every status to `True`. Unlike the repository
  parser it does **not** fail closed to "nothing declared": a malformed setting
  returns the safe value *and* a problem, which `tcw validate` surfaces.
- **Auto-delete writes two commits.** `FsWorkStore.delete_resolved` removes the
  folder and records the *previous* commit as the tombstone's `location` — the
  record points back one commit rather than at itself, since a SHA cannot
  contain itself. Re-runnable, and treats an already-absent folder as done.
- **`Tombstone.location`** is a new opaque field, absent on every existing
  record. `FsWorkStore.describe_location` resolves it before display, so a
  handle that no longer exists is reported rather than printed.
- **The interlock**: a resolving transition with `retain: false` into a
  gitignored folder is refused before the move, naming the rules to remove.
- **`tcw work show <slug>`** answers from the graveyard when the item is gone.
- `tcw work init` writes no ignore rules for a status named in `retain`;
  `resolved_ignore_rules(statuses=…)` takes the subset.
- `WorkStore.transition` returns the settled item, or the moved item where
  retention deleted it — re-reading would report it missing, which is true of
  the store and false of the transition.

### The auto-delete step

- **`auto-delete`** joins `TRANSITION_IDS` and `LIFECYCLE_STEPS` with
  `moves: completed | discarded → (removed)`. Deliberately **not** in
  `LEGAL_TRANSITIONS`: it changes no status. `postmortem` is the precedent for a
  step that does not.
- `tcw work lifecycle` now lists `auto-delete`.
- **`hook_env` exports `TCW_ITEM_PATH` and `TCW_RESOLUTION`**, omitted rather
  than empty where a transition has neither. The path is passed in by the caller
  — always the store's own answer, never composed from `TCW_NODE_ROOT`.
- **The store no longer deletes on its own.** `FsWorkStore.pending_deletion`
  reports the state; `tcw/work/cli.py::_auto_delete` runs the bindings around
  `delete_resolved`. Running a command is a CLI concern, and a `pre` that
  refuses must leave the item intact — only expressible if the removal is a
  separate call.
- **`tcw work delete <slug>`** finishes a removal a failed archive left pending,
  through the same code path. Refuses a live item and a retained one.
- **`tcw serve` performs no removal**, because it runs no hooks. An item resolved
  there stays in its resolved folder for the CLI.
- `delete_resolved` publishes its own commit — the resolving transition pushed
  before this commit existed.

## Changed

- **A `connected-projects` locator naming nothing on this machine is no longer a
  graph problem.** `ProjectRegistry` now separates *unreachable* projects from
  *problems*: the project drops out of the graph, `require_valid()` accepts, and
  the commands that do not need it keep working. Everything else the registry
  refused still fails closed — invalid or duplicate project IDs, cycles,
  unparseable YAML, a registered key disagreeing with its target's ID.
- **Reciprocity is no longer disproved by an absent counterpart.** Two nodes
  naming each other at paths belonging to different machines validate; a
  counterpart that is present and points elsewhere still fails.
- **`tcw validate` reports each connected project it cannot reach** on every run
  — named, located, and not counted toward the exit status. A project some other
  declaration resolved is not reported.
- **`extends`, a qualified work ref, and `tcw capabilities extends` name a
  declared-but-absent project** instead of reporting it as never registered.
- **The `start` gate distinguishes an unresolvable initiative epic from an
  inactive one**, and names the connected projects this checkout is missing.

## Fixed

### Resolved-item deletion

- **Nothing is removed that git does not already hold.** `delete_resolved` now
  refuses unless the item's path is committed *and* `git status --porcelain
  --ignored` over it is empty. The predicate is cleanliness, not existence: a
  tree at the path proves something was committed there once, not that what is
  about to be deleted is in it — an untracked attachment, a receipt a `pre`
  binding wrote, an edit since the resolving commit, or a whole item `git_mv`
  untracked into a gitignored folder all pass an existence check and die with
  the removal. This is the guard that holds; `_require_deletable` is kept for
  refusing earlier with a better message for its one known cause.
- **The check gates the removal, not the record.** With no folder on disk there
  is nothing to destroy, so the finishable state stays finishable.
- **A re-run no longer downgrades the recorded commit.** The second run's HEAD
  does not hold the item, and `_write_tombstone` assigns outright, so recording
  HEAD again replaced a working reference with a useless one.
- **`delete_resolved` takes the graveyard lock and calls
  `_require_writable_graveyard`**, as a resolving transition does — the
  read-modify-write was dropping a concurrent resolution's tombstone, and a
  damaged graveyard surfaced only after the folder was gone. The lock is
  documented as non-reentrant, with its three top-level acquirers named.
- **The removal is committed at the path git holds**, not one derived from the
  item — a binding that relocated the item left the deletion out of the commit,
  and the push then sent a remote that still had it.
- `describe_location` asks whether the recorded commit holds the store, not
  merely whether the commit exists, and no longer leaks git's own error to
  stderr ahead of the friendly one.
- `delete_resolved` calls `_require_repository` and refuses a repository with no
  commit, rather than recording an empty location.

### Routing nodes

- **`nearest_work_ancestor()`** replaces `parent_node()` in every upward walk —
  `FsWorkStore.initiative_epic`, the descendant board's ownership walk, and
  `escalate`. One `registry.ancestors()` traversal rather than repeated single
  hops, so a filter cannot truncate it.
- **`FsWorkStore.initiative_children`** uses `descendant_nodes` instead of
  `child_nodes`, so a slice below a storeless node is found. The two directions
  had disagreed about whether such a node is passable.
- **`registered_parent()`** exposes the direct parent without the store filter,
  and `escalate` refuses with "no registered ancestor keeps a work store" rather
  than claiming the node is the root.
- **`registered_children()`** does the same for children: `tcw work nodes` lists
  every registered child rather than omitting the ones without a usable board,
  which made a node with children read as `(none — leaf)`.
- **Both `tcw work nodes` lines mark the same two cases the same way.** The
  parent line shares the children's `_no_store_note`, so each prints
  `<id>  (no work store)` where the project keeps no board and
  `<id>  (work store not provisioned here)` where it declares one this machine
  has not obtained. The parent line had hard-coded the first marker and so
  reported a declared-but-unprovisioned board as no board at all.
- `parent_node()` and `child_nodes()` are unchanged and still mean the direct
  relations that keep a board — which is what the cross-node operations want.

### Federation reads the sibling's configured store

- **`extends` resolves the extended project's component store** through the same
  ladder every other read uses, instead of composing `docs/<component>` under its
  root. A sibling that moved its tree with `<component>.path` can be extended
  from; one whose tree is declared and unprovisioned reports the remote and
  `tcw provision` rather than "has no docs/<component>/".
- Federation carries the projects already on its path (`_seen_nodes`), so a cycle
  truncates rather than recurring — resolving a sibling's store now opens it, and
  opening a tree store resolves its own `extends`, so the guard has to run on
  project identity, before any store is built.
- **The resolved store is reused, not rebuilt.** `_extended_component_roots`
  became `_extended_component_stores` and returns the stores it opened.
  Reconstructing them from `.root` dropped the node root — `FsTreeStore` falls
  back to `root.parent.parent`, correct only for `docs/<component>` — so the hop
  *past* a sibling with a moved tree resolved against the wrong project graph and
  reported the next project unreachable. It also built each subtree twice per
  edge: depth 11 went from 15.7 s to 0.10 s.
- **`check()` reports an `extends` cycle.** The edge that closes one is recorded
  by the store that truncates it and gathered up the tree by the
  `_FederationCycles` mixin, so the store a caller is holding reports it. The
  registry's own `check()` only knows `connected-projects`, which is a different
  graph — two projects may be legitimately connected and still extend in a loop.
  The two hand-rolled `_cycles` walkers are removed; both recomputed the
  resolution with `parent.parent` as the node root.
- **A sibling's own error survives.** `StoreNotProvisioned`,
  `StoreDeclarationError` and `ValueError` are each prefixed with
  `project '<id>':` rather than rewritten as `has no <component> component`,
  which used to send readers to create a store that already existed.

### A partial graph no longer reads as an empty one

- **`WorkStore.incomplete_graph_note()`** joins the storage-neutral interface,
  defaulting to `""`. `FsWorkStore` overrides it; the gate that needs it lives in
  `WorkStore`.
- **`complete` refuses to close an epic when the graph is partial**, naming the
  missing projects and offering `--force`. `initiative_children` returns a
  *shorter* list once unreachable nodes stopped being fatal, and the gate read
  that as "no open children" — closing an epic over slices in an absent node.
  `epic_completable` returns False for the same reason.
- **A directory with no `tcw-config.yaml` fails `require_valid()` again.** The
  root's own config is separated from the target edges before the unreachable
  fail-open, which is argued for targets and said nothing about the node the
  command was run in; every helper built on `require_valid()` had begun
  answering "no parent, no children, valid" for any directory.

## Internal

- `tcw/store/checkouts.py` holds the `(url, ref)` → working-copy-directory
  computation, which `fs.py` and `project.py` both need and neither may import
  from the other.
- `tests/fixtures/lifecycle_baseline/*.json` regenerated for the new step. A
  deliberate contract change, visible in the diff exactly as those fixtures are
  meant to make it.
