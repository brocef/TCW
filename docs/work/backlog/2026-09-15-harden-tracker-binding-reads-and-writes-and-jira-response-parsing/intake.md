## Inbox manifest

- `2026-09-15-tracker-commands-classify-an-unreadable-binding-differently-from-show.md`

## Inbox body

# Tracker commands classify an unreadable binding differently from `show`

Found by the adversarial review of
`2026-09-12-surface-an-item-s-tracker-binding-in-the-board-the-projection-and-the-web-app`,
and judged to need its own change. It was there before that item.

The board read (`FsWorkStore._read_item`) and the tracker commands read `tracker.yaml`
two different ways. The board read catches every way the file can fail to read and
reports it as the item's problem. `tracker link`, `unlink` and `import` go through
`read_sidecar` and `read_binding`, which do not:

- **A directory named `tracker.yaml`:** `show` reports a problem, but `link` and
  `unlink` see no file and treat the item as unbound.
- **A file that is not UTF-8:** `show` says "not a readable text file", but `link`,
  `unlink` and `import` stop with Python's raw decoding error.
- **A named pipe:** `read_sidecar` opens it and blocks.

(A value YAML cannot build, such as `bound: 2026-02-30`, used to crash every reader;
`read_binding` now reports it as malformed.)

**Suggested fix:** give `read_sidecar` (or a binding-specific read beside it) the
same handling as `_read_item`: do not open anything but a regular file, and turn
read errors into a problem the commands report.

**Two more readers of the same kind** were found by the combined review of the tracker
epic's children:

- **Strict-mode `drop`.** `ever_bound` (`tcw/tracker/intake.py`) uses
  `read_sidecar`, which returns nothing for a directory named `tracker.yaml`. So strict
  `tcw work drop` goes through, although the board shows the item as
  `ticket: unreadable` and `commands.md` promises the drop is refused.
- **`tcw work tracker sync <slug>`.** Its single-slug path reads the binding through
  `binding_of`, and prints a raw traceback on text that is not UTF-8.

## Triage (2026-09-15)

Merged at triage because every part is about the tracker binding (`tracker.yaml`)
and the Jira client failing badly on input or state they do not expect: how the
binding is read (`read_sidecar`, `read_binding`, `binding_of`, `ever_bound`), how
binding and record writes are staged and merged back, and how Jira responses are
parsed (`tcw/tracker/jira.py`). The maintainer asked for items touching the same
feature to be combined.

- **In scope:** the entry above, and the three folded in below.
- Parts 1 and 3 of the tracker-link follow-ups were recorded as documented limits
  ("leave it, if nobody is surprised in practice"); whether they stay out is for the
  request stage.

## Folded in: inbox entry `2026-09-15-tracker-client-operations-trust-the-response-shape.md`

## Tracker client operations trust the shape of Jira's response

Found by the code review of
`2026-09-14-publish-concise-progress-links-and-comments-to-a-bound-tracker-ticket`.
It needs its own change.

`JiraClient.recent_comments`, `transitions`, `search` and `issue`
(`tcw/tracker/jira.py`) all assume that a response which parsed as JSON has the
expected shape. A payload that is a list, or an entry in it that is not a mapping,
raises `AttributeError`. That error is not a `TrackerError`, so it escapes the
commands' handling of tracker errors and prints a traceback instead of a pending or
conflicting result.

**Suggested fix:** check the shape in `_json`, or in each operation. A response of
the wrong shape should raise `TrackerError` ("the tracker returned a response of an
unexpected shape for <path>"), and one test should cover each operation, as the
explicit-timeout test does.

## Folded in: inbox entry `2026-09-14-follow-ups-the-tracker-link-review-left.md`

## Follow-ups the tracker-link review left

Found by the multi review of
`2026-09-14-make-tracker-link-record-a-cross-reference-without-claiming-the-ticket`
(PR #38). Each was judged to need its own change rather than a fix on that branch.

### 1. A binding on a finished item is never committed, and nothing says so

`tracker link` and `unlink` now accept completed and discarded items. Their folders
are gitignored by default (`tcw work init` writes the rules), and `git_stage`
(`tcw/store/fs.py`) drops ignored paths without a word — `_warn_hidden` is silent
for resolved folders on purpose. So the command reports success, the file is on
disk, and no other clone ever sees it.

The simplest behaviour was chosen for now: document it (README, capability,
skill reference, release note, `link` help) and leave the code alone. A
`ponytail:` comment in `_item_or_reason` (`tcw/work/cli.py`) marks the spot.

Options when this is revisited:

- Warn when a sidecar write the user asked for lands in a gitignored resolved
  folder. That belongs in the filesystem adapter, not the store interface.
- Refuse to link a resolved item whose folder git will not record.
- Leave it, if nobody is surprised in practice.

### 2. `link` binds a resolved item that is waiting for deletion

Under `work.retain: false`, a resolved item's folder exists until
`tcw work delete` removes it (for example after a failed `pre` hook, or a
completion from `tcw serve`, which runs no hooks). `link` binds it and stages
`tracker.yaml`; `delete_resolved` then refuses with "has content no commit holds"
until that is committed. Safe, not data loss. The store already has
`pending_deletion(slug)`, so refusing there is a one-line guard if wanted.

### 3. Two finished items can hold one ticket and part

`find_binding` skips resolved items, so linking two finished items to the same
ticket and part succeeds twice. Documented as a limit, not refused, because
consulting resolved items would refuse the discarded-then-retaken case the skip
exists for.

### 4. `ClaimOutcome.account_id` and `account_name` are dead in production code

`claim()` still sets them (`tcw/tracker/intake.py`), but nothing outside
`tests/test_tracker_claim.py` reads them since `claimed-by` left `tracker.yaml`.
Removing them means editing that test, which the tracker-link item's plan kept
unedited on purpose.

## Folded in: from inbox entry `2026-09-14-follow-ups-the-lifecycle-sync-review-left.md` (Follow-ups the lifecycle synchronization review left)

### 1. Any staged sidecar write blocks a worktree item's merge-back

**Widened by the combined review of the tracker epic's children (2026-09-15).** Git
refuses a non-fast-forward merge while *any* file is staged, not only files in the
merging item's folder. So a `sync` or `comment` record staged on item Y blocks the
merge-back of worktree item X, and `_complete`'s hint only looks at X's own
`tracker.yaml`. Progress comments make records more common: a project whose account
may move tickets but not comment gets a comment record on every move. The hint
should check `git diff --cached` across the whole store.

`tcw work complete` merges the item's work branch into the primary checkout
(`merge_worktree`, `tcw/store/fs.py`). The branch carries the item's folder, so a
staged but uncommitted file in that folder on the primary checkout makes git refuse
the merge ("would be overwritten by merge"). Sidecar writes are staged, never
committed: `tracker link`, `tracker unlink`, and now the synchronization record all
do it. The synchronization item added a hint naming the record when one exists;
`link` and `unlink` on a worktree item still produce only git's message.

Options: commit sidecar writes made to an item with a worktree, or check for staged
changes in the item's folder before merging and name them.
