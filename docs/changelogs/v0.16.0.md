# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Added (`f8f95d5..4de80a2`)

- **`review` work status.** `WORK_STATUSES` becomes a 5-tuple:
  `("backlog", "active", "review", "completed", "discarded")`.
  `RESOLVED_STATUSES` is unchanged — `review` is an *open* status, so an item in
  review still counts as an unresolved blocker, still holds its initiative epic
  open, and stays on the default board.
- **Four `LEGAL_TRANSITIONS` edges:** `(active, review)`, `(review, active)`,
  `(review, completed)`, `(review, discarded)`. `(review, active)` is the
  model's first and only reverse edge; nothing transitions out of a resolved
  status.
- **`WorkStore.submit()` / `WorkStore.rework()`** beside `start()` / `complete()`.
  `submit()` carries no gate. `rework()` fails closed while the
  `refined-outcome` artifact is present and content-bearing, reading through
  `artifacts()` rather than probing a path, so the gate stays in the model.
- **`tcw work submit <slug>`** and **`tcw work rework <slug>`**, each with a
  next-step hint on stderr.
- **`WorkItem.pr`** — pull-request URL, persisted in `state.yaml`, set with
  `tcw work edit --pr` (via `set_field`, not the composite `update_work`), shown
  by `show` when non-empty. No consumer yet; it is the field
  `complete --already-integrated` will read.
- **`WORK_ARTIFACTS` gains `rework` and `post-mortem`**, appended rather than
  inserted so no existing item's stage-letter string shifts. Board letters `W`
  and `M`.
- **`tests/test_status_parity.py`** — asserts `web/client/src/model/types.ts`
  and `tree.ts` agree with `WORK_STATUSES`. Verified to fail in both directions
  before landing.
- **`tests/test_work_review.py`** — the transition matrix, the `rework` gate,
  `review`-as-open-status, discovery/addressing, and missing-folder repair.

## Changed (`f8f95d5..4de80a2`)

- **`FsWorkStore._effect_transition` creates the destination status folder**
  (`mkdir(parents=True, exist_ok=True)`) before the move. `git mv` refuses when
  the destination's parent is missing, and nodes scaffolded before `review`
  existed have no such folder. Status-agnostic, so it also repairs a
  hand-deleted folder. Adapter-private: "ensure a directory exists" has no
  abstract analog.
- **`tcw work complete` warns on stderr when invoked from `active`** — that path
  skips the verify stage. `[prompted]`, not a gate: exit status is unchanged and
  no additional confirmation is read. Emitted by the CLI, not by
  `WorkStore.complete()`, since advisory output is not a store concern. The
  status is captured before the transition.
- **`WORK_STATUS_ORDER`** (`web/client/src/model/tree.ts`) gains `review` at
  index 1; `backlog`/`completed`/`discarded` shift to 2/3/4.
- **The board's stage-letter map uses `.get`**, so a name registered in
  `WORK_ARTIFACTS` without a corresponding letter can no longer raise `KeyError`
  in `tcw work list`.

## Removed (`f8f95d5`)

- **`WorkItem.phase`** — the field, its read in the FS loader, the three
  `"phase": ""` `state.yaml` creation sites, the `show` line, and the reconcile
  rollup column. Declared since the first work commit and never assigned a
  non-empty value by any code path; the rollup column read `-` on every row of
  every table.

  **Migration is a no-op and adds no rewrite pass.** The loader ignores unknown
  keys, so an existing `state.yaml` still carrying `phase:` loads normally; and
  `set_field` is a read-modify-write over the raw mapping, so the inert key
  simply persists. Erasing it would mean touching every item's `state.yaml` to
  delete an already-ignored value.

## Internal

- `RESERVED_PROJECT_IDS` derives from `WORK_STATUSES`, so `review` is now a
  reserved project id. `validate_project_id("review")` raises with a message
  naming the collision.
- Two existing assertions updated for the new constants
  (`test_formal_work_statuses_exclude_raw_inbox`,
  `test_artifacts_report_bounded_presence_and_locator`).


## Added (`e34f082..HEAD`)

- **`work.auto-commit-transitions` (default `true`)** — every status transition
  commits its own move, implemented in `FsWorkStore._effect_transition`. That is
  the single choke point both the CLI and `tcw serve` pass through; a CLI-side
  implementation would leave web-app transitions staged but uncommitted.
  Commits are scoped to the item's source and destination folders, **not**
  `docs/work` — a scoped `git commit -- <paths>` takes working-tree state, so a
  broad pathspec sweeps in every other item's uncommitted edits.
