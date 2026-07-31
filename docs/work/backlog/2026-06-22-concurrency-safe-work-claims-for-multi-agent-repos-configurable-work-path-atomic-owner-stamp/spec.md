# Specification: concurrency-safe work claims

## Capability changes

- Change `work/start-a-work-item`: a user can identify the claimant when starting
  work, receives a contention-specific result when another claimant won, and can
  deliberately take over an existing claim without overloading the blocker
  override.
- Change `work/view-the-board`: active items show their claimant and claim time.
- No new taxonomy entry is planned. The existing `work-item` Vocabulary and
  `work-item/transition` term cover these changes. The existing
  `configurable-work-lifecycle` Feature is about lifecycle hook bindings rather
  than storage placement or claims, so these capability changes remain linked to
  their current taxonomy entries.

## Problem

`WorkStore.start` currently reads an item, checks blockers, and delegates to the
general transition path; that path reads the status, checks legality, effects the
move, then reads the item again (`tcw/store/base.py:1255-1260,1278-1294`). Two
callers can therefore both observe the same backlog state before either changes
it. The filesystem adapter stages and invokes `git mv` as separate subprocesses
(`tcw/store/fs.py:277-298`), so Git's index lock and subprocess errors, rather
than the work model, currently determine how a race loses.

The model has no claim metadata: `WorkItem` records worktree and branch but no
claimant or claim time (`tcw/store/base.py:818-837`), and the filesystem reader
does not load either field (`tcw/store/fs.py:2060-2078`). Consequently the board
can report status and blockers but not who owns active work or when it was
claimed (`tcw/work/cli.py:301-323`).

The work store is also fixed to `<node>/docs/work`. `FsTreeStore.open` constructs
that path and derives `node_root` back from it (`tcw/store/fs.py:619-646`), while
the CLI and web server open the store directly from the detected code node
(`tcw/work/cli.py:61-66`; `tcw/serve/__init__.py:380-397`). Pointing only the
store root elsewhere would therefore also misdirect config reads, hooks, Git
operations, and code worktrees. Today the sentinel is found from the current
code tree (`tcw/store/fs.py:110-130`), hooks run with the store's `node_root`
(`tcw/work/hooks.py:54-62`), and `start --worktree` uses that same root for both
work-state commits and code checkout setup (`tcw/work/cli.py:480-529`).

## Goals

- Make a backlog-to-active claim a single-winner operation at the abstract store
  boundary, with a filesystem realization that does not rely on Git's index lock
  for mutual exclusion.
- Make the winning active state and its `owner` and `started` timestamp visible
  together; a normal read must not observe a newly active, unstamped item.
- Return a typed contention result containing the current owner and start time so
  every caller can respond consistently.
- Allow a node to configure the work-store root with `work.path` in its existing
  `tcw-config.yaml`; keep `<node>/docs/work` as the default.
- Keep the code node, work-store location, work-store Git repository, and code
  worktree responsibilities explicit so an external shared work repository does
  not change node discovery, project registration, hook cwd, or code-worktree
  placement.
- Preserve current behavior for nodes that do not configure `work.path`.
- Provide a separately named, explicit takeover operation while retaining
  `--force` solely for unresolved blocker and inactive-initiative overrides.

## Non-goals

- Selecting the next unclaimed item or adding a `claim-next` command.
- Leases, TTLs, heartbeats, stale-claim detection, or automatic claim reaping.
- Building a remote work-store adapter.
- Coordinating agents that do not share the configured filesystem.
- Using lockfiles, Git branches, merges, or worktrees as the abstract claim
  protocol.
- Moving taxonomy or capabilities stores outside the code node.
- Automatically migrating or copying an existing `docs/work` tree when
  `work.path` changes.
- Changing the meanings of submit, rework, complete, discard, blockers, or
  initiative gates beyond retaining or clearing claim metadata as specified.

## Design

### Abstract claim contract

Treat claiming as a specialized, atomic `WorkStore` operation rather than a
check followed by a generic transition. It accepts a stable claimant string, a
UTC claim timestamp supplied or minted at the operation boundary, the existing
blocker override, and an explicit takeover choice. It returns the resulting
`WorkItem` or raises a typed `AlreadyClaimed` result carrying the active item's
`owner` and `started` values.

