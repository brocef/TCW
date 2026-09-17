# Outcome: judge a worktree item's completion from its branch copy

Four commits on `work/2026-09-16-judge-a-worktree-item-s-completion-from-its-merged-branch-not-the-primary-checkout-s-stale-copy`,
11 files, +711 / −27.

## What shipped, task by task

**Task 1 — the tracker checks can read the item from a second store** (`e497b144`).
`authorize` and `binding_refusal` (`tcw/tracker/sync.py`) and `_strict_refusal`
(`tcw/work/cli.py`) take a keyword-only `own=`: the item's own binding, status,
owner and undelivered sync record come from it, while `_siblings` and the node's
tracker configuration stay on the primary store. Every existing caller is
unchanged because `own` defaults to the store already passed. One new test in
`tests/test_tracker_strict.py` builds two nodes holding the same slug — one
`active`, one `review` — and shows the same call passing with `own` and refusing
without it. Watched red first (`TypeError: unexpected keyword argument 'own'`).

**Task 2 — read the branch copy and judge from it** (`4b0616b4`).
`worktree_node_root` (`tcw/store/fs.py`) returns this node's own directory inside
the item's worktree, and `_branch_copy` (`tcw/work/cli.py`) opens a store there
and reads the item. `_complete` now computes `shipping` earlier and uses the
branch copy for the skipped-verify message, the blocker check and the strict
refusal. Everything after the merge is untouched. New file
`tests/test_worktree_completion.py` with 8 tests; criterion 11 added to
`tests/test_tracker_strict.py`. All 5 discriminating tests were watched red first.

**Task 3 — refuse an uncommitted worktree folder** (`fcd324fb`).
`uncommitted_paths` (`tcw/store/fs.py`) reads `git status --porcelain -z
--untracked-files=all`, includes untracked entries and consumes a rename's source
record. `_complete` refuses before the merge when the item's folder in the branch
store has anything uncommitted, regardless of `--force`, exempting an external
store by comparing the two stores' resolved roots. 7 more tests; the 5
discriminating ones watched red first.

**Task 4 — documentation** (`db7d980b`). `README.md` (the `complete` refusal
list), `docs/guide/jira.md` (the strict-mode row), `docs/changelogs/upcoming.md`,
`docs/release-notes/upcoming.md`, `skills/work/references/transitions.md`, and
`tests/cli/scenarios/09-worktree-isolation-and-merge-back.md` (assertions 16–20).

## Test result

- `pytest tests/test_worktree_completion.py tests/test_tracker_strict.py` — 79 passed.
- Full bare `pytest` after each code task: Task 1 — 3671 passed; Task 2 — 3680
  passed; **Task 3 — 3687 passed**. All three green, no failures or skips reported.
- **Task 4, the documentation commit, was not covered by a full run.** One was
  started and cancelled on the user's instruction once the work was accepted.
  What did run against it: `tests/test_shipped_procedures.py`,
  `test_plugin_manifests.py`, `test_documented_cli_surface.py`,
  `test_skill_path_pointers.py`, `test_skill_flow.py` and
  `test_skill_lifecycle_parity.py` — 473 passed. That commit changes only Markdown
  (`README.md`, `docs/guide/jira.md`, both `upcoming.md`, the work skill's
  `transitions.md`, and a CLI scenario document); no Python file is touched, and
  the tests above are the ones that read those documents.
- **Mutation checks, all 12 discriminating tests.** Each mutation was applied,
  the test run, and the source restored: warning from the primary copy only
  (criterion 1 red), from the branch copy only (16 red), warning deleted (2 and 3
  red), blockers from `item` (4 and 5 red), `worktree_node_root` without the
  relative sub-path (9 red), `own=None` (11 red), `_branch_copy` never falling
  back (13 red), the guard not refusing (6, 7, 8 red), the guard without the
  external-store exemption (10 red), the guard applied to discards (15 red).

## Verification the suite cannot do

