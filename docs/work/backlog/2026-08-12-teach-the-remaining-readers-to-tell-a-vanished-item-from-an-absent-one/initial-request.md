# Teach the remaining readers to tell a vanished item from an absent one

Raised by review of the claim-race rework in
`2026-06-22-concurrency-safe-work-claims-for-multi-agent-repos-configurable-work-path-atomic-owner-stamp`.
Deliberately **not** folded into that item: fixing it properly is a layering
decision, and that item had already been rejected twice for patching this class
of defect one site at a time.

## Product changes

Two ways a concurrent claim can still mislead a user:

- **A blocked item can be started without `--force`.** If B is `blocked_by` A
  and someone claims A at that instant, `tcw work start B` sees A as
  unresolvable, drops it from the blocker list, and starts B.
- **A blocker can be recorded permanently wrong.** `tcw work new --blocked-by A`
  during the same window writes `{"external": "A"}` into `state.yaml` instead of
  `{"slug": "A"}`. Unlike the first, this one persists: an external blocker
  never auto-resolves, so the item stays blocked until someone edits it by hand.
- **`tcw serve` can return a traceback instead of a 404** when a web read of an
  item races another agent's `tcw work start` on it.

## Technical changes

One question, asked at three sites: **how does a reader distinguish "this item
moved" from "this item does not exist"?**

- `WorkStore.unresolved_blockers` (`tcw/store/base.py:1288`) and
  `_entry_for` (`tcw/store/base.py:1195`) both collapse `get(...) is None` to
  "absent". `start()` disambiguates this (`tcw/store/fs.py:2002`, via
  `_claiming_dirs`); these do not.
- `FsWorkStore.get_detail` (`tcw/store/fs.py:2868`) guards its `_find` result
  and then reads `state.yaml` unguarded — the `_find` → touch-the-path shape,
  on a read path rather than a claim path.

Note `unresolved_blockers`' docstring deliberately treats a slug that no longer
resolves as resolved ("a decision not to do it is as final as doing it"). That
policy is for *deleted* blockers and should stay; the concurrency case is the
unintended reading of it.

## The layering problem, which is the actual work

`.claiming/` is a filesystem-adapter private detail, so `base.py` cannot look in
it — the prime directive forbids it, and the abstraction is the whole reason the
work store can be pointed at Jira. The candidates:

1. A bounded re-probe in the base methods. Storage-neutral and small, but only
   closes the stale-directory half of the window, not the half where the item is
   sitting in `.claiming/` where `_find` never looks.
2. Make `FsWorkStore.get()` itself claim-aware — wait briefly for publication
   when a claim is in flight. Fixes every caller at one point, but turns a hot
   read into a possibly-blocking one, and `_lost_the_claim` polls `get()` in a
   loop, so a naive version turns a 500 ms recovery into 25 s.
3. A storage-neutral store operation that answers "vanished or absent?", which
   a transactional adapter implements trivially and the FS adapter implements
   with `_claiming_dirs`. Passes the litmus test; costs an interface method.

Pick one deliberately. The related item
`2026-08-11-roll-back-or-reorder-the-pre-move-set-field-writes-on-a-lost-transition`
covers `get_detail`'s `None` escaping into non-optional *callers* — downstream of
the unguarded read named here, not the same defect.

## Notes

Not urgent: the `.claiming/` half of the blocker window predates the claim-race
rework and is wider than anything that rework introduced. What the rework
changed is that these sites now return a wrong answer where a narrow
sub-window used to raise.
