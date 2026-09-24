# Test the suite the way CI runs it, and notice red CI runs, unpublished tags and a shadowing install

## What is wanted

A passing local test run should be evidence about CI, a failing CI run or an unpublished
release should be noticed before it matters, and a test run should exercise this
checkout's code rather than whatever `tcw` is installed.

From 2026-09-11 to 2026-09-13 every CI run on `main` failed before any test ran, because
CI runs plain `pytest` and local runs used `python -m pytest`, which puts the repository
on the import path. Publishing depends on CI passing, so **v2.0.3 and v2.1.0 were tagged
and pushed but never reached PyPI**, and nobody knew for two days. The import is fixed
(`pythonpath = ["."]`). What is still wanted:

1. **Run the suite the way CI invokes it**, so a difference like that fails on the commit
   that introduces it.
2. **Warn about a red CI run on `main`, and about a tag that never reached PyPI.**
   *Decided with the maintainer at triage:* the warning comes **when cutting a release,
   and again when the user asks to push it** — not at session start, and not as a GitHub
   notification.
3. **Tests that start `tcw` as a subprocess run the installed CLI**, which in a git
   worktree is the primary checkout's code, not the worktree's. One test was fixed by
   running its own repository explicitly; the same trap applies to every other place that
   starts `tcw`.

## Constraints

- The version-cut script does not push; publishing stays a human step. The warning must
  fit that: it informs the person cutting and pushing, it does not publish.
- Re-pointing this machine's editable install affects every session sharing it; the item
  should not depend on doing that.

## Notes

- Merged at triage from two inbox entries, because both are about the gap between the code
  a test run exercises and the code that ships or runs elsewhere; both kept verbatim in
  `intake.md`.
- Checked at triage on `main`: no test or CI step runs `pytest --collect-only`; the
  existing `skills/documentation-sync/scripts/unpushed-version.sh` asks git remotes whether
  a tag was pushed, never PyPI; the editable install is `tcw-cli` 2.2.0, so the second
  entry's "stale version" no longer holds, but the shadowing does. Ten test modules, two
  fixture capture scripts and `scripts/require_artifact.py` start `tcw` as a subprocess.
- Whether `CLAUDE.md`'s "Working in a `--worktree` branch" section should say tests are
  affected too, not only manual CLI runs, was raised by the second entry.
- Reference material: asked; none provided.

## References

- `.github/workflows/test.yml` and `release.yml` — how CI runs the suite, and the publish
  job's dependency on it.
- `scripts/cut_version.py` — where the release-time warning would be seen.
- `tests/test_documented_cli_surface.py` — the test already changed to run its own
  repository rather than the installed CLI.

## Scope narrowed (2026-09-24 backlog cleanup)

Part 3 (subprocess tests running the installed `tcw` instead of the worktree copy) is out of scope: the venv rule and the worktree section of CLAUDE.md already handle it in practice. Remaining: run the suite the way CI does (bare `pytest --collect-only`), and warn about a red CI run and a tag that never reached PyPI when cutting and pushing a release.
