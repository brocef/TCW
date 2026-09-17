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

**Positions are given by symbol, not by line number.** The repository moved under
this plan once already — other work landed in `tcw/work/cli.py` between writing it
and reviewing it, shifting `_complete` by about 130 lines. Re-read `_complete`
before starting.

## Task 1 — Let the tracker checks read the item from a second store

**Modifies:** `tcw/tracker/sync.py`, `tcw/work/cli.py`, `tests/test_tracker_strict.py`.

- `binding_refusal(store, slug, config, *, own=None)` (`sync.py`): with
  `own = own or store`, read the binding (`binding_of`) and the owner from `own`.
- `authorize(store, slug, client, config, *, target, own=None)` (`sync.py`): pass
  `own` to `binding_refusal`; read the item's status (`store.get(slug).status` in
  the `expected_statuses` call) from `own`; keep `_siblings(store, …)` on `store`,
  which is correct — it skips the item itself.
- `_strict_refusal(st, bare, change, own=None)` (`cli.py`): read the item from
  `own or st` — this also covers its epic exemption — and pass `own` to
  `authorize`. `st.tracker_strict()` and `st.tracker_config()` stay on `st`.
- No caller passes `own` yet, so behavior is unchanged: `submit`, `rework`,
  `_strict_claim`, `tests/test_tracker_sync.py`, `tests/test_tracker_strict.py`.

**Proves it:** one new test in `tests/test_tracker_strict.py` beside
`test_a_claimed_ticket_where_the_item_left_it_authorizes`. Two nodes hold the
same bound item — `bound_item` derives the slug from the title and today's date,
so two nodes made with the same title share a slug — one `started` only, the
other `started(submitted=True)`. The ticket is claimed and in `In Review`.
`authorize(active_store, slug, …, target="Done", own=submitted_store)` returns
`None`, and the same call without `own` refuses. It discriminates: the branch
status `review` allows `In Review`, the primary status `active` does not.

Then run `tests/test_tracker_strict.py` and `tests/test_tracker_sync.py`
unchanged, and the full suite.

## Task 2 — Read the branch copy, and judge from it

**Modifies:** `tcw/store/fs.py`, `tcw/work/cli.py`; **creates**
`tests/test_worktree_completion.py`; **modifies** `tests/test_tracker_strict.py`.

`tcw/store/fs.py`, beside `merge_worktree`:

- `worktree_node_root(node_root: Path, worktree: str) -> Path | None` — this
  node's directory inside the item's worktree: `top = git_root(node_root)`;
  `None` if there is none; otherwise
  `node_root / worktree / node_root.resolve().relative_to(top.resolve())`.
  The docstring says why it is not the worktree top (`git worktree add` checks
  out the whole repository, and `resolve_store` does not search upward). Verified
  in a scratch repository during review, including the nested-node shape.

`tcw/work/cli.py`, `_complete`:

1. Move the `shipping = resolution_status(args.resolution) == "completed"`
   assignment up to just after `has_worktree`. Nothing between the two positions
   depends on the order, and argparse already restricts `--resolution` with
   `choices=sorted(WORK_RESOLUTIONS)`.
2. After the own-worktree refusal, compute the branch copy. `_complete` evaluates
   the precondition — `shipping and has_worktree and branch and not
   args.already_integrated` — and only then calls the helper
   `_branch_copy(st, bare, item) -> (own, judged)`, which takes no `args`. When
   the precondition is false (a discard, `--already-integrated`, or no worktree),
   `own = None`, `judged = item`, and nothing is printed.
   `_branch_copy` itself:
   - `path = worktree_node_root(st.node_root, item.worktree)`;
   - `own = FsWorkStore.open(path)` and `judged = own.get(bare)`, catching
     `ValueError` (which covers `StoreLocationUnusable`, `StoreDeclarationError`,
     `StoreNotProvisioned` and a malformed config), `OSError`, and `MultipleMatch`
     (a plain `Exception`). Review confirmed a missing directory and a directory
     that is not a store both raise `StoreLocationUnusable`.
   - on any of those, on `not path.is_dir()`, or on `judged is None`: return
     `(None, item)` after printing to stderr
     `tcw work complete: could not read {bare} from its worktree at {path}; judging it from the primary checkout's copy`;
   - when `path is None` (the node is not in a git repository — reachable, see
     `tests/test_non_git_writes.py`), the same fallback, but the message names
     `st.node_root / item.worktree` rather than printing `at None`.
