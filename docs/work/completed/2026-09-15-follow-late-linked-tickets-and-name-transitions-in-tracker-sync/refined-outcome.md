# Refined outcome — Let tracker sync name its transitions, bring a late-linked ticket forward, and stop reading ordinary moves as drift

**Accepted.** All five reported defects are fixed, each reproduced against this tree
before it was fixed and each reproduction now a test. 25 of the 26 acceptance
criteria are met as written; the 26th is met in substance and its wording is recorded
below rather than reinterpreted.

## How this was verified

Three things, none of which was allowed to stand for the others:

- **The suite.** `pytest tests/` — 3400 passed, 2 skipped, exit 0, measured on the
  finished tree. The baseline of 3367 passed / 2 skipped was re-derived independently
  from a `git archive` of the plan commit, so the +33 delta is a measurement rather
  than a recollection.
- **Hands on the real thing.** The CLI was driven against the fake tracker and its
  actual output and exit codes read — `tracker link` leaving the ticket untouched,
  `work show` reporting the claim as owed, `work submit` walking the ticket
  `To Do → In Progress → In Review`, `tracker sync` then reporting `current`. That is
  GitHub #42 end to end on a workflow with no shortcut to the top.
- **An adversarial read.** The `tcw-verifier` agent went through the criteria and
  mutated the assertions. It found two defects in shipped code and one untrusted
  test, all reproduced here before being acted on. Details in `outcome.md`; the short
  version is that a late-linked discard was marching tickets through `In Progress`
  and `In Review` to abandon them, and the item's highest-risk gate survived
  mutation with the suite green.

The mutation result is the reason this is accepted rather than accepted-with-doubt.
Two of the three riskiest behaviours — the catch-up gate and the claim-landing guard
— are now pinned by tests that were each confirmed to go red when the behaviour they
name is broken.

## Criterion 23, recorded rather than reinterpreted

Criterion 23 reads "no test deleted except as criterion 19 describes". Three went
beyond that allowance:

- `test_the_transition_keys_c3_adds_are_not_accepted_yet` — deleted. Its own docstring
  names this item as what supersedes it.
- `test_a_discard_of_an_unclaimed_ticket_with_no_discard_status_posts_nothing` —
  re-pointed, and now asserts the opposite of one of its assertions. Its real subject
  (an unmapped `discarded` sends no status move) is preserved; it only posted nothing
  because the ticket was unassigned, which is the defect this item fixes.
- `test_a_ticket_pushed_back_after_tcw_claimed_it_is_still_drift` — renamed, because
  its name described a case it did not exercise.

Each is justified and declared. The criterion was written before it was known which
tests encoded the old behaviour, and its wording was too narrow. Saying so is cheaper
than pretending the criterion was met, and more useful than silently widening it.

## Deferred, with the reason

**GitHub #40, #41 and #42 stay open.** `docs/work/dod.yaml` lists "originating GitHub
issue answered and closed, if the item came from one" as a completion criterion, and
this item does not meet it. That is deliberate and is this repo's own sequencing rule
(`CLAUDE.md`): an issue closed before the fix ships tells the reporter it is fixed
when they still cannot install it. The order is complete every item → cut the version
→ push → then answer and close the issues. Nothing is posted to an issue without the
exact text being approved first, so the replies are not drafted here either.

**No version was cut.** The changelog and release-note entries are written into
`upcoming.md`, which is where a version cut takes them from; the cut is batched across
a run of items, not made one per item.

## What a reader should know that the diff does not say

The chaining this item adds is the only part that applies transitions nobody asked for
individually, in sequence, to a system other people watch. It is bounded to the rungs
the project itself mapped, forward-only, and gated on the claim being owed — so it
only ever runs on a ticket TCW has never held. Two limits are deliberate and are
documented in `docs/guide/jira.md`: a workflow that forces a ticket through a status
the project has not mapped stops the walk, and a claim that lands off the mapped
ladder stops it too. Both refuse rather than guessing a route.
