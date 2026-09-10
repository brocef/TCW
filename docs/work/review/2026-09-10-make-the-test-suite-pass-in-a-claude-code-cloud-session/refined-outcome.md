# Refined outcome — Make the test suite pass in a Claude Code cloud session

## Decision

**Accepted**, by the requester, on the assessment below. Closed
`--resolution done`.

## Evidence

Every criterion was checked against a command run at verification time, not
recalled from implementation.

| # | Criterion | Evidence |
| - | --------- | -------- |
| 1 | Suite green in a cloud session | `2528 passed, 1 skipped in 393.24s`, as root |
| 2 | Promote test passes either user, no `chmod` | root: `122 passed`; non-root: in the `190 passed` run |
| 3 | Cleanup test passes either user, no `chmod` | same two runs |
| 4 | Old cleanup test survives the mutation, rewrite does not | old + mutation: `1 passed`; rewrite + mutation: `FAILED` |
| 5 | Promote test fails a direct-write implementation | `FAILED tests/test_store_editor.py::test_atomic_write_preserves_prior_on_failure` |
| 6 | Scaffold test skips as root, runs otherwise | `SKIPPED [1] tests/test_scaffold.py:320`; non-root run reported **zero** skips |
| 7 | No `chmod` in either rewritten test | both now patch a seam; the file's remaining `chmod` is the mode-preservation test at 1597 |
| 8 | Script parses, stays executable | `bash -n` clean; `test_script_parses_and_is_executable` passes |
| 9 | No pip call at the floor, one below it | `test_a_current_setuptools_is_not_upgraded`, `test_an_old_setuptools_is_raised_to_the_floor` |
| 10 | Existing pip count unchanged | `test_failing_pip_retries_once_then_reports` still sees exactly two `pip install -e` |
| 11 | Failed upgrade prints once, exits 0 | `test_a_failing_setuptools_upgrade_reports_once_and_exits_zero` |
| 12 | `tcw validate`, `tcw capabilities check` | `validate OK`, `capabilities OK` |

Beyond the criteria, the provisioner was run against the real container: it
printed nothing, setuptools moved 68.1.2 → 84.0.0, `tcw --version` still answers
`tcw 2.0.2`, and `tests/test_shipped_prompts.py` went from failing to
`32 passed`.

## Definition of Done

- **tests pass** — `2528 passed, 1 skipped`, plus the non-root run.
- **docs synced** — one entry of four fired; `docs/changelogs/upcoming.md`
  gained an `## Internal` section in `4e11925`. The three that did not fire are
  named in `outcome.md` with the reason.
- **capabilities reconciled** — no ledger delta. The spec declared none and none
  appeared: everything touched is contributor tooling, and the published install
  path `scripts/session_bootstrap.sh` is untouched, so
  `cli/install-from-pypi` and `plugin/bootstrap-the-cli` still describe what
  ships. No `capabilities.yaml` was written, and `tcw capabilities check` exits
  0.
- **reviewed** — accepted by the requester at this stage.
- **version offered** — offered and declined; see below.
- **originating GitHub issue** — none. This item came from a suite run in this
  session, not from a report.

## Closeout choices

- **Merge route: a pull request**, opened from
  `claude/upbeat-hypatia-rx9898`. That branch also carries the planning
  artifacts for the two branch-recording items, which are unrelated to this fix
  and ride along in the same PR by the requester's choice.
- **Version: unchanged at 2.0.2.** The changelog entries stay in
  `docs/changelogs/upcoming.md`. Nothing here is user-facing, and this
  repository's guide asks for a version cut batched across a run of items rather
  than one per item.

## Deferred follow-ups

One, and it is a known gap rather than a loose end:

- **The scaffold write-failure path has no coverage under root.** The test is
  skipped there, so a regression in it would be caught only by CI. Restoring
  coverage means inducing the failure some other way — the target as a directory
  is the obvious candidate — which is a different claim than the one the test's
  name makes, so it is a new item and not a repair to this one. Not opened here;
  it needs a decision about which failure the scaffold path should be pinned
  against, and that is the requester's call.

Nothing else was deferred. The three plan defects found during implementation
were fixed in the same pass and recorded in `outcome.md` rather than carried
forward.

## Notes

- The non-root evidence depends on an account added to this container at
  verification time, which disappears with the container. CI is the durable
  version of that check: `.github/workflows/test.yml` runs `ubuntu-latest` as a
  non-root user, so the PR re-establishes it on every push.
- No post-mortem was offered. Verification surfaced nothing unforeseen — the
  three plan defects were found and fixed during `implement`, and each is
  written up there.
