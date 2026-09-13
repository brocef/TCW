# CI ran bare `pytest` and could not import the eval harness

Filed 2026-09-13. Recorded here rather than through `tcw work` because this
session has edited `tcw/`, which the project guide says makes the CLI unreliable
to drive.

## What happened

From 2026-09-11 to 2026-09-13 every CI run on `main` failed at collection with
three errors:

```
tests/test_eval_fixture.py:20: in <module>
    from evals.seed_fixture import seed
E   ModuleNotFoundError: No module named 'evals'
```

No test ran on either interpreter leg. Because `release.yml` makes its `publish`
job depend on the `test` job, **v2.0.3 and v2.1.0 were tagged and pushed but
never published**; PyPI stayed at 2.0.2. The gate worked correctly — what it
caught was a defect in the test setup rather than in the code.

## Why it was invisible locally

`evals` is deliberately excluded from the distribution: `packages.find` includes
only `tcw*`, because the eval harness is a measuring instrument and not part of
what users install. So the editable install never puts the repository root on the
module search path.

`python -m pytest` puts the current directory on the search path. Bare `pytest`
does not. Local runs used the first form and CI uses the second, so the same
commit passed on a laptop and failed on a runner. Every local full-suite run
during the tracker work reported 2811 passing and was telling the truth about the
invocation it was given.

## Fix

`pythonpath = ["."]` under `[tool.pytest.ini_options]`, which repairs both
invocations. Changing the workflow to `python -m pytest` would have fixed CI
alone and left the trap for the next contributor, since `CLAUDE.md` and the
evals documentation both say to run `pytest`.

## Worth following up separately

1. **Nothing tests the way CI invokes the suite.** A test that runs
   `pytest --collect-only` in a subprocess, without `-m`, would have caught this
   on the commit that introduced it. Consider whether that belongs in the suite
   or as a second CI step.
2. **Nobody was told CI was red for two days.** Two releases were tagged into a
   broken gate. There is no notification on a failed run, and the failure was
   only found because it was asked about directly.
3. **A tagged-but-unpublished release leaves no trace in the repository.** The
   tag exists, the changelog says the version shipped, and PyPI disagrees.
   `scripts/unpushed-version.sh` answers a related question and could perhaps
   answer this one.
