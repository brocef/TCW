# Outcome — Answer capabilities drift from the tombstone

Delivered as planned. The three code tasks and the documentation block all ran;
nothing was dropped or deferred except the one thing the spec already named as
out of scope.

## What shipped

`_shipped_but_missing` (`tcw/capabilities/cli.py`) answers "did this ship?" from
the live item where there is one and from `tombstone()` where there is not,
mapping the recorded resolution through `resolution_status` so the ship-versus-
abandon distinction is drawn by the same function `complete()` uses rather than
by a second literal comparison. A record with no resolution reports nothing.

Five tests in `tests/test_capabilities.py`, plus a corrected fixture helper.

## Evidence

- Full suite: **2235 passed**. `tcw validate`: OK.
- `tcw capabilities drift` in this repository prints `no capability drift` before
  and after, which is the expected no-op — nothing here is Missing while its
  work has shipped. Plan's Verification item, run rather than assumed.
- Criteria 1 and 2 were run against the pre-fix tree and failed in the way each
  describes. Recorded in `spec.md` and reproduced during implementation.

## Two things worth reading before verifying

### A test that passed for the wrong reason, and what was done about it

`test_cli_drift_still_ignores_a_discarded_item_whose_folder_is_gone` and
`test_cli_drift_is_silent_when_the_record_kept_no_resolution` both **passed
before the fix existed** — because "reports nothing" is also what the broken
lookup produced. A green run said nothing about whether they guard anything.

So each was checked against a mutant that treats any tombstone as shipped
(`shipped = bool(grave)`). Both go red on it. That is what makes them worth
keeping; without that check they were decoration.

The first two tests were watched red for the right reason: criterion 1 on
`assert 0 == 1`, criterion 2 on the two verdicts printed side by side.

A third test (`..._naming_a_slug_that_never_existed`) passes either side of the
change and is labelled in the plan as a regression guard, not a defect test.

### The fixture was wrong on its first run

`_shipped_capability` completed straight from `backlog`, which is only legal for
a discard, so the first run of the two headline tests failed with
`IllegalTransition` rather than with the defect. Fixed before reading anything
into the red. Worth recording because it is exactly the failure mode the
implementation rules warn about — a red test whose failure text does not name
the defect proves nothing.

## The sweep

The request made the sweep part of the deliverable, and it is in `spec.md` as a
table: two mechanical searches over `tcw/` (every work-store `get()` outside the
store module; every comparison against a resolved status), with each hit
adjudicated.

It found **a second instance**: `epic_completable` (`tcw/store/base.py:2141-2150`)
reads its children through `initiative_children`, so an epic whose children are
all resolved has zero *visible* children in another clone and the `bool(children)`
guard reports it not completable. Measured on a scratch node, not reasoned:

```
HERE  (completed/ present):    children: ['…-a-child']   epic_completable: True
CLONE (completed/ absent):     children: []              epic_completable: False
```

That is worse than the defect this item fixed — it gates the backlog→completed
bypass, so it **blocks a close** rather than under-reporting — and it is not
fixable with the current record, which carries no `initiative`. Filed as
`docs/work/inbox/2026-09-02-epic-completability-depends-on-which-checkout-is-asking.md`,
with a cheaper alternative to check first (the epic's rollup sidecar may already
record its children, in which case the record need not grow).

**The honest claim for this sweep is "every site those two searches reach", not
"every site".** Two previous sweeps for this pattern were recorded as complete
and were not; this one is stronger because every hit is written down and
adjudicated, but it is still a claim rather than a result, and `verify` should
read it that way.

## Documentation

All four entries evaluated. Release notes, changelog and the `tcw-capabilities`
skill fired and were updated. `README.md` was evaluated and needed no change —
both places it mentions drift stay accurate, and one of them calls the command
CI-usable, which this change makes true rather than false.

## Deviations from the plan

None in substance. The plan predicted a README change as "expected to fire,
check rather than assume"; checking showed no correction was needed, which is
the outcome that instruction was written to allow.
