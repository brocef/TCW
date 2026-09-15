# Refined outcome — accepted

## The decision

Accepted by the requester on 2026-09-02, in their words: *"Approved."*

The assessment they approved on is `outcome.md`, presented in full: the fix, the
evidence, the two tests that passed before the fix existed and how that was
handled, the fixture that was wrong on its first run, and the second instance the
sweep found and this item does not fix.

## What was delivered

`tcw capabilities drift` gives the same verdict in every checkout of a project at
the same commit. `_shipped_but_missing` (`tcw/capabilities/cli.py`) reads the
live item where there is one and the tombstone where there is not, mapping the
recorded resolution through `resolution_status` so the ship-versus-abandon
distinction is drawn once, by the same function `complete()` uses.

Where the record cannot settle the question — a backfilled tombstone with no
resolution — the command reports nothing rather than guessing. Requester's
decision, taken with the trade-off on the table.

## Evidence

- Full suite: **2235 passed**. `tcw validate`: OK. `tcw capabilities check`: OK.
- Measured before and after on a scratch node: `rc=1` with a `shipped-missing`
  finding on the machine that completed the item, `rc=0` and `no capability
  drift` in the clone. Identical after the change.
- `tcw capabilities drift` in this repository prints `no capability drift` either
  side — the expected no-op, run rather than assumed.

## Capability ledger

Reconciled against what shipped. One amendment, as the spec declared:

| Capability | Delta |
| --- | --- |
| `capabilities/detect-capability-drift` (cap-c38e6d) | Amended with the reproducibility promise and the limit on it — silence where no resolution was recorded. Status stays **Supported**. |

Recorded in the item's `capabilities.yaml` as one `changed:` entry. No new
capability and no status flips: the command already promised to report drift, and
this made it keep that promise everywhere.

## What this does not close

**`epic_completable` has the same defect and is the more damaging of the two.**
It gates the backlog→completed bypass, so it blocks a close rather than
under-reporting, and it is not fixable with the record as it stands — the
tombstone carries no `initiative`, so nothing surviving into another clone says
whose child a resolved item was. Filed as
`docs/work/inbox/2026-09-02-epic-completability-depends-on-which-checkout-is-asking.md`,
including a cheaper alternative to test first: the epic's rollup sidecar may
already record its children, in which case the record need not grow at all.

**The sweep is a claim, not a result.** It covers every site reached by two
mechanical searches — every work-store `get()` outside the store module, and
every comparison against a resolved status — with each hit adjudicated in
`spec.md`. That is stronger than the two previous sweeps for this pattern, both
of which were recorded as complete and were not. It is not proof that no third
instance exists.

## Deferred, with reasons

- **The originating item's own release.** As with the tombstone work, nothing is
  reported to any GitHub issue until the version carrying this is cut and pushed.
- **`unresolved_blockers`.** Non-goaled twice now, deliberately: acting on the
  new distinction changes when transitions refuse, which deserves its own item.

## Notes

The two tests that passed before the fix are the part of this item worth
remembering. "Reports nothing" was both the correct behaviour and the symptom, so
a green run distinguished nothing. Checking them against a mutant that treats any
tombstone as shipped is what turned them from decoration into guards — and it is
a cheap habit to keep for any test whose assertion is an absence.
