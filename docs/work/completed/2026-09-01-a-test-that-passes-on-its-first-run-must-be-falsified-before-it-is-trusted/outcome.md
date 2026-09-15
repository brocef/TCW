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

## What the plan got wrong, second finding

**The spec named four guards on the shipped prompt. There are six.** The two it
missed both fired on the full suite:

- `tests/test_prompt_fallback.py` — a **recorded-bytes tripwire**. It replays
  `tcw work stage` in an unconfigured node and asserts the output is byte-identical
  to a baseline captured before documentation entries could reach a prompt. Its
  docstring settles what to do: *"A prompt rewrite is the one reason to touch
  these bytes; a substitution changing them is the regression, and re-baselining
  to hide that is the thing the file exists to prevent."* This is a prompt
  rewrite, so re-baselining is the documented path — done only after asserting
  every other stage was byte-identical, which is the precedent the docstring
  names from the 2026-08-19 item.
- `tests/test_documented_cli_surface.py` — it parses backticked spans in bound
  lifecycle docs and refuses ones naming a CLI verb that does not exist. The new
  message-assertion rule quoted an *error string* containing `tcw work node`,
  which reads as a verb claim. The guard was right for the general case, so the
  prose was rewritten to name the test rather than inline a string that looks
  like a command.

Missing them is a spec defect of exactly the kind this initiative has been
cataloguing — committed, with some irony, in the spec for the item that fixes
that class. The spec enumerated the guards it knew about and treated the
enumeration as the set.

One command settles it. `grep -rln 'prompts/implement\|stage_prompts\|prompt_fallback' tests/`
returns **eleven** files touching this surface; six of them constrain a change to
the implement prompt's content, and the spec named four. Running that grep costs
a second and would have turned a guessed list into a read one — which is the
whole difference between the two, and is not a new lesson so much as the same one
in a smaller box.

**And re-baselining nearly hid itself.** Regenerating the fixture with
`json.dumps(..., ensure_ascii=False)` re-encoded every entry, producing a
six-line diff of which five were pure re-serialization — precisely the noise the
tripwire exists to prevent, since a real change would sit unnoticed among them.
The fix was to splice the single re-encoded value into the original text, leaving
every other byte alone: **one line changed**. A fixture update whose diff is
larger than the change it records is not an update, it is camouflage.

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

## Suite

**2168 passed**, no failures, no skips, outside the restricted sandbox. Two
failures were found and fixed first — both guards this spec had not enumerated —
and the re-baselined fixture's diff is one line.

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
