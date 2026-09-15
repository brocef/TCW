# Outcome — Report a refused reconcile commit as a CLI error, not a traceback

## What shipped

### Task 1: the reproduction (`5ba1a0a`, committed red)

`_refuse_commits` writes a rejecting `pre-commit` hook into the repository's own
`.git/hooks/`, so it does not depend on `core.hooksPath` or on what `git init`
templated in. The plan called the fixture the sharp edge, so it has its own test:
`test_refusing_hook_fixture_actually_blocks_a_commit` fails first if hook
execution ever goes inert, rather than letting the reconcile tests pass because
the commit failed for an unrelated reason.

The reproduction was confirmed to fail for the right cause before any fix —
`subprocess.CalledProcessError` escaping `main`, not an assertion about wording.

### Task 2: route through the non-raising helper (`b740e83`)

`reconcile` commits through `git_commit_result` and raises `ValueError` carrying
git's output. `ValueError` is already in `_ERRORS`, so `_reconcile` reports it
with the `tcw work reconcile:` prefix and returns 1 — no CLI change at all.

Invariants the spec fixed on, both verified:

- `tcw/work/cli.py` is **absent from the diff**; `_ERRORS` is byte-identical.
- `rg -n 'git_commit\(' tcw --glob '*.py'` shows the definition only — no
  production caller remains.

### Task 3: documentation (`ac81c22`)

Changelog and release notes. `README.md` and the skills did not fire: no CLI
surface, model, lifecycle, or guardrail change — the command's contract is
unchanged, only its manners. Recorded here so the skips read as decisions.

## What the spec got wrong

**The spec told me to keep a guard that breaks the recovery the spec itself
prescribes.**

Its Design said the `changed or auto_completed` guard "becomes belt-and-braces
rather than the only thing standing between a no-op and a traceback. Keep it — it
still prevents pointless work."

Keeping it violates this spec's own first constraint — *never report a successful
reconcile when the rollup was not committed*. After a refused commit the rollup is
already correct on disk, so the retry computes `changed=False`, the guard skips
the commit, and the command exits **0** with the change still staged. The user
follows the documented recovery, is told it worked, and nothing was committed.

Caught by `test_reconcile_commit_recovers_once_the_hook_is_removed`, which I wrote
for acceptance criterion 6 (the no-op) and which failed on the *recovery* half
instead. Without that test the item would have shipped a fix whose own retry path
lied.

Removed the guard. With `git_commit_result` it has no remaining job — "nothing to
commit" is answered benignly rather than by raising — so `if commit:` is both
simpler and correct. The correction is recorded in `spec.md` in its own commit
(`edb020d`) ahead of the fix.

**Idempotence is preserved as tested:** an unchanged rollup with nothing else
staged still produces no commit, because there is nothing committable
(`test_reconcile_commits_external_rollup_in_store_repository` and the new retry
test both assert the commit count does not move). One nuance now documented in the
changelog: an unchanged reconcile *does* commit unrelated work-store changes that
were already staged — the same whole-store pathspec behavior a changed reconcile
has always had, now reachable in one more case.

## Verification

| Check | Result |
| --- | --- |
| `python -m pytest -q` | **1281 passed** (was 1277; +4) |
| `pnpm` tsc / lint / test / build / check:build | all clean; 50 frontend tests |
| `tcw taxonomy check` / `capabilities check` / `validate` | all OK |
| `git diff --stat -- tcw/work/cli.py` | empty — `_ERRORS` untouched |
| `rg 'git_commit\(' tcw` | definition only |
| `git diff --check` / `git status --short` | clean |

### Verification beyond the suite

The plan asks to read the rendered stderr as a user would, because criteria 2 and
3 can be satisfied by a string that technically contains "staged" while still
reading as though nothing happened. Actual output:

```
tcw work reconcile: reconciled 2026-01-01-redesign and staged the rollup, but
committing it failed:
policy: no
```

It names what succeeded, what failed, git's own reason, and implies the retry.
Accepted.

Also confirmed by inspection that `tests/test_work_autocommit.py:311` — the
`git_mv` raise-through guard that a widened `_ERRORS` would have swallowed — is
untouched and passing.

## Notes

- No `capabilities.yaml`: the spec established there is no capability covering
  `reconcile`. That gap is now filled by
  `2026-08-13-declare-the-cross-node-recursion-capabilities` (in review), which
  created `work/reconcile-an-epic-rollup` — but this item was specced before that
  landed, and retrofitting a delta here would misattribute the capability to this
  fix. Worth linking the two at the next drift review.
- `git_commit` survives with no production caller as a test helper. The changelog
  says so explicitly, because the obvious next reading is "dead code, delete it".
