# Report a refused reconcile commit as a CLI error, not a traceback

## Product changes

`tcw work reconcile <epic> --commit` prints a Python traceback instead of an
error message when Git refuses the commit. The user sees a
`subprocess.CalledProcessError` and a stack trace naming TCW internals, rather
than a sentence telling them what failed and what to do about it.

Every other failure on that command already reports cleanly — an unknown epic, an
unreadable sidecar, an unreconciled capability. Only the commit step falls through.

Realistic ways a user reaches it: a pre-commit hook that rejects the commit,
`commit.gpgsign` set with no usable signing key, an unmerged path in the index, or
a read-only or locked repository. None are exotic, and none are the user doing
anything wrong with TCW.

## Technical changes

`reconcile` calls `git_commit` (`tcw/store/fs.py:331-337`), which runs
`subprocess.run(..., check=True)` and therefore raises
`subprocess.CalledProcessError`. The CLI handler `_reconcile`
(`tcw/work/cli.py:160-172`) catches `_ERRORS`, defined at `tcw/work/cli.py:34` as
`(ValueError, IllegalTransition, MultipleMatch, TransitionCommitError,
AlreadyClaimed)`. `CalledProcessError` is not in that tuple, so it propagates out
of `main`.

There is a sibling helper that already solves this shape: `git_commit_result`
(`tcw/store/fs.py:357`) distinguishes a *benign* non-commit (nothing staged,
pathspec unknown to git) from a *real* failure, returning an error string rather
than raising. `start --worktree` uses it and reports properly. Whether `reconcile`
should switch to it, or the exception should simply be caught, is a spec decision
— both are plausible and they differ in how a "nothing to commit" case behaves.

Two observations that should shape the spec's sweep rather than be assumed:

- `_ERRORS` guards **16** `except` sites in `tcw/work/cli.py`. Any of those paths
  reaching a `check=True` Git helper has the same exposure, so the question is
  not only about `reconcile`.
- `subprocess.CalledProcessError` is already handled deliberately in three places
  (`tcw/store/fs.py:82`, `tcw/store/project.py:82`, `tcw/work/cli.py:583`), so the
  codebase has an existing opinion about where it is caught. The fix should match
  that opinion rather than invent a new one — in particular, blanket-adding it to
  `_ERRORS` would swallow it at all 16 sites, which may be wider than intended.

## Constraints

- A genuinely refused commit must still exit non-zero. This is about the message,
  not about tolerating the failure.
- Do not make `reconcile` silently succeed when its rollup was not committed.
  Reporting a false success would be worse than the traceback.
- Preserve `reconcile`'s existing behavior: idempotent no-op on an unchanged
  rollup, the auto-completion and capability gates, and the scoped pathspec.

## Out of scope

- Changing what `reconcile` commits, or where. That was settled by
  `2026-08-12-honor-the-configured-work-path-at-every-work-store-call-site`, which
  routed it through `store.store_git_root`.
- Any change to `git_commit`'s or `git_commit_result`'s own contracts beyond what
  this fix needs.

## References

- `2026-08-12-honor-the-configured-work-path-at-every-work-store-call-site` — its
  `outcome.md` and `refined-outcome.md` both record this defect as found-but-unfixed
  while assessing that item's acceptance criterion 8 ("a forced Git failure in each
  write/commit path returns non-zero with an actionable error"). That criterion was
  met for the paths that item touched; this is the path it did not.
- GitHub issue [#16](https://github.com/brocef/TCW/issues/16) — the closing comment
  names this defect explicitly as a separate follow-up, so the issue thread already
  points here.

## Notes

- Found by inspection during another item's verification, not from a user report.
  The traceback has not been observed in the wild; the code path is read from
  source and is unambiguous, but no reproduction exists yet. Producing one is the
  first thing the plan should do.
- The three assumptions worth flagging for `spec`: that a pre-commit hook is the
  most likely real-world trigger, that `git_commit_result` is the intended
  destination, and that the sweep will find other exposed `_ERRORS` sites. None are
  verified here.
