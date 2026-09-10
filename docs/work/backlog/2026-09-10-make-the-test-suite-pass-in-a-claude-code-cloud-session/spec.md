# Spec — Make the test suite pass in a Claude Code cloud session

## Capability changes

None. Every surface this touches is contributor tooling: three tests, and
`scripts/remote_session_setup.sh`, which the repository's own guide calls "not
the published install path" (`scripts/remote_session_setup.sh:13-18`). The
published one, `scripts/session_bootstrap.sh`, is what
`cli/install-from-pypi` and `plugin/bootstrap-the-cli` describe, and it is not
touched. No ledger entry changes and no `capabilities.yaml` is written.

## Reproduction

`python -m pytest -q` in a Claude Code cloud session, on a clean working tree:

```
FAILED tests/test_scaffold.py::test_an_unwritable_target_reports_and_prints_no_path
FAILED tests/test_shipped_prompts.py::test_the_prompts_are_in_the_built_wheel
FAILED tests/test_store_editor.py::test_atomic_write_preserves_prior_on_failure
FAILED tests/test_store_editor.py::test_atomic_write_temp_cleanup_on_failure
4 failed, 2522 passed in 387.98s
```

The container reports `id -u` as `0` and ships setuptools 68.1.2 on Python
3.11.15. `.github/workflows/test.yml:14` runs `ubuntu-latest`, whose runner is
not root and whose setuptools is current, which is why none of this is visible
in CI.

## Problem

### Three tests induce failure with `chmod`, which root ignores

Each removes write permission from a directory and asserts the write is
refused. Root holds `CAP_DAC_OVERRIDE`, so the write succeeds:

- `tests/test_scaffold.py:319` — `folder.chmod(0o500)`, then asserts the command
  exits 1. It exits 0.
- `tests/test_store_editor.py:946` — `os.chmod(d, S_IRUSR | S_IXUSR)`, then
  `pytest.raises(PermissionError)`. Nothing raises.
- `tests/test_store_editor.py:967` — same, same.

### One of them proves nothing on any machine

`test_atomic_write_temp_cleanup_on_failure` (`tests/test_store_editor.py:967`)
says *"If the write step fails, no temp file is left behind."* Its `chmod` makes
`tempfile.mkstemp` itself fail (`tcw/store/fs.py:1317`), which is the first
statement of the staging loop — before `staged.append` and before
`tmp.write_text`. No temporary file is ever created, so the closing
`assert tmp_files == []` holds whether or not the `BaseException` handler at
`tcw/store/fs.py:1332-1335` unlinks anything. It is green on the CI runners for
the wrong reason.

Verified by inducing the failure one statement later, at `Path.write_text`, and
disabling the handler's unlink: a temp is then left behind, which the current
test would not have seen.

```
LEFTOVER: [PosixPath('.../subdir/data.yaml.2xfb08zo.tmp')]
```

### The same file already contains the right way to do this

`_fail_writing` (`tests/test_store_editor.py:994-1008`) patches `Path.write_text`
to raise for one named target, and three tests below it already induce staging
and promote failures without touching permissions:
`test_atomic_write_all_cleans_up_on_base_exception` (1026),
`test_atomic_write_all_staging_failure_promotes_nothing` (1037), and
`test_atomic_write_all_promote_failure_is_the_recorded_ceiling` (1050), which
patches `Path.replace` inline. The two broken tests are the only ones in the
file still reaching for `chmod`.

### The wheel test cannot build under the image's setuptools

`tests/test_shipped_prompts.py:143-146` runs
`pip wheel --no-deps --no-build-isolation`. The flag is deliberate — it keeps
the build offline and fast — and it means the ambient setuptools is what builds.
Two separate things go wrong below the current floor, and one upgrade fixes
both:

| setuptools | Result of the isolation-free build |
| ---------- | ---------------------------------- |
| 68.1.2 (this image, Debian-patched) | `AttributeError: install_layout` |
| 69.5.1, 70.0.0 | `error: invalid command 'bdist_wheel'` |
| 70.1.0, 84.0.0 | `Successfully built tcw-cli` |

70.1 is where `bdist_wheel` moved into setuptools itself, so it is the real
floor for a build that installs nothing. `pyproject.toml:2` declares
`requires = ["setuptools>=61"]`, which is correct for an isolated build and is
never consulted when isolation is off.

