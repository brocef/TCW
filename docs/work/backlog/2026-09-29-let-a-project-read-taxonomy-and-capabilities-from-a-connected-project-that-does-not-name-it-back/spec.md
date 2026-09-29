# Spec — Let a project read taxonomy and capabilities from a connected project that does not name it back

## Capability changes

Planned ledger changes only; nothing is written to the ledger at this stage.

- **new:** `cli/read-from-an-upstream-project` — a project declares an upstream
  project it reads from, without that project naming it; inheritance and
  references reach it, and nothing writes into it.
- **changed:** `taxonomy/federate-shared-vocabulary` and `capabilities/federate`
  — `extends` may name a project reached through an upstream connection.
- **changed:** `cli/validate-a-node` — an upstream connection needs no
  counterpart, is never validated as part of the reader, and a stale counterpart
  entry is a warning.
- **changed:** `work/inspect-the-node-topology` — `tcw work nodes` lists upstream
  projects separately, marked read-only.
- **changed:** `work/delegate-a-request-to-a-child-node` — naming an upstream
  project is refused as read-only.

The taxonomy gains one Vocabulary term, **upstream project**: a connected
project a node reads from and never writes to, and which does not name that node.

## Problem

`connected-projects` has two relations, `parent` and `children`
(`tcw/store/project.py:487-489`), and every connection must be declared from
both sides. The whole graph is loaded and checked on every open
(`_load_graph`, `project.py:383-390`): a child that does not name its parent
fails with `nonreciprocal connection: parent '<id>' is not declared`
(`_validate_reciprocity`, `project.py:715-718`), and `require_valid()`
(`project.py:369-372`) turns any such problem into a refusal. Almost every
command calls it — through `find_node` (`tcw/store/fs.py:273`) and, for every
taxonomy or capabilities store, `_extended_component_stores` (`fs.py:1541`).

So a project that must not name its consumers cannot be connected to them at
all. The requester's case: proposit-core is public and must not name the private
proposit-orchestration root that lists it as a child, while three proposit-app
packages inherit core's vocabulary with `taxonomy: extends: [proposit-core]`
and refer to its terms as `proposit-core/<term>`. Removing core's `parent` entry
breaks every command in the orchestration workspace.

What inheritance actually needs is narrower than a parent/child connection.
`extends` finds its project by id anywhere in the loaded graph
(`registry.get`, `fs.py:1546`; `project.py:217-219`), and `<project-id>/<term>`
references resolve through the stores `extends` opened (`fs.py:2321-2366`).
Neither reads the parent/child relation. Everything that **writes into** or
**walks through** another project does: `delegate` (`routed_children`,
`tcw/work/recursion.py:519-579`), `escalate` (`ancestors`, `recursion.py:582-613`),
`reconcile` and initiative rollups (`descendant_nodes`, `recursion.py:262-266`),
`validate`'s recursion (`registry.descendants()`, `tcw/cli.py:442`),
`work list --include-descendants`, `tcw serve`, `tcw work nodes`, tracker
inheritance, and capability-sidecar routing (`declared_child_ids`,
`recursion.py:203-253`).

## Goals

1. A node can declare an **upstream** project — one it reads from — that does
   not name it back, using the same entry shapes, `path`/`repository` ladder
   and `TCW_PROJECT_<ID>` override as any connection.
2. `taxonomy extends` and `capabilities extends` naming a project reached
   through an upstream connection resolve, from the declaring node and from any
   node whose graph reaches it (the proposit-app packages reach core through two
   parents).
3. `<project-id>/<term>` references and `tcw://` links into an upstream resolve.
4. Nothing writes into an upstream. Commands that would are refused with a
   message saying the connection is read-only.
5. `tcw validate` passes on the reader and on the upstream, and the upstream's
   validation knows nothing of the reader.
6. The Proposit layout can move to this in either order across its two
   repositories without an intermediate state that blocks every command.

## Non-goals

- The upstream discovering, listing or reading its readers.
- Allowing any write into an upstream, even behind a flag.
- `extends_add`'s check for a literal `docs/taxonomy` / `docs/capabilities`
  folder (`fs.py:2549`, `fs.py:3288`) instead of the store's location ladder. It
  is inconsistent with the read path, but it does not block this case, so it is
  noted for a separate item.
- Moving proposit-core's work items or editing any Proposit repository.

## Design

### Declaration: a third relation, `upstream`

