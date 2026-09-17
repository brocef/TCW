# Plan: judge a worktree item's completion from its branch, not the primary checkout's stale copy

Three code tasks, then one documentation block. Each task ends with its own tests
passing and the full suite green, so every commit boundary is green. The
uncommitted-changes guard — the one new refusal, and the change most likely to
disturb existing flows — is isolated in Task 3, after the branch copy is already
being read and tested.

No blockers: the related items named in `spec.md` are not prerequisites.

This item changes `tcw/`, so per `CLAUDE.md` the implementation drives the work
system by editing `docs/work/` files directly rather than through the `tcw` CLI
once code edits begin, and says so.

## Task 1 — Let the tracker checks read the item from a second store

**Modifies:** `tcw/tracker/sync.py`, `tcw/work/cli.py`, `tests/test_tracker_strict.py`.

- `binding_refusal(store, slug, config, *, own=None)` (`sync.py:637`): with
  `own = own or store`, read the binding (`binding_of`) and the owner
  (`sync.py:657-658`) from `own`.
- `authorize(store, slug, client, config, *, target, own=None)` (`sync.py:668`):
  pass `own` to `binding_refusal`; read the item's status at `sync.py:689` from
  `own`; keep `_siblings(store, …)` (`sync.py:687`) on `store`.
- `_strict_refusal(st, bare, change, own=None)` (`cli.py:356`): read the item
  (`cli.py:364`) from `own or st`, and pass `own` to `authorize`.
  `st.tracker_strict()` and `st.tracker_config()` stay on `st`.
- No caller passes `own` yet, so behavior is unchanged everywhere: `submit`
  (`cli.py:1107`), `rework` (`cli.py:1136`), `_strict_claim` (`cli.py:391`),
  `tests/test_tracker_sync.py:765`, `tests/test_tracker_strict.py:119`.

**Proves it:** one new test in `tests/test_tracker_strict.py` beside
`test_a_claimed_ticket_where_the_item_left_it_authorizes`. Two nodes hold the
same bound item: one `started` only, the other `started(submitted=True)`. The
ticket is claimed and in `In Review`. `authorize(active_store, slug, …,
target="Done", own=submitted_store)` returns `None`, and the same call without
`own` refuses. Then run all of `tests/test_tracker_strict.py` and
`tests/test_tracker_sync.py` unchanged, and the full suite.

If a second node cannot hold the same binding cheaply with the existing fixtures,
the test builds the `own` store from the worktree of a `--worktree` item instead,
which is the case Task 2 needs anyway. It must not be replaced by a test that
passes whether or not `own` is honored.

## Task 2 — Read the branch copy, and judge from it

**Modifies:** `tcw/store/fs.py`, `tcw/work/cli.py`; **creates**
`tests/test_worktree_completion.py`; **modifies** `tests/test_tracker_strict.py`.

`tcw/store/fs.py`, beside `merge_worktree`:

- `worktree_node_root(node_root: Path, worktree: str) -> Path | None` — this
  node's directory inside the item's worktree: `top = git_root(node_root)`;
  `None` if there is none; otherwise
  `node_root / worktree / node_root.resolve().relative_to(top.resolve())`.
  The docstring says why it is not the worktree top (`git worktree add` checks
  out the whole repository, and `resolve_store` does not search upward).

`tcw/work/cli.py`, `_complete`:

1. Move `shipping = resolution_status(args.resolution) == "completed"` from
   `cli.py:2665` up to just after `has_worktree` (`cli.py:2636`). `--resolution`
   is restricted by argparse `choices` (`cli.py:3252`), so this cannot change
   which error a bad value produces.
2. After the own-worktree refusal (`cli.py:2645-2653`), compute the branch copy.
   Only when `shipping and has_worktree and branch and not args.already_integrated`:
   - `path = worktree_node_root(st.node_root, item.worktree)`;
   - `own = FsWorkStore.open(path)` and `judged = own.get(bare)`, catching
     `ValueError` (covers `StoreLocationUnusable`, `StoreDeclarationError` and a
     malformed config, `fs.py:1165-1168`), `OSError`, and `MultipleMatch`
     (a plain `Exception`, `base.py:2555`);
   - on any of those, on `path is None`, on `not path.is_dir()`, or on
     `judged is None`: set `own = None`, `judged = item`, and print to stderr
     exactly
     `tcw work complete: could not read {bare} from its worktree at {path}; judging it from the primary checkout's copy`.
   When that condition is false (a discard, `--already-integrated`, or no
   worktree), set `own = None`, `judged = item`, and print nothing.
   Keep this in a small private helper `_branch_copy(st, bare, item) -> (own, judged)`
   in `cli.py` so `_complete` stays readable.
