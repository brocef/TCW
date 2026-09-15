# Spec — A test that passes on its first run must be falsified before it is trusted

## Capability changes

**Changed**

- `work/run-a-lifecycle-stage` — the `implement` stage's shipped instructions
  gain a step. The capability describes running a stage and printing its
  instructions; what those instructions say is the surface a user meets, so the
  body should not go stale on a rule this load-bearing.

No new capability: this adds no verb, flag, or file. A user's set of possible
actions is unchanged; what changes is what one of them tells them to do.

**Taxonomy.** None. `lifecycle-stage` already exists and this changes one
stage's content, not the vocabulary.

## Problem

The rule is already there, and already correct.
`tcw/work/prompts/implement.md:19-20`:

> 3. **Write the failing test first and watch it fail** before the code that
>    makes it pass. A test that has never been red proves nothing.

It ships to every TCW user, it is printed at every `tcw work stage implement`,
and across the three children of
[the store-provisioning epic](tcw://W/2026-08-26-declare-a-component-store-s-home-repository-so-a-fresh-checkout-can-provision-it)
five defects still reached `verify` or an external review from behind green
tests.

**The gap is that "watch it fail" produces nothing.** It is a private act. When
the test comes up green instead, the instruction has already been satisfied in
the author's own account of events — they wrote the test, they ran it, it did not
fail, and now they must decide what that means with no rule to consult. Three
times in that epic the author decided, and each explanation was *locally true*:

| Where | Explanation given | What it missed |
| ----- | ----------------- | -------------- |
| child B, criterion 9 | "the ladder already delivers these, since `main` catches `ValueError`" | true for the inputs the fixture built — it defaulted the axis |
| child C, divergence test | the author did ask why, and found a spurious match | — |
| child C, no-network pins | "they pass trivially, which is the point" | correct and legitimate |

The third row is the constraint on any fix: **green on first run is sometimes
right**, so a rule of "your test must fail" would be false and would be worked
around. What is missing is a mechanical discriminator.

The sharpest instance is child C's divergence test. It asserted
`"diverged" in err`, matched **git's** push-rejection hint, and stayed green
while TCW's own message was the unhelpful `Not possible to fast-forward,
aborting`. No amount of care about coverage finds that; the assertion was aimed
at a string this program does not own.

## Goals

1. An author who meets a green new test performs one action with a visible result,
   rather than forming a judgement.
2. The rule reaches TCW users, not only this repository — the weak line is the
   shipped one.
3. The `implement` step list does not grow a bullet nobody reads.

## Non-goals

- **Coverage gaps.** Three of the five defects were fixtures that never reached
  the case; falsification does not find those, and they are already addressed by
  the `### Coverage` table in `docs/lifecycle/templates/spec.md` and the
  no-defaulted-axis rule in `docs/lifecycle/implementation.md`. Saying so is part
  of this spec's job, because a rule oversold is a rule relied on wrongly.
- **Automated mutation testing.** Rejected on the record below.
- The `### Coverage` table's own upstreaming, which is
  [a separate item](tcw://W/2026-08-31-upstream-the-acceptance-criteria-coverage-table-to-tcw-s-own-spec-stage)
  deliberately waiting for more evidence. This rule is not waiting, because the
  line it strengthens already ships and is already believed.

## Design

### 1. The rule

Step 3 of `tcw/work/prompts/implement.md` is **rewritten, not appended to**:

> 3. **Write the failing test first and watch it fail** before the code that
>    makes it pass. A test that has never been red proves nothing. If a new test
>    passes on its first run, break the behaviour it names and confirm it goes
>    red before writing anything else — a green that was never earned is the
>    same as no test, and the explanation for it is usually true and beside the
>    point.

Rewritten because the list is a numbered sequence an author reads once; a fourth
bullet is the shape of thing that gets skimmed, and this rule's whole subject is
an instruction that was read and not acted on.

### 2. The supporting rule, in this repo only

`docs/lifecycle/implementation.md`, beside the two rules the epic's post-mortem
already put there:

> **When asserting a user-facing message, assert that the message it replaces is
> absent.** An assertion aimed at a string another program owns is not a test of
> this one.

Local rather than shipped because it is narrower — it is about error-message
tests specifically — and because the pattern is already present in this codebase
(`test_the_board_no_longer_misdirects_to_tcw_init` asserts
`"no tcw work node here" not in err`) and was simply not reapplied. A rule that
generalizes one repository's idiom should earn its way upstream separately.

### 3. What constrains the edit

The prompt is guarded, and the guards decide the wording:

- `tests/test_skill_lifecycle_parity.py:205-213` — **no sentence of eight or more
  words may appear in both** `prompts/implement.md` and
  `skills/tcw-work/references/stage-implement.md`. So the router must not restate
  this, and the prompt's wording must not collide with anything already there.
- `tests/test_skill_lifecycle_parity.py:216-224` — the router has a line ceiling.
  Not touched here, because the router is not gaining a line.
- `tests/test_documentation_prompt.py:88, 280` — the shipped prompts are asserted
  to carry exactly one documentation span and to render without a code-block
  hazard. A rewritten step 3 must not disturb either.

## Abstraction litmus test

| Operation | Verdict |
| --- | --- |
| Printing a stage's instructions | **No new operation.** `tcw work stage` already does this; its content changes. |
| The rule's content | **Not an operation at all.** It instructs a human or agent and reaches no store. A tracker-backed store prints the same text. |

Nothing here touches the store interface, so the prime directive has nothing to
rule on beyond confirming that.

## Acceptance criteria

1. **`tcw work stage implement <slug>` prints the falsification rule**, in step
   3 rather than as an additional step, for any item and under both harnesses.
2. **The step list is no longer than it was.** Step 3 is rewritten; no fourth
   bullet is added, and steps 4-9 keep their numbers, so nothing that references
   a step by number goes stale.
3. **`docs/lifecycle/implementation.md` carries the message-assertion rule**, and
   `tcw work stage implement` composes it after the shipped prompt as it already
   composes that file's existing rules.
4. **Every existing prompt guard still passes**, unmodified: the shared-sentence
   check, the router ceiling, the one-documentation-span check, and the
   code-block-hazard check.
5. **The changed capability's body describes the rule**, so the ledger does not
   assert a stage's instructions that the stage no longer gives.
6. **Reproducible from a bare shell**, with no Claude hook and no slash command.

### Coverage

The Design section numbers three things, so criteria are crossed against them.
A cell is a test name, or `n/a` with the line that makes it so.

| # | D1 shipped rule | D2 local rule | D3 the guards |
| - | --------------- | ------------- | ------------- |
| 1 | `test_the_implement_prompt_requires_falsifying_a_green_test` | n/a — D2 is composed by this repo's binding, not by the prompt (`tcw-config.yaml` `stages.implement.prompt`) | n/a |
| 2 | `test_the_implement_step_list_did_not_grow` | n/a | n/a |
| 3 | n/a — D1 is the shipped half | `test_the_implement_stage_composes_the_message_assertion_rule` | n/a |
| 4 | — | — | the four existing guards, run unmodified |
| 5 | n/a — capability body, not the prompt | n/a | n/a — checked by reading, and by `tcw capabilities check` resolving |
| 6 | bare-shell walk | bare-shell walk | bare-shell walk |

**What the table surfaced.** Criterion 4 has no cell of its own under D1 or D2:
it is entirely about D3, and its "test" is that four existing tests keep passing
rather than a new one. Writing that out is what makes it visible that criterion 4
adds no test — which is correct here, and would be a finding anywhere the
existing guards did not already exist.

## Risks

- **A rule about not trusting green, landed via tests that must go red first.**
  The tests for criteria 1-3 assert strings in a prompt; they will pass the moment
  the string is there and fail before. That is genuinely falsifiable, but it is
  worth applying this item's own rule to this item's own tests, out loud, in the
  outcome.
- **The shared-sentence guard is easy to trip.** The new wording must not
  duplicate an eight-word sentence in `stage-implement.md`. This is a
  build-time failure, not a silent one, so the risk is wasted effort rather than
  a bad ship.
- **Wording that describes a disposition instead of an action** would repeat the
  original mistake in new words. "Break the behaviour and confirm it goes red" is
  an action with a result; "be suspicious of green tests" is not, and the second
  is what this will drift into if it is ever shortened for space.

## Notes

- Rejected on the record, so the decision is not re-litigated: **real mutation
  testing** (`mutmut`, `cosmic-ray`) — a dependency and a slow CI job for
  something a thirty-second manual check catches at the moment of writing, when
  the author still has the context to interpret the result; and **a repo test
  that greps test files** for stderr assertions lacking a paired `not in` —
  brittle, and gameable by exactly the person in a hurry that the rule exists for.
- The finding this item exists to fix is that *the instruction was right and
  produced no observation*. Any wording that adds a fifth instruction to a list
  whose third instruction went unfollowed has repeated the mistake rather than
  fixed it.