```yaml
connected-projects:
    children:
        proposit-app-repo: {path: proposit-app, repository: {…}}
    upstream:
        proposit-core:
            path: proposit-core
            repository:
                url: https://github.com/Proposit-App/proposit-core.git
                ref: main
```

`upstream` is a mapping of project id to entry, exactly like `children`: a bare
path string, or a mapping with `path` and/or `repository`
(`parse_connected_entry`, `tcw/store/base.py:2647-2697`). The location ladder is
the existing one (`_target_path`, `project.py:529-572`), so `TCW_PROJECT_<ID>`,
`path`, then the `repository` checkout apply unchanged. Any number of upstreams.

**Why a separate key, not a flag on a child.** Every walker and writer listed in
the Problem reads `children` or `parent`. A `read-only: true` flag on a child
would have to be remembered in each of them, and a walker added later that forgot
it would write into a public repository. A separate relation is excluded from all
of them by construction: `children()`, `descendants()`, `parent()` and
`ancestors()` (`project.py:221-269`) never return it.

**Abstraction check.** This is a relation in the project graph model, not a store
operation; a non-filesystem project registry records a third kind of edge as
easily as two. No store interface changes.

### Loading

`_visit` (`project.py:392-429`) follows `upstream` edges of every config it
loads, as it follows `children` and `parent`, so `registry.get(id)` finds an
upstream from any node whose graph reaches its declarer. That is what lets the
proposit-app packages resolve `extends: [proposit-core]` through
`proposit-app-repo` and the orchestration root. The upstream's own `parent` and
`children` edges are followed too, so its graph is loaded and checked as it
would be from its own checkout; an upstream's own upstreams likewise.

An absent upstream is **unreachable**, reported as a warning exactly as an
absent child is (`project.py:332-345`, `tcw/cli.py:426-440`), never a failure.

### Reciprocity

`_validate_reciprocity` (`project.py:706-749`) exempts `upstream` edges: no
counterpart is expected.

Two new graph problems:

- a node declaring the same id under `upstream` and under `children` or
  `parent` — "'<id>' is declared both as upstream and as <relation>; an upstream
  connection is read-only, so it cannot also be a <relation>";
- a node declaring itself as its own upstream.

**The one relaxation, for migration.** When a node names a parent that declares
it under `upstream` instead of `children`, that is reported as a **warning**,
not the `child '<id>' is not declared` failure: "'<id>' names '<parent>' as its
parent, but '<parent>' reads it as an upstream project; remove the parent entry
from '<id>' — an upstream need not name its readers". This lets the reader
switch first and the upstream drop its `parent` entry later, with neither
repository blocked in between (Goal 6). The reverse order — the upstream drops
`parent` while the reader still lists it as a child — still fails with the
existing message, which already names the fix.

### What reads an upstream

Unchanged code paths, now reaching it:

- `taxonomy extends` / `capabilities extends`, reading and `extends add`
  (`registry.get`).
- `<project-id>/<term>` and alias-qualified capability references, through the
  inherited stores.
- `tcw://T/…`, `tcw://C/…` and `tcw://W/…` links (`tcw/refs.py:95-161`,
  `resolve_qualified_work_ref`, `fs.py:534-616`), and `tcw work show` / `path`
  of a qualified reference into it.
- `tcw provision`: `declared_connected_projects` (`fs.py:3900-3934`) gains
  `upstream`, so a fresh clone obtains an upstream from its `repository` entry.
  Cloning into this machine's checkout area writes nothing into the upstream.

### What is refused

Every refusal names the project, says it is a read-only upstream of the
declaring node, and says where the write belongs ("run it in <id> itself").

- **`tcw work delegate <upstream>`** — before the existing
  `no child node '<id>'` refusal (`recursion.py:560`), when `<id>` is an upstream
  of this node or of an ancestor.
- **Transitions and edits through a qualified reference** — `start`, `submit`,
  `rework`, `complete`, `edit`, `drop`, `delete` and every other `tcw work` verb
  that changes an item, given `<upstream>/<slug>`. Reading verbs (`show`,
  `path`) are allowed.
- **Capability sidecar paths** — a `capabilities.yaml` entry naming
  `<upstream>/<path>` is reported by the completion gate as read-only, rather
  than as a path nothing can check (`route_capability_path`,
  `recursion.py:203-253`).
- **Taxonomy and capabilities writes** into an inherited project are already
  refused by the stores; the plan confirms each and gives the message the same
  read-only wording where it is a qualified write.