3. Warning (`cli.py:2658`): test `judged.status`.
4. Blockers (`cli.py:2673`): `st.unresolved_blockers(judged)`.
5. Strict (`cli.py:2700`): `_strict_refusal(st, bare, "complete", own=own)`.
6. Leave everything after the merge unchanged: the re-read at `cli.py:2720`,
   `run_pre`, `previous`, `st.complete`, the capability gate.

**Proves it** — `tests/test_worktree_completion.py`, one test per spec criterion,
using the `_git_subnode`-style setup (its own committed repository) and
`tcw.cli.main` with `monkeypatch.chdir`, as `tests/test_work.py:1011` does. A
shared `refused_before_merge(root, wt, slug, branch)` assertion helper checks
the spec's definition: the item is still `active` on the primary checkout, the
worktree directory exists, and `git merge-base --is-ancestor <branch> HEAD`
exits non-zero.

- Criterion 1 (submitted on the branch — no `directly from active`).
- Criterion 2 (not submitted — warning printed).
- Criterion 3 (`submit` then `rework` in the worktree — warning printed).
- Criterion 4 (blocker given before `start --force --worktree`, removed and
  committed in the worktree — completes without `--force`).
- Criterion 5 (blocker added and committed in the worktree, blocker item created
  and committed before `start` — refused before the merge, `blocked by`).
- Criterion 9 (nested node): reuse `nested_node_worktree`'s layout idea from
  `tests/test_environment_hardness.py:866`, but create the worktree with
  `tcw work start --worktree` run from the nested node; assert criterion 1's
  result and no `could not read`.
- Criterion 13 (worktree removed with `git worktree remove --force`, branch
  kept — completes, stderr has `could not read` and
  `judging it from the primary checkout's copy`).
- Criterion 11, in `tests/test_tracker_strict.py` beside
  `test_complete_is_refused_before_the_worktree_merge`: bound item, `start
  --worktree` via `cli`, `submit` via `cli` run in the worktree, ticket claimed
  by `A` and in `In Review`; `complete --resolution done --confirm` exits 0.

Commits made in the worktree during a test use `git -C <worktree> add -A` then
`commit`, since only transitions commit themselves.

Each new test is mutation-checked once before it is trusted: revert the one
line it guards (for criteria 1–3, `judged.status` back to `item.status`; for 4–5,
`judged` back to `item`; for 9, drop the relative sub-path; for 11, drop
`own=own`), confirm the test goes red for the stated reason, restore. Criterion
13 is checked by making `_branch_copy` never fall back.

Then criteria 12 and 14: run the existing tests named there unchanged, and the
full suite with bare `pytest`.

## Task 3 — Refuse when the item's worktree folder has uncommitted changes

**Modifies:** `tcw/store/fs.py`, `tcw/work/cli.py`, `tests/test_worktree_completion.py`.

`tcw/store/fs.py`, beside `worktree_node_root`:

- `uncommitted_paths(directory: Path) -> list[str]` — the entries of
  `git -C <directory> status --porcelain --untracked-files=all -- .`, as paths,
  **including** untracked (`??`) ones, unlike `_has_committable_changes`
  (`fs.py:674`), whose docstring explains why it excludes them. Empty on any git
  failure. Uses `_git`.

`tcw/work/cli.py`, `_complete`, immediately after `_branch_copy` returns a
readable branch copy and **before** the warning:

- Only when `own is not None` and `own.root.resolve() != st.root.resolve()`
  (an external store is shared, so it is exempt).
- `changed = uncommitted_paths(own.path(bare))`. If non-empty, print to stderr
  and return 1, before the warning and regardless of `--force`:
  `tcw work complete: {bare} was not completed: its folder in the worktree at {folder} has changes that are not committed on {branch}, and the merge-back carries only commits: {", ".join(changed)}. Commit them in the worktree, then complete again.`
  and, when any changed path ends in `tracker.yaml`, a second line:
  `tracker.yaml may record a ticket move or comment that did not reach the tracker. Run \`tcw work tracker sync {bare}\` in the worktree, or commit it — do not discard it.`
- Add one comment at the check saying why `--force` does not skip it (it
  protects what gets merged, not whether shipping is allowed).

**Proves it** — in `tests/test_worktree_completion.py`:

- Criterion 6: untracked file in the item's worktree folder → refused before the
  merge, stderr names the folder, no `directly from active`; repeat with a staged
  edit to `state.yaml`; repeat both with `--force`.
