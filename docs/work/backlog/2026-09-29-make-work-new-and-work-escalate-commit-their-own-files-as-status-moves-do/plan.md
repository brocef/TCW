# Plan — Make work new and work escalate commit their own files, as status moves do

Worked in a worktree (`start --worktree`), with a scratch venv pinned to it.

## Task 1 — Failing tests

**Creates** `tests/test_creation_commits.py`, with one test per acceptance
criterion 1-7, in scratch git repositories, driving `tcw.cli.main`
in-process:

- criteria 1 and 5: `new`, with an unrelated staged file, and with a
  rejecting `pre-commit` hook;
- criterion 2: `inbox accept`;
- criterion 3: `escalate` and `delegate`, using a parent and child pair in two
  repositories, as `tests/test_recursion.py` sets up;
- criterion 4: the switch off;
- criterion 6: the fake tracker, as in `tests/test_tracker_sync.py`;
- criterion 7: the web app, through the test client `tests/test_serve*.py`
  uses.

All are committed `xfail(strict=True)`, except the parts of criterion 4 that
pass today.

## Task 2 — The helper and the four commands

**Modifies** `tcw/work/cli.py`:

- adds `_commit_creation(st, message, paths) -> str | None`, next to
  `_own_locally`. It returns None when the switch is off or the commit
  succeeded, and git's message otherwise. It stages first with `git_stage`.
- `_new` calls it after `_ticket_on_filing`, with the item folder. `st.path`
  after the tracker write, so a sidecar is included.
- `_inbox_accept` calls it with the item folder and the entry path.
- `_escalate` and `_delegate` call it with the destination store and the
  written file.
- A failure prints `tcw work <verb>: created <x>, but committing it failed:
  <git>; commit it yourself` to stderr and exits 0.

**Modifies** `tcw/work/recursion.py`: `_inbox_write` stages the file it wrote
(goal 4).

**Proves** criteria 1-5.

## Task 3 — Tracker and web app

**Checks** that `tracker import`'s rollback (`st.drop`) runs before any
commit; it does, if the commit is at the end of `_new`. That needs a test
only if the order is not obvious.

**Modifies** `tcw/serve/__init__.py`: the creation `POST` calls the same
helper after `_owe_ticket_if_configured`, and a commit failure is logged as a
warning in the response, not an error.

**Proves** criteria 6-7.

## Task 4 — Existing tests and wording

- **Updates** tests that counted commits or asserted a staged `new`: grep
  `log_count`, `--cached`, and `status --short` in `tests/test_work*.py`,
  `test_recursion.py`, `test_tracker_sync.py`, and
  `test_store_publication.py`.
- **Corrects** the comment in `_complete` (`only transitions commit
  themselves`).

## Task 5 — Documentation Sync

- `skills/work/SKILL.md` and `skills/work/references/transitions.md`: "TCW
  commits the transitions" becomes "commits what it writes on its own:
  transitions and creation". [Skill-Driven-Component]
- `tcw/work/prompts/inbox.md` step 7 ("Commit the new item"): the item is
  already committed unless the switch is off. Re-baseline the prompt-fallback
  fixture, following its procedure.
- `skills/configure/references/work.md` and `docs/guide/work.md`
  ("Transitions and commits"): the switch covers creation.
  [Guide-Topic-Change]
- The four capability descriptions, and the item's `capabilities.yaml`.
- The changelog, and release notes calling out the new commits.

## Task 6 — Full suite

Bare `pytest`, with the venv first on PATH. **Proves** criterion 8.

## Verification

By hand in a scratch parent and child repository: `new`, `accept`,
`escalate`, `delegate`, reading `git log --stat -1` in each repository. Then
the same with the switch off.
