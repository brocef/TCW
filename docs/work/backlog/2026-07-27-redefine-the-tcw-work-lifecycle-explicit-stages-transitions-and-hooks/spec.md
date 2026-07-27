# Specification (overview)

This is an epic overview spec. It fixes the lifecycle contract every child task
must honor and names the child boundaries. Implementation detail belongs in each
child's own `spec.md`.

## Capability changes

Planned ledger changes only — no taxonomy or capability records are created at
this checkpoint.

- Changed: `work/start-a-work-item`, `work/complete-a-work-item`,
  `work/view-the-board` (new status), `plugin/work-lifecycle`.
- New: submit a work item for review; send a reviewed item back for rework;
  configure the work lifecycle; inspect the effective lifecycle contract; run a
  post-mortem on a finished work item.
- New taxonomy: a `lifecycle-stage` and `lifecycle-transition` vocabulary, plus a
  `configurable-work-lifecycle` Feature.

## Problem

The lifecycle was never defined once. It exists in three partly-contradictory
forms — a 4-status machine the CLI enforces, a 5-artifact spine the agent drives
by hand, and gates named inconsistently across six documents. Measured
consequences in this repo's own history:

- `task-lifecycle.md` and `epic-lifecycle.md` are ~85% identical and have already
  drifted (the epic doc omits tags; the task doc omits `reconcile`).
- The commit-per-stage rule is restated ~14 times and enforced nowhere.
- `dod:` is written to every completed item as a fixed 5-string constant; it can
  never differ, so it records nothing.
- `phase` has existed since the first work commit, is displayed by `show` and the
  reconcile table, and is never written by any code path.
- Of 60 completed items, 39 have `outcome.md` and 37 have `refined-outcome.md` —
  the artifacts a post-mortem would need are the ones nothing checks for.

There is also no state between "implemented" and "accepted", and no reverse edge:
verification can fail and the model has no transition for that outcome.

## Goals

- One canonical model: named **stages** (one artifact each) and named
  **transitions** (one status move each), with stable IDs that are public API.
- A `review` status and a `rework` edge, so verification is a state and a failed
  verification has somewhere to go.
- A hook layer letting a node bind its own skills or shell commands to any stage
  or transition, without TCW surrendering ownership of state or gates.
- One reference document per stage, each declaring its own minimum inputs, so an
  agent loads the stage it needs and nothing above it.
- A command surface addressing stage *ranges*.
- Every transition commits, so status is visible on trunk rather than stranded in
  a feature branch.

## Non-goals

- Built-in methodology presets, or custom prompt bodies.
- Resolving harness-installed skills inside the Python CLI (agent preflight owns
  that).
- Inheriting lifecycle configuration across connected projects.
- Making TDD, subagents, or worktrees TCW requirements.
- Reconstructing stage state from git history.

## The lifecycle contract

**Stages** — each produces exactly one artifact and gets one reference doc:

| id | artifact | runs in |
|---|---|---|
| `inbox` | — (creates the item) | pre-item |
| `request` | `initial-request.md` | backlog |
| `spec` | `spec.md` | backlog |
| `plan` | `plan.md` | backlog |
| `implement` | `outcome.md` | active |
| `verify` | `refined-outcome.md` | review |
| `postmortem` | `post-mortem.md` | review, or after `completed` |

**Transitions** — each changes status and commits:

| id | from → to | gates |
|---|---|---|
| `start` | backlog → active | blockers, epic-active; soft: `plan.md` present |
| `submit` | active → review | soft: `outcome.md` present |
| `complete` | review \| active → completed | capability gate, merge-back, `--confirm` |
| `rework` | review → active | none |
| `discard` | backlog \| active \| review → discarded | `--confirm` |

`complete` is **one** transition id with two legal source statuses, not two
transitions. From `active` it additionally prints a warning that the `verify`
stage was skipped — plain stderr output, not a second acknowledgement gate, and
not a distinct binding target. `complete` does **not** require
`refined-outcome.md`: verification is optional by design, and the artifact's
absence is itself the signal that verification produced nothing.

### `postmortem` is a stage with no transition

`postmortem` writes `post-mortem.md` into the item's folder wherever that folder
currently lives, and **never changes status**. Running it does not reopen a
completed item, and there is no `completed → …` edge anywhere in the model.
Before `complete` it is an ordinary stage in `review`; after `complete` it is the
single permitted write into a `completed/` item, which stays immutable in every
other respect. It is never a gate: `complete` does not wait on it.

Invariants every child must preserve:

- **IDs are public API.** No ordinal appears in an ID. Inserting a stage later
  must not renumber an existing binding.
- **A stage produces an artifact; a transition moves status.** Nothing is both.
  Stage detection stays artifact presence; status stays the folder.
- `RESOLVED_STATUSES` remains `(completed, discarded)` — an item in `review` still
  blocks its dependents.
- `postmortem` is the only artifact writable after `completed`.
- The compressed `active → completed` path survives for small changes.
- Verification rigor is hook-defined. Unbound means the skill's stop-and-ask.

## Hook layer

Adopted from the superseded `planning-agnostic-tcw-lifecycle-orchestration` spec,
which designed this in detail and remains readable at
`docs/work/discarded/2026-07-22-planning-agnostic-tcw-lifecycle-orchestration/`.
Carried forward substantially unchanged:

- A storage-neutral `LifecyclePolicy` model plus `WorkStore.lifecycle_policy()`;
  the FS adapter reads node-local policy from `tcw-config.yaml`.
- Values are ordered lists of opaque non-blank strings; declaration order is
  significant; omitted ids use TCW's neutral guidance.
