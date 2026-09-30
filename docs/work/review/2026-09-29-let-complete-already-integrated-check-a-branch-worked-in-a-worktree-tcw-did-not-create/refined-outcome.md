# Refined outcome

**Accepted.** `tcw work complete --already-integrated` now checks that the
branch reached the node repository's `HEAD` (a merge, a fast-forward, or a
squash that leaves nothing to merge) before anything changes. It refuses
otherwise, and says how to get out. `--branch <name>` completes an item worked
on a branch TCW did not create, and never deletes that branch.

## Evidence

- **`tcw:verifier`:** all ten acceptance criteria met, each with a named test;
  84 tests passed in the three focused files. Its probe also covered an item in
  `review` (the tests start from `active`): refused, left in review, with the
  branch and `HEAD` untouched.
- **Full suite** as CI runs it (bare `pytest`), at `0f5a51dd`: 5060 passed,
  3 skipped. Since then:
  - `c95712e4` added the outcome only;
  - `6b6eea0f` changed one condition, with a new test; the new file's 17 tests
    pass.
- **Hands-on**, in a scratch repository with the branch's own code:
  - a hand-made worktree branch, unmerged, was refused with the way out named;
  - after `git merge --squash` and a commit, it completed, and `feature/x`
    still exists;
  - an item started with `--worktree` and holding an unmerged commit was
    refused, and both the item (`active`) and `work/<slug>` are still there.

## Found at verify, fixed

- `--branch` naming the item's own recorded branch counts as the recorded
  branch. After a passing check it is deleted as usual; nothing is lost,
  because it was just checked as merged. The way-out text for that case wrongly
  said "an item without a worktree". It now gets the recorded branch's advice
  (`6b6eea0f`, with a test).

## Deferred

- **Closing GitHub issue #72 waits for publication.** This repository's
  instructions say an issue closed before the fix ships tells the reporter it
  is fixed when they cannot install it yet. The order is: complete the batch →
  cut the version → push → answer and close, with the reply text approved
  first.
- Follow-ups already filed in the inbox: a detached worktree's unbranched
  commits lost at teardown, and whether a custom merge driver can fool the
  check.
