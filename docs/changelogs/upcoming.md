# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- `work.tracker.transitions` accepts `submit`, `rework`, `complete` and `discard`
  alongside `claim`, naming the transition each move applies. `discard` takes one
  name or one per discard resolution, and may be partial. A named transition that
  the ticket does not offer, that matches more than one offered transition, or that
  leads to a status other than the mapped one is refused before anything is sent.
  Validation is shape-only, as for `statuses`.
- `tcw work tracker link --sync-status`: for an item past `backlog`, records a
  `pending`/`claim: owed` sync record and delivers it at once — the claim, then one
  transition straight to the item's mapped status when offered, otherwise one per
  mapped status, re-reading between hops, and writes `catch-up: true` on the binding.
  Forward-only: no claim transition is applied to a ticket already past `active`
  (one assigned to the caller carries on from where it is; any other is refused), a
  ticket past its item is refused, and a resolved ticket is never moved. Refused for
  an item somebody else started. What does not arrive stays recorded for `tracker
  sync`, which resumes a walk the claim finished but a later hop did not, and aims at
  the item's current status rather than the recorded move's. Only a `catch-up`
  binding is walked through more than one status; every other delivery, including
  an owed claim from a failed `start`, is followed by one transition as before.
- A shared rung in the ladder (two local statuses mapped to one tracker status) is
  named for the higher local status, so its hop uses that move's named transition.
- A plain `link` of an item past `backlog` changes nothing in the tracker. When the
  ticket's status differs from the item's mapped one, or an open item's ticket is not
  assigned to the caller, it warns and writes `status-synced: false` on the binding
  (not part of `--json`). While that note stands, a move refused only because the
  ticket is out of its window or unclaimed is `held` with the `--sync-status` repair
  instead of `conflicting`, and records nothing; another holder and transition-name
  refusals stay `conflicting`. Strict mode's refusal names the same repair. The note
  clears once a delivery — or a checking `sync` — finds the ticket where its item says.

## Fixed

- A discard moves a ticket nobody is assigned; every other move still refuses one,
  and a ticket assigned to another account is still never moved. The post-transition
  read-back no longer demands the ticket be assigned to the caller for resolved work,
  which had turned a successful unassigned discard into `did not reach 'Won't Do': it
  is in 'Won't Do'`, and the progress comment for such a discard is posted rather
  than skipped.
- Drift is judged against the whole path from where the ticket was left to the move's
  target, so a hand move to an intermediate mapped status is accepted instead of
  reported as drift. The path is walked toward the target rather than derived by
  inverting the status mapping, which is ambiguous when `completed` and `discarded`
  map to one name.
- `tcw work tracker sync <slug>` exits 1 when the named item was started by somebody
  else and still carries a sync or comment record, naming it and `TCW_WORK_OWNER`;
  with nothing recorded, and under `--all`, it still exits 0. Strict
  mode's refusal names the owner to run as, so its "run sync" advice can no longer
  end in a silent success.
- Messages distinguish an unassigned ticket from one somebody else holds.

## Internal

- `ladder_steps`/`ladder`/`forward_from` in `tcw/tracker/sync.py` express the mapped
  statuses as an ordered ladder, used both for the drift window and for the walk.
  `MOVE_ONTO` (the inverse of `MOVE_STATUS`) is shared by the walk and `link`.
- `transitions` keys other than `claim` are unknown to 2.3.0 and earlier, which
  reject the whole tracker block when one is set.
  `assess_move` takes the move it is serving and the transition named for it.
- `tests/tracker_fake.py` records applied transition ids and gains the `AMBIGUOUS`,
  `STRICT_LADDER` and `BROKEN_LADDER` workflows.
