# Spec — Declare a component store's home repository so a fresh checkout can provision it

_This is an **epic** spec: it fixes the boundaries between children and the
acceptance criteria for the initiative as a whole. Implementation detail belongs
in each child's own spec._

## Capability changes

Planned ledger deltas only — nothing is written here. Each child declares and
seeds its own entries at its `plan` stage.

**Changed**

- `work/configure-the-work-store-location` — today it promises "an absolute path
  or a path relative to the owning project's primary checkout". It gains a
  second, portable way to name the store: the repository it lives in.
- `cli/locate-tcw-storage-folders` — `tcw work path` and friends must have an
  answer for a store that is declared but not yet materialized here.
- `cli/validate-a-node` — `tcw validate` must tell "declared but not provisioned"
  apart from "misconfigured".
- `cli/scaffold-the-doc-trees` — `tcw init` / `tcw work init` learn to record a
  home repository alongside `--work-path`.

**New**

- `work/declare-the-work-stores-home-repository` (child A)
- `cli/provision-declared-stores` (child A)
- `taxonomy/configure-the-taxonomy-store-location` (child B)
- `capabilities/configure-the-capabilities-store-location` (child B)
- `work/publish-store-writes-to-the-remote` (child C)

**Taxonomy**

The existing Feature is `configurable-work-store-location`, whose name is now too
narrow. Child A registers a Feature for provisioning — working name
`provisioned-component-stores` — and links the new capabilities to it; child B
decides whether the older Feature is renamed or kept alongside. A Vocabulary term
for the declaration itself (working name `home-repository`, under `store`) is
child A's to register, since `tcw capabilities set` refuses a `Feature=` that
does not resolve.

## Problem

A TCW node already supports a work store that lives outside the code repository.
`FsWorkStore.open` reads `work.path` from `tcw-config.yaml`, accepts an absolute
path or one relative to the node (`tcw/store/fs.py:2436-2447`), and commits
transitions in whatever Git repository contains it
(`tcw/store/fs.py:2456-2459`). The requester uses exactly this: their project's
items live in a separate orchestrator folder next to the code checkout.

**A path is a fact about one machine.** When Claude Code on the web starts a
session it clones the code repository and nothing else. The orchestrator folder
is not there, so `raw_root.is_dir()` is false and `FsWorkStore.open` raises
(`tcw/store/fs.py:2450-2451`). The failure is total, not partial: the board,
every item, and every lifecycle artifact are gone at once.

Worse, the reason does not survive the trip to the user. `_has_work_store`
swallows that `ValueError` and reports the node as having *no* work component at
all (`tcw/store/fs.py:194-201`), and `find_node` does the same
(`tcw/store/fs.py:147-161`). Reproduced on a node whose `work.path` names an
absent folder, the board says:

```
$ tcw work list
tcw work: no tcw work node here — run `tcw init` in the project folder.
```

That is not merely vague, it is misleading: following it would scaffold a second,
empty store rather than recover the real one. Only `tcw validate` still reports
the truth (`work.path is not a directory: …`), and the path it names is one the
environment can do nothing with. The same swallowing propagates through node
discovery, validation across the graph (`tcw/validate.py:145-148`) and
`tcw capabilities drift`, all of which skip the node in silence.

Nothing in the config says *where that folder comes from*. The one fact that
would let a fresh checkout fix this — the repository the store lives in — is the
one fact TCW never records.

Taxonomy and capabilities are worse off still: they have no configurable
location at all. `FsTreeStore.open` hard-codes `node_root/docs/<component>`
(`tcw/store/fs.py:1023-1025`), so a project that keeps its capability ledger in
an orchestrator repo cannot express that today by any means.

## Goals

1. A project can record, in `tcw-config.yaml`, the repository that holds a
   component store — portably enough that a machine which has never seen that
   store can obtain it.
2. An explicit CLI command materializes every declared-but-absent store for the
   current node, and is idempotent.
3. A command that needs an unprovisioned store fails with an error naming that
   provisioning command, distinguishable from a genuine misconfiguration.
4. The declaration covers all three component trees — work, taxonomy, and
   capabilities.
5. Writes to a provisioned store stay in step with the remote it came from, so
   work done in an environment that is later discarded is not lost with it.
6. Every existing `work.path` configuration keeps working unchanged, and a node
   with no declaration performs no network I/O whatsoever.