`reconcile`, initiative rollups, `escalate`, tracker inheritance,
`--include-descendants` and `tcw serve` never reach an upstream, because they
walk `children`/`parent` only. There is nothing to refuse there; the tests
assert the upstream is absent from each.

### Topology

`tcw work nodes` prints a separate `upstream (read-only):` section listing the
current node's upstreams and those of its ancestors, with location or
"unreachable". `tcw validate` does not recurse into an upstream.

### The Proposit move, for the requester

1. In proposit-orchestration's root `tcw-config.yaml`, move `proposit-core` from
   `connected-projects.children` to `connected-projects.upstream`, entry
   unchanged. Everything keeps working; `validate` warns that core still names
   `proposit-app` as its parent.
2. In proposit-core, delete `connected-projects.parent`. The warning goes away.
   Core's own `validate` sees no connections at all.
3. The packages' `extends: [proposit-core]` lines are unchanged.

Core's `work.path` into the orchestration repository is independent of this and
moves on the requester's own schedule.

## Acceptance criteria

All in scratch projects built by tests, with real git repositories where a
`repository` entry is involved.

1. **Reader, one hop.** Project `app` declares `upstream: {core: ../core}`;
   `core` declares no connections and one term. In `app`: `tcw taxonomy extends
   add core` succeeds, `tcw taxonomy list` includes core's term, `tcw taxonomy
   show core/<term>` resolves, and `tcw validate` exits 0. The same holds for
   `capabilities extends`. In `core`: `tcw validate` exits 0 and its output
   names nothing of `app`.
2. **Reader, through parents.** A node two parents below the declarer resolves
   `taxonomy: extends: [core]` and a `core/<term>` reference, and `validate` in
   it exits 0 — the proposit-app package shape.
3. **Ladder.** An upstream given only by `repository` resolves after
   `tcw provision`; `TCW_PROJECT_CORE` pointing elsewhere is honored; an absent
   upstream is a warning in `validate` and exit 0, and `extends` of it reports it
   unreachable as today.
4. **Refusals.** `tcw work delegate core …`, `tcw work start core/<slug>`,
   `tcw work edit core/<slug> …`, and completion with `core/<path>` in
   `capabilities.yaml` each exit non-zero with a message containing
   `read-only` and `core`, and not `nonreciprocal`; the upstream's files are
   unchanged (checked by git status of `core`).
5. **Reads allowed.** `tcw work show core/<slug>` and a `tcw://W/core/<slug>`
   link resolve.
6. **Not walked.** `core` does not appear in `tcw work list --include-descendants`,
   `tcw validate`'s recursion, `tcw serve`'s aggregation, or `reconcile` of an
   epic; it does appear under `upstream (read-only):` in `tcw work nodes`.
7. **Graph problems.** The same id under `upstream` and `children` is a problem;
   a self-upstream is a problem.
8. **Migration order.** Reader switched, upstream still naming the reader as
   parent: `validate` exits 0 in both with the warning above. Upstream dropped
   `parent`, reader still listing it as a child: the existing
   `nonreciprocal connection` failure, unchanged.
9. The existing reciprocity tests (`tests/test_project_registry.py:127-366`)
   pass unchanged.
10. The full suite passes, run as CI runs it (bare `pytest`).

## Risks

- **Loading more of the graph.** Following upstream edges loads the upstream's
  own connections into every reader's registry. A broken upstream graph would
  then block its readers. Accepted: the same is already true of every parent and
  child, and the upstream validates cleanly on its own before readers depend on
  it. If it proves a problem, problems found only beyond an upstream edge can
  later be demoted to warnings.
- **A write path missed.** The refusal list is built from the verbs that accept a
  qualified reference. The plan enumerates them from the parser, not from
  memory, and the tests cover each class.
- **Name clash.** An id reached both as an upstream (from one node) and as a
  child (from another) is one project with two relations. It is writable from the
  node that has it as a child and read-only from the node that has it upstream;
  the refusal is decided by the relation the current node's own chain uses.

## Notes

- Design goes to the requester (the Proposit orchestrator session) for review
  before the plan stage, as they asked.
- Research: the connected-projects code map summarized in the Problem and Design
  sections, from a read of `tcw/store/project.py`, `tcw/store/fs.py`,
  `tcw/work/recursion.py`, `tcw/cli.py` and `tcw/refs.py`.
- Docs that state connections are always two-way and will change:
  `skills/configure/references/projects.md:30-40`, `docs/guide/multi-repo.md:21`,
  `docs/capabilities/cli/validate-a-node/description.md:7`.
