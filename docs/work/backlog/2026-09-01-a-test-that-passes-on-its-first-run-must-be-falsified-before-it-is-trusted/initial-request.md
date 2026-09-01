# A test that passes on its first run must be falsified before it is trusted

## The request

Strengthen the `implement` stage's existing red-test rule from an intention into
a check, in two places: this repository's `docs/lifecycle/implementation.md`, and
**TCW's own shipped prompt**, `tcw/work/prompts/implement.md:19-20`, which is
where the gap actually is because that line reaches every TCW user.

## The rule that already exists, and what it does not do

`tcw/work/prompts/implement.md:19-20`:

> **Write the failing test first and watch it fail** before the code that makes
> it pass. A test that has never been red proves nothing.

That is correct and it is not enough. "Watch it fail" is a private act that
leaves no artifact, so nothing ever contradicts an author who did not do it — or
who did it, got green, and explained the green away.

## Where this came from

The store-provisioning epic
([initiative](tcw://W/2026-08-26-declare-a-component-store-s-home-repository-so-a-fresh-checkout-can-provision-it)),
across all three children. Five defects reached the `verify` stage or an external
review behind tests that were green. Three times the author met a new test that
passed on its first run and explained it rather than distrusting it, and **every
explanation was locally true**:

| Where | The explanation given | What it missed |
| ----- | --------------------- | -------------- |
| child B, criterion 9 (16 tests) | "the ladder already delivers these, since `main` catches `ValueError`" | true for the inputs the fixture built; the fixture defaulted the axis |
| child C, divergence test | *(the author did ask why, and found it)* | — |
| child C, task 3 no-network pins | "they pass trivially, which is the point — they are regression pins" | correct, and legitimate |

The third row is why "never write a test that passes" is the wrong rule.
Green-on-first-run is sometimes exactly right. What is needed is a mechanical
discriminator, not a judgement call.

## The rule to add

> When a new test passes on its first run, **break the specific behaviour it
> names and confirm it goes red**, before writing anything else. If it stays
> green, the test does not test that behaviour.

Thirty seconds, and it collapses "is this green legitimate?" into one action.

It is also the only thing that catches the sharpest defect this epic produced. A
divergence test asserted `"diverged" in err`, matched **git's** push-rejection
hint, and stayed green while TCW's own message was the unhelpful `Not possible to
fast-forward, aborting`. Deleting TCW's message would have left that test green —
which is the whole tell, and a falsification step surfaces it immediately.

A supporting rule, cheap and mechanical, for the same class:

> When asserting a user-facing message, assert that the message it replaces is
> **absent**.

This pattern was already in the codebase and simply not reapplied:
`test_the_board_no_longer_misdirects_to_tcw_init` asserts
`"no tcw work node here" not in err`, and that is why it is a good test.

## What this does not cover

Stated so nobody expects more of it than it gives. Three of the five defects were
**coverage** gaps — a fixture that never reached the cell — and falsification
does not find those: break the behaviour and the tests that *do* reach it go red
as expected, while the unreached cell stays unreached. Those are already
addressed, by the `### Coverage` cross-product table in
`docs/lifecycle/templates/spec.md` and the no-defaulted-axis rule in
`docs/lifecycle/implementation.md`.

The two families and their countermeasures:

| Defect family | Countermeasure | Status |
| ------------- | -------------- | ------ |
| the test does not reach the case it names | Coverage table + no defaulted axis in fixtures | landed |
| the test reaches it and asserts the wrong thing | **falsification** | this item |

## Considered and rejected

- **Real mutation testing** (`mutmut`, `cosmic-ray`). A dependency and a slow CI
  job for something a thirty-second manual check catches at the moment of
  writing, when the author still has the context to interpret the result.
- **A repo test that greps test files** for `capsys`/stderr assertions lacking a
  paired `not in`. Cute, brittle, and gameable by whoever is in a hurry — which is
  exactly the person the rule exists for.

Both are worth re-stating at spec so the decision is on the record rather than
implicit.

## Scope

- `docs/lifecycle/implementation.md` — this repo's binding, alongside the two
  rules already there from the epic's post-mortem.
- `tcw/work/prompts/implement.md` — the shipped prompt. This is a change to CLI
  behaviour for every user, so it needs the usual care: the prompt is covered by
  `tests/test_skill_lifecycle_parity.py` and by line budgets, and the edit must
  strengthen line 19-20 rather than append a fourth bullet nobody reads.

## Out of scope

- The `### Coverage` table's own upstreaming, tracked separately in
  [Upstream the acceptance-criteria coverage table to TCW's own spec stage](tcw://W/2026-08-31-upstream-the-acceptance-criteria-coverage-table-to-tcw-s-own-spec-stage).
  That one is deliberately waiting for more evidence; this one is not, because the
  rule it strengthens already ships and is already believed.

## Notes

- The whole finding is that **the instruction was right and produced no
  observation**. Any fix that adds a fifth instruction to a document whose third
  instruction went unfollowed has repeated the mistake rather than fixed it, so
  the wording must describe an action with a visible result, not a disposition.