7. Codex and Claude get the same behavior, because it lives in `tcw`.

## Non-goals

- **Replacing the store with a remote tracker.** The store stays a folder in a
  Git repository. `tcw://W/2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge`
  and `tcw://W/2026-06-19-remote-adapter-jiraworkstore` own that direction.
- **Credential management.** Provisioning shells out to Git and inherits
  whatever authentication the environment already has. TCW stores no tokens and
  prompts for none.
- **Materializing a whole connected project.** A registered parent or child node
  that is absent stays absent; this initiative provisions *component stores*,
  not nodes. Revisit only if the children prove it insufficient.
- **Implicit provisioning.** No command outside the provisioning verb reaches the
  network. This is a deliberate constraint, not an omission — see Risks.
- **Attaching repositories to a hosted session.** Whether a second repository is
  reachable from a cloud environment is that environment's policy; TCW's job is
  to fail legibly when it is not.

## Design — child boundaries and ordering

Three children, each independently shippable and verifiable. Child A alone
resolves the requester's reported problem.

### Child A — Declare and provision the work store's home repository

The foundation: the config vocabulary, the resolution rules, the command, and
every error surface that has to change.

- **Declaration.** A `repository` block beside the existing `work.path`, naming
  the remote, an optional ref, an optional subpath within it, and an optional
  local checkout location. Shape and key names are child A's to settle; what is
  fixed here is that `path` keeps its current meaning and the new block is
  additive.
- **Resolution precedence.** An existing local store wins — the requester's
  laptop must keep using the working copy it already has. The declaration is
  what answers the question only when the local store is absent.
- **Materialization target.** The declaration may name one; absent that, a
  per-machine cache directory outside the code checkout. Not the node root: a
  store nested there collides with the resolved-work ignore rules
  (`tcw/store/fs.py:631-641`) and would be refused as an ignored store.
- **The command.** One explicit verb, node-scoped, covering every declared
  component (child A implements work; the seam must not be work-shaped).
  Idempotent: clone when absent, bring an existing checkout to the declared ref,
  do nothing when the store already resolves.
- **Error surfaces.** `FsWorkStore.open`, `_has_work_store`, `tcw validate` and
  the node-discovery helpers must report *declared but not provisioned* as its
  own condition, naming the command, rather than as a missing directory or a
  missing component.

### Child B — Generalize the declaration to taxonomy and capabilities

Blocked by A. Lifts the hard-coded `node_root/docs/<component>` in
`FsTreeStore.open` (`tcw/store/fs.py:1023-1025`) into the same configured
locator + declaration mechanism child A builds, so all three trees resolve
identically. Includes the corresponding `tcw init` and validation surfaces, and
the Feature-naming decision left open above.

### Child C — Keep a provisioned store in step with its remote across writes

Blocked by A; independent of B. Refreshes from the remote before a transition and
publishes after it, so a status change made in an ephemeral environment survives
that environment. Owns everything that follows from putting a network hop inside
a state machine that is local and atomic today: failure semantics, divergence and
conflict, whether publication is best-effort or blocking, and how to turn it off.
Deliberately isolated as its own child because it carries risk none of the rest
does.

### Ordering

```
A ──┬── B
    └── C          (B and C are parallel; neither blocks the other)
```

Recorded with `tcw work edit <child> --blocked-by <A-slug>`, not implied by
`--initiative`.

## Abstraction litmus test

| Operation                                                    | Verdict                                                                                                                                                                                             |
| ------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| _Is this store available for use here?_                      | **Model / store interface.** A Jira adapter answers it by checking credentials and reachability; a wiki adapter by resolving its space. Every adapter has an answer, so the question belongs upstairs. |
| _Make this store available._                                 | **Model / store interface.** Same argument: the abstract operation is "provision me", not "clone me". Adapters that need nothing implement it as a no-op, which is a legitimate implementation.        |
| _Clone a Git repository at a ref into a cache directory._    | **Filesystem-adapter private detail.** No abstract analog — this is the FS adapter's realization of the operation above, and nothing outside it may name a clone, a ref, or a cache path.              |
| _Publish a write so other clients see it._                   | **Model / store interface**, as a property of the store rather than a verb on each transition. A tracker's write is published by definition; the FS adapter realizes it as commit-and-push.            |
| _Where the checkout lands; the XDG cache layout._            | **Filesystem-adapter private detail.**                                                                                                                                                                |
| _The `repository` declaration in `tcw-config.yaml`._         | **Adapter locator, not a store operation** — consistent with the existing rule that canonical IDs are identity and filesystem paths are adapter locators only. A tracker adapter would read a different locator block from the same slot. |