- `tcw validate` rejects unknown ids, non-mapping/non-list shapes, blank or
  duplicate references, and must not reorder or disturb unrelated config.
- Read-only `tcw work lifecycle [work-ref] [--json]` reports every id in order
  with its objective, allowed inputs, required evidence, TCW-owned destination
  paths, and configured bindings. It never executes anything or changes state.
- A fixed prompt envelope for invoking a bound reference, carrying an ownership
  rule: only TCW performs transitions, commits, capability reconciliation, and
  completion. A configured-but-missing skill fails closed at agent preflight.
- `tcw work complete --already-integrated` for items whose branch was merged
  outside TCW (a merged PR): skips the auto-merge, keeps every other gate,
  tolerates prior cleanup.

Extended by this initiative:

- Bindings apply to **both** ladders, keyed by stage id or transition id.
- A binding may be a skill reference **or** a shell command.
- Transition bindings distinguish `pre` (may block the move) from `post` (may
  not).

## Child tasks

Sequential; the CLI must land before the skill documents it.

1. **`review` status and transitions** — `WORK_STATUSES`, the new edges, the `pr`
   field, deletion of `phase`, the web TS mirror and its missing parity test.
2. **Transition commits, config, and DoD cleanup** — auto-commit every
   transition; `work.auto-commit-transitions` and `work.trunk-branch`; stop
   persisting `dod:`; the `LifecyclePolicy` model, validation, and
   `tcw work lifecycle`.
3. **Skill and command restructure** — seven stage docs on a fixed five-part
   shape (Purpose / Inputs / Produce / Gates / Exit), delta-only epic and
   cross-node docs, deletion of `lifecycle.md`, `task-lifecycle.md`, and
   `epic-lifecycle.md`, and five commands.
4. **Post-mortem skill** — the skill, the `post-mortem.md` artifact, and the
   `verify`-stage hook that offers it when verification surfaced serious
   unforeseen issues.

## Migration

- Existing nodes have four status folders; `review/` must be created lazily
  rather than assumed, and a node missing it must not crash.
- **No in-flight item needs migrating.** No existing item can be in `review`,
  since the status does not yet exist. Items already in `backlog` or `active`
  keep their status and gain the new edges: an `active` item may either `submit`
  to `review` or complete directly. Nothing is rewritten, and no item changes
  status as a result of the upgrade.
- `RESERVED_PROJECT_IDS` derives from `WORK_STATUSES`, so `review` becomes a
  reserved project id — a node already using that id is a validation failure that
  needs an actionable message.
- `auto-commit-transitions` changes existing behavior (plain `start` commits
  nothing today) and needs a release note regardless of its default.
- Items completed before this change keep their stored `dod:`; new ones omit it.

## Deferred — explicitly not in scope

Carried from the superseded
`2026-07-23-capability-first-lifecycle-…` item so it is not lost. Recreate as a
follow-up item after this epic:

- Authoring a capability's expected behavior *before* `spec.md` for product
  deltas, making the capability the artifact that drives the work.
- A capability-vs-tests attestation at completion.
- That item had already rejected structured or executable acceptance-criteria
  fields and test-ID traceability as too heavy; that rejection still stands.

Also deferred: the `tcw-lifecycle-audit` skill from the superseded spec (auditing
a candidate skill or a whole configured workflow for TCW compatibility).

## Acceptance criteria

- Every stage and transition id resolves to exactly one reference doc; no id
  contains an ordinal.
- An item can go `active → review → active` and back to `review`, and complete
  from either `review` or `active`, with the compressed path warning.
- A node with no lifecycle config behaves exactly as it does today, apart from
  transition commits.
- Valid policy round-trips in declared order; invalid shapes fail validation with
  actionable messages; unrelated `tcw-config.yaml` keys are untouched.
- `tcw work lifecycle` and its `--json` form expose the same contract.
- A qualified descendant item uses its own node's policy.
- An agent resuming at a stage loads that stage's doc and only its declared
  inputs.
- `phase` is gone from the model, `state.yaml`, `show`, and the reconcile table.
- Python and TypeScript status sets are guarded by a parity test.
- README, release notes, changelog, skills, and plugin manifests describe the
  shipped behavior.

Each child spec owns its own test detail. Three areas must not be left to
inference, and each child's spec is expected to name them explicitly: lazy
`review/` creation against a node that predates the status; `tcw validate`
coverage for every rejected policy shape; and auto-commit behavior on an existing
repository, including that it creates no empty commits.

## Risks

- **Scope.** Four children touching CLI, config, skills, commands, and a new
  skill. The sequencing constraint is real: child 3 documents transitions that
  children 1–2 create.
- **Behavior change.** Auto-commit alters what every existing `tcw work` command
  does to the repo. Scoped `git commit -- <paths>` limits blast radius but the
  default needs a deliberate decision.
- **Cross-language drift.** The TS status mirror has no parity guard today; this
  epic adds a status, which is exactly when that bites.
- **Hook ownership blur.** A bound skill may attempt its own commits or
  transitions. The envelope's ownership rule is the only guard.
- **ID stability.** Once published, renaming a stage or transition id breaks user
  configuration. The set should be reviewed hard before release.

## Open questions

- `work.trunk-branch`: warn when `HEAD` differs (design leans this way), or
  actually commit to the named branch?
- `auto-commit-transitions`: default `true` (matches intent, changes behavior) or
  `false` (preserves it)?
- Does `submit` warrant its own CLI verb, or is it `tcw work review <slug>`?
