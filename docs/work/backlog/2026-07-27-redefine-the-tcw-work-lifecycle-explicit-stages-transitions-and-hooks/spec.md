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
- **Every documented behavior states who performs it and whether anything
  enforces it**, so reliance on agent judgment is visible rather than implied.
- A delegation model that lets a coordinating session dispatch stages to
  subagents and keep only transitions and user interaction in its own context.

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
- **A stage produces at most one *lifecycle artifact*; a transition moves
  status.** Nothing is both. "Artifact" means the named lifecycle Markdown file
  and nothing else: `inbox` produces none (it creates the item), and `implement`
  produces `outcome.md` plus arbitrary code, which is not an artifact in this
  sense. Stage detection stays artifact presence; status stays the folder.
- `RESOLVED_STATUSES` remains `(completed, discarded)` — an item in `review` still
  blocks its dependents.
- `postmortem` is the only artifact writable after `completed`. It is an
  **out-of-band stage**: it produces an artifact like any other, but holds no
  position in the ordering and is triggered by condition rather than by sequence.
  It is not a separate kind of thing — inventing a third category for one member
  would cost more than the label.
- The compressed `active → completed` path survives for small changes.
- Verification rigor is hook-defined. Unbound means the skill's stop-and-ask.

### Every artifact carries an optional `Notes` section

Any lifecycle artifact may end with `## Notes`: free-form observations the
authoring agent judged worth keeping but that do not belong in the artifact
proper. Typical contents are how the stage actually ended, a dead end not worth
re-exploring, or something the next stage should know before it starts.

This matters most under delegation. **A subagent's context is discarded when it
returns** — everything it noticed and did not write down is lost. `Notes` is the
only channel for the part of that knowledge which has no home in the artifact's
required sections. It is also the trail a post-mortem reads: `Notes` across the
spine is the record of what each stage knew at the time.

`Notes` is always optional, never a gate, and never required to be non-empty. A
stage that has nothing to add omits it.

## Execution model

Every behavior the lifecycle describes carries two attributes, and both must be
stated wherever the behavior is documented. Readers — human or agent — must never
have to guess whether something happens on its own.

**Actor:** `tcw`, `agent`, or `user`.

**Enforcement level:**

| Marker | Meaning |
|---|---|
| `[auto]` | The tool does it. Cannot not happen. |
| `[gated]` | The agent initiates; the tool refuses if preconditions fail. Outcome guaranteed. |
| `[prompted]` | **The tool must emit a reminder**; the agent may ignore it. |
| `[judgment]` | Nothing is emitted and nothing enforces it. |

