# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- **A capability record for reporting upstream** — `plugin/report-an-issue-upstream`,
  which the `tcw-report` skill has answered since it shipped without the ledger
  ever saying so. Its two siblings in the same namespace (`triage-github-issues`,
  `run-a-post-mortem`) already carried one.

## Changed

- **`tcw-report` writes the report from a mirrored example instead of the real
  thing.** A new `## What goes in the report` section states the asymmetry the
  skill never mentioned — the tracker is public, the project being reported from
  may not be — and names what to swap (repository, branch and directory names,
  node ids, work-item slugs, capability paths and wording, absolute paths,
  taxonomy terms) against what to keep (the command's shape and flags, the
  config's shape, the error type and message, the triggering sequence, and the
  Environment block's real values, which describe the install rather than the
  project). A six-line before/after example carries both lists.
    - The section also encourages reproduction steps from a clean install and a
      scratch project, says a report is welcome without them, and suggests handing
      that reproduction to a subagent or agent team member working in a temporary
      directory. Harness-neutral by construction: no slash command and no
      Claude-only tool is named.
    - The closing paragraph no longer opposes "a real command, a real error, a real
      scenario" to "an abstract description" — the sentence that invited the leak.
      Concreteness is now located in the shape: real flags, a real error type, the
      real sequence, under names that are not the reporter's. The taxonomy /
      capabilities / work axis hint is unchanged.
    - The bug skeleton's `Steps to reproduce` and `Actual` placeholders point at the
      mirrored run, so the skeleton stops contradicting the section above it.
    - All of it is guidance. The skill's one standing requirement is still that TCW
      feedback goes to the GitHub tracker rather than the reporter's own `tcw work`
      store; no sentence refuses a report, gates it on approval, or redacts against
      the reporter's wish, and `allowed-tools` is unchanged.
- **`tcw-plugin`'s router bullet for `tcw-report`** gains one clause naming the
  mirrored default, so an agent deciding where to route a "can I paste this?"
  question lands on the skill that answers it.

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