3. The skipped-verify warning: print it only when **both** copies say `active`
   (`item.status == "active" and judged.status == "active"`). Branch copy alone
   would produce the mirrored false warning whenever `submit` was run from the
   primary checkout, which `tests/test_recursion.py`'s
   `_submit_then_complete_a_worktree_item` and `tests/test_tracker_sync.py` both
   drive. Neither test asserts on stderr, so the suite would not catch it.
4. Blockers: `st.unresolved_blockers(judged)`. The primary-side blocker edit this
   stops catching before the merge is a recorded non-goal in `spec.md`.
5. Strict: `_strict_refusal(st, bare, "complete", own=own)`.
6. Leave everything after the merge unchanged: the re-read, `run_pre`,
   `previous`, `st.complete`, the capability gate.

**Proves it** — `tests/test_worktree_completion.py`, one test per spec criterion,
using the `_git_subnode`-style setup (its own committed repository) and
`tcw.cli.main` with `monkeypatch.chdir`, as `tests/test_work.py`'s
`test_complete_gate_reads_after_worktree_mergeback` does. A shared
`refused_before_merge(root, wt, slug, branch)` helper asserts the spec's
definition: the item is still `active` on the primary checkout, the worktree
directory exists, and the branch's own commit has not reached the primary
checkout.

**That last assertion needs the branch to have a commit of its own.** `start
--worktree` cuts the branch from `HEAD`, so `git merge-base --is-ancestor
<branch> HEAD` exits 0 — "merged" — until the branch commits something. Every
refusal fixture therefore commits on the branch first, and the helper asserts on
that commit: `git merge-base --is-ancestor <branch tip sha> HEAD` exits non-zero.

- Criterion 1 (submitted on the branch — no `directly from active`).
- Criterion 2 (not submitted — warning printed).
- Criterion 3 (`submit` then `rework` in the worktree — warning printed).
- Criterion 4 (blocker given before `start --force --worktree`, removed and
  committed in the worktree — completes without `--force`). The blocker must be
  added **before** `start`, which commits the item folder's working-tree content
  as it creates the branch; a field edit does not commit itself.
- Criterion 5 (blocker item created and committed before `start`; the blocker
  added to the item and committed in the worktree — refused before the merge,
  `blocked by`).
- Criterion 9 (nested node): the layout of `nested_node_worktree` in
  `tests/test_environment_hardness.py`, with the worktree created by
  `tcw work start --worktree` run from the nested node; assert criterion 1's
  result and no `could not read`.
- Criterion 13 (worktree removed with `git worktree remove --force`, branch kept
  — completes, stderr has `could not read` and
  `judging it from the primary checkout's copy`).
- Criterion 16 (`submit` run from the **primary** checkout while the work sits on
  the branch — completes, no `directly from active`). This is the regression the
  "both copies" rule exists for.
- Criterion 11, in `tests/test_tracker_strict.py` beside
  `test_complete_is_refused_before_the_worktree_merge`: bound item, `start
  --worktree` via `cli`, `submit` via `cli` run in the worktree, ticket claimed
  by `A` and in `In Review`; `complete --resolution done --confirm` exits 0.

Commits made in the worktree during a test use `git -C <worktree> add -A` then
`commit`, since only transitions commit themselves.

**Mutation checks.** Each test is checked against a mutation it can actually
detect, then the mutation is reverted:

- criteria 1 and 16: make the warning read one copy only — criterion 1 goes red
  with `item.status`, criterion 16 with `judged.status`;
- criteria 4 and 5: `judged` back to `item`;
- criterion 9: drop the relative sub-path from `worktree_node_root`;
- criterion 11: drop `own=own`;
- criterion 13: make `_branch_copy` never fall back.