`[prompted]` and `[judgment]` look identical from the agent's side — both are
skippable — and the difference is deliberately on the *tool's* side. `[prompted]`
is an obligation on the CLI, and therefore testable ("does `complete` from
`active` print the verify-skipped warning?"). `[judgment]` asserts the CLI says
nothing at all. Two reviewers read these as redundant; they are not, but only
because the requirement they encode belongs to the implementation, not to
behavior.

### Stage commits stay agent-owned

`auto-commit-transitions` covers **transitions only**. Nothing in the CLI runs at
the end of a stage, so a stage commit cannot be `[auto]` without inventing a
stage-finalization command — deliberately not built. Committing a stage artifact
is `[judgment]`, stated once in each stage document's `Exit` rather than
scattered through the guidance.

This is an accepted, named weakness: the artifacts most often skipped today are
the ones nothing checks, and this leaves them that way.

### Terminology rule

**"Gate" is reserved for `[gated]`.** A gate is something the tool refuses past.
Anything the agent is merely expected to do is a **check** or a **step**, never a
gate. The one existing misuse is the tcw-capabilities "planning gate", which is
`[judgment]` and must be renamed to **planning check** wherever it appears.
"DoD gate" is two different things and must be split when rewritten: displaying
the checklist is `[prompted]`, capability reconciliation is `[gated]`.

Context injection and Claude's prompt-based hooks are `[prompted]` delivered by
the harness rather than by stdout — same strength, Claude-only delivery. A bound
skill is `[judgment]` regardless: injection makes the binding visible without the
agent going looking, but never makes invocation certain.

This is why the `Gates` section disappears from the stage-doc *shape*: a gate is
simply a step marked `[gated]`. That is a documentation change only — it does not
move where a gate runs or who evaluates it. Gates remain in the CLI, evaluated at
their transition.

### Current distribution, and what it means

Classifying today's lifecycle shows every enforcement mechanism clustered at
`complete`: `inbox accept`, the `start` blocker and epic-active checks, capability
reconciliation, `--confirm`, and merge-back are `[gated]` or `[auto]`, while the
whole planning half — writing each artifact, the capability *planning* gate,
per-stage commits, documentation sync — is `[judgment]` end to end. The most
repeated rule in the current documentation, "stop for user verification," is
`[judgment]` with nothing behind it.

That distribution matches the measured artifact data (97% `spec.md` / `plan.md`,
62% `refined-outcome.md`): the front half works because agents follow
instructions, not because anything checks. This initiative does not attempt to
convert the planning half to `[gated]`. It requires only that **every step
declares its level**, so the reliance on judgment is visible instead of implied.

## Delegation model

Derived from the two-ladder split, and binding on the stage docs:

- **Stages are delegable to a subagent. Transitions are not.** A transition
  carries the gates, and those are evaluated once, by the session that holds the
  user relationship and the primary checkout. (The earlier rationale — "so status
  is visible on trunk" — overclaimed: `trunk-branch` only warns, so TCW commits
  on whatever branch is checked out and cannot guarantee trunk.)
- **"Delegable" means permitted, never required.** A harness without subagents —
  Codex has none — executes the same stage in the main session, following the
  same stage document. Delegation is an optimization for context isolation; no
  behavior depends on it, and the isolation and token savings simply do not
  apply where it is unavailable.
- **`request` and `verify` are not delegable either** — for a different reason: a
  subagent cannot ask the user, and both stages exist to obtain user input.

| Stage | Delegable |
|---|---|
| `inbox`, `request`, `verify` | no — interactive |
| `spec`, `plan`, `implement`, `postmortem` | yes |

The table lists **stages only**. `review` is a status, not a stage, and `submit` /
`rework` are transitions — all three are covered by the rule above that
transitions are never delegated.

`verify` is non-delegable because it ends in a user decision, not because all of
its work is interactive. Its **assessment** — reading the diff, running checks,
forming an opinion — is delegable read-only work; its **approval** is not. The
coordinating session dispatches the assessment, presents the result, and holds
the user's answer. This is what `tcw-verifier` exists for, and why that agent
cannot write.

If a delegated stage fails to produce its named artifact, that is a `[judgment]`
failure caught by the coordinating session, not a `[gated]` one: no transition has
been attempted yet, so nothing refuses. The session checks `Produce` and either
re-dispatches or escalates to the user.

This makes the main session a coordinator: it owns transitions and the two
interactive stages, and dispatches the rest. `implement` is the largest token
sink and the most valuable delegation, leaving the main context holding
`outcome.md` rather than an entire diff.

Isolation is not free, and the spec should not pretend otherwise: the
coordinating session **re-reads each delegated artifact** to verify it. The win
is reading an artifact of a few hundred lines instead of an implementation
transcript of several thousand — large, but not total. Where `Produce` names
required sections, the check can be structural rather than a full read.

Two consequences for the stage-doc shape:

- **`Inputs` doubles as the subagent's context brief.** The section that exists
  for token efficiency is the same one that makes delegation correct.
- **`Produce` is the return contract, and must be specific enough to check.** A
  subagent returning "done" gives the coordinating session nothing to verify; the
  session confirms the named artifact exists and reads it before transitioning.

### Custom agents

A custom agent earns its place only when it needs a different tool set or model
than the default; otherwise the stage doc is already the brief and a general
agent suffices. That test passes twice:

- `tcw-verifier` — read-only (no `Edit`/`Write`), for the `verify` stage's
  assessment work.
- `tcw-post-mortem` — read-only, for `postmortem`.

Both stay inside the plugin-subagent restrictions (no `hooks`, `mcpServers`, or
`permissionMode`). Codex has no custom agents, so per the harness-compatibility
rule in `AGENTS.md` these are accelerators only: every stage doc must stand alone
without them.

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
- A third output mode, `--directive`, exists for Claude's dynamic context
  injection. It emits a **complete instruction line or nothing at all** — never a
  bare value — so an unbound stage renders as empty rather than as a broken
  sentence:

  ```
  !`tcw work lifecycle --stage spec --directive`
  →  "For this stage, invoke the superpowers:brainstorming skill."
  →  ""            (unbound)
  ```

  Exit status is 0 in both cases — bound and unbound are both success. **Failure
  is distinguishable:** on an unreadable config, an unknown stage id, or an
  unresolvable work reference, `--directive` writes nothing to stdout, a
  diagnostic to stderr, and exits **non-zero**, so a silent empty injection never
  masks an error.

  `--directive` **never executes a binding.** For a shell-command binding it
  emits an instruction naming the command; running it remains the agent's step,
  subject to the same `[judgment]` level as any other binding. This keeps a
  read-only inspection command read-only.

  Codex receives no injection, so every stage doc must also carry the
  harness-neutral instruction to consult `tcw work lifecycle <slug>` for its
  bindings. Injection is the accelerator; the command is the contract.

## Child tasks

Sequential; the CLI must land before the skill documents it.

1. **`review` status and transitions** — `WORK_STATUSES`, the new edges, the `pr`
   field, deletion of `phase`, the web TS mirror and its missing parity test.
2. **Transition commits, config, and DoD cleanup** — auto-commit every
   transition; `work.auto-commit-transitions` and `work.trunk-branch`; stop
   persisting `dod:`; the `LifecyclePolicy` model, validation, and
   `tcw work lifecycle` in all three output modes (human, `--json`,
   `--directive`).
3. **Skill and command restructure** — seven stage docs on the fixed shape
   **Purpose / Inputs / Produce / Steps / Exit**, every step carrying its actor
   and enforcement marker; delta-only epic and cross-node docs; deletion of
   `lifecycle.md`, `task-lifecycle.md`, and `epic-lifecycle.md`; five commands;
   and the read-only `tcw-verifier` agent.

   `Exit` covers **both** how the stage ends well and how it ends badly — the
   failure paths (a missing input, discovery that contradicts the request, work
   too large for one item) live there rather than in a sixth section.

   Reference files are `transitions.md` (all five in one file — do not pre-split
   for five short gate sets) and `hooks.md` (genuinely rare; most projects
   configure nothing). Delegation guidance folds **into `SKILL.md`**, because
   deciding whether to dispatch a stage applies every time and the router is
   where always-relevant judgment belongs.

   **`SKILL.md` has a hard budget of 80 lines.** It is loaded on every use of the
   skill, so its size is a recurring token cost rather than a one-time one. The
   delegation rule gets roughly five lines — the stage table already carries a
   `Delegable` column, so the prose is only "transitions never; subagents cannot
   ask the user." If folding it in would breach the budget, it goes back to its
   own file instead; the budget wins, not the tidiness.
4. **Post-mortem skill** — the skill, the `post-mortem.md` artifact, the
   read-only `tcw-post-mortem` agent, and the `verify`-stage hook that offers it
   when verification surfaced serious unforeseen issues.

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
- **Stage documents are skill files, not per-item artifacts.** Changing their
  shape rewrites `skills/tcw-work/references/` and nothing under `docs/work/`. No
  existing work item contains a stage document, so none needs migrating.

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
- Every documented step names an actor and an enforcement marker; no step is
  ambiguous about whether it happens on its own.
- `--directive` emits a complete instruction or empty output, never a fragment,
  and exits 0 in both cases.
- Each delegable stage's `Produce` section names the artifact's path and the
  sections it must contain, so verifying a delegated result is "the file exists
  and has these sections" rather than a judgment about quality.
- Every stage doc is followable by a Codex agent with no injection, no custom
  agents, and no slash commands.
- No document uses the word "gate" for anything that is not `[gated]`.
- `SKILL.md` is at most 80 lines.
- Every stage doc's `Exit` names at least one failure path.
- `Notes` is accepted and preserved on every artifact, and required on none.
- `phase` is gone from the model, `state.yaml`, `show`, and the reconcile table.
- Python and TypeScript status sets are guarded by a parity test.
- README, release notes, changelog, skills, and plugin manifests describe the
  shipped behavior.

Each child spec owns its own test detail. Three areas must not be left to
inference, and each child's spec is expected to name them explicitly: lazy
`review/` creation against a node that predates the status; `tcw validate`
coverage for every rejected policy shape; and auto-commit behavior on an existing
repository, including that it creates no empty commits.

Child 2 additionally owns the `--directive` contract: bound emits one complete
instruction, unbound emits nothing, both exit 0, and every error path exits
non-zero with stderr output and an empty stdout.

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

## Resolved decisions

- **`work.trunk-branch` warns only.** It declares the branch transitions are
  expected to land on; when `HEAD` differs, TCW prints a warning and commits
  where it is. It never checks out, rewrites, or commits to a branch other than
  the current one — that plumbing is not worth it for a case that is already an
  operator mistake worth surfacing.
- **`auto-commit-transitions` defaults to `true`.** Every transition commits its
  own status move. This changes existing behavior — plain `tcw work start`
  commits nothing today — so it needs a release note and a prominent changelog
  entry, not just a config line.
- **The transition verb is `submit`.** `tcw work submit <slug>` moves
  `active → review`. The CLI verb, the transition id, and the hook binding key
  are all the same string. It fits the existing operator-perspective family
  (`start` → `submit` → `complete`); `review` was rejected because it names what
  happens next rather than what the caller is doing, and reads as though the
  command performs the review.
