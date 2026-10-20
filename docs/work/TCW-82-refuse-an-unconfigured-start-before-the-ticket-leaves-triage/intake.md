# An import moves a ticket out of triage and then refuses

Found by the `verify` stage of
`2026-09-18-make-transitions-start-optional-now-that-a-start-goes-through-assess-move`,
and deliberately kept out of it because it is a behavior change with its own test
to write. That item's `refined-outcome.md` records the deferral.

## What happens

`intake.claim` (`tcw/tracker/intake.py`) calls `leave_pre_backlog` before
`_claim_from`. So with `work.tracker.pre-backlog` configured and
`work.tracker.transitions.start` unset, `tcw work tracker import` applies the
triage-exit transition to the ticket and only then refuses, because the claim needs
a start transition it does not have.

The result is a ticket that has been moved out of triage with no item created. The
refusal was decidable from configuration alone, before any tracker call.

Verified by probe against the real code, using the existing
`tests/test_tracker_pre_backlog.py` fixtures with `start_transition=""`:

```
row: 1d   claimed: False   left_status: Triage
message: TRI-6 cannot be claimed: work.tracker.transitions.start is not set, ...
applied: ['11']
ticket status now: To Do   assignee: None
```

## Why it is low severity, and still worth fixing

The user is told: the CLI prints the "moved out of triage" line before the refusal,
so the side effect is visible rather than silent. And this is a newly reachable
state rather than a regression — before `transitions.start` became optional, this
configuration could not exist, because the parser refused it.

What makes it worth fixing anyway is that the move is not undone and not easily
undoable by the same command, and the refusal did not need the tracker to be
touched at all to be decided.

## The shape of the fix

A guard on `config.start_transition` inside `claim()`, ahead of
`leave_pre_backlog`. That places the check where every caller routes through it
rather than in each caller.

## What is missing today

Nothing covers this path. The shared helper
`_assert_named_the_key_and_changed_nothing` asserts `fake.applied == []`, but its
fixture configures no `pre-backlog`, so the triage exit never runs under it. A test
for the fix needs a fixture with both `pre-backlog` set and `transitions.start`
unset.