Criteria 2 and 3 are **non-discriminating regression guards** and are labelled as
such in their docstrings: both copies read `active` in those fixtures, so no
single-copy mutation changes their result. What they guard is the warning being
dropped or inverted altogether — check them by deleting the warning, which turns
both red.

Then criteria 12 and 14: run the existing tests named there unchanged, and the
full suite with bare `pytest`.

## Task 3 — Refuse when the item's worktree folder has uncommitted changes

**Modifies:** `tcw/store/fs.py`, `tcw/work/cli.py`, `tests/test_worktree_completion.py`.

`tcw/store/fs.py`, beside `worktree_node_root`:

- `uncommitted_paths(directory: Path) -> list[str]` — runs
  `git -C <directory> status --porcelain -z --untracked-files=all -- .` and
  returns the paths, **including** untracked (`??`) ones, unlike
  `_has_committable_changes`, whose docstring explains why it excludes them.
  `-z` because porcelain quotes paths containing a space or non-ASCII characters
  otherwise; with `-z` the records are NUL-separated, each `XY <path>`, and a
  rename carries its source as a second NUL-separated field. Take the path after
  the status field, and for a rename take the destination. Paths come back
  relative to the repository root, which is what the message should print. Empty
  on any git failure. Ignored files are excluded, which is deliberate: the work
  store's resolved-status folders are git-ignored by design. Uses `_git`.

`tcw/work/cli.py`, `_complete`, immediately after `_branch_copy` returns a
readable branch copy and **before** the warning:

- Only when `own is not None` and `own.root.resolve() != st.root.resolve()`
  (an external store is shared, so it is exempt — confirmed correct for both a
  relative escaping `work.path` and an absolute one).
- `changed = uncommitted_paths(own.path(bare))`. If non-empty, print to stderr
  and return 1, before the warning and regardless of `--force`:
  `tcw work complete: {bare} was not completed: its folder in the worktree at {folder} has changes that are not committed there, and the merge-back carries only commits: {", ".join(changed)}. Commit them in the worktree, then complete again.`
  Say "not committed there" rather than naming `{branch}`: the check compares
  against that worktree's `HEAD`, which a user may have moved off the item's
  branch by hand.
- When any changed path ends in `tracker.yaml`, a second line, leading with the
  action that always works:
  `tracker.yaml may record a ticket move or comment that did not reach the tracker — commit it in the worktree rather than discarding it, and if it still records an undelivered move, run \`tcw work tracker sync {bare}\` there first.`
  Not "run `tracker sync`" first: every sidecar write stages the file, including
  the ones that *clear* a record, so `sync` can legitimately find nothing owed,
  write nothing, and leave the file staged — which would refuse again and send
  the user in a circle.
- Add one comment at the check saying why `--force` does not skip it (it
  protects what gets merged, not whether shipping is allowed), and one noting
  that it therefore also precedes the Definition-of-Done checklist: a dirty
  worktree folder now stops the command before that checklist is printed, which
  is intended.

**Proves it** — in `tests/test_worktree_completion.py`, each fixture committing on
the branch first so `refused_before_merge` is not vacuous:

- Criterion 6: untracked file in the item's worktree folder → refused before the
  merge, stderr names the folder, no `directly from active`; repeat with a staged
  edit to `state.yaml`; repeat both with `--force`.
- Criterion 7: stage a `tracker.yaml` in the item's worktree folder → refused,
  stderr contains `commit it in the worktree` and `tcw work tracker sync`, and
  advises committing before syncing. Do **not** assert that stderr lacks the
  string `discard`: the message deliberately contains "rather than discarding
  it". Assert the order of the two pieces of advice instead.
- Criterion 8: `work.auto-commit-transitions: false` set and committed before
  `start --worktree`; `submit` in the worktree; `complete` refused by the guard.
  The status move appears as a rename entry, which is why `uncommitted_paths`
  handles renames.
- Criterion 10: external store (the `_external_node` layout from
  `tests/test_external_work_store.py`, which does support `--worktree`) with an
  untracked file in the item's store folder → not refused by the guard.
- Criterion 15: discard with an untracked file in the worktree folder → exit 0,
  branch not merged.