**The original incident, reproduced and fixed.** In a scratch repository: `start
--worktree`, commit code on the branch, `submit` inside the worktree, commit
`refined-outcome.md` there, then complete from the primary checkout. Before the
change: `tcw work complete: completing 2026-09-17-manual-check directly from
active; the verify stage was skipped`. After: no such line, exit 0, item
completed.

**Cost.** Three `complete` runs each way through identical scratch flows, in two
virtual environments built the same way: before 0.920s / 1.178s / 1.196s, after
1.135s / 1.192s / 1.195s. The extra store open is inside the noise, and the spec's
cost risk is discharged.

## What the plan and spec got wrong

- **The plan's `cli.py` line numbers were stale before implementation started.**
  Other sessions landed work in that file between planning and implementing, moving
  `_complete` by about 130 lines, so the numbers pointed inside a different
  function. The plan review caught it and the plan was rewritten to cite symbols;
  worth remembering that a line number in a plan has a shelf life of hours in an
  actively worked repository.
- **Judging the warning from the branch copy alone was wrong**, and the spec said
  to do exactly that until the plan review found it. `submit` can be run from the
  primary checkout (`tests/test_recursion.py` drives this), which leaves the
  primary at `review` and the branch at `active` — the same defect mirrored. The
  spec now requires both copies to read `active`, and criterion 16 guards it.
- **Two directions of blocker edit cannot both be caught before the merge.** A
  blocker added on the primary checkout after `start` used to refuse before the
  merge and now refuses after it. Recorded as a non-goal in `spec.md` rather than
  fixed, because catching both needs the merged item reconstructed, and the
  direction the spec requires is the one where the work resolves its own blocker.
- **`tracker sync` could not be the first remedy offered.** Every sidecar write
  stages the file, including one that clears a record, so a sync with nothing owed
  writes nothing and leaves `tracker.yaml` staged — the refusal would repeat.
  Committing is named first, syncing second and conditionally.
- **The "nothing was merged" assertion would have been vacuous.** `start
  --worktree` cuts the branch from `HEAD`, so `merge-base --is-ancestor` reports
  "merged" until the branch commits something of its own. Every refusal fixture
  now commits on the branch first, and the helper asserts against that commit.
- **`git status --porcelain` needed `-z`.** Plain porcelain quotes any path with a
  space or a non-ASCII character and renders a rename as `old -> new`, so the
  refusal message would have printed quoted paths and the auto-commit-off case
  would have mis-parsed.

## Notes

- **The editable install is a single shared resource, and this repository has at
  least three sessions in it.** `pip install -e <worktree>` per `CLAUDE.md` was
  re-pointed to another session's worktree partway through, so the first manual
  CLI check silently exercised that session's code. The pytest runs were
  unaffected — run from a checkout's own root, that checkout's `tcw/` wins over
  the import hook — but the CLI check had to be redone in a private virtual
  environment (`python -m venv --system-site-packages`, then `pip install -e
  <worktree> --no-deps`), which is what the timing numbers above used. That
  isolation is worth preferring to the shared pin whenever more than one session
  is active; `CLAUDE.md` currently documents only the shared pin.
- Two related items were **not** driven by the `tcw` CLI: per `CLAUDE.md`, once
  this session began editing `tcw/`, the lifecycle was driven by editing
  `docs/work/` directly. `tcw work start --worktree` was run before the first code
  edit, while the tree was still clean; this artifact and the status move to
  `review` are hand-written.
- A concurrent session (`tcw-44`) landed `4cfdcaab`, which also edits
  `skills/work/references/transitions.md`, `README.md` and both `upcoming.md`
  files, and removes `version offered` from `DEFAULT_DOD`. Its checklist change
  cannot interact with the new refusal, which returns before the checklist is
  printed — but this branch lands second, so the merged `complete` section of
  `transitions.md` needs reading end to end rather than hunk by hunk.
- A third session filed `docs/work/inbox/2026-09-17-complete-says-the-verify-stage-was-skipped-for-a-worktree-item.md`,
  a duplicate report of this defect. Its Notes record a separate observation that
  this item does **not** address: the Definition of Done checklist printed with
  every box unticked in a non-interactive run and completion continued. That inbox
  entry still needs triage.
