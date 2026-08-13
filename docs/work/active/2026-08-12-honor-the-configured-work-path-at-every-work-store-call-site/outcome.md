# Outcome — Honor the configured work.path at every work-store call site

Implemented on branch `work/2026-08-12-honor-the-configured-work-path-at-every-work-store-call-site`
in the linked worktree `.worktrees/2026-08-12-honor-the-configured-work-path-at-every-work-store-call-site`.

## What shipped

### Task 1 — configured-store discovery is authoritative (`8364d7e`)

`_has_work_store` (`tcw/store/fs.py:172`) lost its `docs/work` fast path and is
now exactly "does `FsWorkStore.open` succeed", catching only `ValueError`.
`child_nodes` / `parent_node` / `descendant_nodes` inherit it unchanged.

Tests (`tests/test_external_work_store.py`): decoy default beside a broken
configured store, registered-child discovery through a valid external store, and
the incomplete-default-store case.

**Plan Step 3b — decision recorded.** `_has_work_store` is **strict**: no
structural allowance for default layouts. Rationale, written into `spec.md` in the
same commit: `init` gitignores the resolved status folders with a `.gitkeep`
re-include, so a fresh clone of a default-layout node keeps all six folders, and
`WORK_STATUSES` has not changed — the exposure is narrow. `tcw work init` is the
named repair (it recreates missing leaves idempotently) and is stated in the
release notes.

### Task 2 — cross-node inbox writes (`d74061c`)

`_inbox_write` now takes the opened `FsWorkStore` instead of a composed path
(`tcw/work/recursion.py:217`). It refuses a missing store root with
`ValueError("work store root does not exist: …")` and only `mkdir(exist_ok=True)`
on the `inbox` leaf, so it can restore a missing leaf inside a valid store but
never manufactures the root or its ancestors. `delegate` and `escalate` resolve
their target through `FsWorkStore.open`.

`mk_node(..., work_repo=)` in `tests/test_recursion.py` is the new
split-repository fixture. Coverage: configured-inbox routing for both directions,
the missing-root refusal, the restorable `inbox` leaf, and a CLI-level test that
`tcw work delegate` to a broken child store exits 1 with a message on stderr,
prints nothing on stdout, and creates no `<child>/docs/work`.

### Task 3 — epic reconciliation (`254e9a9`)

`reconcile` stages through `store.store_git_root` and commits with a pathspec
derived from `store.root.relative_to(store.store_git_root)`
(`tcw/work/recursion.py:206-210`). Before this it staged an external path through
the code node's repository and died with `CalledProcessError`, reproduced in the
new test before the fix.

The new test also pins scoping (a file staged outside the store root stays
staged) and idempotence (a second unchanged reconcile adds no commit).

### Task 4 — capability drift (`2272a1d`)

`_shipped_but_missing` (`tcw/capabilities/cli.py:198`) opens the configured store
and returns `[]` only on `ValueError`, replacing the `docs/work` directory guard.
The parameterized test confirmed the predicted split before the fix: the no-decoy
case reported "no capability drift", the decoy case passed under the faulty guard.

### Task 5 — split `start --worktree` persistence (`5bdf9e9`)

`ensure_worktree_ignored` returns `bool` (`tcw/store/fs.py:432`) so a caller
committing elsewhere knows whether the code node still owes a commit; it still
stages `.gitignore` itself.

`_start` (`tcw/work/cli.py:537-582`) commits store-owned state in
`st.store_git_root` with a pathspec scoped to the started item's two status
folders, then `.gitignore` in the code node, then `add_worktree`. Both guards
protected by the plan hold:

- the store pathspec names the item, never the store root — covered by
  `test_worktree_start_commit_excludes_another_staged_work_item` (external) and
  `test_worktree_start_is_one_commit_and_excludes_another_staged_item` (default);
- the default in-repository layout stays at **one** commit carrying `.gitignore`
  with the message `tcw work: start <slug> (worktree)`; the
  `(worktree metadata)` / `(worktree ignore)` pair appears only when the
  repositories genuinely differ.

Failure ordering is covered at both boundaries by monkeypatching
`git_commit_result` and asserting `add_worktree` is never called.

### Task 6 — the call-site class

The scan produced **no additional live bypass**, so no commit (per the plan's
"skip this step when the audit produces no diff"). Classification of every
retained match from
`rg -n 'docs/work|"docs"\s*/\s*"work"|git_stage|git_commit|git_commit_result' tcw --glob '*.py'`:

| Location | Classification |
| --- | --- |
| `tcw/store/base.py:808` | docstring |
| `tcw/store/fs.py:174` | comment in `_has_work_store` |
| `tcw/store/fs.py:280, 331, 357` | helper definitions (`git_stage`, `git_commit`, `git_commit_result`) |
| `tcw/store/fs.py:312, 361, 1910` | docstrings |
| `tcw/store/fs.py:439` | `ensure_worktree_ignored` stages `.gitignore` — the code node owns it |
| `tcw/store/fs.py:500` | `resolved_ignore_rules` default prefix; already parameterized for external stores |
| `tcw/store/fs.py:526` | `init`'s pristine-default check — initialization default |
| `tcw/store/fs.py:739` | `FsTreeStore._stage`; taxonomy/capabilities always live at `node_root/docs/<c>` |
| `tcw/store/fs.py:1938` | the default layout inside `FsWorkStore.open` — the definition of the default |
| `tcw/store/fs.py:1960, 2011, 2035, 2080, 2866` | already `self.store_git_root` |
| `tcw/validate.py:69, 88` | malformed-node fallback; both try `FsWorkStore.open` first and fall back only on `ValueError` |
| `tcw/work/recursion.py:17, 206, 210` | import + the Task 3 fix |
| `tcw/work/cli.py:17, 551, 566, 574` | import, comment, and the Task 5 fix |