- Criterion 7: stage a `tracker.yaml` in the item's worktree folder → refused,
  stderr contains `tcw work tracker sync`, and does not contain `discard`.
- Criterion 8: `work.auto-commit-transitions: false` set and committed before
  `start --worktree`; `submit` in the worktree; `complete` refused by the guard.
- Criterion 10: external store (the `_external_node` layout from
  `tests/test_external_work_store.py:28`) with an item started `--worktree` and
  an untracked file in its store folder → not refused by the guard. If an
  external store and `--worktree` cannot be combined in that fixture, assert
  instead that `uncommitted_paths` is never consulted, by monkeypatching it to
  raise, and say so in the test's docstring.
- Criterion 15: discard with an untracked file in the worktree folder → exit 0,
  branch not merged.

Mutation checks: remove the guard's `return 1` (6, 7, 8 go red); drop the root
comparison (10 goes red); make the guard apply to discards (15 goes red).

Then the full suite with bare `pytest`. Any existing test that now trips the
guard is read, not patched around: if it leaves item files uncommitted in a
worktree by accident, commit them in the test; if it does so on purpose, stop
and bring it back to the spec.

## Task 4 — Documentation Sync

One pass over the finished diff, after Task 3 is green. Expected to fire:

- `docs/changelogs/upcoming.md` **[Any-Code-Change]** — under **Fixed**: `complete`
  judges a `--worktree` item's skipped-verify warning, blockers and strict
  refusal from the branch copy (`_branch_copy`, `worktree_node_root`); under
  **Changed**: the uncommitted-changes refusal (`uncommitted_paths`), not skipped
  by `--force`; `authorize`/`binding_refusal` gain `own=`.
- `docs/release-notes/upcoming.md` **[Public-API]** — plain language: completing
  a worktree item no longer claims the verify stage was skipped when it was not,
  or refuses over a blocker or ticket status the branch already changed; and it
  now stops, before merging, when the item's files in the worktree are not
  committed, saying what to do.
- `README.md` **[Public-API]** — the `complete` row of the transitions table
  (`README.md:482`): add "the item's folder in its worktree has uncommitted
  changes" to the refusal list.
- `docs/guide/jira.md` **[Tracker-Change]** — the strict-mode row for
  `submit`/`rework`/`complete` (around line 528): for a `--worktree` item, the
  ticket is judged against the item as its worktree holds it, before anything is
  merged.
- `skills/work/references/transitions.md` **[Skill-Driven-Component]** —
  - the `--worktree` bullet under `start` (line 45-48) says "transitions stay on
    the primary checkout", which is false for the default in-checkout store and
    is the belief behind this bug: say that transitions made in the worktree are
    committed on the branch, and the primary copy is updated at merge-back;
  - under `complete`: the pre-merge checks read the worktree's copy; the new
    uncommitted-changes refusal, with `tracker sync` for a staged
    `tracker.yaml`, not skipped by `--force`. `[gated]`

Not expected to fire: `skills/configure/references/<document>.md`
**[Configuration-Key-Change]** — no configuration key changes.

## Verification

What the suite cannot check:

1. **Reproduce the original incident with the real CLI.** In a scratch repository
   outside this checkout, with the worktree's editable install pointed per
   `CLAUDE.md` § "Working in a `--worktree` branch": `tcw init`, `tcw work new`,
   commit, `tcw work start <slug> --worktree`, `cd` into the worktree, `tcw work
   submit <slug>`, write and commit a `refined-outcome.md`, `cd` back, `tcw work
   complete <slug> --resolution done --confirm`. Expect no `directly from active`
   line, exit 0, item in `completed`. Then repeat with an uncommitted
   `refined-outcome.md` and expect the new refusal message to read as guidance.
2. **Store-opening cost** (spec risk). Time `tcw work complete` on that scratch
   item before and after the change with `time`; report both numbers in
   `outcome.md`. A difference well under a second is acceptable; more than that
   is brought back before completing.
3. **Harness parity.** Nothing here is skill- or hook-dependent; confirm by
   noting the diff touches no skill logic beyond `transitions.md` wording.

## Notes

- `own` is keyword-only with a default everywhere, so no existing caller changes.
- The branch-only blocker item stays a known gap (spec `## Notes`); no task
  covers it.
- Criterion mapping: 1, 2, 3, 4, 5, 9, 11, 12, 13, 14 → Task 2 (11 depends on
  Task 1); 6, 7, 8, 10, 15 → Task 3; 16 → every task's full-suite run.
