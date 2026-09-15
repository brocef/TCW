# Follow-ups the tracker-link review left

Found by the multi review of
`2026-09-14-make-tracker-link-record-a-cross-reference-without-claiming-the-ticket`
(PR #38). Each was judged to need its own change rather than a fix on that branch.

## 1. A binding on a finished item is never committed, and nothing says so

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

## 2. `link` binds a resolved item that is waiting for deletion

Under `work.retain: false`, a resolved item's folder exists until
`tcw work delete` removes it (for example after a failed `pre` hook, or a
completion from `tcw serve`, which runs no hooks). `link` binds it and stages
`tracker.yaml`; `delete_resolved` then refuses with "has content no commit holds"
until that is committed. Safe, not data loss. The store already has
`pending_deletion(slug)`, so refusing there is a one-line guard if wanted.

## 3. Two finished items can hold one ticket and part

`find_binding` skips resolved items, so linking two finished items to the same
ticket and part succeeds twice. Documented as a limit, not refused, because
consulting resolved items would refuse the discarded-then-retaken case the skip
exists for.

## 4. `ClaimOutcome.account_id` and `account_name` are dead in production code

`claim()` still sets them (`tcw/tracker/intake.py`), but nothing outside
`tests/test_tracker_claim.py` reads them since `claimed-by` left `tracker.yaml`.
Removing them means editing that test, which the tracker-link item's plan kept
unedited on purpose.
