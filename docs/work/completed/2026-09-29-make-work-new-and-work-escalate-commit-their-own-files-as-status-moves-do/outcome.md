# Outcome

Creating an item now commits its own files, as status moves already did, under
`work.auto-commit-transitions`. That covers:
- `tcw work new`;
- `inbox accept`, including a ticket;
- `tracker import`;
- `escalate` and `delegate`, committed in the receiving store;
- the web app's `POST /api/work`.

A refused commit is a warning with exit 0 and the files left staged. It is not
an error, because running a creation again would make a second item.

## What shipped

| Task | Commit |
| --- | --- |
| `FsWorkStore.commit_writes`, `inbox_source`, `_commit_created`; the creation paths; web POST; failing-first tests | `c5a4b83d` |
| Documentation: skills, guide, configure reference, inbox prompt, capability descriptions, changelog, release notes | `55226149` |
| Review fixes (below) | `42265250` |
| Documentation for the review fixes | `d0bda49f` |
| Test fixtures that committed by hand after `work new` | `31021446` |

## Tests

- **`tests/test_creation_commits.py`**: 11 tests, each mutation-checked
  (breaking what it checks turns it red):
  - the refresh before a provisioned store's creation;
  - the accepted folder entry's untracked leftover;
  - the rest of the creation paths.
- **Full suite (bare `pytest`) at `d0bda49f`**: 5017 passed, 3 skipped, and 29
  failed plus 9 errors, all in `test_upstream_projects.py` and
  `test_non_git_writes.py`.
  - Cause: their fixtures ran `git commit` after `tcw work new`, and that commit
    now has nothing to commit.
  - Fixed in `31021446`; the two files now pass, 127 tests. The combined run on
    main after the merge is the full confirmation.

## What the plan or spec got wrong

- **The spec did not consider a store that publishes to a remote.** In that
  layout the store is a provisioned home repository. Committing a creation on
  a stale copy made it diverge from the remote, and every later transition's
  fast-forward refused. Creation now refreshes first, as a transition does. If
  the refresh fails, the files are left staged with a warning, so creating
  still works offline.
- **Spec goal 5 says a request into another project must never be pushed.**
  The first version did push when the receiving store published. It is now
  left staged there (`commit_writes(publish=False)`).
- **The plan staged an accepted entry's path.** Staging it recorded back into
  the inbox any untracked file its removal left on disk. The path is now
  committed but never staged (`removed=`).
- **The plan missed `tracker import` and ticket accept.** Both create an item
  and now commit it, after the binding write and its rollback.

## Autonomous decisions

- **Review verdict "NOT DONE, two blockers"** (`adversarial-code-reviewer`).
  - Blocker 1, the stale provisioned store: accepted.
  - Blocker 2, the entry's leftovers: accepted.
  - Significant 2 and 3, ticket import and ticket accept: accepted.
  - Significant 4, the process-inbox skill telling the agent to commit each
    item: accepted and reworded.
  - Notes: the stale comment was fixed. Failure advice no longer says "Commit
    it yourself" when the fix is to push.
- **The failed-refresh fallback: stage and warn rather than refuse.** A
  creation that fails for lack of network loses the user's typing. A staged
  one loses nothing. I chose this myself, from the spec's own rule that a
  creation must not look like a failure; no advisor was consulted.
- **Moved to a separate change, not done here:**
  - `_own_locally` reusing `commit_writes`;
  - hook timeouts;
  - two web requests committing at once, which #73's single store lock
    addresses.
- **The web app writes its warning to stderr only.** It is not shown in the
  page. Recorded as a divergence from the CLI, not fixed.