The operation has compare-and-set semantics:

- backlog + ordinary claim -> active with `owner` and `started` applied as one
  observable state change;
- active + ordinary claim -> `AlreadyClaimed`, including metadata when present;
- active + takeover -> active with replaced `owner` and `started` and an
  auditable store write;
- any other status -> the existing illegal-transition result.

This contract has direct non-filesystem analogs (an issue-tracker status update
with assignee and transition time under optimistic concurrency, or a database
transaction). Atomic directory operations remain an `FsWorkStore` detail.

`owner` and `started` become optional `WorkItem` fields stored in `state.yaml`.
Legacy active items without them remain readable and render as unowned rather
than failing. A transition out of active clears both fields, so a later rework
does not silently resurrect a stale claim; rework produces an active but unowned
item until explicitly claimed/taken over. This item does not alter rework into a
claim operation.

The CLI adds `tcw work start <slug> --owner <identity>` and
`tcw work start <slug> --take-over --owner <identity>`. Owner resolution is, in
order: non-empty `--owner`, non-empty `TCW_WORK_OWNER`, then the local Git
`user.email`, falling back to `user.name`. If none resolves, `start` refuses with
a concise instruction to pass `--owner` or set `TCW_WORK_OWNER`; TCW does not
invent a machine username that may be identical across agents. `--take-over`
requires an owner and is valid only when the item is already active. `--force`
continues to mean only "ignore blockers or the initiative-start gate"
(`tcw/store/base.py:1278-1294`; `tcw/work/cli.py:1022-1026`).

### Filesystem atomicity

For a normal backlog claim, `FsWorkStore` uses an adapter-private claiming area
under the work root. It atomically renames the item from its backlog location to
a unique claiming location. Exactly one process can remove that source entry;
losers re-read the canonical statuses and return `AlreadyClaimed` once the
winner publishes, with a short bounded retry only for that transient publish
window. The winner writes `owner` and `started` while it exclusively owns the
claiming directory, then atomically renames the fully stamped directory into
`active`. The claiming area is not a model status, is excluded from queries, and
is never exposed as an item locator.

Git staging and the scoped transition commit happen after publication and cover
the original and final canonical paths. A held `index.lock` can still make the
automatic commit fail, but it cannot allow two claimants to win. The existing
`TransitionCommitError` rule remains: the claim stays active and stamped when
its follow-up commit fails (`tcw/store/fs.py:329-377,2520-2539`). No retry is
applied to arbitrary Git failures.

If a process dies after acquiring the private claiming directory but before
publishing, later claim attempts report a distinct interrupted-claim diagnostic
that names the private claim metadata and recovery command; they do not guess
that the claim is stale. `--take-over` explicitly recovers either an active claim
or an interrupted claiming directory, rewrites the metadata, and publishes it.
This is manual recovery, not a lease.

### Configurable store location

The existing sentinel accepts:

```yaml
work:
  path: /srv/shared/team-work/docs/work
```

An absent or blank key resolves to `<code-node>/docs/work`. A relative value is
resolved against the code-node root; an absolute value is used as written. The
resolved path is normalized after expansion but must not be silently created or
migrated. It must already be a directory containing the expected work status
folders and must reside in a Git worktree when automatic transition commits are
enabled. Invalid types, missing paths, or a path that does not represent a work
store fail with a message naming `tcw-config.yaml: work.path`; `tcw validate`
reports the same problem.

Store construction separates:

- `node_root`: the code node discovered from the nearest sentinel; it remains the
  source of configuration, registry identity, lifecycle policy, hook cwd, and
  code-worktree operations;
- `root`: the resolved work-store directory;
- `store_git_root`: the Git worktree containing `root`, used only for staging and
  committing work-state changes.

