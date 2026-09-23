# Give a recordless sync a move, and let strict mode work without `transitions.start`

Three defects found by an adversarial review of the whole tracker-verbs epic, read
as one combined change rather than child by child. None is visible from any single
child: each needs two of them present at once, which is why six rounds of per-child
review missed all three. All three were reproduced against the in-repo fake tracker,
first by the reviewer and then independently by the coordinating session running the
same probes against `main`.

The epic that produced them is
`2026-09-16-separate-claim-from-status-movement-in-the-tracker-verbs`, and it is held
open until these are fixed. Its whole purpose was to make a class of claim-and-status
problems unreachable; closing it while it has created three more of the same kind
would be closing it on its own terms and failing them.

## 1. Running the diagnostic command corrupts a healthy binding

A `tcw work tracker sync` on an item with no sync record writes `move: null` into the
binding, and the binding reader then refuses to read its own record.

Observed on a healthy item: started, ticket in the active status and assigned to the
caller, nothing owed. The tracker is briefly unreachable. One `tcw work tracker sync`
later, `tcw work show` reports `tracker sync: record cannot be read ('sync' has no
text for: move)`. Nothing was wrong before that command ran.

Two things make it worse than a cosmetic record problem:

- Under strict mode it blocks `tcw work complete` until a second sync happens to
  succeed, and the refusal tells the user the binding is unreadable when what
  actually happened was a short outage.
- The advice attached to that refusal includes unlinking the item and discarding it.
  That is dangerous advice for a state TCW created itself.

It is transient — one more sync clears it — but a user who reaches for the
diagnostic command during an outage is the exact person who will be told to discard
their work.

## 2. A reopened ticket on finished work cannot be closed again

Same root cause. Because the move is absent, the rule that a completion or a discard
never needs a claim does not fire, so syncing a resolved item whose ticket somebody
reopened demands ownership of that ticket.

Where `exclusive-claim-transition` is set, this is a closed loop with no way out
inside TCW:

```
tracker sync               -> "Take it with `tcw work tracker claim`"
tracker claim              -> refused: the ticket does not offer that transition
tracker claim --take-over  -> the identical refusal
tracker sync               -> back to the first message
```

Only editing the ticket by hand in the tracker escapes it. Where the exclusive
transition is not set, the only recovery inside TCW is taking a colleague's ticket
away in order to close work that is already finished — which is the precise outcome
the rule about resolutions not needing a claim was written to prevent.

## 3. A strict configuration in which no work can be created, blessed by `tcw validate`

Strict mode with `work.tracker.transitions.start` unset is a dead end. `tcw work new`
refuses and points the user at `tcw work tracker import`; `import` refuses because it
claims through `transitions.start` and points the user at `tracker claim` and
`tracker link`, which need an item that `new` will not create. The two commands point
at each other and `tcw validate` reports the configuration as fine.

This one was created today, by the last two children of the epic interacting: one
made strict mode require `exclusive-claim-transition`, the other made
`transitions.start` optional. Nothing checked the combination.

The documentation leads projects straight into it. The release note written for the
optional key says "Leave it out — or leave the whole `transitions` block out", and
mentions only that `import` and `inbox accept` still need it — not that under strict
mode this means no work can be created at all. The Jira guide lists strict mode's
requirements without it, and names `tracker import` as the way in.

A ticket already assigned to the caller still imports, so for a strict project the
failure is invisible on the author's own tickets and total on anybody else's.

## The requester's decision on 3

**Require `transitions.start` under strict mode**, beside the existing
`exclusive-claim-transition` requirement, so `tcw validate` refuses the dead-end
configuration instead of blessing it.

The alternative considered and rejected was falling back to
`exclusive-claim-transition` when `transitions.start` is unset, on the grounds that
strict mode guarantees it is set and describes it as the transition that takes a
ticket into work. The requester chose the explicit requirement: a configuration error
reported by `tcw validate` is better than a silent substitution, even though it means
the key is optional everywhere except strict mode.

This partly walks back the child completed today. That child is not wrong — the key
is genuinely optional for ordinary projects, which is the common case — but its
release note now needs to say that strict projects must still set it.

## Constraints

- **Findings 1 and 2 share one root cause** and are expected to share a fix. They are
  written separately because they fail differently and need separate tests.
- **There is a known trap in fixing 1 and 2.** The obvious repair is to give the
  recordless case a move derived from the item's status. For an active item that
  yields `start`, and a record naming `start` is exactly what the delivery code reads
  as "the claim is still owed" — so a careless fix would make a failed sync claim the
  ticket on the next run. The value written into the record and the value handed to
  the move assessment may have to stop being the same value.
- The epic stays open until this lands.
- No version is being cut for this work; it merges to local `main` only.

## Notes

- **Asked and answered:** the requester was asked how strict mode should claim with
  no `transitions.start` set, and chose the explicit requirement. No other reference
  material was requested from them, because every reference here was produced inside
  this session and is listed below.
- The reviewer raised two further things that are **not** part of this item: a
  forward-only return that deletes an existing record while its comment and the
  changelog both say it writes none, and the open question of whether
  `exclusive-claim-transition` is required to land on the active status. Neither was
  traced to a failure. They belong in their own item if anywhere.
- A cosmetic defect was also reported: a refusal sentence in the strict binding advice
  is assembled with a capital letter after a semicolon and a lowercase one after a
  full stop. Small enough to fold into this item's work if the file is open anyway.

## References

- `probes/` in this item's folder — the seven probes that reproduce all three
  findings, kept because the scratch tree they were written in has already been lost
  to a crash once in this run. They print rather than assert, so they record current
  behaviour; converting them into real tests is part of the fix.
- `docs/work/active/2026-09-16-separate-claim-from-status-movement-in-the-tracker-verbs/`
  — the epic's spec and plan. Its goal 6, that six named problems stop being
  reachable, is the standard this item is measured against.
- `tcw/tracker/sync.py` — the move fallback that produces the absent move, the
  record write that stores it, and the ownership check that the absent move defeats.
- `tcw/tracker/intake.py` and `tcw/store/base.py` — the claim path that needs
  `transitions.start`, and the strict-mode requirement list it has to join.
- `docs/release-notes/upcoming.md` and `docs/guide/jira.md` — the two documents that
  currently invite a strict project into finding 3.
