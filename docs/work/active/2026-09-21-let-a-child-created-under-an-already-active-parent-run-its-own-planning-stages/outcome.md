# Outcome — Let a child created under an already-active parent run its own planning stages

This item changed `tcw/`, so, as the project guide requires, the work system was
driven by editing files rather than with `tcw work` transition verbs. The only
exception was the `start --worktree` the coordinating session ran before
implementation began. The work was done in
`.worktrees/<slug>` with a private virtual environment pinned to the worktree.

## What shipped, task by task

| Task | Commit | What it did |
| ---- | ------ | ----------- |
| 1 | `469a9a16` | The parent is read from a `parent:` field first, and from folder nesting only when the field is absent. `tcw validate` reports a `parent:` that names no item or tombstone, and one that disagrees with the folder a nested item sits in. |
| 2 | `48bc00fc` | Added `WorkStore.independent_descendants` and `open_descendants` (a `parent_children` added here was removed at verify as unused). They walk the whole subtree, pass through old nested children without letting them hide what is beneath them, and cannot loop on a cycle. The filesystem store also counts items mid-claim in `.claiming/`, including anything nested inside a claimed folder. `validate` no longer reports an old nested child carried to completion as having no resolution. |
| 3 | `0a4a271f` | `complete` refuses while anything beneath the item is open. This applies to both resolutions, and `--force` does not bypass it. `drop` refuses while any item names this one as its parent, open or resolved. |
| 4 | `94a42e37` | `epic_completable` is false while anything beneath the epic is open, so "ready to close" and `reconcile --complete-when-ready` agree with `complete`. |
| 5 | `4af10135` | `tcw work complete` runs the check before merging a worktree branch. It checks both the primary checkout's copy of the store and the branch's copy. |
| 6 | `91443e56` | Every new child is created in `backlog/<slug>` with `parent:`. Creating a child under a resolved item, or under one with a resolved ancestor, is refused. Re-parenting is a field write, with the live-parent check and a cycle check that walks the relation. The tests that pinned the old layout now pin it for old nested children. |
| 7 | `2d3b3a93` | An old nested child's own transition or claim writes `parent:` in the same move. The claim writes it *before* the folder enters `.claiming/`. Take-over finds the vacated path from the git index (`_tracked_source`, which refuses on two matches). `start --worktree` commits the real source path. |
| 8 | `243d9e2e` | Tests for re-parenting through the store and the web app's PATCH route. The code landed in Task 6 (see below). |
| 9 | `5ac36c78` | `delete_resolved` lists nested children from `git ls-tree`, so a rerun still finds them after the folder is gone. It records them with the parent in one graveyard write (`_write_tombstones`). A resumed removal tolerates uncommitted graveyard entries for exactly those items. `_committed_item_path` and `_commit_holds` find a nested item in a past commit. |
| 10 | `be7332ab` | Tests for the other surfaces: the web complete route refuses and names the child, the projection, the web tree with mixed statuses, and tracker sync after the child's own moves and its parent's. |
| 11 | `7d3202f8` | Documentation. |

The capability change is declared in `capabilities.yaml`
(`work/decompose-a-work-item-into-children`, changed). Its description was
rewritten in Task 11 and does not contradict any other record in the ledger.

## Tests

- Full suite, run without any git identity
  (`GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null pytest -q -p no:cacheprovider`):
  `3963 passed in 817.12s (0:13:37)`.
- `pnpm exec vitest run web/client/src/model/tree.test.ts`: 9 passed.
- **Mutation checks.** Every new test was either watched red before its code
  existed, or broken afterwards and seen to go red for the reason it names. The
  mutations, each restored afterwards:
  - reading only the nesting;
  - dropping each `validate` message;
  - dropping the tombstone allowance;
  - counting legacy followers as open;
  - not recursing into grandchildren;
  - dropping the `.claiming/` scan;
  - taking a claimed folder's hex-suffixed name as the parent;
  - removing the cycle guard (the test hangs, killed by an alarm);
  - removing the legacy-resolution exemption and its narrowing;
  - removing the `complete` check, or putting it back inside `if not force:`;
  - removing the `drop` check;
  - removing the branch-copy check in the CLI;
  - nesting new children again;
  - dropping the live-parent and ancestor walks;
  - forcing `open_item` either way;
  - passing `moving=None`;
  - staging `backlog/<slug>` on take-over;
  - not writing `parent:` on claim or on transition;
  - the old worktree pathspec;
  - skipping nested tombstones;
  - dropping `also=` from the graveyard guard;
  - accepting any graveyard dirt;
  - dropping the nested lookup in `_commit_holds`;
  - making the web tree refuse to nest across statuses.