This separation is specific to `FsWorkStore`; taxonomy and capabilities keep the
shared tree-store defaults. All CLI, validation, qualified-reference,
recursion, capabilities-gate, and web-server construction paths must use the
same config-aware `FsWorkStore.open(node_root)` factory. `locate` returns a
node-relative path for the default/inside-node store and an absolute path for an
external store, matching its existing outside-node fallback
(`tcw/store/fs.py:1840-1864`).

In external mode, lifecycle hooks still run in the code node. `--worktree`
creates and later merges/removes the code checkout in the code repository, while
the status/claim commit lands in `store_git_root`. The two repositories may
therefore receive separate commits. In default mode the current single-repository
behavior and commit messages remain unchanged.

### Presentation and claim lifecycle

CLI board rows append `| owner: <owner> | started: <UTC timestamp>` for active
items; missing legacy metadata renders `| owner: unclaimed`. `show` and the web
API expose the two model fields through normal `WorkItem` serialization. The web
client displays them in active-item metadata but does not add takeover controls
in this item.

When a start race is lost, the CLI prints a stable, non-traceback diagnostic such
as `X is already claimed by alice@example.com since 2026-07-31T14:22:00Z; pick
another item or use --take-over --owner <identity>`. Missing legacy metadata is
reported as `an unknown owner` and `an unknown time`. Hooks run only for the
winner of an ordinary claim. A rejected contender runs neither post-start hooks
nor worktree setup. A takeover runs the start transition bindings because it is
an explicit replacement of claim ownership, even though the status remains
active.

## Acceptance criteria

1. Two independently opened `FsWorkStore` instances racing to claim the same
   backlog item produce exactly one success and one typed `AlreadyClaimed`; the
   resulting item is active with the winner's owner and a UTC `started` value.
2. Repeated stress races never expose the same item as both backlog and active,
   never produce two successful claim results, and never expose a newly active
   item without its claim metadata.
3. A claim loser receives the winner's owner and start time without a Python or
   Git stack trace and does not run post-start hooks or create a worktree.
4. `--force` still overrides only blockers/initiative gates. It does not take
   over an active or interrupted claim; `--take-over --owner …` does.
5. A takeover replaces owner and start time and produces an auditable write; an
   interrupted private claim can be recovered only through the explicit takeover
   path.
6. With no `work.path`, current filesystem locations, transition commits,
   qualified references, descendant boards, hooks, web reads/writes, and
   `--worktree` behavior remain compatible.
7. Relative `work.path` values resolve from the code node, absolute values can
   target a separate Git worktree, and malformed/missing/non-store targets fail
   with an actionable config diagnostic in both normal commands and validation.
8. In external mode, work-state changes commit in the repository containing the
   configured work root, while hooks and code worktree create/merge/remove
   operations use the original code node repository.
9. Active CLI board rows, `work show`, and the web API/client present `owner` and
   `started`; legacy active items without those fields remain readable and are
   clearly shown as unclaimed.
10. Leaving active clears claim metadata. Rework remains active but unowned; it
    does not preserve or fabricate a prior claim.
11. The changed capabilities, README configuration and multi-agent guidance,
    `tcw-work` skill, release notes, and developer changelog describe the shipped
    behavior, and all capability and node validation checks pass.

## Risks

- The private claiming state introduces crash recovery. Hiding it from ordinary
  queries is necessary, but diagnostics and takeover tests must ensure an item
  cannot become silently stranded.
- Filesystem atomic rename guarantees require the backlog, private claiming, and
  active directories to be on one filesystem. Keeping all three beneath one
  configured root enforces that boundary; config must reject layouts that split
  them.
- A shared Git worktree still serializes index and commit writes. Claims remain
  safe when a commit loses that race, but operators can receive a truthful
  "claimed but not committed" result requiring manual commit/retry.
- Externalizing work breaks the co-located code/status commit bonus and makes
  dirty-state handling span two repositories. Tests must prove that scoped
  commits never sweep unrelated changes in either repository.
- Owner strings are operator-supplied identity labels, not authentication.
  Takeover is deliberate coordination, not an authorization boundary.
- Some code paths currently instantiate `FsWorkStore` directly. Missing even one
  config-aware construction path would yield inconsistent boards or writes, so
  repository-wide construction-path coverage is required.
