# Refined outcome — A test that passes on its first run must be falsified before it is trusted

**Accepted.** All six criteria hold; 2168 tests pass.

## The decision

The rule ships in `tcw/work/prompts/implement.md`, so it reaches every TCW user
rather than only this repository — which was the point, because the line it
strengthens was already shipping and already believed.

## Evidence

| # | Criterion | How it was checked |
| - | --------- | ------------------ |
| 1 | the stage prints the rule | `test_the_implement_prompt_requires_falsifying_a_green_test`, plus a throwaway node with no configuration at all |
| 2 | the step list did not grow | steps asserted to be exactly 1-9 |
| 3 | the local message rule is composed by the stage | `test_the_implement_stage_composes_the_message_assertion_rule` |
| 4 | every existing prompt guard passes unmodified | six guards, including the two this spec failed to enumerate |
| 5 | the changed capability describes the rule | `work/run-a-lifecycle-stage`; `tcw capabilities check` |
| 6 | reproducible from a bare shell | `git init`, `tcw init`, `tcw work new`, `start`, `stage implement` — no hook, no slash command |

**Task 3 is the evidence that matters.** Four tests, four falsifications, each
observed red for its own reason and only its own. Two of the four passed on their
first run legitimately — they assert state that had to survive the edit — and
under the previous rule that would have gone unexamined.

## What this is not

**Unproven.** It is an instruction, and the instruction previously occupying that
exact position was also correct and still did not fire. The argument for why this
one is different — that it names an action with a visible result rather than a
disposition — is an argument, not evidence. The honest test is whether the next
several items actually run the check, and nothing here guarantees that.

**Not a fix for the whole class.** Three of the five defects that motivated it
were coverage gaps, which falsification does not find. Those belong to the
`### Coverage` table and the no-defaulted-axis rule. Each of the three changes
this initiative produced has a stated limit rather than a claim of completeness:

| Change | Catches | Does not catch |
| ------ | ------- | -------------- |
| `### Coverage` table | criteria that never reach a case | contradictions with code the spec did not describe |
| no defaulted axis in a fixture | the same, at the fixture layer | anything about what is asserted |
| falsification of a green test | assertions that reach the case and check the wrong thing | missing coverage |

**And none of them catches the third finding**, which bit twice more while
landing this item: enumerating a list where one could be read. The spec named
four guards on the shipped prompt; six constrain it, and
`grep -rln 'prompts/implement\|stage_prompts\|prompt_fallback' tests/` returns
eleven files touching that surface. Left unaddressed on purpose — a fourth
process change written in the same session that produced the first three would be
enthusiasm rather than evidence, and this initiative has already demonstrated
what an unproven countermeasure is worth.

## Closeout choices

- **Route.** Direct to `main`, six commits.
- **Documentation.** `docs/release-notes/upcoming.md` and
  `docs/changelogs/upcoming.md`; README does not fire (no CLI surface change) and
  the `tcw-work` skill deliberately does not, because restating the prompt in the
  router is what `test_no_router_sentence_appears_in_its_prompt` exists to refuse.
- **Capabilities.** One changed, `work/run-a-lifecycle-stage`, body edited and
  verified by reading its git history.
- **Version.** Not cut. `v1.2.0` was tagged an hour ago at the epic's closeout;
  this rides in `upcoming.md` to the next release rather than earning a patch
  bump of its own. The change is real but small, and cutting a second version in
  one session for a prompt sentence is the kind of release-noise this repository's
  own history already shows the cost of.

## Deferred

Whether the narrower message-assertion rule belongs upstream alongside the
Coverage table. Both are this repository's local bindings, both came out of the
same initiative, and both should be decided together in
[the upstream item](tcw://W/2026-08-31-upstream-the-acceptance-criteria-coverage-table-to-tcw-s-own-spec-stage)
with evidence from real use rather than from the session that invented them.