- **`git_commit_result(node_root, message, *paths)`** — a commit that
  distinguishes benign from real failure, which `git_commit` cannot.
  Not-a-repository and nothing-to-commit return `None`; everything else (a held
  `index.lock`, no write permission, a rejecting pre-commit hook) returns a
  message. Detection is `git status --porcelain`, not a match on `git commit`'s
  stderr: three different localized, version-dependent sentences cover the benign
  cases. Untracked (`??`) entries are excluded, and pathspecs are filtered
  individually — `git commit` fails outright if *any* pathspec matches nothing,
  which is exactly what a transition's vacated source folder does.
- **`TransitionCommitError`** — raised when the move landed but its commit was
  refused. Deliberately distinct: the item *did* move, so reporting a failed
  transition would be false and would invite a retry of something that already
  happened.
- **`git_current_branch(node_root)`** — `None` outside a repo or on a detached
  `HEAD`.
- **`work.trunk-branch`** — advisory. Warns once when `HEAD` differs and commits
  where it is; never checks out, never commits elsewhere, never refuses.
  Suppressed when the item's own `branch` field equals `HEAD`, so a `--worktree`
  item does not warn on every transition.
- **`tcw work complete --already-integrated`** — for a `--worktree` item whose
  branch was merged outside TCW. Skips the merge-back and nothing else; rejected
  on an item with no worktree; suppresses the branch-not-merged warning.
- **`tests/test_work_autocommit.py`** — the plumbing, the policy keys, the
  scoping, `--worktree`, and `--already-integrated`.

## Changed (`e34f082..HEAD`)

- **`tcw work start --worktree` no longer double-commits.** The store commits the
  move; `_start`'s commit narrows to `.gitignore` and the `worktree`/`branch`
  fields. Both still land before `add_worktree`, since the work branch is created
  from `HEAD`. **`--worktree` commits regardless of
  `auto-commit-transitions`** — otherwise the branch would be created without the
  item's own status move on it.
- **`tcw serve` treats `TransitionCommitError` as success**, logging to stderr.
  The item moved, so an error status would make the UI re-render the old status.
- `skills/tcw-work/`, its references, and `commands/tcw-drive-work-to-completion.md`
  no longer instruct the agent to commit status moves by hand — that guidance is
  now wrong, not merely redundant.

## Removed (`e34f082..HEAD`)

- **`dod:` is no longer persisted.** `_complete` passed the entire checklist as
  the acknowledgement unconditionally, so every completed item stored the same
  fixed 5-string constant and the field could never differ. The checklist is
  still printed before `--confirm`. `dod_ack` stays in `complete()`'s signature —
  a remote adapter may have somewhere to put it. Existing items keep their stored
  value unread; no rewrite pass, same treatment as `phase`.

## Internal

- Pre-existing behavior pinned rather than changed: a store outside a git
  repository fails at item *creation*, because every write stages and staging is
  `git add` with `check=True`. `git_commit_result`'s not-a-repo branch is
  defensive depth for a repo that vanishes mid-run.


## Added (`36193dd..HEAD`)

- **`LifecyclePolicy`, `Binding`, `TransitionBindings`, `STAGE_IDS`,
  `TRANSITION_IDS`** in `store/base.py`, plus `WorkStore.lifecycle_policy()`.
  The ids are public API — user config keys on them, so a rename breaks it
  silently. `discard` is the one transition with no CLI verb: it is
  `complete --resolution <not-done>`, and bindings key on the **move**, so the
  two resolutions of `complete` fire different hooks.
- **`parse_lifecycle_policy(raw) -> (policy, problems)`** — pure, never raises.
  `tcw validate` reports the problems; `FsWorkStore.lifecycle_policy()` discards
  them, because reading a policy must not break `tcw work list` over a mistyped
  key. One implementation so the two cannot disagree. Parsing is partial: one bad
  binding does not discard its siblings, and every problem is reported.
- **`LIFECYCLE_STEPS`** — the machine-readable contract for every stage and
  transition (objective, inputs, produced artifact, status move, gates). Child
  4's stage documents must agree with it; one source makes that checkable.
- **`tcw work lifecycle [work-ref]`** — read-only, in three modes. Human and
  `--json` expose the same contract. `--directive` emits **one complete
  instruction line or nothing at all**, exits 0 for both bound and unbound, and
  on any error writes nothing to stdout, a diagnostic to stderr, and exits
  non-zero — so a silent empty injection can never mask a typo. It never executes
  a binding.
- **`tcw/work/hooks.py`** — `run_pre` / `run_post` / `run_bindings`. Node-root
  cwd, shell execution, `TCW_SLUG`/`TCW_STATUS`/`TCW_TRANSITION`/`TCW_NODE_ROOT`,
  300s default timeout (`work.lifecycle.timeout`), declared order, first `pre`
  failure aborts. Skill bindings are reported, never executed.
