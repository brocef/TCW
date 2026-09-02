# Outcome — Restore the CI test suite to green

Every `test` run since v1.1.0 failed (15 failures on the 3.11 leg, 16 on 3.14),
and because `release.yml` gates publication on `test`, the v1.1.0, v1.2.0 and
v1.2.1 tags never reached PyPI. This item is the diagnosis and the fix.

It had no `spec` or `plan` stage: the work was reading four CI logs, reproducing
each failure locally, and correcting the tests. Recorded as an outcome only,
rather than back-filling artifacts for a lifecycle that was not run.

## What shipped

Four causes, all of them in the tests or the dev environment. **No shipped code
changed** — the production paths these tests cover were correct throughout.

1. **`tests/conftest.py` — a suite-wide `_git_identity` autouse fixture.**
   13 `test_store_publication` failures. Fixtures `git config` an identity into
   the repositories they build, but not into the ones TCW *clones*:
   `tcw provision` checks a store out, and a clone inherits no local config.
   Those commits fell through to the developer's global identity, which a CI
   runner has none of — `fatal: empty ident name (for <runner@...>) not
   allowed`. The fixture sets `GIT_AUTHOR_*`/`GIT_COMMITTER_*` as environment
   rather than `git config --global`, deliberately: global config would also
   answer the `git config --get user.email` fallback in `tcw work start`'s
   claimant resolution, silently satisfying a precondition other tests exercise.
2. **`tests/test_non_git_writes.py` — set `TCW_WORK_OWNER` in
   `test_every_cli_write_refuses_with_one_wording_and_writes_nothing`.** Same
   missing identity, different route: `work start` resolves a claimant *before*
   the repository guard, so with no identity anywhere it refused with `claimant
   identity required` rather than the one wording the test asserts.
3. **`tests/test_generate_hook.py` — POSIX octal instead of `\xNN`.**
   `run_generate` uses `shell=True`, i.e. `/bin/sh` — dash on Debian and on the
   runner — whose `printf` has no `\x` escape and emitted `ok\xff\xfe`
   literally. The hook therefore received valid UTF-8 and the assertion had
   nothing to replace. `\377\376` means the same byte in dash and bash.
4. **`pyproject.toml` — `setuptools>=61` added to the `dev` extra.**
   `test_the_prompts_are_in_the_built_wheel` builds with
   `--no-build-isolation` to keep the suite off the network, which requires the
   backend to be installed already. setuptools has not been bundled with the
   interpreter since 3.12, which is exactly why this failed on the 3.14 leg
   alone (pip exit 2, `ModuleNotFoundError: No module named 'setuptools'`).

## Tests

Each cause was reproduced locally before being fixed — the identity failures by
stripping git config, the wheel failure in a venv with setuptools uninstalled
(which reproduced CI's pip exit status 2 exactly).

The four previously-failing files, run with no git identity and in a venv with
no pre-installed setuptools (the closest local match to the 3.14 leg):

```
$ env -u HOME GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null \
    venvtest/bin/python -m pytest tests/test_store_publication.py \
    tests/test_non_git_writes.py tests/test_generate_hook.py \
    tests/test_shipped_prompts.py -q
FAILED tests/test_generate_hook.py::test_a_grandchild_does_not_survive_the_timeout
1 failed, 129 passed in 14.50s
```

Full suite under the same conditions: `4 failed, 2176 passed in 261.64s`. All
15/16 CI failures are gone. The four that remain are pre-existing and local to
this container, not regressions — see Notes.

## Corrections

None to a spec or plan; there were none. One correction to the diagnosis made
while working: the `printf` failure was first read as an encoding/locale
problem, since the CI assertion (`assert '�' in 'ok\\xff\\xfe'`) looks like a
decode that did not happen. Comparing `dash` and `bash` showed the bytes never
existed — dash emits the escape literally. `run_generate` already decodes with
`errors="replace"` (`tcw/work/generate.py:198`) and needed no change.

## Notes

- **Four failures in this container are environmental, not regressions.** Three
  (`test_an_unwritable_target_reports_and_prints_no_path`,
  `test_atomic_write_preserves_prior_on_failure`,
  `test_atomic_write_temp_cleanup_on_failure`) assert `PermissionError` on a
  read-only directory and fail because this container runs as **root**, which
  bypasses permission bits. They fail identically on the unmodified tree and
  pass on CI, which runs as `runner`.
- **`test_a_grandchild_does_not_survive_the_timeout` is genuinely flaky here** —
  5 runs on the unmodified tree: pass/fail/pass/fail/pass; 5 on this branch:
  pass/fail/fail/fail/pass. Same rate either side of the change, and it is green
  on CI, so it is untouched by this work. It is a process-group/orphan-reaping
  assertion, and container PID semantics are the likely cause. Worth its own
  backlog item if it ever surfaces on a runner.
- **`tcw validate` still reports 4 problems**, all dangling `tcw://` references
  in backlog intake files that predate this change; they are owned by
  `2026-09-01-make-tcw-validate-usable-as-a-gate-suppressible-references-and-graded-exit-codes`.
- Deprecation warning left alone as out of scope: `actions/checkout@v4` and
  `actions/setup-python@v5` target Node 20 and are being forced onto Node 24.
