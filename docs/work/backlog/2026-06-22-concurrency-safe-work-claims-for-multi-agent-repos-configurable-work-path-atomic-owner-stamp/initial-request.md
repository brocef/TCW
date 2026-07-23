# Concurrency-safe work claims for multi-agent repos (configurable work-path + atomic owner stamp)

**Status: stub captured from a brainstorm — to be spec'd out before implementation.**

## Problem

`tcw work` gives no guarantee that two agents in the same repo don't both work
the same item. `start()` is a check-then-move (`tcw/store/base.py` `transition`:
`_require(slug)` reads the status, then `_effect_transition` moves the folder) —
a TOCTOU window. The folder rename and git's `index.lock` give _accidental_
mutual exclusion today, but the loser of a race gets an ugly git stack trace,
nothing records _who_ holds an active item or _when_ they claimed it, and nothing
coordinates selection (two agents both pick the top of `board`).

## Decided design (one machine, shared filesystem; work axis only; git-backed)

The unifying principle: serialize claims through exactly one shared write target.
On a shared filesystem that target is a directory, and **a directory rename is the
lock** — `git mv backlog/X → active/X` bottoms out in an atomic POSIX `os.rename`,
so exactly one racer wins. The fix is to point the store at one shared dir, catch
the loser, and stamp the winner.

## Product changes

- **`work-path` config in the node sentinel `tcw-config.yaml`** selects where the
  work store lives. (The original request proposed a new `tcw.yaml`; the
  `tcw-config.yaml` sentinel shipped in
  `2026-06-22-node-sentinel-tcw-config-yaml-and-sentinel-based-node-detection`
  and is now the node's config file — do not add a second one. It already carries
  the `work.tags` registry, so a `work.path` key fits the existing shape.)
  Default / relative → resolved against the node root (`docs/work`, in-repo,
  unchanged behavior). Absolute → external shared dir for multi-agent use.
  Both modes run the **same `FsWorkStore` code** — only the resolved root differs.
- **`owner` + `started` shown on the board/view**: `active (alice, 2h ago)`.
- **Graceful contention message**: `start X` on an already-active item →
  "X claimed by alice since <T>; pick another (or `--force` to take over)" instead
  of a git stack trace / bare `IllegalTransition`.

## Technical changes

- **Config resolution**: read `work.path` from `tcw-config.yaml`, compute the
  store root; `FsWorkStore`
  already takes `root` as a parameter, so this is the only new branching. No
  symlinks, no baked paths (honors AGENTS.md "no hard-coded paths in references" —
  it's a config value resolved through the store).
- **Atomic-rename claim**: keep `git mv` (its worktree move is an atomic rename),
  wrap in retry-on-`index.lock`, translate "source gone" → a typed
  `AlreadyActive(owner, since)` exception the CLI renders gracefully.
- **`owner` / `started` fields** on `WorkItem`; `start(owner=…)` stamps the winner
  _after_ the move (only the rename winner reaches the stamp, so no contention).
- **Worktree decoupling (external mode only)**: today `start --worktree` commits
  the work-state move and creates the code worktree in the same `node_root`. In
  external mode these split — work-state commit → external work repo, code worktree
  → code repo. In-repo mode is unchanged.
- **Claim is caller-agnostic**: AI self-serve, orchestrator, or human all use the
  same safe `start`. Selection needs no new command — `board` (see what's free) →
  `start` (claim); on `AlreadyActive`, pick the next. A 3-line loop, not a feature.

## Meta changes

- Litmus: externalizing work = literally what `JiraWorkStore` would be (✓✓);
  owner/started = assignee/transition-time (✓); atomic-rename claim is an FS-adapter
  realization of the abstract "atomic transition" (✓). Accepted trade: in external
  mode the status flip is no longer in the same commit as the code (AGENTS.md calls
  co-location a _bonus, not load-bearing_) — completion becomes a separate write to
  the external store.
- **Explicitly out of scope**: leases/TTL + stale-claim reaping (add only if many
  ephemeral agents churn), lockfiles (the rename is the lock), a `claim-next`
  command (the board→start loop covers it), dedicated-branch-merge propagation
  (fails the litmus test — a git-merge trick with no abstract analog), and the
  remote store adapter (the config-root is the on-ramp to it, build later).
- **Docs to sync at spec time**: `README.md` (new `work-path` config + multi-agent
  usage), `tcw-work` SKILL (claim semantics, `owner`, contention), changelog +
  release notes, version bump.

## Open for the spec

- Exact key shape under `tcw-config.yaml` (`work.path`?) and precedence.
- Exact `index.lock` retry policy (count/backoff).
- Whether `owner` defaults from an env var (e.g. agent id) or must be passed.
- Capabilities-axis reconciliation (tcw-capabilities planning gate) — there is a
  product delta, so the capabilities gate runs before the technical plan is finalized.
