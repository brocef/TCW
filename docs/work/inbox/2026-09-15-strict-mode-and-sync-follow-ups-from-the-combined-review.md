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
