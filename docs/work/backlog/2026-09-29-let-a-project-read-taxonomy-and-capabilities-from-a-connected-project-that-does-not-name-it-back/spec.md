# Spec — Let a project read taxonomy and capabilities from a connected project that does not name it back

## Capability changes

Planned ledger changes only; nothing is written to the ledger at this stage.

- **new:** `cli/read-from-an-upstream-project` — a project declares an upstream
  project it reads from, without that project naming it; inheritance and
  references reach it, and nothing writes into it.
- **changed:** `taxonomy/federate-shared-vocabulary` and `capabilities/federate`
  — `extends` may name a project reached through an upstream connection.
- **changed:** `cli/validate-a-node` — an upstream connection needs no
  counterpart and is never validated as part of the reader; a stale counterpart
  entry is a warning.
- **changed:** `work/inspect-the-node-topology` — `tcw work nodes` lists
  upstream projects separately, marked read-only.
- **changed:** `work/delegate-a-request-to-a-child-node` — naming an upstream
  project is refused as read-only.
- **changed:** `cli/reference-a-tcw-object` — a qualified work reference into a
  read-only project reads, and refuses to write.
- **changed:** `cli/declare-a-connected-projects-home-repository` — `upstream`
  entries take the same `path` / `repository` ladder.

The taxonomy gains one Vocabulary term, **upstream project**: a connected
project a node reads from and never writes to, and which does not name that node.
The capabilities docs already say "upstream" loosely for any project a store
`extends`, including writable children; the term's definition says so and that
the looser use means "the project an inherited entry comes from".

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

What inheritance needs is narrower than a parent/child connection. `extends`
finds its project by id anywhere in the loaded graph (`registry.get`,
`fs.py:1546`; `project.py:217-219`), and `<project-id>/<term>` references
resolve through the stores `extends` opened (`fs.py:2321-2366`). Neither reads
the parent/child relation.

Writes are a different story, and today **any** project in the loaded graph is
writable through a qualified work reference: `resolve_qualified_work_ref`
(`fs.py:607-615`) accepts any id `registry.get` knows, and both the CLI's
`_resolve` (`tcw/work/cli.py:132-148`, used by `start`, `submit`, `rework`,
`complete`, `edit`, `drop`, `delete`, `scaffold`, `stage …` and `lifecycle`)
and `tcw serve`'s `_resolve_work` (`tcw/serve/__init__.py:499-508`, used by its
`PATCH`, `POST …/actions/…`, `PUT` and `DELETE` endpoints) route through it.
The other cross-project paths walk `children`/`parent`: `delegate`
(`tcw/work/recursion.py:519-579`), `escalate` (`recursion.py:582-613`),
`reconcile` and initiative rollups (`recursion.py:262-266`), `validate`'s
recursion (`tcw/cli.py:442`), `--include-descendants`, `tcw serve`'s board, and
tracker inheritance (`fs.py:6627-6650`, through `registry.ancestors()`).

## Goals

1. A node can declare an **upstream** project — one it reads from — that does
   not name it back, using the same entry shapes, `path`/`repository` ladder
   and `TCW_PROJECT_<ID>` override as any connection.
2. `taxonomy extends` and `capabilities extends` naming a project reached
   through an upstream connection resolve, from the declaring node and from any
   node whose graph reaches the declarer (the proposit-app packages reach core
   through their parent).
3. `<project-id>/<term>` references and `tcw://` links into an upstream resolve.
4. Nothing writes into an upstream, by any route. Every write through a
   reference to it is refused with a message saying it is read-only.
5. `tcw validate` passes on the reader, and on the upstream once the upstream's
   own configuration stands alone (see the migration section for what that takes
   for proposit-core). The upstream's validation knows nothing of the reader.
6. The Proposit layout can move to this **in one stated order** across its two
   repositories without an intermediate state that blocks every command.

## Non-goals

- The upstream discovering, listing or reading its readers.
- Allowing any write into an upstream, even behind a flag.
- The capability-sidecar route (`route_capability_path`, `recursion.py:203-253`).
  A `capabilities.yaml` entry `<upstream>/<path>` already routes to the
  inherited reading when the node's ledger `extends` that project, where a local
  override is a legitimate write (`tcw capabilities set`); the completion gate
  only reads. It is left as is.
- `extends_add`'s check for a literal `docs/taxonomy` / `docs/capabilities`
  folder (`fs.py:2549`, `fs.py:3288`); inconsistent with the read path but not
  blocking here — a separate item.
- Moving proposit-core's work items or editing any Proposit repository.

## Design

### Declaration: a third relation, `upstream`

```yaml
connected-projects:
    parent:
        proposit-app: {path: .., repository: {…}}
    children:
        proposit-shared: packages/shared
    upstream:
        proposit-core:
            path: ../proposit-core
            repository:
                url: https://github.com/Proposit-App/proposit-core.git
                ref: main
```

