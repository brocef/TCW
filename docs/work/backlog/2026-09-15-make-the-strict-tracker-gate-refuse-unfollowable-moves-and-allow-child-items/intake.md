## Inbox manifest

- `2026-09-15-strict-mode-and-sync-follow-ups-from-the-combined-review.md`

## Inbox body

# Strict mode and sync: follow-ups from the combined review

The combined adversarial review of the tracker epic's four children (binding surface,
lifecycle sync, strict mode, progress comments) found two interactions that need
their own change.

## 1. Strict mode lets through a move the ticket cannot follow

`authorize` (`tcw/tracker/sync.py`) checks the ticket's assignee and status but not
whether the workflow offers a transition to the target. `deliver` does check that.
The review reproduced it with strict mode on and a workflow with no transition from
In Progress to In Review:

- `tcw work submit` passed the gate and moved the item to `review`;
- delivery then recorded `conflicting: … offers no transition to 'In Review'`;
- the next `rework` was refused because of that record.

**Suggested fix:** after its assignment check, `authorize` asks `assess_move`
whether exactly one offered transition leads to the target, and refuses when none
does. This changes what the gate means, so it needs a spec note in C4's
capability, `work/require-tracker-backed-work`, and tests.

## 2. `sync`'s owner rule can leave a strict item stuck

`tcw work tracker sync` skips an item whose owner is someone else and still exits 0.
Strict mode refuses while a record exists. Take an active item started as
`--owner agent-7` whose record says the claim is still owed:

- `submit`, or `start --take-over`, is refused with "run sync";
- `sync` from a shell without `TCW_WORK_OWNER=agent-7` prints "skipped" and exits 0.

**Suggested fix:** exit 1 when a slug named on the command line is skipped, and
mention `TCW_WORK_OWNER` in the strict refusal.

## 3. A held item whose claim is still owed stays locked under strict mode

`deliver` keeps a held item's record while it still owes the claim, which is correct:
the claim is this item's own. Under strict mode, though, `submit` is refused ("run
sync"), while `sync` prints `held`, exits 0 and keeps the record, so the item stays
locked until the other part resolves. This is rare. One option is to let
`binding_refusal` skip a record while the item is held, which needs the sibling scan
inside it.

A related case is visible rather than silent. An open item in review holds a submit
record, is held, and has its record cleared; then the other part is unlinked. The
item's later `complete` reports a conflict instead of accepting the old `since`.

## Triage (2026-09-15)

Merged at triage because every part changes what strict tracker mode
(`work.tracker.strict`) refuses or lets through — `authorize` and
`binding_refusal` in `tcw/tracker/sync.py`, and the strict checks in the work
commands. The maintainer asked for items touching the same feature to be combined.

- **In scope:** §1 and §3 of the entry above; the strict nesting entry below; the
  "epic worktree from before strict mode" note below.
- **Not in scope here:** §2 of the entry above (`sync` exiting 0 when it skips a
  named slug) is tracked in `2026-09-15-let-tracker-sync-name-its-transitions-bring-a-late-linked-ticket-forward-and-stop-reading-ordinary-moves-as-drift`.
- Related: GitHub #44 asks for the same "does the workflow offer a transition" check
  ahead of time, from `tcw validate`; §3 touches the tracker hold item's records.

## Folded in: inbox entry `2026-09-15-strict-tracker-mode-cannot-nest-or-group-children.md`

## Strict tracker mode cannot nest or group children

Found while specifying
`2026-09-12-refuse-local-work-that-no-claimed-tracker-ticket-authorizes` (its Risk 6).

Under `work.tracker.strict: true`, `tcw work new` is refused for everything but an
epic, so `tcw work new --parent <slug>` and `tcw work new --initiative <epic>` are
unavailable. `tcw work tracker import` creates items but takes neither option. A
child for an initiative can still be made by importing and then setting
`initiative` with `tcw work edit`; nesting under a parent cannot be done at all.

Options: give `tracker import` `--parent` and `--initiative`, or let `new --parent`
and `new --initiative` through and require `tracker link` before the child starts
(the start gate already refuses an unbound child).

## Folded in: from inbox entry `hold-entry.md` (A tracker hold leaves no evidence outside this checkout)

### Also: an epic worktree from before strict mode

An epic started with `--worktree` before `strict: true` was set can still merge its
branch when it completes, because epics are exempt from the gates. Strict mode only
refuses starting an epic with a worktree.
