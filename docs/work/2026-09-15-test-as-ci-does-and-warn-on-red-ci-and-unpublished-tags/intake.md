## Inbox manifest

- `ci-ran-bare-pytest-and-could-not-import-the-eval-harness.md`

## Inbox body

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

## Triage (2026-09-15)

Merged at triage because both entries are about the gap between the code a test run
exercises and the code that ships or runs elsewhere: how CI invokes the suite, what
tells anyone CI or publishing failed, and tests that start the installed `tcw`
rather than this checkout's. The maintainer asked for items touching the same feature
to be combined.

Checked at triage:

- The fix the entry above describes (`pythonpath = ["."]`) is in `pyproject.toml`;
  its three follow-ups are not done. No test or CI step runs `pytest --collect-only`.
  The script the entry names is `skills/documentation-sync/scripts/unpushed-version.sh`,
  and it asks git remotes whether a tag was pushed, never PyPI whether it published.
- The editable install is now `tcw-cli` 2.2.0, matching the project, so the stale
  *version* the entry below reports no longer holds; the shadowing does. Thirteen files
  start `tcw` as a subprocess: ten test modules, two fixture capture scripts, and
  `scripts/require_artifact.py`.

## Folded in: inbox entry `the-editable-install-is-a-stale-version-pinned-to-the-primary-checkout.md`

## The editable install is stale, and silently shadows every worktree

`pip list` reports `tcw 0.10.3` installed from `/Users/brian/Projects/TCW`, while
the project is at `2.0.3` (`pyproject.toml`, `tcw/__init__.py`). Two consequences,
and the second one cost real time.

**The `tcw` on PATH is not the tree you are working in.** The editable install
registers an import hook pinned to the primary checkout, so inside a git worktree
the console script runs the *other* checkout's source. The agent guide documents
this for running the CLI by hand. What it does not say is that it reaches tests:
`tests/test_documented_cli_surface.py` shelled out to `tcw` to discover the command
surface, so in a worktree it measured whether the **installed** CLI matched **these**
docs. Any command added in a worktree read as "no such verb" however correct it was.

Fixed in passing on 2026-09-13 by having that test invoke its own repository via
`sys.path.insert(0, REPO)` in a subprocess, which does win over the install's
finder. Filed because the same trap applies to anything else that shells out to
`tcw`, and because a stale *version* in the hook is the condition the guide warns
"shadows the right one".

**Suggested actions**, none of which this note takes:

1. Decide whether the machine's install should be re-pointed and refreshed. Doing so
   affects every session sharing it, which is why this session did not.
2. Grep for other places tests or scripts invoke `tcw` as a subprocess rather than
   importing it, and give them the same treatment.
3. Consider whether the guide's "Working in a `--worktree` branch" section should say
   that tests are affected too, not only manual CLI runs.

Storage-abstracted: nothing here touches the model. It is packaging and test
plumbing.
