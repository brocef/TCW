# Working across repositories

Projects are identified by a canonical ID; filesystem paths are only locators.
This document covers connecting projects, keeping a component store in another
repository, and obtaining stores and projects a checkout does not have.

See also [The Work component](work.md) and
[Taxonomy and Capabilities](taxonomy-and-capabilities.md).

## Connected projects

Projects may be nested, siblings, or anywhere else on the filesystem. Their
canonical IDs are identity; filesystem paths are adapter locators only.

```sh
cd orchestrator && tcw init --id orchestrator
cd ../project-a && tcw init --id project-a
```

Each invocation still selects the nearest enclosing sentinel. Cross-project
operations use only reciprocal registrations:

```yaml
id: orchestrator
connected-projects:
    children:
        project-a: ../project-a
```

```yaml
id: project-a
connected-projects:
    parent:
        orchestrator: ../orchestrator
```

An entry may also say where the project _comes from_, taking the same
`repository` block a component store takes (see [Where a component store
lives](#where-a-component-store-lives)) in the place a locator goes:

```yaml
id: project-a
connected-projects:
    parent:
        orchestrator:
            path: ../orchestrator # optional; where it is here
            repository:
                url: https://github.com/me/orchestrator.git
                ref: main
```

A bare locator string stays a locator, so nothing already written changes. The
ladder is the store's, and `tcw provision` is what walks it.

**Telling TCW where a project actually is on this machine.** A locator is a fact
about one machine, written in a file every machine reads — so it cannot describe
a machine that lays the graph out differently. Set `TCW_PROJECT_<ID>` to say
where a connected project really sits here:

```sh
export TCW_PROJECT_PROPOSIT_CORE=/home/you/proposit-core
```

The name is the project's ID, uppercased, with hyphens as underscores. **It
follows node IDs, not repository names** — the two are often different.

It is consulted first, above the declared locator and above `repository`. That
ordering is the point: the case it exists for is a locator that resolves to the
_wrong_ place, and a rung below the locator could never correct it.

Naming a project this machine does not have is **not** an error. The variable
falls through to `repository` exactly as if it were unset, so one set of
variables can be configured once for an environment — a cloud session, a CI
runner — and used by sessions that check out different subsets of the
repositories, with no session needing to know which case it is in. Naming
something that _is_ here and is wrong — a directory with no `tcw-config.yaml`, or
a node with a different ID — is refused and says what it found.

Every command honours it, because it is read when the graph is loaded rather than
by any one command: `tcw provision` does not fetch a project an override
resolves, and refuses outright — before contacting anything — when a variable
names something that is present and wrong. `tcw validate` prints a line naming
each variable in effect and where it points, so a graph that resolves only
because of one is never a mystery to the next reader.

Relative locators resolve from the declaring config; absolute locators are also
allowed. `children` contains direct children only and `parent` has at most one
entry. TCW derives deeper descendants and ancestors transitively, never by
scanning directories to discover a project. `tcw work list --include-descendants`
groups registered boards by project ID, and any work command accepts
`<descendant-project-id>/<slug>`.

**A locator is a fact about one machine, and a project that is not on it drops
out of the graph rather than failing your commands.** A checkout holding only
some of a graph's repositories — a fresh clone, a cloud session that cloned one
repo — keeps working: the absent project is simply not in the graph, and
everything that does not need it behaves normally. `tcw validate` names each
project it could not reach, every run. A project some other declaration did
resolve is not listed — in a
reciprocal graph both sides name every connection, and on a machine holding only
some of the repositories one of those two is routinely a path that is not here:

```
tcw-config.yaml: connected project 'orchestrator' is declared but not reachable
in this checkout (/home/you/orchestrator)
```

A command that _does_ need the absent project says which one and where it was
declared, rather than reporting that it was never registered. This is the same
courtesy a declared store already gets when it has not been provisioned here.
`tcw work nodes` lists it as a parent or a child that is not in this checkout,
and `tcw work escalate` and `tcw work delegate` name it instead of calling the
node a root or a leaf.

`tcw validate` also reports a declared locator that does not resolve here for a
project it _does_ have — declared there, found here — without calling it a
problem. Nothing on disk separates a typo from a path that is simply right for
another machine, and in a workspace whose repositories sit differently on
different disks the second is routine, so it states both facts and draws no
conclusion.

**A node need not keep a work store.** A repository root that only groups the
packages owning the boards is a registered project like any other, and relations
pass straight through it: an epic two levels up resolves, its slices below one
are found, and `tcw work escalate` reaches the nearest ancestor that does keep a
board. `tcw work nodes` says `parent: <id>  (no work store)` for such a parent
rather than calling this node the root, and `(work store not provisioned here)`
for one whose declared board this machine has not obtained — the same two markers
it puts on the children lines.

Configuration that is genuinely wrong still fails closed, unchanged: an invalid
or duplicated project ID, a cycle, unparseable YAML, a registered key that
disagrees with the target it names. The one thing that relaxes with it is
reciprocity — two nodes that name each other at paths belonging to different
machines are correctly configured, and only a counterpart that is _present_ and
points somewhere else is a non-reciprocal declaration.

Inside a **linked git worktree** a relative locator would otherwise be off by the
worktree's nesting depth, because it was written against the project's position
in its primary checkout. TCW re-anchors it against that project's own counterpart
in the main worktree — but only when the target leaves the worktree. A target
that stays inside is a sibling on the same branch and stays with the worktree, so
several projects in one repo behave the same inside a worktree as outside it.
This is the one place git metadata is consulted, and it only re-points a locator:
it never discovers a project or infers a relation. Projects outside a worktree,
and projects not in a git repository at all, are unaffected.

The same rule governs a relative **store** path (`work.path`, `taxonomy.path`,
`capabilities.path`): one that leaves the checkout re-anchors, one that stays
inside belongs to the worktree exactly as the default `docs/<component>` does.
Both re-anchor at the project's own counterpart, so a project nested inside its
repository keeps its sub-path instead of having it dropped at the repository
root.

Connections do not imply component inheritance. Each axis opts in explicitly:

```yaml
# docs/taxonomy/config.yaml
extends:
    - orchestrator
```

The source project ID is also the inherited namespace. Inheritance is
transitive: if one source extends another, both sources' terms are available
under their own project IDs.

---

## Where a component store lives

Print the absolute folder each filesystem store resolves to with:

```sh
tcw taxonomy path
tcw capabilities path
tcw work path
tcw work inbox path
```

A store that is declared but not obtained here has no path to print: these say so
and name `tcw provision`, rather than printing a folder that does not exist. The
work commands follow a configured `work.path`, so they report the external store
and its inbox when work storage lives outside the project.

To keep a project's work in another Git repository while preserving its own ID
and lifecycle configuration, set `work.path` in its `tcw-config.yaml` or pass
`tcw work init --path <path>` (`tcw init --work-path <path> work`). A relative
path is anchored to the project's own directory — inside a linked worktree, to
the primary checkout's copy of it, but only when the path points outside the
worktree (see below); absolute paths and symlinks are supported. Existing
non-pristine stores are never moved automatically.

All three component stores work this way — `taxonomy.path` and
`capabilities.path` do for those trees what `work.path` does for work items, with
`tcw init --taxonomy-path <path>` and `--capabilities-path <path>` to scaffold
them. A project that configures nothing keeps resolving `docs/<component>`
exactly as before.

A path is a fact about one machine, so a checkout that has never seen that folder
— a fresh clone, or a cloud session that cloned only the code — cannot use it. To
say where the store _comes from_, add a `repository` block beside `work.path`:

```yaml
id: my-project
work:
    path: ../orchestrator/docs/work/my-project # optional; where it is here
    repository:
        url: https://github.com/me/orchestrator.git
        ref: main # optional (default: remote HEAD)
        path: docs/work/my-project # optional (default: repo root)
        checkout: ~/src/orchestrator # optional (default: a cache dir)
taxonomy:
    repository: # the same block, per component
        url: https://github.com/me/orchestrator.git
        path: docs/taxonomy
```

A connected project takes the same block, in the same place its locator goes —
see [Connected projects](#connected-projects).

**A store that is already here always wins.** The declaration is consulted only
when the local store is absent, so the same config keeps working untouched on a
machine that has the folder, and answers for one that doesn't.

"Already here" is not limited to the configured path. Before falling back to a
fetched copy, TCW asks whether some project it has located is a checkout of the
declared repository, and if one is, reads the store inside it. That is what lets
a workspace cloned flat — every repository side by side, where the config
describes them nested — work from `TCW_PROJECT_<ID>` alone, with no symlink and
no absolute path baked into a file other machines read. A store found this way
is yours: it is read on whatever branch you have it on, and TCW never pushes to
it. Only a copy TCW fetched publishes.

Where the store is
absent, every command that needs it says so in those words and names the remote —
instead of reporting that the project has no such component. That last part
matters most for the trees: a checkout that cloned only the code has no
`docs/taxonomy/` folder, which used to read as "this project has no taxonomy".

## Obtaining a declared store or project

`tcw provision` is what obtains it:

```sh
tcw provision                 # every declared store and connected project
tcw provision --dry-run       # print the plan; contact nothing
tcw provision --refresh       # bring an existing copy to the declared version
tcw provision --component taxonomy
```

Each declared component is obtained on its own, so one bad declaration does not
suppress another's result. Connected projects are obtained after the components,
and **transitively**: a project obtained because it was declared may declare
others, and those are obtained in the same run. That is the one place `tcw`
contacts a URL you did not write yourself, so every remote is printed before it
is contacted — the transitive ones included — and `--dry-run` walks the whole
queue without touching the network, saying plainly that a project it has not
fetched may declare more. `--component` scopes the component pass only —
connected projects are still obtained, and every remote is still printed first. A
project this checkout can already reach is never fetched, however it is declared
— the same "already here wins" rule the stores follow — so declaring an edge on
both sides costs nothing. `--refresh` does not override that: it brings a copy
`tcw` itself provisioned back to the declared version, and a project you resolve
somewhere else has no such copy to bring anywhere — obtaining one would put a
second node in the graph under a single ID.

If the `repository` block itself is wrong — a missing `url`, a path that escapes
the repository root, a key that is not one of the four — every command says which
line to fix. None of them falls back to "no tcw node here", which would send you
to `tcw init` and scaffold a second, empty store beside the real one.

Running it twice does nothing the second time. Nothing acts on a config-supplied
URL until you ask: the remote is printed before it is contacted — and is the
remote actually contacted, since a `checkout` directory already holding a
different repository is refused before any fetch.

A failure says why and leaves nothing new behind. A working copy you already had
is never deleted for you: if it turns out to carry no store at the declared
`path`, you are told, and it stays where it is.

## Keeping a provisioned store in step

A store you obtained with `tcw provision` is a working copy of somebody else's
repository, and on a machine that may not last — a cloud session, a container.
So its transitions travel: `tcw work start`, `submit` and `complete` bring the
copy up to date before they move anything, and push the result afterwards.

**Only a provisioned store does this.** A store found at your own `work.path`
does not publish even when a `repository` block is also present — the
declaration is a fallback and did not answer the read, so it does not cause a
write, and that copy is on your disk for you to push. A store with no
declaration at all never publishes; it commonly has a Git `origin` of its own,
usually your project's, and TCW does not push your repository because you changed
an item's status.

Taxonomy and capabilities are not published, deliberately and not as an omission.
A capability's status is a claim about the code, true when the code implementing
it merges, so the edit belongs to that change and lands with it. Publishing one
on its own would announce a capability while the code making it real is still
unmerged.

If the remote cannot be reached, _when_ it fails decides what happens. The
refresh runs first, before anything moves, so a failure there refuses the
transition and leaves the item exactly as it was. The push runs last, after the
move is committed locally, so a failure there tells you where your work is saved
and exits non-zero without undoing it. A remote that has moved incompatibly is
reported as divergence and never merged for you.

To switch it off, `work.publish-transitions: false`:

```yaml
work:
    publish-transitions: false # default: true, for a provisioned store
```

**What is checked differs by component, and it is worth knowing which.** A work
store is recognizable — it names six status folders — so a repository that has
no work store at the declared `path` is refused. A taxonomy or capabilities tree
is just a directory of entry folders with no required marker, so the check is
that a directory is there, and a declared path holding an empty or unrelated
directory is accepted rather than refused. What holds for all three is that a
failure publishes nothing: a repository with no directory at the declared path
is refused before any working copy is put in place.

Everything that reads or writes work follows `work.path`: `delegate` and
`escalate` land in the target project's configured inbox, `reconcile` writes and
commits the epic rollup in the store's repository, `tcw capabilities drift` finds
completed planning items there, and status transitions and web edits commit there
too. What stays with the code repository is what the code owns — lifecycle hooks,
the `.gitignore` entry for worktrees, and the branches and linked worktrees
themselves. A project that names a `work.path` and also happens to have a leftover
`docs/work/` folder is read through its configured path, not the leftover.

When the two repositories differ, `tcw work start --worktree` commits the item's
state in the store repository and the `.gitignore` change in the code repository,
then creates the worktree — and if either commit is refused it stops, says which
repository already committed, and creates no worktree. A code branch cannot carry
lifecycle files that live in another repository, so the work branch holds the
code side only; the item itself stays visible through the store.
