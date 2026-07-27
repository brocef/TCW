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