Mutation checks: remove the guard's `return 1` (6, 7, 8 go red); drop the root
comparison (10 goes red); make the guard apply to discards (15 goes red).

Then the full suite with bare `pytest`. Review checked every existing test that
completes a worktree item without `--already-integrated` and found none that
leaves the item's folder uncommitted, so the guard should break none of them. If
one trips anyway, read it rather than patching around it: if it leaves files
uncommitted by accident, commit them in the test; if on purpose, stop and bring
it back to the spec. One flow that **will** trip the guard by design is a strict
tracker delivery that fails or is held for another part, since that writes a
staged `tracker.yaml`; add it as a test only if it already has a fixture.

## Task 4 — Documentation Sync

One pass over the finished diff, after Task 3 is green. Expected to fire:

- `docs/changelogs/upcoming.md` **[Any-Code-Change]** — under **Fixed**: `complete`
  judges a `--worktree` item's skipped-verify warning, blockers and strict
  refusal from the branch copy (`_branch_copy`, `worktree_node_root`), with the
  warning requiring both copies to read `active`; under **Changed**: the
  uncommitted-changes refusal (`uncommitted_paths`), not skipped by `--force`;
  `authorize`/`binding_refusal` gain `own=`.
- `docs/release-notes/upcoming.md` **[Public-API]** — plain language: completing
  a worktree item no longer claims the verify stage was skipped when it was not,
  or refuses over a blocker or ticket status the branch already changed; and it
  now stops, before merging, when the item's files in the worktree are not
  committed, saying what to do.
- `README.md` **[Public-API]** — the `complete` row of the transitions table:
  add "the item's folder in its worktree has uncommitted changes" to the refusal
  list.
- `docs/guide/jira.md` **[Tracker-Change]** — the strict-mode row for
  `submit`/`rework`/`complete`: for a `--worktree` item, the ticket is judged
  against the item as its worktree holds it, before anything is merged.
- `skills/work/references/transitions.md` **[Skill-Driven-Component]** —
  - the `--worktree` bullet under `start` says "transitions stay on the primary
    checkout", which is false for the default in-checkout store and is the belief
    behind this bug: say that transitions made in the worktree are committed on
    the branch, and the primary copy is updated at merge-back;
  - under `complete`: the pre-merge checks read the worktree's copy; the new
    uncommitted-changes refusal, with the commit-then-`tracker sync` remedy, not
    skipped by `--force`. `[gated]`
- `tests/cli/scenarios/09-worktree-isolation-and-merge-back.md` — not covered by
  any configured trigger, so named here explicitly: it is the CLI acceptance
  scenario for this exact flow and gains assertions for the corrected warning and
  the new refusal.

Checked and **not** owed: `skills/work/SKILL.md` (mentions no worktree behavior,
so the Skill-Driven-Component entry is discharged by `transitions.md`) and
`skills/configure/references/<document>.md` **[Configuration-Key-Change]** (no
configuration key changes).

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
   Paste both terminal outputs into `outcome.md`.
2. **Store-opening cost** (spec risk). Time `tcw work complete` on that scratch
   item before and after the change with `time`; report both numbers in
   `outcome.md`. Review measured under a millisecond in a scratch repository, but
   this repository has a project registry to walk, so measure here. More than a
   second is brought back before completing.
3. **Harness parity.** Nothing here is skill- or hook-dependent; confirm by
   noting the diff touches no skill logic beyond `transitions.md` wording.

## Notes

- `own` is keyword-only with a default everywhere, so no existing caller changes.
- Two gaps are recorded in `spec.md` rather than fixed here: a blocker item
  created only on the branch, and a blocker added on the primary checkout after
  `start`.
- Criterion mapping: 1, 2, 3, 4, 5, 9, 11, 12, 13, 14, 16 → Task 2 (11 depends on
  Task 1); 6, 7, 8, 10, 15 → Task 3; 17 → every task's full-suite run.
- Reviewed by the adversarial reviewer agent and by Codex (read-only). `bllm` was
  unavailable — it answers every command with "temporarily disabled for
  maintenance" — so this was a two-way review, not the full multi review.