## Goals

- `python -m pytest` reports no failures in a Claude Code cloud session.
- The two atomic-write tests stop depending on the user id, using the induction
  seam their own file already established.
- `test_atomic_write_temp_cleanup_on_failure` proves what its docstring claims:
  a temporary file exists when the failure lands, and the handler removes it.
- A cloud session provisions a build toolchain the suite can actually use.

## Non-goals

- **No change to `_atomic_write_all`.** Its behaviour is correct; only the tests
  aiming at it are wrong. The `# ponytail` note at `tcw/store/fs.py:1304-1307`
  stays as it is.
- **No replacement induction for the scaffold test.** It drives the CLI in a
  subprocess (`tests/test_scaffold.py:324`), so nothing can be patched into it
  from the test process, and the alternatives — `chattr +i`, a read-only bind
  mount — need capabilities and filesystem support a container may not have.
  Substituting a different error class (making the target a directory) would
  change the claim the test's name makes. It is skipped under root instead, and
  the CI runners keep covering it.
- **No new test for the scaffold path under root.** Restoring that coverage
  means a differently-induced failure and a new claim, which is its own item,
  not a side effect of getting the suite green.
- **`pyproject.toml`'s declared `setuptools>=61` is left alone.** Raising it
  would describe the isolation-free floor honestly but change nothing: pip does
  not read `requires` when `--no-build-isolation` is passed, so it would not fix
  the failure and would tighten a constraint isolated builds do not have.
- **Nothing changes about how the container starts.** Running the suite as a
  non-root user is not reachable from this repository.

## Design

**D1 — the promote-failure test moves to the `Path.replace` seam.**
`test_atomic_write_preserves_prior_on_failure`
(`tests/test_store_editor.py:946`) drops its `chmod` and patches `Path.replace`
to raise `PermissionError`, the seam
`test_atomic_write_all_promote_failure_is_the_recorded_ceiling` already uses at
line 1050. Its distinct contribution over that test is the **single-pair**
shape — 1050 fails on the *second* of two promotes, so a first-promote failure
is otherwise uncovered — and that shape is kept. The assertions stand: the
exception propagates, and the target still reads its prior bytes.

**D2 — the cleanup test moves to the `Path.write_text` seam, one statement
later than `chmod` reached.** `test_atomic_write_temp_cleanup_on_failure`
(`tests/test_store_editor.py:967`) uses `_fail_writing`, so `mkstemp` succeeds,
`staged` holds the entry, and a real temporary file exists when the handler
runs. This is the correction that makes the test non-vacuous; being
user-independent is the same change. The `*.tmp` glob assertion is kept as the
file's other cleanup tests write it.

Neither test moves in the file. `_fail_writing` is defined below them, which
Python resolves at call time and pytest never notices.

**D3 — the scaffold test is skipped when the effective user id is zero.**
`@pytest.mark.skipif(os.geteuid() == 0, reason=...)` on
`tests/test_scaffold.py:319`, with a reason naming root's `CAP_DAC_OVERRIDE` as
the cause rather than saying the test is flaky. `tests/test_session_bootstrap.py:353`
is the precedent for a skip whose reason states what the environment cannot
host. The module gains an `import os`; it has none today.

**D4 — the cloud provisioner raises setuptools to the isolation-free floor.**
A new numbered step in `scripts/remote_session_setup.sh`, placed **after** the
editable install so a failed upgrade cannot cost the session its `tcw` and
`pytest`, and renumbering the two steps below it. It checks before it upgrades,
so an image already at or above the floor makes no network call and no pip
invocation:

```sh
if ! python3 -c '<version check>' >/dev/null 2>&1; then
    python3 -m pip install --upgrade "setuptools>=70.1"   # with the
    #   --break-system-packages retry the install step already uses
fi
```

A version string the check cannot parse exits non-zero and is treated as "below
the floor", so the failure mode is an unnecessary upgrade rather than a skipped
one. Failure prints one line and exits 0, as every other path in that script
does (`scripts/remote_session_setup.sh:20-22`).

The floor belongs here rather than in the test because the test's
`--no-build-isolation` is a property it wants, and because this script already
exists to make exactly this environment usable without a manual step.

