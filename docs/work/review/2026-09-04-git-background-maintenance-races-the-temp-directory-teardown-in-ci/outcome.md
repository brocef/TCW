# Outcome — Git background maintenance races the temp-directory teardown in CI

## What shipped

One autouse fixture in `tests/conftest.py`, `_no_git_background_maintenance`,
setting `gc.auto=0` and `maintenance.auto=false` through `GIT_CONFIG_COUNT` /
`GIT_CONFIG_KEY_n` / `GIT_CONFIG_VALUE_n`.

**The mechanism was reproduced before anything was changed.** `GIT_TRACE=1` on a
plain `git fetch` shows the second process:

```
trace: run_command: git maintenance run --auto --no-quiet
```

and with the override present, nothing. That process writes
`.git/maintenance.lock`; `rmtree` walking `tmp_path` sees the entry in
`scandir` and finds it gone at `unlink`. The test that carries the resulting
error has already passed and has nothing to do with it.

Three choices worth stating:

1. **The environment, not `git config --global`.** The suite runs `git` three
   ways — directly from fixtures, through TCW, and inside repositories
   `tcw provision` cloned — and a clone inherits no local config from its
   source. Only the environment reaches all three. This is the same reasoning,
   for the same reason, as the `_git_identity` guard directly above it.
2. **Remove the second process, not tolerate it.** Teaching the teardown to
   ignore a missing file would also make it ignore one that was missing for a
   real reason.
3. **Both keys.** `maintenance.auto` is the one that matters here;
   `gc.auto` covers the other background process rather than waiting for it to
   produce its own version of this.

## Tests

None added: this is a suite-wide guard, and a test for it would have to
provoke a race that is timing-dependent by definition. The evidence is the
`GIT_TRACE` comparison above, recorded in the fixture's docstring so the next
reader does not have to rediscover it.

```
$ python -m pytest -q -p no:randomly tests/
5 failed, 2372 passed in 357.03s (0:05:57)
```

The four environmental failures, plus the timing-sensitive
`test_a_grandchild_does_not_survive_the_timeout`. No new failures, and none of
these is the error CI reported — this container cannot reproduce that one, since
it runs as root and never crossed the fetch threshold. **The real verification is
CI going green**, which is checked after the push rather than claimed here.

## Autonomous decisions

Codex is not installed in this container; no advisor was consulted. The trace
settled the diagnosis, and the fix follows from it.

1. **Whether to fix it in the workflow or in `conftest.py`.** `conftest.py`. A
   workflow-level environment variable would fix CI and leave every contributor
   and every other environment exposed to the same race.
2. **Whether this is "not my defect".** It is not a defect in the changed code,
   and it is still this branch's to fix: `main` is green, this branch is red,
   and the reason is that the branch taught the suite to fetch. Filing it as
   somebody else's flake would leave the PR unmergeable on a true statement.

## Notes

The first draft of the fixture's docstring said git starts maintenance "after a
commit". That was a guess, and it was wrong — `GIT_TRACE` showed it is `fetch`.
Corrected before the commit, because a docstring that explains the wrong trigger
is exactly the class of thing three review passes on this branch have been
removing.
