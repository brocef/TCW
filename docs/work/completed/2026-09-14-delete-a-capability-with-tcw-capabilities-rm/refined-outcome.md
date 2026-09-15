# Refined outcome — Delete a capability with `tcw capabilities rm`

## Decision

**Accepted.** On 2026-09-14 the requester handed acceptance of this item to a
multi review plus the test suite, with no human review. The developer ran two
review rounds and then stopped, as the agreed limit required, because Codex still
reported one point that belonged to this change.

The requester was shown that finding. They decided to fix it, test it and approve,
without a third review round. The fix is `ef045a4a`.

## Evidence

- **Full suite.** Bare `pytest` from the worktree root at `ef045a4a` gave **2861
  passed**, with no failures. Earlier runs, under both bare `pytest` and
  `python -m pytest`, gave 2860 at `c193740c` and 2846 at `ba02f4f0`.
- **Merge.** Merged into `main` as `069f7093`. The changelog and release-note
  conflicts were resolved by keeping both sides. The full suite on the merged
  `main` is run before the version cut.
- **Mutation checks.** The code was deliberately broken 24 times. 23 breaks turned
  tests red with the right failure. The 24th was a redundant branch for ambiguous
  paths that no test could detect, so it was deleted.
- **The final fix's test.**
  `test_remove_does_not_proceed_when_comparing_folders_fails_for_another_reason`
  failed with `DID NOT RAISE PermissionError` before the fix, and passes after it.

## Review verdicts

- **Adversarial code reviewer: DONE.**
  - Round 1 found three real defects, each fixed with a test:
    - references written as `..` or in a different letter case slipped past the
      reference check;
    - a capability inside a dot-folder slipped past the nested check;
    - the gate could never pass when an inherited capability shared a removed
      path.
  - Two notes were left unchanged: a capability inside a dot-folder blocks its
    parent but `rm` can't reach it, and a symlinked capability folder is refused
    more than it needs to be.
- **Codex (read-only sandbox confirmed on every run; tree unchanged).**
  - Round 2 found that a pattern name such as `a*` also deleted `abc`. This was
    fixed in the shared `git_rm`, so `tcw taxonomy rm` and the work store's deletes
    are fixed too.
  - It also found a crash when a folder vanished mid-check; that was guarded.
  - Its last finding was that the vanished-folder guard caught every `OSError`,
    so a permission error let the delete go ahead. Fixed in `ef045a4a` by catching
    only `FileNotFoundError`, with the test above.
- **`bllm`: no answer.** It reported "temporarily disabled for maintenance" on
  every run. This was filed in the llama inbox.

## Requester decisions

- **Both cautious refusals are kept.** `rm` refuses a capability that another
  capability still points at, and one with capabilities nested under it. In each
  case the message names what is in the way.

## Deferred follow-ups

These need separate changes. Some are filed as inbox notes, including the gate's
capabilities location, the store git calls, and `tcw taxonomy rm`.

- **Configured ledger location.** The completion gate ignores a configured
  capabilities location.
- **Other store git calls.** `git add`, `git mv` and `git ls-files` still read a
  path as a pattern.
- **`tcw taxonomy rm`** still deletes nested terms.
- **Dot-folder names.** `add` accepts names that `list` and `check` then hide.
- **Unreadable files.** An unreadable `meta.yaml` or folder produces a Python
  traceback, not a one-line message. Nothing is deleted.
- **Clearing a reference field.** The command line can't clear one today, so a
  refusal over a reference can only be resolved by repointing it.

## Closeout

- **Capability ledger:**
  - `capabilities/remove-a-capability` is created and `Supported`;
  - `capabilities/reset-an-override` and `work/complete-a-work-item` are updated
    to name `rm` and `removed:`;
  - `capabilities.yaml` matches these.
- **`removed:` form for item C:** list each deleted capability path under
  `removed:` in `capabilities.yaml`. Completion is refused while a local
  capability still exists at any listed path.
- **No GitHub issue** is attached.
- **Version:** this ships in the patch release cut right after this item
  completes.