- `tests/test_lifecycle_policy.py`, `tests/test_lifecycle_hooks.py`.

## Changed (`36193dd..HEAD`)

- **`pre` hooks run before the store is touched at all.** `complete()` writes the
  resolution with `set_field` before it moves the item, so a hook evaluated
  inside the store would strand a resolution on an unmoved item. Execution lives
  in the CLI, which owns the ordering — no interface change, no transaction
  concept. `tests/test_lifecycle_hooks.py` asserts the *field* as well as the
  status after an aborted `complete`.
- **A failing `post` hook exits non-zero without rolling back**, and says so:
  the move and its commit have already happened.
- The web complete modal states that configured hooks do not run there, and that
  a refused auto-commit still moves the item and reports to `tcw serve`'s
  terminal. Carried over from child 2a's deferred item — same surface.
- `work/cli.py`'s `SUBCOMMANDS` gains `submit`, `rework`, and `lifecycle`. The
  first two were a child-1 omission; latent, since work's `DEFAULT_SUBCOMMAND` is
  `None`, but wrong data that would misdispatch if that changed.


## Changed (`ae8e2d3..HEAD`)

- **`skills/tcw-work/` restructured into one document per lifecycle id.** Seven
  `references/stage-<id>.md` files on a fixed shape — Purpose / Inputs / Produce
  / Steps / Exit — with every step carrying an actor and one of `[auto]`,
  `[gated]`, `[prompted]`, `[judgment]`. No ordinals in any filename; order lives
  in the router's table.
- **`SKILL.md` is a 58-line router**, down from 170. The rule on breach is
  extract, never grow. Every displaced section has a named destination.
- New references: `transitions.md` (all five in one file), `hooks.md`,
  `delegation.md`, `epic-deltas.md`, `tags.md`, `commands.md`.
  `cross-node-epic.md` → `cross-node-deltas.md`.
- `epic-deltas.md` is a **delta list**, not a second lifecycle. That is what
  `epic-lifecycle.md` was, and why it drifted from `task-lifecycle.md`.
- The tcw-capabilities "planning gate" is now the **planning check** — it is
  `[judgment]`, and "gate" is reserved for `[gated]`.
- `tests/test_documentation_sync_wiring.py` retargeted at `stage-plan.md` and
  `stage-implement.md`, the two stages where `AGENTS.md` requires the skill.

## Added (`ae8e2d3..HEAD`)

- **`tests/test_skill_lifecycle_parity.py`** — 71 checks asserting the skill
  agrees with `LIFECYCLE_STEPS`: one document per id and no orphans; `Produce`
  and `Inputs` covering the table's artifacts; five sections in order; every
  marker recognized; no ordinals; no reference to a deleted document; the router
  reachable to every reference and within budget. Proven to fail on real drift in
  both `Produce` and `Inputs` before landing.
- `commands/tcw-process-inbox.md` and `commands/tcw-verify-work.md`;
  `tcw-plan-work` and `tcw-drive-work-to-completion` retargeted at stage ranges.
- **`agents/tcw-verifier.md`** — read-only assessment for the `verify` stage, plus
  the `agents` key in the Claude manifest. Codex has no custom agents, so it is an
  accelerator: every stage document stands alone without it.

## Removed (`ae8e2d3..HEAD`)

- `references/lifecycle.md`, `task-lifecycle.md`, `epic-lifecycle.md`, and
  `process-inbox.md`. The first two were ~85% identical and had already drifted —
  the measured fact that opened this epic.


## Added (`494eec9..HEAD`)

- **`skills/tcw-post-mortem/`** — the methodology half of the `postmortem` stage:
  reading the artifact spine backwards, what each layer tends to reveal, and the
  distinction between "nobody could have known" and "nobody checked" (only the
  second is actionable). It points at
  `tcw-work/references/stage-postmortem.md` for the contract and deliberately
  does not restate it.
- **`agents/tcw-post-mortem.md`** — read-only analysis; reports, never writes.
- **`commands/tcw-post-mortem.md`**, also reachable by invoking the skill.
- Capability `plugin/run-a-post-mortem`.

## Removed (`494eec9..HEAD`)

- **`WorkItem.pr`**, added earlier in this same epic. It was introduced on the
  prediction that `complete --already-integrated` would read it; that flag needs
  only the pre-existing `worktree` and `branch` fields, and neither the lifecycle
  policy work nor the stage documents found a use. Four children passed with no
  consumer, so it is deleted rather than left as a persisted field nothing reads.

  Third application of the pattern this epic established, after `phase` and
  `dod` — and the only one where the epic removed a field it had itself added.
