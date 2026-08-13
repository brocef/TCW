# Refined outcome — Report a refused reconcile commit as a CLI error, not a traceback

**Decision: accepted.** Approved by the user on 2026-08-13, who asked for the
review-stage bug items to be checked as merged and closed.

## Evidence at acceptance

Implemented directly on `main`; `95dca46`, `b740e83`, and `74c6c09` are ancestors
of `HEAD` (`5645635`), and no branch or worktree remains.

The three criteria most able to pass falsely were re-checked mechanically on
`main`, not read off `outcome.md`:

- **Criterion 7 — `_ERRORS` byte-identical.** `git show --stat b740e83 --
  tcw/work/cli.py` returns nothing: the fix commit does not touch the file at all.
- **Criterion 9 — no production caller of `git_commit`.** `rg -n 'git_commit\('
  tcw --glob '*.py'` returns one line, `tcw/store/fs.py:340`, the definition.
- **Criteria 1-6.** `pytest tests/test_recursion.py -k reconcile` → 12 passed,
  including the refusing-hook fixture's own guard test and the recovery test.

| Check | Result |
| --- | --- |
| `python -m pytest -q` | 1294 passed |
| `tcw taxonomy check` / `capabilities check` / `drift` | all OK, no drift |
| `tcw validate` | `validate OK` |
| `git status --short` | clean |

## The removed guard is the right call

The spec instructed keeping the `changed or auto_completed` guard as
belt-and-braces; keeping it would have violated the spec's own first constraint,
because after a refused commit the retry computes `changed=False`, skips the
commit, and exits 0 with the change still staged — the documented recovery would
report success having committed nothing. Caught by
`test_reconcile_commit_recovers_once_the_hook_is_removed`, and the correction was
committed to `spec.md` (`edb020d`) ahead of the fix. Accepted.

Idempotence survives as tested: an unchanged rollup with nothing else staged still
produces no commit. The one nuance — an unchanged reconcile now also commits
unrelated already-staged work-store changes, the same whole-store pathspec
behavior a changed reconcile always had — is recorded in the changelog rather than
left to be discovered.

## Capability reconciliation

No `capabilities.yaml` delta. The spec established there was no capability
covering `reconcile` at the time; the gap has since been filled by
`2026-08-13-declare-the-cross-node-recursion-capabilities`, which created
`work/reconcile-an-epic-rollup`. Retrofitting a delta here would misattribute the
capability to this fix. `tcw capabilities drift` is clean either way.

## Closeout

- **Route: direct to `main`.** No branch to merge.
- Documentation current at acceptance: changelog and release notes. `README.md`
  and the skills did not fire — no CLI surface, model, lifecycle, or guardrail
  change; only the command's manners.
- Released in **v0.21.1**, folded in by `5645635`.

## Follow-ups

- **Worth a drift review, unfiled:** link this fix's behavior to
  `work/reconcile-an-epic-rollup` when that capability next gets touched, so the
  error-reporting contract has a capability to hang from.
- **Deliberate, documented:** `git_commit` survives with no production caller as a
  test helper. The changelog says so explicitly, because the obvious next reading
  is "dead code, delete it".
