# Refined outcome: Restore the CI test suite to green

**Accepted.** The user verified and approved closeout after being shown the
green run and the three open questions the work raised (the guard-ordering
finding, the container-local flake, and the unpublished tags).

## Evidence

The claim this item exists to make is "CI is green", and the only thing that can
settle it is the runner. Local reproduction guided the fixes but proves nothing
on its own, because every failure here was a *difference* between a workstation
and a bare runner.

- [Run #46](https://github.com/brocef/TCW/actions/runs/33585626173) on `0cf755e`
  — `pytest (3.11)` **success**, `pytest (3.14)` **success**. The first green
  `test` run since v1.1.0.
- Each cause was reproduced before it was fixed, not inferred: the identity
  failures by stripping `HOME`/`GIT_CONFIG_GLOBAL`/`GIT_CONFIG_SYSTEM`, and the
  wheel failure in a venv with setuptools uninstalled — which reproduced CI's
  pip **exit status 2** exactly, distinguishing it from the unrelated
  Debian-setuptools `install_layout` error this container raises.
- `tcw capabilities check` — `capabilities OK`.
- `tcw capabilities drift` — `no capability drift`.
- `tcw validate` — 4 problems, byte-identical to the pre-change run; all are
  dangling `tcw://` references owned by
  `2026-09-01-make-tcw-validate-usable-as-a-gate-suppressible-references-and-graded-exit-codes`.

## Capability reconciliation

**None.** No capability entry changed, and none should: nothing TCW ships
behaves differently. All four fixes are in tests or the `dev` extra, and the
production paths under them were correct throughout — `run_generate` already
decoded with `errors="replace"`, and the store-publication code was only ever
failing because the runner had no committer.

## Corrections

One to the diagnosis, made while working and recorded here because the first
reading was wrong in a way worth remembering: the `printf` failure looked like a
decode/locale problem, since the CI assertion (`assert '�' in 'ok\\xff\\xfe'`)
reads as a replacement that did not happen. It was a **shell** problem — dash's
`printf` has no `\x` escape, so the invalid bytes were never produced and there
was nothing to replace. A fix aimed at the decoder would have been wrong and
would have passed review.

## Notes

- `test_invalid_utf8_is_replaced_rather_than_fatal` was one of the five failures
  the previous item's `refined-outcome.md` recorded as "confirmed pre-existing"
  and moved past. It was a real, fixable defect for four releases. The three
  root-only `PermissionError` tests in that same list remain genuinely
  environmental.

## Deferred follow-ups

Neither is filed as a work item; both are recorded here and were raised with the
user, who chose to leave them.

- **`tcw work start` resolves a claimant before the repository guard.** Outside
  a repository with no ambient identity it refuses with `claimant identity
  required` rather than `not inside a git repository`. Nothing is written on
  either path, so the safety contract holds and only the single-wording contract
  does not. Explicitly deferred ("leave it for now").
- **`test_a_grandchild_does_not_survive_the_timeout` is flaky under this
  container**, ~50% either side of the change (unmodified: pass/fail/pass/fail/
  pass; this branch: pass/fail/fail/fail/pass) and green on both CI legs. A
  process-group/orphan-reaping assertion meeting container PID semantics. Worth
  filing only if it ever fails on a runner.
