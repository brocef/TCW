# Make the test suite pass in a Claude Code cloud session

`pytest` reports **4 failed, 2522 passed** in a Claude Code cloud session. None
of the four is a defect in what they test, and none reproduces on the
GitHub-hosted runners, so the suite is green in CI and red for every agent
working the repository remotely. That gap is the problem: a suite that fails
four tests on arrival teaches whoever reads it to ignore its output.

## Why it happens

Two unrelated properties of the cloud container.

**It runs as root.** Three tests induce a write failure by `chmod`-ing a
directory read-only and asserting the write is refused. Root bypasses
directory permission bits, so the write succeeds and the expected
`PermissionError` never arrives.

- `tests/test_scaffold.py::test_an_unwritable_target_reports_and_prints_no_path`
- `tests/test_store_editor.py::test_atomic_write_preserves_prior_on_failure`
- `tests/test_store_editor.py::test_atomic_write_temp_cleanup_on_failure`

**Its setuptools is too old for an isolation-free build.**
`tests/test_shipped_prompts.py::test_the_prompts_are_in_the_built_wheel` builds
a wheel with `--no-deps --no-build-isolation`, which forces the ambient
setuptools 68.1.2 rather than fetching one. That version raises
`AttributeError: install_layout` on this Python (3.11.15), so the build fails
before the test can read the zip.

## A defect found while diagnosing this

`test_atomic_write_temp_cleanup_on_failure` does not test what its docstring
claims, on any machine. The `chmod` makes `mkstemp` itself fail, so no temporary
file is ever created — and the assertion that no temp file is left behind then
passes whether or not `_atomic_write_all`'s cleanup handler exists. It is green
on the CI runners for the wrong reason.

Inducing the failure *after* `mkstemp` succeeds fixes both problems at once: it
does not depend on permissions, so root sees it, and a real temporary file
exists for the cleanup to remove. Confirmed by disabling the cleanup and
watching the stronger assertion go red:

```
LEFTOVER: [PosixPath('.../subdir/data.yaml.2xfb08zo.tmp')]
```

## What is wanted

The suite passes in a Claude Code cloud session, without weakening what any of
these four tests proves on a non-root machine. Where a test can be made
user-independent it should be, rather than skipped; where it genuinely cannot,
skipping with a stated reason is acceptable.

## Constraints

- **Running the suite as a non-root user is not available.** The cloud container
  starts as root and nothing in this repository controls that.
- **The wheel test's `--no-build-isolation` is deliberate** — it keeps the build
  offline and fast — so a fix that removes the flag is trading a property the
  test wanted for one it did not ask for.
- Out of scope: the shape of `_atomic_write_all` itself, and any other test that
  happens to be weak for an unrelated reason.

## Notes

- The requester raised this from a suite run in this session rather than from an
  external report, so the observations below are first-hand and reproducible
  here; no outside reference material was offered or needed.
- Two build routes were confirmed working in this container, which is what
  narrows the wheel failure to setuptools rather than to the package: building
  **with** isolation succeeds, and building **without** it succeeds under
  setuptools 84.0.0 in a fresh virtual environment.
- Whether the fix for the wheel case belongs in the test or in
  `scripts/remote_session_setup.sh` is deliberately left open here. The script
  already exists to make a cloud session work without a manual step, but giving
  it responsibility for the build toolchain is a design question, not an
  obvious call.

## References

- `tests/test_store_editor.py` — the two `chmod`-based atomic-write tests, and
  the one whose assertion is vacuous.
- `tests/test_scaffold.py` — the third `chmod`-based test; it drives the CLI in
  a subprocess, so nothing can be patched into it from the test process.
- `tests/test_shipped_prompts.py` — the wheel build, and the comment explaining
  why it reads the zip rather than installing it.
- `tcw/store/fs.py` — `_atomic_write_all`: the staging loop, and the
  `BaseException` handler whose unlink the vacuous test was meant to pin.
- `scripts/remote_session_setup.sh` and `.claude/settings.json` — the existing
  `SessionStart` provisioning for exactly this environment, and the candidate
  home for a toolchain floor.
- `.github/workflows/test.yml` — `runs-on: ubuntu-latest`, i.e. a non-root user,
  which is why none of this is visible in CI.
- `tests/test_session_bootstrap.py` — the existing `skipif` with a stated
  reason, the precedent for skipping a test an environment cannot host.
