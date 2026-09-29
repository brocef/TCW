# Outcome — Warn when a project override names the primary checkout's copy from a linked worktree

The user asked for this item on 2026-09-29, to go into the same patch release,
because they use both `TCW_PROJECT_*` overrides and linked worktrees.

## What shipped

| Commit | What |
| ------ | ---- |
| `f2200c07` | `ProjectOverride.warning`, filled in by `_reconcile_overrides` through `_other_branch_warning` and printed by `tcw validate` beneath the override line; tests; the guide sentence in `multi-repo.md`; changelog and release note. |
| `99d7c4e2` | Review notes: the worktree copy's id is read with `validate_project_id`, as `_read_config` reads it; the different-project test asserts the exit code. |

## Tests

`tests/test_override_in_linked_worktree.py` has 4 tests:

- the reproduction, which warns;
- the same override run from the primary checkout, which does not;
- an override naming the worktree's own copy, which does not;
- a worktree copy holding a different project id, which does not.

Only the reproduction test fails on the code before the fix; the other three
pass before and after, as the plan intended.

Mutation checks:

- Removing the warning turns the reproduction test red.
- Removing the id comparison turns the different-project test red.

Full suite at `99d7c4e2`: 4887 passed, 3 skipped.

Checked by hand with the real CLI, with the worktree beside the repository
rather than under `.worktrees/`:

- From the worktree, the warning names both paths and `validate` still exits 0.
- From the primary checkout, there is no warning.

## Decisions

- **Warn, but still follow the override.** This keeps what the earlier item
  settled: the override says exactly where the project is.
- **Only `tcw validate` prints the warning.** That is the command that reports
  overrides; `tcw provision` prints only overrides that failed.
- **Review** (adversarial-code-reviewer, DONE, nothing blocking): both notes
  were folded in.
- **Filed** as `2026-09-29-accept-a-project-override-spelled-in-other-letter-case-from-a-linked-worktree`:
  an override spelled in different letter case, used from a linked worktree,
  breaks the graph. The reviewer found this; it predates this change.