Also checked and left alone: `merge_worktree(st.node_root, …)` and
`remove_worktree(st.node_root, …)` in `complete`, and the `git config --get`
identity probe in `_start` — all correctly addressed at the **code** repository,
which owns branches, worktrees, and Git identity. Non-goal per `spec.md`.

### Tasks 7-11 — documentation (`36b7218`)

- `README.md`: the `work.path` section now enumerates what follows the configured
  store (delegate/escalate, reconcile, drift, transitions, web edits) versus what
  stays with the code repository (hooks, `.gitignore`, branches, worktrees), and
  states plainly that a code branch cannot carry another repository's lifecycle
  files. The cross-node definition of a node no longer says "a git repo with a
  `docs/work/`". The `--worktree` section gains the split-commit note.
- `docs/release-notes/upcoming.md`: plain-language `## Fixed` block, no module
  names, no atomicity claims, plus the `tcw work init` repair instruction.
- `docs/changelogs/upcoming.md`: `Fixed` / `Changed` / `Internal` entries.
- `skills/tcw-work/SKILL.md`, `references/transitions.md`,
  `references/commands.md`, `skills/tcw-capabilities/SKILL.md` — see the
  correction below.
- The five capability descriptions named by `capabilities.yaml`. IDs, statuses,
  subjects, features, and planning pointers untouched.

## What the plan and spec got wrong

1. **The `tcw-work` router has a hard line budget the plan did not account for.**
   Plan Task 10 says "add the always-relevant configured-store rule tersely to
   `tcw-work/SKILL.md`". `tests/test_skill_lifecycle_parity.py::test_the_router_stays_within_its_line_budget`
   caps the body at 60 lines and the router was already at 59 — one line of
   headroom, and the test's own message is "extract, don't grow". The rule was
   therefore folded into the existing opening sentence (one line: never compose
   store paths, see `commands.md`) and the substance moved to
   `skills/tcw-work/references/commands.md`, which already owned the
   "external work stores" section. `references/commands.md` is an addition to the
   plan's file list.

2. **`docs/capabilities/capabilities/detect-capability-drift/description.md` was
   empty (0 bytes).** Plan Task 11 says "update all five descriptions"; this one
   had to be written from scratch rather than amended. Written to cover both drift
   kinds, the configured-store resolution, the graceful degradation, and the
   `completed`-only rule.

3. **Two plan snippets were pseudocode, not literal.** `_inbox_write`'s error
   message and the `_start` block both needed adjusting to the real surrounding
   code (`_start` keeps the existing `err`/`store_err` variable name and the
   existing `ensure_worktree_ignored` import). Behavior matches the plan.

4. **The plan's reconcile test asserted `porcelain(parent) == ""`.** Not
   achievable: in the fixture the parent repository legitimately holds an
   uncommitted nested child repo and its own config, and `git add -A` on a parent
   containing a commit-less nested repo aborts (the existing
   `test_child_nodes_finds_children_excludes_own_worktree_keeps_nested_repo`
   documents this). Replaced with the assertion that actually carries the
   criterion: no `<parent>/docs/work` phantom, and the rollup commit landed in the
   store repository scoped to the store.

Nothing in `spec.md` was contradicted. Its one open question (the strictness of
`_has_work_store`) was settled and recorded in `spec.md` itself.

## Verification

Run with cwd = the worktree, so `import tcw` resolves to worktree source rather
than the editable install pinned at the primary checkout (confirmed:
`tcw.store.fs.__file__` printed from the worktree).

| Check | Result |
| --- | --- |
| `python -m pytest -q` | **1247 passed** in 216s |
| `pnpm exec tsc --noEmit` | clean |
| `pnpm run lint` | clean (`eslint web --max-warnings 0`) |
| `pnpm run test` | 50 passed, 11 files |
| `pnpm run build` / `pnpm run check:build` | both built; no diff to committed assets |
| `tcw taxonomy check` | `taxonomy OK` |
| `tcw capabilities check` | `capabilities OK` |
| `tcw capabilities drift` | `no capability drift` |
| `tcw validate --no-recurse` | `validate OK` |
| `git diff --check` / `git status --short` | clean at every commit |

`pnpm install --frozen-lockfile` was needed once — a fresh linked worktree has no
`node_modules`.

### Two-repository smoke fixture

A code repo + a separate store repo (`work.path` absolute into the store repo),
one committed backlog item, then `tcw work start <slug> --worktree`:

```
CODE   status: ''   HEAD: tcw work: start … (worktree ignore)   .gitignore | 1 +
STORE  status: ''   HEAD: tcw work: start … (worktree metadata) work/active/<slug>/state.yaml | 2 ++
phantom code/docs/work exists: False
worktree dir: True
```

Both repositories clean, `.gitignore` only in the code repository, work state only
in the store repository, neither commit carrying an unrelated file.

## Notes

- The item was started before the worktree existed, so `git worktree add` created
  the branch and the `worktree`/`branch` fields were set through
  `FsWorkStore.set_field` afterwards and committed on `main` as
  `48bc9f3` — not through `start --worktree`. Closeout should merge
  `work/<slug>` back into `main` normally; `tcw work complete` will find the
  fields and do the merge-back itself.
- The editable install still points at the primary checkout
  (`/Users/brian/Projects/TCW`), so nothing needs restoring before `complete`.
