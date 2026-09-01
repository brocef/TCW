# Outcome — A test that passes on its first run must be falsified before it is trusted

All five planned tasks landed. `tcw work stage implement` now tells an author
what to do about a green test, and it says it in the shipped prompt, so it
reaches every TCW user rather than only this repository.

## What shipped

| Task | Commit | What |
| ---- | ------ | ---- |
| 1, 2, 3 | `9e1f74c` | the three tests, red first; step 3 rewritten; all three falsified |
| 4 | *(with the docs commit)* | the message-assertion rule in `docs/lifecycle/implementation.md`, and its test |
| 5 | *(docs commit)* | capability body, changelog, release notes |

## The rule, as shipped

`tcw/work/prompts/implement.md`, step 3 — rewritten, not appended to:

> 3. **Write the failing test first and watch it fail** before the code that
>    makes it pass. A test that has never been red proves nothing. When a new
>    test passes on its first run, break the behaviour it names and confirm it
>    goes red before writing anything else — the explanation for an unearned
>    green is usually true and beside the point.

The final clause is doing the real work. The author in the epic *was* suspicious
of the greens, wrote down why each was fine, and was locally right every time.
"Be suspicious" was never the missing ingredient; an action with a visible result
was.

## Acceptance criteria

| # | Criterion | Evidence |
| - | --------- | -------- |
| 1 | the stage prints the falsification rule | `test_the_implement_prompt_requires_falsifying_a_green_test`; and by hand from a throwaway node with no configuration at all |
| 2 | the step list did not grow | `test_the_implement_step_list_did_not_grow` — asserts the steps are exactly 1-9 |
| 3 | `implementation.md` carries the message rule and the stage composes it | `test_the_implement_stage_composes_the_message_assertion_rule`; `tcw work stage implement` prints it |
| 4 | every existing prompt guard still passes, unmodified | shared-sentence, router ceiling, one-documentation-span, code-block hazard — 114 green with no test rewritten |
| 5 | the changed capability describes the rule | `work/run-a-lifecycle-stage` body; `tcw capabilities check` |
| 6 | reproducible from a bare shell | the walk below |

### Verified by hand

A throwaway git repository, `tcw init --id rulecheck work`, one item, `start`,
then `tcw work stage implement`. The rule printed in a node that configures
nothing — no bindings, no hook, no slash command — which is the layer it had to
be in for a Codex user to get it.

## Task 3, which is the point

The item's own rule, applied to the item, because a rule whose shipping change
did not itself follow it would be the most eloquent possible argument against it.

Four tests, four falsifications, each observed red for its own reason and only
its own:

| Test | Broken by | Result |
| ---- | --------- | ------ |
| requires-falsifying-a-green-test | deleting the new sentence | red |
| step-list-did-not-grow | appending a tenth step | red |
| original-rule-survives-the-rewrite | deleting "never been red proves nothing" | red |
| composes-the-message-assertion-rule | mangling the phrase in `implementation.md` | red |

Two of those four passed on their **first** run — deliberately, because they
describe state that had to survive the edit. Under the old rule that would have
been fine and unexamined. Under the new one they were falsified, and are now
known to test what their names say rather than assumed to.

## What the plan got wrong

Very little, and worth recording that this item was smaller than the ones before
it — a short plan for a small change turned out to be accurate, which is not the
usual finding in this initiative.

One thing: the plan said task 1's tests might need "a new module if the parity
file's fixtures do not fit; decide at implementation". They did not fit — the
parity module's fixtures are all parametrized over stage ids, and these tests are
about one stage's content — so `tests/test_falsification_rule.py` is new. The
plan was right to leave that open rather than guess.

## What this does not fix, stated so it is not over-relied on

Three of the five defects that motivated this were **coverage** gaps — a fixture
that never reached the case. Falsification does not find those: break the
behaviour, and the tests that *do* reach it go red as expected while the
unreached cell stays unreached. Those are the `### Coverage` table's job, and the
no-defaulted-axis rule's.

The two families, and where each is answered:

| Defect family | Countermeasure | Where |
| ------------- | -------------- | ----- |
| the test never reaches the case it names | Coverage table; no defaulted axis in a shared fixture | `templates/spec.md`, `implementation.md` |
| the test reaches it and asserts the wrong thing | falsification; assert the replaced message is absent | shipped prompt, `implementation.md` |

## Notes

- The finding behind this item is that **the instruction was right and produced
  no observation**. That is why the fix rewrote an existing step rather than
  adding one: a list whose third entry went unfollowed is not repaired by gaining
  a tenth entry, and a fix shaped like the original mistake would have been the
  mistake.
- Whether the narrower message-assertion rule belongs upstream too is left open
  deliberately. It is one repository's idiom so far, and the sibling item about
  upstreaming the Coverage table is the right place to decide both together, with
  evidence rather than enthusiasm.