`upstream` is a mapping of project id to entry, exactly like `children`: a bare
path string, or a mapping with `path` and/or `repository`
(`parse_connected_entry`, `tcw/store/base.py:2647-2697`). The location ladder is
the existing one (`_target_path`, `project.py:529-572`): `TCW_PROJECT_<ID>`,
then `path`, then the `repository` checkout. Any number of upstreams.

**Why a separate key, not a flag on a child.** A flag could be split into its own
mapping when the config is read, so walkers would not have to remember it; that
is not the reason. The reasons are what the relation *is*. An upstream is not
below the node, so listing it as a child is wrong in `tcw work nodes`, in the
docs and to `delegate`; and a node with no children — a package — can still
declare one. A separate key also makes it impossible for a later walker of
`children` to reach it by accident.

### The registry interface

`ProjectRegistry` (`tcw/store/base.py:191`) gains two operations, which the
filesystem registry implements:

- `declared_upstream_ids(project_id=None) -> list[str]` — the ids a project
  declares under `upstream`, as `declared_child_ids` does for children.
- `read_only_reason(project_id) -> str | None` — `None` when the current node may
  write to that project; otherwise the sentence saying why not. This is the only
  place the write rule lives.

**Abstraction check.** Both are questions about the connected-project graph that
any registry — a database, a tracker's project links — can answer; neither is a
filesystem trick. No work, taxonomy or capabilities store interface changes.

### Loading: to the upstream's own config, and no further

`_visit` (`project.py:392-429`) follows `upstream` edges of every config it
loads, as it follows `children` and `parent`, so `registry.get(id)` finds an
upstream from any node whose graph reaches its declarer. That is how the
proposit-app packages resolve `extends: [proposit-core]` through their parent
`proposit-app-repo`.

It loads the upstream's `tcw-config.yaml` **and does not follow that config's own
`parent`, `children` or `upstream` edges.** Two reasons. Readers stay insulated
from the upstream's graph: a problem in it, or a project it connects to, is not
the reader's to load, check, provision or write. And a project reachable only
beyond an upstream never enters the reader's registry, so it cannot be named at
all. The upstream's own stores are opened from its own root when `extends`
reads them (`fs.py:1584-1585`), so its own inheritance still works on its own
terms.

A config reached this way is marked as reached through an upstream edge. If the
same project is also reached through a `children` or `parent` edge, it is one
project (same resolved path, as today) and is loaded fully.

An absent upstream is **unreachable**, a warning exactly as an absent child is
(`project.py:332-345`, `tcw/cli.py:426-440`), never a failure. `checkout_of`
(`project.py`, around line 290) also searches `upstream` entries, so a
provisioned upstream is found by its repository URL. `tcw provision`'s
`declared_connected_projects` (`fs.py:3900-3934`) includes `upstream`, so a fresh
clone obtains an upstream from its `repository` entry; cloning into this
machine's checkout area writes nothing into the upstream.

### The write rule

**A project is writable from the current node if, and only if, it is reachable
from the current node by following `parent` and `children` edges alone** — as
declared by each project on the way. The current node itself is writable. Every
other project in the registry was reached through at least one `upstream` edge
and is read-only from here.

This answers the cases a narrower rule misses:

- an upstream declared by a sibling (`proposit-shared` declares core; from
  `proposit-server` core is still read-only);
- an upstream declared by a descendant (the orchestration root reaches core only
  through `proposit-app-repo`'s upstream edge, so core is read-only from the
  root whether or not the root also declares it);
- the upstream's own checkout, where it is the current node and writable to
  itself.

The rule is checked at the **anchor node**, where the reference is resolved —
never inside a store opened at the upstream, whose own registry would have the
upstream as its current node and allow the write.

`resolve_qualified_work_ref` (`fs.py:534-616`) is split in two: the reading form
keeps today's behavior; the writing form calls `read_only_reason` first and
refuses. Every write caller uses the writing form, so a new caller is safe by
construction rather than by being listed:

- `_resolve` in the work CLI, for every verb that changes an item or runs the
  project's own scripts: `start`, `submit`, `rework`, `complete`, `edit`, `drop`,
  `delete`, `scaffold`, `stage gate`, `stage prompt` and `lifecycle`. The
  `stage` verbs count as writes because they execute the upstream's own `pre`
  and `generate:` bindings; reading an upstream item is `show` and `path`.
- `tcw serve`'s `_resolve_work` for every mutating request (`PATCH`, `PUT`,
  `DELETE`, `POST …/actions/…`); `GET` uses the reading form.
- `tcw work delegate`, before its existing `no child node` refusal
  (`recursion.py:560`).
