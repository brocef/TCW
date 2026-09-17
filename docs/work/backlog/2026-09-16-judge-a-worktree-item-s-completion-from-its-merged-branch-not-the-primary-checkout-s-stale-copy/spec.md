# Spec: judge a worktree item's completion from its branch, not the primary checkout's stale copy

## Capability changes

None. `work/complete-a-work-item` and `cli/run-from-a-git-worktree` are both
already `Supported`; this corrects wrong behavior inside them and adds no
capability.

## Problem

`tcw work start --worktree` records `worktree` and `branch` on the item, commits
that on the primary checkout, then creates the branch from `HEAD`
(`tcw/work/cli.py:1043-1087`). From then on, the work store the item lives in is
the worktree's own copy whenever the store sits inside the checkout:
`anchor_configured_path` keeps an inside-the-checkout store in the worktree and
only re-anchors a path that leaves it (`tcw/store/fs.py:1455-1490`). So `submit`,
`rework`, verify artifacts, blocker edits and tracker records made during the
work are all committed on the branch, and the primary checkout's copy of the item
stays as it was at `start` — `active`.

`tcw work complete` has to run from the primary checkout (`cli.py:2645-2653`
refuses it from inside the item's own worktree). In `_complete`
(`cli.py:2622`), the item is read once from the primary copy (`cli.py:2628`),
several judgments are made from it, and only then does the merge-back run
(`merge_worktree`, `cli.py:2703`). The item is re-read after the merge
(`cli.py:2720`) for the capability gate, the `pre` hook and tracker delivery, so
those are already correct. The judgments made **before** the merge are not:

1. **The "skipped verify" warning** (`cli.py:2658-2660`) reads `item.status`.
   It printed "completing … directly from active; the verify stage was skipped"
   for `2026-09-16-route-agents-to-tcw-work-stage-for-stage-instructions-and-validate-its-arguments`,
   which on its branch had been submitted (`dc14ca2b`) and accepted
   (`3b4f843a`, `refined-outcome.md`). The warning was false.
2. **The blocker check** (`cli.py:2672-2677`) passes the primary copy to
   `st.unresolved_blockers`, which iterates that copy's `blocked_by`
   (`tcw/store/base.py:3428`).
   - A blocker **removed** on the branch still refuses the completion — the user
     is pushed to `--force`, which also switches off the capability gate
     (`cli.py:2726`).
   - A blocker **added** on the branch is not seen, so the check passes, the
     branch is merged, and then the store's own blocker check inside
     `complete` (`base.py:3559-3563`) refuses — **after** the merge. The
     comment at `cli.py:2697-2699` states the rule this breaks: "a refusal must
     leave the item, its branch and its worktree exactly as they were."
3. **The strict tracker-mode refusal** (`_strict_refusal`, `cli.py:356-371`,
   called at `cli.py:2700`) re-reads the item from the primary store and hands
   that store to `authorize` (`tcw/tracker/sync.py:668`). `authorize` works out
   which ticket statuses to accept from `store.get(slug).status`
   (`sync.py:689`), and reads the binding and any undelivered sync record from
   the same store (`binding_refusal`, `sync.py:637-662`). After a `submit` on the
   branch has moved the ticket to its review status, the primary copy still says
   `active`, so a correctly placed ticket is refused as out of place. A binding
   made or a sync record cleared on the branch is equally invisible.

Nothing else before the merge reads the item's own state in a way the branch
can change: `branch` and `worktree` (`cli.py:2634-2635`) are written at `start`
on the primary checkout and not edited afterwards; the Definition-of-Done
checklist (`cli.py:2678`) is node configuration, not item state.

**Sweep.** `_complete` is the only command that reads an item's `worktree` or
`branch` field to act on it (`grep` over `tcw/` for `.worktree` / `item.branch`:
`cli.py` start and complete, and `fs.py:6154`, which only suppresses an
off-trunk warning). `tcw serve` has no merge-back. Other commands run from the
primary checkout (`show`, `list`, …) do read the stale copy, but the requester
put them out of scope (see `initial-request.md`); this item does not sweep them.

## Goals

- For a shipping completion (`--resolution done`) of an item started with
  `--worktree`, whose merge-back will run, every pre-merge judgment about the
  item's own state — the skipped-verify warning, the blocker check, the strict
  tracker refusal — is made from the item as its worktree holds it.
- Every such refusal still happens before the merge, leaving the item, branch and
  worktree untouched.
- The judgments cannot silently disagree with what the merge will deliver: if
  the item's folder in the worktree holds changes that are not committed on the
  branch, `complete` refuses before merging and says how to resolve them.

## Non-goals

- Other verbs run from the primary checkout (`show`, `list`, `stage gate`, …).
  Requester's decision.
- Discards (any resolution other than `done`). Nothing is merged, so the primary
  copy is the one that gets transitioned and it stays the one judged. A discard
  of a worktree item submitted on its branch may also hand tracker delivery a
  stale `previous` status (`cli.py:2749`); that is suspected, not verified, and
  belongs to a separate item.
- `--already-integrated`. The branch was merged by someone else, so the primary
  copy already holds the work; it stays the one judged.
- Uncommitted changes in the worktree **outside** the item's folder. Today they
  surface as a teardown warning after completion (`fs.py:830-846`); unchanged.
- Other items' state. Blocker items and other items bound to the same ticket are
  still read from the primary checkout, which is where their current state is.
- Refusals that already happen after the merge and are not about stale item
  state: the store's epic-children check (`base.py:3533-3553`), the `pre` hook,
  and the capability gate.
- Node configuration edited on the branch — the lifecycle policy
  (`cli.py:2670`) and the Definition-of-Done checklist (`cli.py:2678`) are read
  from the primary checkout before the merge. Separate item.
- `2026-09-15-resolve-sibling-nodes-to-their-worktree-copies` (GitHub #39).

## Design

**Which copy is judged.** When `complete` is shipping, the item has a
`worktree` and a `branch`, and `--already-integrated` is not given, `_complete`
opens a second work store — the "branch store" — at **this node's directory
inside the worktree**, and reads the item there (the "branch copy").

That directory is the worktree's top joined with the node's path relative to
its repository's top, not the worktree top itself. `git worktree add` checks out
the whole repository at `<node>/.worktrees/<slug>` (`fs.py:777-783`), so a node
at `apps/server` has its copy at `<worktree top>/apps/server`; and the store is
looked up at exactly the directory it is given, with no search upward
(`resolve_store`, `fs.py:3219-3220`). `_complete` already does this arithmetic
for its own-worktree refusal (`cli.py:2647`).

Opening a store there, rather than reading files off the branch with git, lets
the adapter's own resolution answer both layouts: the default `docs/work` is the
worktree's copy (`fs.py:3644-3645`), and a relative `work.path` that leaves the
checkout re-anchors to the primary's store (`fs.py:1484-1490`), as does an
absolute one — where there is no stale copy to begin with.

**The uncommitted-changes guard.** A store opened on the worktree reads working
files, but the merge carries only committed branch content. So before any
judgment, and only when the branch store's root differs from the primary store's
root (an external store has no separate branch copy and is exempt), `complete`
checks the item's folder in the branch store for changes that are staged,
unstaged, or untracked. If there are any, it refuses before the merge:

- naming the worktree folder and the changed files;
- telling the user to commit them in the worktree and re-run;
- and, when `tracker.yaml` is among them, saying it may hold a ticket move or
  comment that did not reach the tracker (TCW leaves those staged and
  uncommitted on purpose, via `write_sidecar`, `fs.py:6586`), so the remedy is
  `tcw work tracker sync <slug>` run in the worktree, or committing it — never
  discarding it.

Uncommitted item changes are an ordinary state, not an edge case: only
transitions commit themselves, so a blocker edit, a field edit or a verify
artifact written in the worktree is at most staged, and with
`work.auto-commit-transitions: false` even `submit` is. The message must read as
routine guidance, not as an error report.

`--force` does **not** skip this guard. `--force` overrides the blocker check
and the capability gate — judgments about whether shipping is allowed — while
this guard protects against shipping something other than what was judged.

**Order.** The branch copy is read and the guard run first, then the
skipped-verify warning. Today the warning is printed before `shipping` is known
(`cli.py:2658` vs `cli.py:2665`), so `shipping` must be computed earlier. A
refusal from the guard therefore prints no warning.

**The three judgments** use the branch copy:

- the skipped-verify warning tests the branch copy's status — the latest status
  on the branch wins, so an item submitted and then sent back by `rework` still
  warns;
- the blocker check passes the branch copy to the **primary** store's
  `unresolved_blockers`, so `blocked_by` comes from the branch while each
  blocker's status comes from the primary checkout;
- the strict refusal judges the ticket against the branch copy's status,
  binding, undelivered sync record and owner, while items sharing the ticket
  (`_siblings`, `sync.py:257`) and the tracker configuration
  (`tracker_strict()`, `tracker_config()`) still come from the primary store.

**When the branch copy cannot be read** — the worktree directory is gone, the
store cannot be opened there (including a configuration error on the branch),
or the item is not found in it — `complete` falls back to the primary copy, as
today, skips the guard, and prints exactly one line to stderr:
`tcw work complete: could not read <slug> from its worktree at <path>; judging it from the primary checkout's copy`.
It does not refuse: the merge-back already tolerates a missing branch
(`fs.py:807-809`), and a worktree removed by hand is a recovery path worth
keeping open.

**Abstraction litmus.** A worktree is a filesystem-adapter detail with no abstract
analog, so none of this enters the `WorkStore` interface. The branch store is
opened in `_complete`, which already calls the adapter's worktree helpers
(`merge_worktree`, `remove_worktree`, `worktree_anchors`) directly; the
uncommitted-changes probe belongs beside them in `tcw/store/fs.py`. A
non-filesystem store has no worktree and never reaches this path. The tracker
functions only gain a second store argument, which any adapter can supply.

**Harness compatibility.** All of it is CLI behavior, identical under Claude and
Codex. No skill text changes are required.

## Acceptance criteria

Each is a pytest case in a git-backed temporary node whose work store is inside
the checkout, unless it says otherwise. "Refused before the merge" means: exit
code 1, the branch's commits are not reachable from the primary checkout's
`HEAD`, the worktree directory still exists, and the primary copy of the item is
still `active`.

1. **Warning suppressed when the branch was submitted.** Start `--worktree`;
   from the worktree, `tcw work submit` (committed by auto-commit); from the
   primary checkout, `complete --resolution done --confirm` exits 0, the item is
   `completed`, and stderr does **not** contain `directly from active`.
2. **Warning kept when the branch was not submitted.** Same, without `submit`:
   stderr **does** contain `directly from active`.
3. **Latest branch status wins.** Same as 1, then `tcw work rework` in the
   worktree: stderr **does** contain `directly from active`.
4. **Blocker removed on the branch.** Give the item an unresolved blocker, then
   `start --force --worktree` (the store refuses to start a blocked item without
   `--force`, `base.py:3469-3472`). In the worktree, remove the blocker and
   commit. `complete --resolution done --confirm` (no `--force`) exits 0 and the
   item is `completed`.
5. **Blocker added on the branch.** Start `--worktree`; in the worktree, add an
   unresolved blocker (an item that exists on both checkouts) and commit it.
   `complete` is refused before the merge, and stderr contains `blocked by`.
6. **Uncommitted change to the item's folder.** After `start --worktree`, write
   an untracked file into the item's folder in the worktree. `complete` is
   refused before the merge, stderr names the worktree folder, and stderr does
   not contain `directly from active`. Repeat with a staged, uncommitted edit to
   `state.yaml`, and again with `--force` added: same result each time.
7. **Staged tracker record.** In the worktree, stage a `tracker.yaml` in the
   item's folder without committing. `complete` is refused before the merge,
   stderr contains `tcw work tracker sync`, and stderr does not advise discarding
   the file.
8. **Auto-commit off.** With `work.auto-commit-transitions: false`, start
   `--worktree` and run `submit` in the worktree without committing. `complete`
   is refused before the merge by the guard.
9. **Nested node.** For a node at a subdirectory of its repository (as in
   `tests/test_environment_hardness.py`), criterion 1 holds, and stderr does not
   contain `could not read`.
10. **External store exempt.** With a work store outside the checkout (as in
    `tests/test_external_work_store.py`) and an untracked file in the item's
    folder, `complete --resolution done --confirm` is not refused by the guard.
11. **Strict mode, submitted on the branch.** Under strict tracker mode with the
    fake tracker from `tests/test_tracker_strict.py`, a bound item started
    `--worktree` and submitted in the worktree, whose ticket is assigned to the
    caller and sits in the status mapped to `review`, completes with exit 0.
12. **Strict refusals still fire.** `test_complete_is_refused_before_the_worktree_merge`
    (`tests/test_tracker_strict.py:393`) passes unchanged.
13. **Worktree directory gone.** After `start --worktree` and a commit on the
    branch, remove the worktree with `git worktree remove --force` (branch kept).
    `complete --resolution done --confirm` merges and completes as today, and
    stderr contains `could not read` and `judging it from the primary checkout's copy`.
14. **Unchanged paths.** The existing tests for `--already-integrated`
    (`tests/test_work_autocommit.py:566`, `:588`), the external work store
    (`tests/test_external_work_store.py`), completing from inside the worktree,
    the capability gate after merge-back (`tests/test_work.py:1011` and the test
    after it), and strict `start`/`submit`/`rework` (`tests/test_tracker_strict.py`)
    pass unchanged.
15. **A discard is unchanged.** Discarding (`--resolution wontfix --confirm`) a
    worktree item with an untracked file in its worktree folder exits 0 and
    leaves the branch unmerged.
16. The full suite passes with bare `pytest` from the repository root.

## Risks

- **New refusal on uncommitted item files.** A user who writes
  `refined-outcome.md` in the worktree and forgets to commit it is now refused
  where today the completion lands without that file and the teardown then warns
  that the worktree is dirty. Intended — today's behavior ships the item without
  its acceptance record — but it is a behavior change for the changelog.
- **Tracker function signatures change.** `authorize` (`sync.py:668`) uses one
  store for four reads: `binding_of`, the status (`sync.py:689`), `_siblings`
  (`sync.py:257`), and the owner inside `binding_refusal` (`sync.py:657-658`).
  Splitting them means `authorize` and `binding_refusal` take the item's own
  store separately from the store used for siblings — optional, defaulting to
  the same store. Their other callers must be unchanged in behavior:
  `_strict_refusal` for `submit`/`rework` (`cli.py:1107`, `cli.py:1136`),
  `_strict_claim` (`cli.py:391`), and the direct tests in
  `tests/test_tracker_strict.py`.
- **Store-opening cost.** Opening a second store may walk the project graph
  again. `worktree_anchors` is cached per directory (`project.py:78-94`); the plan
  should confirm the extra cost is small rather than assume it.

## Notes

- The requester narrowed this item to `complete`'s pre-merge judgments; the
  repo-wide sweep above records what else reads the stale copy without fixing
  it.
- **Known gap, accepted:** a blocker item created only on the branch is unknown to
  the primary store, and `unresolved_blockers` counts an unknown slug as resolved
  (`base.py:3426`). The pre-merge check passes, and the store's own check refuses
  after the merge (`base.py:3559-3563`) — today's behavior, unchanged. Looking
  unknown blockers up in the branch store was considered and left out to keep
  this item to the stale copy of the item itself.
- Spec reviewed once by the adversarial spec reviewer (not a multi review). Its
  blocking findings — the nested-node directory, the staged tracker record, the
  external-store exemption — and its significant ones are folded in above; the
  branch-only blocker was narrowed to the known gap above.
- Assumption to confirm at plan time: which exception `FsWorkStore.open` raises
  for a directory with no configuration or no store, so the fallback catches it.