## Abstraction litmus test

**No new operation.** Nothing here touches the store interface, the work model,
or any adapter. Three changes are to test files; one is to a provisioning shell
script that is not part of the CLI and never runs against a store. The prime
directive has nothing to rule on.

## Acceptance criteria

1. `python -m pytest -q` reports zero failures in a Claude Code cloud session
   (running as uid 0, after the provisioner has run).
2. `tests/test_store_editor.py::test_atomic_write_preserves_prior_on_failure`
   passes as root and as a non-root user, and calls no `chmod`.
3. `tests/test_store_editor.py::test_atomic_write_temp_cleanup_on_failure`
   passes as root and as a non-root user, and calls no `chmod`.
4. With `_atomic_write_all`'s `tmp.unlink(missing_ok=True)` removed,
   `test_atomic_write_temp_cleanup_on_failure` **fails**. Against the same
   mutation, the test as it stands today passes — that contrast is the evidence
   the rewrite was needed, and it is recorded in the outcome.
5. With `_atomic_write_all` changed to write each target directly instead of
   staging and promoting, `test_atomic_write_preserves_prior_on_failure` fails.
6. `tests/test_scaffold.py::test_an_unwritable_target_reports_and_prints_no_path`
   reports as skipped under uid 0, with a reason naming root's permission
   override, and still runs and passes under a non-root user.
7. `grep -n chmod tests/test_store_editor.py` returns nothing for the two
   rewritten tests; any other `chmod` in the file is left alone.
8. `bash -n scripts/remote_session_setup.sh` succeeds and the script stays
   executable, i.e. `tests/test_remote_session_setup.py::test_script_parses_and_is_executable`
   still passes.
9. The provisioner makes **no** pip call for setuptools when the ambient
   version already meets the floor, and makes one when it does not — both pinned
   by a test driving the existing stubbed `python3`
   (`tests/test_remote_session_setup.py:37-58`).
10. `tests/test_remote_session_setup.py::test_failing_pip_retries_once_then_reports`
    still passes: the setuptools step must not change the number of
    `pip install -e` invocations that test counts.
11. A failure of the setuptools upgrade prints one line and leaves the script's
    exit status at 0.
12. `tcw validate` and `tcw capabilities check` both exit 0.

## Risks

- **The upgrade mutates the container's interpreter.** `pip install --upgrade
  setuptools` changes a package the editable `tcw` install shares. It is run
  after that install for exactly this reason, and the container is disposable —
  the same argument `scripts/remote_session_setup.sh:72-76` already makes for
  `--break-system-packages`. On a `--force` run on a developer's machine it
  would touch their environment, which is a real cost and the reason the check
  runs first: an up-to-date machine is never written to.
- **An offline container cannot upgrade.** The wheel test then still fails, with
  one printed line saying why. Judged better than a test-side fallback that
  would quietly build differently depending on the machine.
- **Skipping hides a regression under root.** A change that broke the scaffold
  write-failure path would go unnoticed in every cloud session and be caught
  only in CI. Accepted, because the alternative is a test that reports a pass it
  did not earn, which is what the suite has now.
- **`70.1` is a floor found empirically, not from a changelog.** It is where the
  table above flips, on this Python. A different interpreter could move it.
  Named in the script's comment as the `bdist_wheel` boundary so the next reader
  can check the reasoning rather than the number alone.

## Notes

- The four failures were confirmed to be environment-caused before any of this
  was designed, by running the same four tests against a detached checkout of
  `origin/main` in this container rather than by reasoning from the branch's
  diff. All four fail there too:

  ```
  FAILED tests/test_scaffold.py::test_an_unwritable_target_reports_and_prints_no_path
  FAILED tests/test_shipped_prompts.py::test_the_prompts_are_in_the_built_wheel
  FAILED tests/test_store_editor.py::test_atomic_write_preserves_prior_on_failure
  FAILED tests/test_store_editor.py::test_atomic_write_temp_cleanup_on_failure
  4 failed in 2.01s
  ```
- Criteria 4 and 5 are mutation checks, not ordinary assertions. They exist
  because this item's central finding is a test that passed without measuring
  anything, and asserting the rewrite is better without falsifying it would
  repeat the mistake in the fix.