- `tcw work tracker` verbs that take a qualified reference and bind or move a
  ticket for it (`link`, `create`, `claim`, `release`, `sync`); the plan lists
  them from the parser.

The refusal reads: `tcw work <verb>: '<id>' is a read-only upstream project here
(reached through '<declarer>'); run this in <id> itself.`

`reconcile`, initiative rollups, `escalate`, tracker inheritance,
`--include-descendants`, `tcw serve`'s board and `validate`'s recursion walk
`children`/`parent` only, so they never reach an upstream; the tests assert its
absence from each.

### Reciprocity and graph problems

`_validate_reciprocity` (`project.py:706-749`) exempts `upstream` edges: no
counterpart is expected. A config reached only through an upstream edge is not
checked for reciprocity at all, since its own edges were not loaded.

New graph problems:

- a node declaring itself as its own upstream;
- an upstream id that is **also writable from the declaring node** under the
  write rule — the same id under `children` or `parent`, or an ancestor,
  descendant or sibling reached by parent/children edges: "'<id>' is declared
  upstream (read-only) by '<declarer>', but '<declarer>' is also connected to it
  as a parent/child; declare one or the other".

**The relaxation, for migration.** A node naming a parent that does not list it
as a child is today's `child '<id>' is not declared` failure. It becomes a
**warning** when some project in the loaded graph declares that node as its
upstream: "'<id>' names '<parent>' as its parent, but is read as an upstream
project by '<reader>'; remove the parent entry from '<id>' — an upstream need not
name its readers". While it stands, the old parent still behaves as the node's
parent from the node's own checkout (escalate, tracker inheritance, initiative
resolution) — fine for a transitional state.

### One upstream, several declarers

Any number of nodes may declare the same upstream id. They are one project when
their entries resolve to the same folder, which is the case in a workspace where
the same checkout is reached by different relative paths. Entries resolving to
**different** folders are the existing `duplicate project id` problem
(`project.py:411-415`), reported with both declarers named — two copies of one
project in one graph is not something TCW can choose between.

### Topology

`tcw work nodes` prints an `upstream (read-only):` section listing the upstreams
declared by the current node and by its ancestors, each with its declarer and
location, or "unreachable".

### The Proposit move, for the requester

Order matters: the reader side changes first.

1. In `proposit-app/tcw-config.yaml` (`proposit-app-repo`), add
   `connected-projects.upstream.proposit-core` with `path: ../proposit-core` and
   core's `repository` entry. Optionally declare it on the orchestration root
   too, with `path: proposit-core`; both resolve to the same folder.
2. In the orchestration root, remove `proposit-core` from
   `connected-projects.children`. Everything keeps working; `validate` warns
   that core still names `proposit-app` as its parent.
3. In proposit-core, before removing its parent:
   - **Tracker:** its `work.tracker` block holds only `candidate-query` and
     inherits `provider`, `base-url` and `credentials` from the root. Delete the
     block, or declare it in full; otherwise core's `validate` fails with
     "required" problems once step 4 lands.
   - **Initiatives:** items stamped `initiative: <root-epic>` keep the stamp;
     core's `validate` ignores an initiative it cannot resolve, and `start` on
     such an item refuses without `--force`. Clear them with
     `tcw work edit <slug> --initiative ""`.
   - **Board:** `work.path` / `work.repository` still point into the private
     orchestration repository, naming it. Moving the board is the requester's
     own step; until then, the root can read core's board but no longer write to
     it through `proposit-core/<slug>`.
4. In proposit-core, delete `connected-projects.parent`. The warning goes away;
   core's `validate` sees no connections.
5. The packages' `extends: [proposit-core]` lines are unchanged.

The reverse order — core dropping `parent` while the root still lists it as a
child — fails with today's `nonreciprocal connection` message, which names the
fix.

When the tracker block is incomplete and the project has no parent to inherit
the rest from, `validate` and the `tracker` verbs add one line to their existing
"required" problems: "this project has no parent to inherit work.tracker
settings from; declare the whole block or remove it". That is exactly the state
step 4 can create.

## Acceptance criteria

All in scratch projects built by tests, with real git repositories where a
`repository` entry is involved.

1. **Reader, one hop.** `app` declares `upstream: {core: ../core}`; `core` has no
   connections and one term. In `app`: `tcw taxonomy extends add core` succeeds,
   `tcw taxonomy list` includes core's term, `tcw taxonomy show core/<term>`
   resolves, and `tcw validate` exits 0; the same for `capabilities extends`.
   In `core`: `tcw validate` exits 0 and its output does not contain `app`.
2. **Reader, through a parent.** A package node whose parent declares the
   upstream resolves `taxonomy: extends: [core]` and a `core/<term>` reference,
   and `validate` in it exits 0 — the proposit-app package shape.
