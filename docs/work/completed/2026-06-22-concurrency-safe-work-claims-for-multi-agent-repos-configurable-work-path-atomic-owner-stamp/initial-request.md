# Concurrency-safe filesystem work claims for shared local stores

**Status: stub captured from a brainstorm — specify before implementation.**

## Problem

Two agents or processes using the same filesystem-backed TCW work store can both
select the same backlog item. `WorkStore.transition()` currently performs a
read/check followed by `FsWorkStore._effect_transition()`, leaving a TOCTOU
window. The folder move and git's `index.lock` provide accidental contention,
but the losing caller gets an implementation-shaped failure, and an active item
does not record who claimed it or when.

This item is the filesystem-only fallback for callers that genuinely share one
store root. Cross-machine and organization-wide assignment, non-developer
intake, and tracker-visible status belong to the separate external work-tracker
bridge item.

## Product changes

- Allow a node to resolve its filesystem work store from a configurable
  `work.path` in the existing `tcw-config.yaml`. The default remains
  `<node>/docs/work`; a relative value resolves from the node root. An absolute
  value may point several local processes at one shared store.
- Record an abstract claim owner and claim timestamp when an item starts, and
  surface them in `work show` and the board.
- Turn a lost start race into a clear result such as "claimed by Alice since T"
  rather than a traceback or generic illegal-transition error.
- Support an explicitly named takeover operation or flag chosen during the spec.
  Do not overload `start --force`, which already means "ignore unresolved
  blocker or initiative gates."

## Technical changes

### Separate the node from the store root

`FsTreeStore` currently derives `node_root` from the component root. A
configurable work path breaks that assumption: git operations, sentinel reads,
hook working directories, and code worktree creation still belong to the code
node, while work-state reads and writes target the configured work root. Treat
`node_root` and `store_root` as independent resolved inputs and read the sentinel
from the code node before resolving `work.path`.

### Use the filesystem transition as the claim

For a store on a filesystem whose rename semantics are proven atomic for the
configured location, the backlog-to-active directory rename is the serialization
point. Exactly one caller wins; translate a missing source or already-moved item
into a typed contention result carrying the current owner and timestamp when
available.

Do not claim safety for network or distributed filesystems merely because they
accept an absolute path. The future spec must define supported filesystem
semantics and fail validation or document degraded guarantees where atomic
rename cannot be established.

### Stamp the winning transition coherently

Add portable owner/started claim metadata to the work model so another store
could realize the same concept. The filesystem adapter must persist that metadata
as part of the winning transition commit, without an observable active-but-
unowned window and without producing a second claim commit. The spec must resolve
how transition metadata is supplied to `_effect_transition()` while preserving
the core legal-transition graph.

Retrying a held git `index.lock` may improve independent git-operation
contention, but it is not the claim lock. Retry policy, backoff, and terminal
error rendering remain specification decisions.

### Keep worktree behavior attached to the code node

When `work.path` differs from `<node>/docs/work`, work-state mutation belongs to
the configured store while `start --worktree`, branch creation, hook execution,
merge-back, and cleanup still operate on the code repository. Existing in-repo
behavior remains unchanged.

## Boundaries

This item does not provide:

- Jira, Linear, GitHub, or another external tracker integration;
- cross-machine assignment or an organization-wide claim service;
- product-facing intake outside the repository;
- status, comment, or branch synchronization with another service;
- a `WorkStore` replacement adapter;
- leases, TTLs, or automatic stale-claim reaping without evidence of need;
- a `claim-next` command when `list` followed by contention-safe `start` is
  sufficient; or
- branch-merge propagation as claim coordination.

If the configured store is not truly shared, separate clones can still claim
their separate copies. That is outside this filesystem mechanism's guarantee.

## Capability and documentation implications

The future specification has a product delta and must run the capabilities gate
before implementation. It should distinguish starting a work item from safely
claiming one and decide whether the standing `work/start-a-work-item` capability
is changed or a new capability is warranted.

Expected documentation triggers at implementation time: `README.md` for
`work.path`, claim metadata, and shared-store guarantees; `tcw-work` skill
guidance for contention/takeover behavior; release notes; and the developer
changelog.

## Relationship to external tracker coordination

The external work-tracker bridge is the higher-priority solution for shared team
assignment: the tracker owns intake, assignee, and claim state, while Git retains
the technical TCW lifecycle artifacts. This item remains useful for local agents
sharing one filesystem when no tracker is configured. Neither item implements or
blocks the other.

## Open for the future specification

- Exact `work.path` schema, validation, and precedence.
- Supported local/shared filesystem guarantees.
- Claim owner source and required/optional CLI input.
- Transition-metadata plumbing and atomic commit mechanics.
- Exact takeover command, authorization signal, and audit record.
- `index.lock` retry count and backoff.
- Migration behavior when enabling or changing `work.path`.
