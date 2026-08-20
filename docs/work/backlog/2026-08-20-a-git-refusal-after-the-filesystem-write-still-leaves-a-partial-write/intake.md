## Origin

Found by adversarial review during 2026-07-30-fix-non-git-write-paths-work-new-and-init-fail-outside-a-git-repository (see its refined-outcome.md, "Deferred, with the user's agreement").

## Problem

The non-git work established preconditions: a write is refused before it touches
the filesystem when the repository is *absent*. A repository that exists and
*refuses* — a held `index.lock`, a rejecting hook, a permissions error, a
corrupt `.git` — is still detected only when staging fails, which is after the
content has been written. `main()` renders it as `tcw: git command failed`
rather than a traceback, so it is legible, but the partial write stands.

## Shape

This is not another precondition; a precondition cannot predict a lock acquired
a millisecond later. It needs rollback: write to a staging area and move into
place once git has accepted, or record enough to undo. Scenario 14 assertion 8
covers the message shape and explicitly not the atomicity.