- **Manual reproduction** (`/private/tmp/claude-501/childrepro*`, with this
  worktree's `tcw`):
  - `new --parent` under an active parent prints a `backlog/` path;
  - `stage gate spec <child>` passes;
  - the suggested `start` works;
  - `submit` keeps the parent;
  - completing the parent while the child is open exits 1 naming the child, and
    succeeds once the child is done;
  - `validate` is clean.
- **The real legacy board.** A copy of the proposit-app work store (copied to
  `/private/tmp/claude-501/proposit-copy`; the original was never written to)
  reads its four nested children as `active` under their parent. `tcw validate`
  output is byte-identical between released 2.5.0 and this branch.

## What the plan or spec got wrong

1. **`_follows_parent(item)` could not live on `WorkStore` as planned.** A
   `WorkItem` cannot tell a `parent:` field from nesting, and items mid-claim
   have no findable folder. The base class now has `_relation_snapshot()`, which
   returns `(item, follows_parent)` pairs and defaults to "never follows". The
   filesystem store overrides it, using a private `_follows_parent_at(path)`.
2. **Task 8's store changes landed in Task 6**, as the revised plan anticipated
   for part of them. The resolved-item rules (existence and cycle checks for
   every item; the resolved-parent refusal only for open items) went in with
   `_require_live_parent`, because Task 6 needed that function anyway. Task 8
   became tests only.
3. **Task 9 planned for a rerun after the folder was removed but before the
   graveyard was written, and that case needs nothing new.** A resolving
   transition already writes the item's tombstone, so the existing "no such work
   item" check never fires. A relaxation I added for it and a fallback that read
   the resolution from git were both unreachable (a mutation check proved it),
   so both were removed. The interruption tests remain and pass.
4. **`tcw work start --take-over` cannot reach an interrupted claim from the CLI
   at all.** `st.get()` raises "has an interrupted claim" first. This was
   already true before this item and is the subject of
   `2026-09-15-make-start-take-over-recover-an-interrupted-claim-from-the-cli-and-the-web-app`.
   The CLI's `start --worktree` fallback to `_tracked_source` is kept, so that
   item gets a correct commit path when it lands, but it cannot be tested
   through the CLI today. The same recovery is tested at the store level
   instead (`test_take_over_of_a_legacy_child_stages_its_nested_source`).
5. **Where tests went.** Most new store tests live in a new
   `tests/test_child_status.py` rather than being spread across `test_work.py`,
   `test_validate.py` and `test_recursion.py`. The epic `reconcile` test is in
   `test_epic_completable.py`, which already imports `reconcile`, and the
   archived `show` check is in `test_retention.py` rather than
   `test_tombstone.py`.

## Limits and notes

- **The pre-merge check reads the branch's copy only when it can, and only for
  children the primary copy lacks.** If `_branch_copy` cannot read the worktree,
  only the primary copy is checked, and a child that exists only on that branch
  is caught by the store's own check after the merge. The branch copy is frozen
  at `start --worktree`, so for a child both copies have, the primary copy is
  trusted. The consequence: a child completed *on the branch only* still reads
  open in the primary copy, and the parent is refused until the child's
  completion reaches the primary checkout.
- **An old nested child whose claim loses a race is left with a `parent:`
  field.** The field names the folder it is still in, so `validate` is quiet.
  From then on it counts as having its own status, so it holds its parent open
  instead of riding along with it. Only a claim that dies between writing the
  field and moving the folder reaches this state.
- **Output order when `tcw work complete` refuses.** It prints the Definition of
  Done checklist (stdout) alongside the refusal (stderr), which can look out of
  order. Nothing is merged or moved.
- **`docs/release-notes/upcoming.md`** still opens by saying nothing else
  changed since v2.5.0. The new section added below it contradicts that, which
  is for whoever merges the batch's notes to reconcile.
- **Prettier** already reported `README.md`, `skills/work/references/commands.md`
  and `tests/cli/scenarios/10-…` before this change. The lines edited here did
  not change that.

## Suite result

`GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null pytest -q -p no:cacheprovider`
from the worktree, at `7d3202f8`: **3963 passed in 817.12s (0:13:37)**, exit 0.

## Verify fixes

The code review returned NOT DONE with one blocking finding and four smaller
ones. Each was fixed in its own `tcw work(verify):` commit, with a test that
was watched fail and a mutation check:

| Commit | Finding and fix |
| ------ | --------------- |
| `5d6572e7` | **Blocking.** The pre-merge check asked the branch's copy of the store, which is frozen at `start --worktree`. A child completed in the primary checkout since then still read open there, and completing the parent was refused. The branch copy is now asked only about children the primary copy does not have. Test: the reviewer's exact sequence (`test_a_child_completed_in_the_primary_checkout_does_not_refuse`). |
| `b0f710f5` | **The `.claiming/` scan could hang.** If a claim landed mid-scan, the walk up from a nested item climbed past the claim folder to the filesystem root and never stopped. It now stops at the claim folder and skips an entry that vanished. Test adapted from the reviewer's reproduction; with the old walk it times out. In the same commit: a claim left by 2.5.0 has no `parent:` field, so the scan and `--take-over` now take its parent from where git's index still holds it, and take-over writes the field. This was practical, so no limit is recorded for it. |
| `7ff0fabc` | **Parent cycles.** `tcw validate` did not report a loop of `parent:` fields; it now names each item in the loop and the chain. |
| `ee2ebe5e` | **Unused code.** Removed `WorkStore.parent_children`, which nothing called. The changelog records the verify fixes. |

After the fixes, run with no git identity:
`tests/test_child_status.py`, `test_worktree_completion.py`, `test_work.py`,
`test_store_editor.py`, `test_external_work_store.py`, `test_retention.py` and
`test_epic_completable.py` gave **550 passed in 149.08s**.
