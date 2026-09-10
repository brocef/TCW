# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Internal

- **The two atomic-write failure tests induce their failure at a seam instead of
  through directory permissions.** Both made a parent read-only and asserted the
  write was refused; root holds `CAP_DAC_OVERRIDE`, so the write succeeded and
  the suite failed for anyone running as root. The promote-failure test now
  patches `Path.replace`, the seam
  `test_atomic_write_all_promote_failure_is_the_recorded_ceiling` already used,
  and keeps its single-pair shape — that test fails on the *second* of two
  promotes, so a first-promote failure is covered nowhere else.
- **`test_atomic_write_temp_cleanup_on_failure` now measures cleanup.** Its
  read-only parent killed `tempfile.mkstemp` itself, which is the first
  statement of the staging loop, so no temp was ever created and the
  no-temp-left-behind assertion held whether or not `_atomic_write_all`'s
  handler unlinked anything. Deleting the `tmp.unlink(missing_ok=True)` left the
  old test green. The failure is now induced at `Path.write_text` via the file's
  own `_fail_writing`, one statement later, where a temp exists to be removed;
  the same mutation turns the rewritten test red. `_atomic_write_all` itself is
  unchanged — it was always correct, and only the test aimed at it was not.
- **`tests/test_scaffold.py::test_an_unwritable_target_reports_and_prints_no_path`
  is skipped when `os.geteuid()` is 0.** It drives the CLI in a subprocess, so
  the failure cannot be moved to a patchable seam, and the alternatives — an
  immutable attribute, a read-only bind mount — need capabilities and filesystem
  support a container may not have. The skip reason names root's permission
  override rather than calling the test unreliable.
- **`scripts/remote_session_setup.sh` raises setuptools to 70.1 when
  provisioning.** `tests/test_shipped_prompts.py` builds a wheel with
  `--no-build-isolation`, so the interpreter's own setuptools builds it and
  `pyproject.toml`'s `requires` is never consulted; `bdist_wheel` moved into
  setuptools at 70.1, and below that the build fails and the test reports a
  packaging defect that is not there. A new step 5 checks the version before
  upgrading, so an interpreter already at the floor is never written to and a
  `--force` run on a developer's machine stays safe. A failed upgrade prints one
  line and the script still exits 0, as every other path does.
- The provisioner's call-order assertions filter the new version check out of
  the recorded call log rather than shifting their indices, so the next step
  added to that script does not break them. The stubbed `python3` gained a `-c`
  case defaulting to "already at the floor", which is what keeps every existing
  test's pip count unchanged.
