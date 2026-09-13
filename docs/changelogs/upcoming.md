# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Fixed

- **CI ran bare `pytest` and could not import the eval harness.** Three test
  modules import `evals`, which is deliberately outside the distribution
  (`packages.find` includes only `tcw*`), so the editable install never puts the
  repository root on the module search path. `python -m pytest` adds the current
  directory and bare `pytest` does not, so local runs collected 2811 tests and
  the runner collected none, failing with three `ModuleNotFoundError`s before any
  test ran. `pythonpath = ["."]` under `[tool.pytest.ini_options]` repairs both
  invocations; pointing the workflow at `python -m pytest` would have fixed the
  runner alone and left the trap for a contributor following `CLAUDE.md`, which
  says to run `pytest`.

    Red since 2026-09-11. Because `release.yml` makes `publish` depend on the
  `test` job, **v2.0.3 and v2.1.0 were tagged and pushed but never published**;
  PyPI stayed on 2.0.2. The gate behaved correctly — what it caught was a defect
  in the test setup rather than in the code.

- **The committed eval example runs named the author's home directory.**
  `timing.json` records where the runner put the fixture tree and the runner
  writes that path absolutely, so the four runs under
  `tests/fixtures/eval_grading/` carried `/Users/...`. The ten tests reading them
  passed on one machine and errored with `FileNotFoundError` everywhere else —
  the second failure, uncovered once collection worked again.

    `grade_run` now resolves a relative `fixture` against the run directory,
  which is where the runner puts it, and the committed runs are relative. An
  absolute path still takes precedence, so a live run is unchanged.

- **`tests/test_committed_paths.py`** fails if any tracked JSON, YAML or TOML
  file names a home directory. Scoped to data files rather than everything
  tracked: a document naming an absolute path is illustrating a command, and
  `tests/test_eval_runner.py` uses `/Users/somebody/...` as a literal it never
  opens. A repository-wide version flagged those four and would have needed an
  exception list to stay green, which is the weaker instrument.
