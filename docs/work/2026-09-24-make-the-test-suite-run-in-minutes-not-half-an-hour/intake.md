# Make the test suite run in minutes, not half an hour

The full suite takes about 26 minutes on a developer machine (4,471 passed,
3 skipped in 1585 s on 2026-09-24, run as CI runs it: bare `pytest`). That is long
enough that a change is committed on a partial run, or a run is started and
forgotten, and it slows every release.

Two causes are visible: tests run one at a time — no `pytest-xdist` is installed,
so `pytest -n auto` is rejected — and most tests build one or more real git
repositories under `tmp_path` and run the CLI in-process against them.

What is wanted: a full local run fast enough to wait for, with CI running the
same way, and nothing about what the tests check weakened.

## Origin

Raised by the user on 2026-09-24 while the suite ran for
`2026-09-24-leave-an-accepted-or-imported-ticket-in-the-backlog-status-matching-its-item`
("25 minutes is pretty long for a unit test suite"). The user said not to change
the test framework in that item.

## References

- `pyproject.toml` `[tool.pytest.ini_options]` — where parallel running or markers
  would be configured.
- `tests/test_tracker_sync.py` (`cli`, `make_node`) and
  `tests/test_tracker_import.py` (`run`) — in-process CLI runs that `os.chdir`
  into the node. Changing the process-wide working directory and environment is
  what could make parallel runs collide, so it is the first thing to check.
- `2026-09-15-test-as-ci-does-and-warn-on-red-ci-and-unpublished-tags` — related:
  running the suite as CI does. Whatever speeds up local runs must keep that
  property.

No blockers.
