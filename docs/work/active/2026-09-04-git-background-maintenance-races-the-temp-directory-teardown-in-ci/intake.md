CI is red on this branch: `pytest (3.11)` fails, `pytest (3.14)` passes, on both
runs. It is not a test failure —

```
2376 passed, 1 error in 280.35s
ERROR tests/test_non_git_writes.py::test_every_cli_write_refuses_with_one_wording_and_writes_nothing
FileNotFoundError: [Errno 2] No such file or directory: 'maintenance.lock'
```

— the error is in `tmp_path`'s teardown, inside `shutil.rmtree`, after the test
has already passed. `main` is green, so this branch is what trips it.

**Mechanism, reproduced.** `.git/maintenance.lock` is written by
`git maintenance run`, and `git fetch` starts one:

```
$ GIT_TRACE=1 git fetch
trace: run_command: git maintenance run --auto --no-quiet
```

That is a process pytest knows nothing about. It removes its lock between the
`scandir` and the `unlink` of the temp-directory walk, and `rmtree` raises.

**Why now.** The suite only began fetching when `tcw provision` gained a store to
clone — `test_store_provisioning.py` grew 469 lines on this branch and
`test_store_publication.py` 35. Nothing about `test_non_git_writes.py` changed;
it is simply whichever test held the temp directory when the race landed, which
is also why it moves between runs and Python versions.

**Fix.** Turn the second process off for the suite rather than teach the cleanup
to tolerate a missing file — a cleanup that ignores a vanished path would also
ignore a real one. `maintenance.auto=false` is the key that matters, `gc.auto=0`
covers the other background process, and both go through `GIT_CONFIG_*`
environment variables so they reach every `git` the suite runs: the ones the
fixtures invoke directly, the ones TCW invokes, and the ones inside repositories
`tcw provision` cloned, which inherit no local config from their source. That is
the same reasoning, and the same mechanism, as the `_git_identity` guard already
in `tests/conftest.py`.
