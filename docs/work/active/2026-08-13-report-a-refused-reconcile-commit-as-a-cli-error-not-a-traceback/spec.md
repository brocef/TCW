# Report a refused reconcile commit as a CLI error, not a traceback

## Capability changes

**None.** Checked against the ledger rather than assumed: `tcw capabilities search
reconcile` returns only `work/complete-a-work-item` and
`work/customize-the-definition-of-done`, neither of which describes rollups, and a
full pass over the `work/` namespace found no entry for `tcw work reconcile`,
epics, or cross-node coordination. There is nothing to record a `changed:` delta
against.

That is a real gap in the standing ledger — `reconcile`, `delegate`, `escalate`
and the epic relation are all shipped, documented in `README.md`, and driven by
`skills/tcw-work`, yet unrepresented in `docs/capabilities/`. Declaring that
capability is its own piece of work, not a rider on an error-message fix, and a
`new:` declaration here would oblige this item to flip it to `Supported` at
`complete` for behavior it did not build. Left for a separate item; noted so the
absence reads as observed rather than overlooked.

No taxonomy change either. This restores an error contract the rest of the command
already honors.

## Problem

`reconcile` commits through `git_commit` (`tcw/work/recursion.py:210`), and
`git_commit` (`tcw/store/fs.py:331-337`) runs `subprocess.run(..., check=True)`,
so a refusal raises `subprocess.CalledProcessError`. `_reconcile`
(`tcw/work/cli.py:160-172`) catches `_ERRORS` — `(ValueError, IllegalTransition,
MultipleMatch, TransitionCommitError, AlreadyClaimed)` at `tcw/work/cli.py:34` —
which does not include it. The exception escapes `main`.

**Reproduced**, not inferred. With a `pre-commit` hook that exits non-zero
(the trigger the request nominated as most likely), `main(["work", "reconcile",
<epic>, "--commit"])` raises:

```
policy: no
UNCAUGHT: subprocess.CalledProcessError
```

The user sees a stack trace through TCW internals instead of a sentence.

### Sweep

Repo-wide, against the criterion "a CLI path that can reach a raising Git helper
without a handler for it":

- **`git_commit` has exactly one production caller** — `reconcile`
  (`tcw/work/recursion.py:210`). Every other commit path in the codebase already
  uses `git_commit_result` (`tcw/store/fs.py:2048`, `:2879`,
  `tcw/work/cli.py:566`, `:574`), which returns an error string instead of
  raising and distinguishes a benign non-commit from a real failure. `reconcile`
  is the outlier, not the pattern.
- **`git_stage` / `git_rm` / `git_mv` also raise** (`fs.py:287`, `:292`,
  `:322-326`) and are reachable from every transition, but that raise-through is
  a **deliberately pinned contract**:
  `tests/test_work_autocommit.py:311` exists specifically so "nobody 'fixes' it".
  Out of scope, and the fix must not disturb it.
- `subprocess.CalledProcessError` is already handled deliberately at
  `tcw/store/fs.py:82`, `tcw/store/project.py:82`, and `tcw/work/cli.py:583` — all
  narrow, per-call-site handlers. The codebase's existing opinion is to catch it
  where it is raised, not centrally.

That opinion rules out the tempting one-line fix. Adding `CalledProcessError` to
`_ERRORS` would apply it to all **16** `except _ERRORS` sites in
`tcw/work/cli.py`, silently converting the pinned `git_mv` raise-through into a
caught error at every transition — the opposite of what `:311` guards.

## Goals

- A refused reconcile commit exits non-zero with a message naming what failed and
  including Git's own output.
- Bring `reconcile` onto the same commit contract as every other commit path in
  the codebase, rather than adding a second way to fail.
- Leave the `git_stage`/`git_rm`/`git_mv` raise-through exactly as it is.
- Never report a successful reconcile when the rollup was not committed.

## Non-goals

- Widening `_ERRORS`, at all.
- Changing what `reconcile` commits or where — settled by
  `2026-08-12-honor-the-configured-work-path-at-every-work-store-call-site`.
- Changing `git_commit_result`'s contract.
- Making any transition tolerate a Git failure it currently raises on.

## Design