3. **Public upstream, reader-only checkout.** `app`'s upstream entry for `core`
   has a `repository` (a local bare repository) and a `path` that does not exist.
   `tcw provision` in `app` obtains `core`; criterion 1 then holds; `core`'s
   `tcw-config.yaml` contains no connection. `TCW_PROJECT_CORE` pointing at
   another copy is honored. An absent upstream is a `validate` warning with exit
   0, and `extends` of it reports it unreachable as today.
4. **Refused writes.** Each of these exits non-zero with a message containing
   `read-only` and `core` and not `nonreciprocal`, and leaves `core`'s git status
   clean: `tcw work delegate core …`; `tcw work start core/<slug>`;
   `tcw work edit core/<slug> --title x`; `tcw work stage gate spec core/<slug>`;
   `tcw work tracker link core/<slug> <key>`; `tcw serve --include-descendants`
   `PATCH /api/work/core%2F<slug>` and `POST …/actions/start` (HTTP 4xx).
5. **Read-only from every direction.** With `core` declared by one child `a` of
   root `r`: from `a`'s sibling `b`, and from `r`, `tcw work start core/<slug>` is
   refused as in 4, and `tcw work show core/<slug>` succeeds.
6. **Reads allowed.** `tcw work show core/<slug>`, `tcw work path core/<slug>`,
   `GET /api/work/core%2F<slug>` and a `tcw://W/core/<slug>` link resolve.
7. **Not walked, not beyond.** `core` is absent from `tcw work list
   --include-descendants`, `validate`'s recursion, `tcw serve`'s board and
   `reconcile` of an epic; it appears under `upstream (read-only):` in
   `tcw work nodes` from `app` and from a node below `app`. A child `x` of `core`
   is absent from `app`'s registry: `tcw work show x/<slug>` in `app` reports no
   such project.
8. **Graph problems.** A self-upstream is a problem. An upstream that is also
   the declarer's child, parent, grandparent or sibling is a problem. Two
   declarers resolving the same id to the same folder are fine; to different
   folders, a `duplicate project id` problem naming both.
9. **Migration order.** Reader switched (upstream declared, removed from the
   parent's `children`), upstream still naming that parent: `validate` exits 0
   in both with the warning above. Upstream dropped its parent while the reader
   still lists it as a child: the existing `nonreciprocal connection` failure.
   An upstream whose tracker block lacks `provider` and which has no parent: the
   "no parent to inherit" line appears beside the "required" problems.
10. The existing reciprocity tests pass unchanged:
    `test_nonreciprocal_connection_fails`,
    `test_an_absent_counterpart_does_not_disprove_reciprocity`,
    `test_a_present_counterpart_pointing_elsewhere_still_fails`,
    `test_a_correct_pair_still_validates` (`tests/test_project_registry.py`).
11. The full suite passes, run as CI runs it (bare `pytest`).

## Risks

- **A write path missed.** Mitigated structurally: the writing form of
  `resolve_qualified_work_ref` is the only way to a writable store from a
  qualified reference, and the plan lists the remaining id-taking verbs from the
  parser rather than from memory.
- **Upstream items with a stale `initiative`.** Defined, not changed: tolerated
  by `validate`, refused by `start` without `--force` (measured on 2.6.5).
- **The relaxation hides a real mistake.** A node that names a parent which reads
  it as upstream is only warned. Accepted: it is the migration's middle state,
  and the warning names the fix.

## Notes

- Overlapping backlog items should cite this rule rather than absorb it:
  `2026-09-19-aggregate-descendant-nodes-taxonomy-and-capabilities-in-tcw-serve`
  (new serve paths must use the writing form),
  `2026-09-04-tcw-provision-cannot-be-scoped-and-a-third-hop-config-can-name-a-checkout-directory`,
  `2026-09-01-fan-the-backlog-audit-out-across-every-connected-work-root` (must
  exclude upstreams), and
  `2026-09-26-decide-whether-a-capability-path-may-name-a-connected-project-by-an-unambiguous-shorthand`.
- Review history. The requester (the Proposit orchestrator session) approved
  the relation and the migration, asked for the upstream on `proposit-app-repo`,
  for defined initiative and tracker behavior, and for criteria 3 and 7's `nodes`
  case. An adversarial spec review (round 1, on `e68fc26e`) found that the first
  write rule leaked — through qualified references from siblings and
  descendants, through projects beyond an upstream, and through `tcw serve`'s
  write endpoints — and that the migration steps would leave core failing
  `validate`. All accepted; the capability-sidecar refusal it questioned was
  dropped as out of scope. The loading rule became config-only on its
  recommendation.
- Docs that state connections are always two-way and will change:
  `skills/configure/references/projects.md:30-40`, `docs/guide/multi-repo.md:21`,
  `docs/capabilities/cli/validate-a-node/description.md:7`.
