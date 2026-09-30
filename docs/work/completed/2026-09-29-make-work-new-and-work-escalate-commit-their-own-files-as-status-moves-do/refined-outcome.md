# Refined outcome

**Accepted.** Creation commits its own files, as status moves do, under
`work.auto-commit-transitions`. That covers `new`, `inbox accept`, `tracker
import`, ticket accept, `escalate`, `delegate` and the web app's create.

## Evidence

- **`tcw:verifier`: all eight acceptance criteria met.**
  - Full suite, bare `pytest` at `512e1f27`: 5055 passed, 3 skipped, 0 failed.
  - Its probe ran the real `escalate` and `delegate` commands between a
    scratch parent and child: one commit in the receiving repository, and the
    sender's HEAD unmoved.
  - It ran `inbox accept` and `delegate` with the switch off by hand: staged,
    not committed.
- **Hands-on, in a scratch repository with the branch's code:**
  - `new` made one commit and left a clean tree;
  - accepting an entry made one commit (`idea.md → <slug>`) and left a clean
    tree;
  - with the switch off, `new` left the item staged and made no commit.

## Found at verify, fixed

- **The new store methods existed only on `FsWorkStore`,** yet the CLI and the
  web app call them. `WorkStore` now declares `refresh_for_creation` and
  `commit_writes`, with defaults that do nothing, which is what a store whose
  writes are already durable needs.
- **The escalate and delegate capability texts omitted the publishing-store
  case,** where the request is left staged. Added.
- One overlong line in the guide was rewrapped.

## Not fixed, recorded

- **The spec named a CLI helper `_commit_creation`.** It became the store
  method `commit_writes`, with a thin `_commit_created` in the CLI, so the web
  app and `_inbox_write` share it.
- **The web app's commit warning goes to the server's stderr only,** not to
  the browser.
- **Criterion 4's test covers `new` and `escalate` only.** `inbox accept` and
  `delegate` were checked by hand by the verifier.

## Deferred

- **Closing GitHub issue #66 waits for publication.** The order is: complete
  the batch → cut the version → push → answer and close, with the reply text
  approved first.
