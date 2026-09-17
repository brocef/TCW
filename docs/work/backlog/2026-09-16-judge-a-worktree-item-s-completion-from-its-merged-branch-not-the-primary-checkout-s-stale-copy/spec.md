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
  branch, `complete` refuses before merging and says so.

## Non-goals

- Other verbs run from the primary checkout (`show`, `list`, `stage gate`, …).
  Requester's decision.
- Discards (any resolution other than `done`). Nothing is merged, so the primary
  copy is the one that gets transitioned and it stays the one judged — including
  for the skipped-verify warning, which a discard also prints today.
- `--already-integrated`. The branch was merged by someone else, so the primary
  copy already holds the work; it stays the one judged.
- Uncommitted changes in the worktree **outside** the item's folder. Today they
  surface as a teardown warning after completion (`fs.py:830-846`); unchanged.
- Other items' state. Blocker items and other items bound to the same ticket are
  still read from the primary checkout, which is where their current state is.
- `2026-09-15-resolve-sibling-nodes-to-their-worktree-copies` (GitHub #39).

## Design

**Which copy is judged.** When `complete` is shipping, the item has a
`worktree`, a `branch`, and `--already-integrated` is not given, `_complete`
opens the work store at the item's worktree directory (the path the primary
checkout's `item.worktree` names, relative to the node root) and reads the item
there — the "branch copy". The existing tests already open stores this way
(`tests/test_work.py:1033`, `FsCapabilitiesStore.open(wt)`).

Opening the store from the worktree, rather than reading files off the branch
with git, is chosen because the adapter's own resolution then gives the right
answer in both layouts without new logic: an in-checkout store resolves to the
worktree's copy, and an external `work.path` re-anchors to the same shared store
the primary sees (`fs.py:1484-1490`), where there is no stale copy to begin with.

**Keeping the judgment honest.** A store opened on the worktree reads the working
files, but the merge carries only committed branch content. Before judging,
`complete` checks the item's folder in the worktree for uncommitted changes —
staged, unstaged, or untracked — and if there are any, refuses before merging,
naming the worktree path and telling the user to commit (or discard) them and
re-run. With that refusal in place, the worktree's copy equals the branch's
committed copy for everything the judgments read.

**The three judgments** use the branch copy:

- the skipped-verify warning tests the branch copy's status;
- the blocker check passes the branch copy to the **primary** store's
  `unresolved_blockers`, so `blocked_by` comes from the branch while each
  blocker's status comes from the primary checkout;
- the strict refusal judges the ticket against the branch copy's status and
  binding (including any undelivered sync record and the item's owner), while
  items sharing the ticket are still read from the primary store.

**When the branch copy cannot be read** — the worktree directory is gone, or the
item cannot be found there — `complete` falls back to the primary copy, as today,
and prints one line to stderr saying the judgments were made from the primary
checkout because the worktree copy could not be read. It does not refuse: the
merge-back itself already handles a missing branch (`fs.py:807-809`), and a
worktree removed by hand is a recovery path worth keeping open.

**Abstraction litmus.** A worktree is a filesystem-adapter detail with no abstract
analog, so none of this enters the `WorkStore` interface. The reads happen in
`_complete`, which already uses the adapter's worktree helpers
(`merge_worktree`, `remove_worktree`, `worktree_anchors`) directly; the
uncommitted-changes probe belongs beside them in `tcw/store/fs.py`. A
non-filesystem store has no worktree and never reaches this path.

**Harness compatibility.** All of it is CLI behavior, identical under Claude and
Codex. No skill text changes are required.

## Acceptance criteria

Each is a pytest case in a git-backed temporary node, with the store inside the
checkout, unless it says otherwise. "Refused before the merge" means: exit code 1,
the branch's commits are not reachable from the primary checkout's `HEAD`, the
worktree directory still exists, and the primary copy of the item is still
`active`.

1. **Warning suppressed when the branch was submitted.** Start `--worktree`;
   from the worktree, `tcw work submit` (committed by auto-commit); from the
   primary checkout, `complete --resolution done --confirm` exits 0, the item is
   `completed`, and stderr does **not** contain `directly from active`.
2. **Warning kept when the branch was not submitted.** Same, without `submit`:
   stderr **does** contain `directly from active`.
3. **Blocker removed on the branch.** The item has an unresolved blocker at
   `start`; the blocker is removed from the item in the worktree and committed;
   `complete --resolution done --confirm` (no `--force`) exits 0 and the item is
   `completed`.
4. **Blocker added on the branch.** The item has no blocker at `start`; an
   unresolved blocker is added in the worktree and committed; `complete` is
   refused before the merge, and stderr contains `blocked by`.
5. **Uncommitted change to the item's folder.** After `start --worktree`, write
   a new untracked file into the item's folder in the worktree without
   committing; `complete` is refused before the merge, and stderr names the
   worktree path. Repeat with a modified, uncommitted `state.yaml`: same result.
6. **Strict mode, submitted on the branch.** Under strict tracker mode with the
   fake tracker from `tests/test_tracker_strict.py`, a bound item started
   `--worktree` and submitted in the worktree, whose ticket is assigned to the
   caller and sits in the status mapped to `review`, completes: exit 0, and
   stderr does not contain the strict-mode refusal text.
7. **Strict refusals still fire.** `test_complete_is_refused_before_the_worktree_merge`
   (`tests/test_tracker_strict.py:393`) passes unchanged.
8. **Worktree directory gone.** After `start --worktree` and a commit on the
   branch, remove the worktree directory with `git worktree remove --force`
   (branch kept); `complete --resolution done --confirm` still merges and
   completes as today, and stderr contains a line saying the judgment used the
   primary checkout's copy.
9. **Unchanged paths.** The existing tests for `--already-integrated`
   (`tests/test_work_autocommit.py:566`, `:588`), the external work store
   (`tests/test_external_work_store.py`), completing from inside the worktree,
   and the capability gate after merge-back (`tests/test_work.py:1011` and the
   test after it) pass unchanged.
10. **A discard is unchanged.** For a worktree item submitted on the branch, with
    an uncommitted untracked file in its worktree folder, discarding
    (`--resolution wontfix --confirm`) exits 0, still prints
    `directly from active`, and leaves the branch unmerged.
11. The full suite passes with bare `pytest` from the repository root.

## Risks

- **New refusal on uncommitted item files.** A user who writes
  `refined-outcome.md` in the worktree and forgets to commit it is now refused
  where today the completion lands without that file and the teardown then warns
  that the worktree is dirty. This is intended — today's behavior ships the item
  without its acceptance record — but it is a behavior change and belongs in the
  changelog.
- **Two stores opened for one command.** The worktree store loads its own node
  configuration. If the worktree's configuration differs from the primary's
  (for example, tracker settings edited on the branch), the strict refusal could
  read settings from the branch. The plan must decide deliberately which store
  supplies tracker configuration; the primary checkout's is the one that governs
  the completion and should be used.
- **Store-opening cost.** Opening a second store may walk the project graph
  again. `worktree_anchors` is cached per directory (`project.py:78-94`); the plan
  should confirm the extra cost is small rather than assume it.
- **`_strict_refusal` signature.** It currently takes the store and re-reads the
  item itself; judging from a different copy means either passing the item in or
  passing a status and binding through. Whichever the plan picks must keep
  `submit` and `rework`, its other callers (`cli.py:1107`, `cli.py:1136`),
  unchanged in behavior.

## Notes

- The requester narrowed this item to `complete`'s pre-merge judgments; the
  repo-wide sweep above records what else reads the stale copy without fixing
  it.
- Assumption to confirm at plan time: a store opened at the worktree directory
  resolves the same node id and tracker binding files as the primary. The
  `FsCapabilitiesStore.open(wt)` test suggests so for capabilities; the work
  store with a tracker has not been checked.