The trap to avoid is letting "provision" mean "git clone" anywhere above the
adapter boundary. If any store-interface signature mentions a URL, a ref, or a
clone directory, the seam is in the wrong place.

## Acceptance criteria

Checked on the whole initiative, once all three children are resolved.

1. On a machine holding only the code repository, a node whose config declares a
   home repository for its work store: `tcw work list` exits non-zero with a
   message naming the provisioning command; after running that command,
   `tcw work list` prints the board and `tcw work show <slug>` prints an item's
   artifacts.
2. `tcw validate` on that same unprovisioned node reports the store as declared
   but not provisioned, in different words from a store whose path is simply
   wrong, and names the provisioning command.
3. `tcw work nodes` and `tcw capabilities drift` report an unprovisioned node as
   unprovisioned rather than as having no work component.
4. Criteria 1–3 hold identically for a declared taxonomy store and a declared
   capabilities store.
5. Running the provisioning command twice in a row leaves the working tree
   unchanged after the first run and exits 0 both times.
6. On a node that declares no home repository, no `tcw` command performs a
   network operation at all. On one that does, the only commands that may are the
   provisioning verb and the publish step child C adds to a transition — enforced
   by a test, in the shape of the existing package-wide subprocess rule in
   `tests/test_subprocess_stdin.py`.
7. A node configured with `work.path` and no `repository` behaves exactly as it
   does today: `tests/test_external_work_store.py` passes with no test rewritten
   to accommodate this work.
8. With a provisioned store, `tcw work start <slug>` followed by
   `tcw work complete <slug> --resolution done --confirm` commits in the store
   repository and publishes to its remote; provisioning the same declaration into
   a fresh directory afterwards shows the item in `completed`.
9. A provisioning failure — unreachable remote, refused authentication, unknown
   ref — reports the cause and exits non-zero without hanging for input, and
   leaves no partial store behind.
10. Every criterion above is reproducible from a bare shell with no Claude hook
    or slash command involved.

## Risks

- **A config file that names a URL to clone is a supply-chain surface.** Checking
  out a repository and running one command would fetch from a remote its config
  chose, and Git remote helpers and hooks are code. Requiring an explicit verb
  is the mitigation and is the reason the requester's "explicit provision
  command" choice is load-bearing rather than stylistic; child A should also say
  what it does about non-obvious URL schemes.
- **Hosted environments restrict which repositories are reachable.** In the
  requester's own case the second repository must be deliberately attached to the
  session. Provisioning will fail there until it is, so the error text is the
  feature — it has to say which remote failed and why.
- **Child C puts a network hop inside a state machine that is currently local
  and atomic.** Push failures, diverged remotes, and conflicts are new states for
  transitions that today either happen or don't. This is why it is a separate
  child and why nothing else depends on it.
- **Two working copies of one store on one machine.** A laptop with both a local
  `path` store and a cache clone of the same repository can drift. Precedence
  rules make it deterministic which one is used; they do not make the other one
  disappear.
- **Generalizing three trees at once (child B) touches the shared
  `FsTreeStore.open` seam** that taxonomy, capabilities, and work all pass
  through — the highest-blast-radius change in the initiative.
- **Git prompting for credentials could hang a session.** The repo already closes
  stdin on every Git call (`tcw/store/fs.py:_git`); provisioning must not be the
  exception that reintroduces it.

## Notes

- Four design choices were fixed by the requester at intake and are treated as
  constraints, not open questions: explicit provisioning over implicit;
  configurable checkout target defaulting to a cache directory; pull-before /
  push-after around writes; and scope covering all three component trees.
- No reference material was supplied — the requester's answer was that the code
  is enough — so every claim about current behavior above is cited to a line in
  this tree rather than to a document.
- The sweep for sibling defects was scoped to store *location* resolution
  (`FsWorkStore.open`, `FsTreeStore.open`, `_has_work_store`, and the validation
  and discovery paths that call them) rather than repo-wide: the reported defect
  is that one fact is missing from the configuration, and it has no siblings
  outside the code that reads that configuration.
