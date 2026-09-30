# Outcome

A write through an item's old path no longer fails quietly.

- **`complete --resolution done` from review needs `refined-outcome.md`.**
  - Both the store and the CLI check it. The CLI checks before the checklist
    and before a worktree item's merge-back, reading both copies of the item.
  - `--force` overrides it, and epics are exempt.
  - The refusal names `tcw work path <slug>` and any stray folder.
- **`tcw validate` reports stray folders and slugs held by two folders,**
  instead of crashing on the latter.
- **The implement and verify prompts say where to write.**
- **Folders printed by `new`, `start`, `submit`, `rework` and `complete`** are
  reachable from the current directory.

## What shipped

| Task | Commit |
| --- | --- |
| Store and CLI check; `stray_folders`, `duplicate_slugs`; `check` restructure; prompts; `_shown`; tests | `eddfa41e` |
| Documentation | `f6f09cb0` |
| Existing tests that completed from review without the file; the prompt-fallback re-baseline | `8bfeeae5` |
| Review fixes and their tests; docs | `91846fcc` |

## Tests

- **`tests/test_stale_item_path.py`: 22 tests, each mutation-checked.**
- **42 existing tests completed an item from review without
  `refined-outcome.md`.** Each now writes it first; none uses `--force`.
- **The prompt-fallback fixture** changed by exactly the new sentence in the
  `implement` and `verify` stages.
- **Full suite:** see `refined-outcome.md`.

## What the plan or spec got wrong

- **The CLI check read one copy of a worktree item.** `submit` may run in the
  worktree, and verify may write in either copy. Now the item counts as in
  review, and as accepted, if either copy says so.
- **The spec did not consider an epic in review.** `reconcile
  --complete-when-ready` has no `--force`, so the check would strand it. Epics
  are exempt, like an epic closed from backlog.
- **Criterion 6's premise was wrong.** The web app has no whole-store
  validate endpoint and never returned a 500: it validates the one item it
  just wrote, and already turned an exception into the warning "validation
  could not complete". That per-item validation now returns the duplicate as a
  problem, which is the useful half of the goal.
- **The spec named a capability `work/validate-the-work-store`,** which does
  not exist. `cli/validate-a-node` owns validation and is the one updated.
- **Outside a git repository**, the missing-file refusal now comes before "not
  a repository". That matches how `rework` already behaves.

## Autonomous decisions

- **Review verdict "NOT DONE"** (`adversarial-code-reviewer`). Accepted and
  fixed:
  1. the check must use either copy's status;
  2. `@abstractmethod` had moved from `artifacts` to `stray_folders`;
  3. either copy may hold the artifact;
  4. exempt epics — the reviewer offered this or changing `epic_completable`,
     and I chose the exemption because the spec already exempts epics closed
     from backlog;
  5. the nested child's old spot;
  7. refuse before the checklist.

  Also accepted: the missing documentation (`commands.md`, the guide's
  "Where an item's files go") and the promised inbox entry (a folder that
  never moves).
- **Moved to a separate change, agreed with the reviewer:**
  - the stray scan's resistance to a concurrent move;
  - `_item_problems` dropping partial problems in a duplicate-parent edge
    case;
  - `_shown` using the filesystem-only `path`.
- **The 42 test updates were delegated** to a helper agent, told to write the
  file rather than use `--force`, and to report anything that looked like a
  real bug. It reported the not-a-repository ordering above; I accepted it.
- **No advisors were consulted at implementation.** The design (a store-level
  check, `--force`, strays found by name, duplicates reported by `validate`)
  was settled with advisors at the spec stage.