Switch `reconcile` from `git_commit` to `git_commit_result`, and raise `ValueError`
— already in `_ERRORS` — carrying the returned message. The abstract-store
question does not arise: this is filesystem-adapter-internal error routing, and
`reconcile` already lives above the store in the FS-flavored recursion layer.

```python
err = git_commit_result(store.store_git_root, f"tcw work: {msg}", work_pathspec)
if err:
    raise ValueError(f"reconciled {epic_slug}, but committing the rollup failed:\n{err}")
```

The wording must say the rollup **was written and staged** — because it was, at
`recursion.py:205-206`, before the commit was attempted. A message implying
nothing happened would send the user looking for a change that is sitting in
their index.

`git_commit_result` also returns `None` when there was legitimately nothing to
commit. That is strictly better than today: the current `git_commit` would
*raise* on an empty commit, so the `changed or auto_completed` guard at
`recursion.py:208` is load-bearing against a crash. After this change the guard
becomes belt-and-braces rather than the only thing standing between a no-op and a
traceback. Keep it — it still prevents pointless work — but it is no longer
carrying that weight alone.

**`git_commit` then has no production caller.** Deliberately **keep** it: it is
imported by `tests/test_recursion.py:15` as a test fixture helper, and deleting a
small, correct, documented primitive to satisfy a dead-code rule would churn the
test suite for no behavioral gain. Note the change in status in the changelog so
a future reader does not mistake it for the house pattern.

## Acceptance criteria

1. With a `pre-commit` hook that exits non-zero, `tcw work reconcile <epic>
   --commit` returns exit code 1 and raises nothing out of `main`.
2. That run's stderr begins `tcw work reconcile:` and contains Git's own refusal
   output (the hook's message).
3. That message states the rollup was written/staged, so the user knows the change
   is in their index rather than lost.
4. After that failed run, the rollup text is present in
   `<epic>/initial-request.md` and staged in the store repository.
5. `tcw work reconcile <epic>` **without** `--commit` is unaffected by a refusing
   hook and still exits 0.
6. Re-running `reconcile --commit` on an unchanged rollup after the hook is
   removed remains a no-op with no empty commit, and returns 0.
7. `_ERRORS` (`tcw/work/cli.py:34`) is byte-identical to its current value.
8. `tests/test_work_autocommit.py::test_a_transition_outside_a_repository_fails_in_git_mv_as_it_always_has`
   passes **unmodified**.
9. `rg -n 'git_commit\(' tcw --glob '*.py'` shows the definition only — no
   production caller.
10. The full Python suite passes, and `tcw taxonomy check`, `tcw capabilities
    check`, and `tcw validate` exit 0.
11. `docs/changelogs/upcoming.md` records the change, including `git_commit`'s new
    test-only status. Release notes updated only if the reader-facing behavior
    warrants it — a traceback becoming a message does warrant one line.

## Risks

- **The `pre-commit` hook fixture is the sharp edge.** Existing tests create
  repositories with `git init`, which under some configurations inherit a
  `core.hooksPath` or template hooks. The regression test must write its hook into
  the repository's own `.git/hooks/` and make it executable, and must assert the
  hook actually fired (its message in stderr) rather than assuming the non-zero
  exit came from it. A test that passes because the commit failed for an unrelated
  reason proves nothing.
- **Wording that implies nothing happened would be worse than the traceback.** The
  rollup really is staged when this fires. Criterion 3 exists for this and is the
  one most likely to be satisfied sloppily.
- Switching to `git_commit_result` changes empty-commit behavior from *raise* to
  *quiet None*. That is desirable here, but it means the `changed or
  auto_completed` guard no longer fails loudly if it is ever removed. Criterion 6
  pins the no-op.
- `git_commit` surviving with no production caller invites a later "dead code"
  deletion that would break `tests/test_recursion.py`. The changelog note is the
  mitigation.

## Notes

- An earlier draft of this spec named `work/manage-cross-node-epics` as a
  `changed:` delta. No such capability exists; checking the ledger is what turned
  that guess into the gap recorded above. The item therefore ships **no**
  `capabilities.yaml`.
- Found by inspection during another item's verification and reported on GitHub
  issue [#16](https://github.com/brocef/TCW/issues/16)'s closing comment as a known
  follow-up, so that thread already points at this work.
