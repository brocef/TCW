# Outcome

- `request` is legal for an `active` item as well as a `backlog` one, as
  `spec` and `plan` have been since 2.6.3.
- `tcw work start` now warns about a missing `initial-request.md` while there
  is no spec, and sends the item to the `request` stage first in that case.
- A stage refused for the item's status adds one line after the unchanged
  refusal, saying how to go on:
  - `rework` from review;
  - `start` from backlog;
  - `submit` for a postmortem on an active item;
  - writing the request directly in review;
  - "no stage runs on it" for a resolved item;
  - in every open case, `stage prompt`, offered for reading only.

## What shipped, task by task

| Task | What | Commit |
| ---- | ---- | ------ |
| 1 | failing tests | `08d07177` |
| 2 | legality, `start_next_stage`, `_unwritten_planning`, `start:request` | `285eea7f` |
| 3 | `_illegal_stage_hint` | `285eea7f` |
| 4 | skill, guide, capability descriptions, #74's amendment rule, changelog, release notes | `a72a5020` |
| 5 | review fixes, README stage table, guide's next-step paragraph | `ea537b59` |

## What the plan and spec got wrong

- **"Follow the skill's order" would have sent implemented work back for its
  request.** Read literally, "Finding your place" names `request` for any item
  without `initial-request.md`, even one with a spec, plan and outcome, and that
  is exactly the shape of work written up after it started. The request now
  counts as missing only while the spec is too, in `start_next_stage`, the
  warning, and the skill's own line. The spec's goal 3 records it.
- **The `start:request` next-step key was missing from the plan.** The first
  hand run crashed with `KeyError: 'start:request'`. Added to
  `TRANSITION_NEXT_STEPS` and `TRANSITION_LANDS_IN`, and the table's
  completeness test was updated.
- **Plan task 2's fixture re-baseline, and criterion 6's "`tcw work lifecycle`
  shows it", were impossible as written.** `tcw work lifecycle` prints no stage
  legality, and the lifecycle baseline fixture holds none. The criterion is
  proved by a direct assertion on `STAGE_STATUSES` instead.
- **Goal 4 offered `stage prompt` as an equal way on.** For `implement` on a
  backlog item, that skips everything `start` checks. It is now offered "to
  read, without entering the stage".

## Review

The adversarial review returned "merge after the fixes below". Accepted:

1. `tests/test_work.py`'s next-step assertion for an unplanned item was passing
   on the new warning's text, not on the next step. It now asserts the
   `→ next:` line exactly.
2. The guide's paragraph on what `start` points at, and the README's stage
   table (stale for `spec` and `plan` since 2.6.3), were updated.
3. #74's changelog entry says "past backlog". This change's entry says it
   supersedes that, since another change's entry file is never edited.
4. `request` refused in review advised `rework`, contradicting the amendment
   rule. It now says to write `initial-request.md` directly. `rework` advice on
   accepted work names `refined-outcome.md` as what must go first.
5. Postmortem on an active item names `submit`, and the prompt alternative is
   framed for reading. The reviewer offered this as a design question; I took
   it.
6. Test gaps: the warning with a spec present, a completed item's "except
   `postmortem`", postmortem on an active item, and request in review.

Not taken:

- Folding the "request only while spec is missing" rule into one shared
  helper. It lives in two places, the store's `start_next_stage` and the CLI's
  warning, which cross-reference each other. A shared helper would add an
  import from the CLI into the store's rule for a two-line condition.

## Checks

- The new file, plus `tests/test_transition_hints.py`,
  `tests/test_stage_verb.py` and the next-step test in `tests/test_work.py`,
  pass.
- `tcw validate` and `tcw capabilities check` pass.
- Full suite: see `refined-outcome.md`.

## Autonomous decisions

- **Legal in active, or only a better refusal?** No advisors. Settled by the
  accepted precedent `994727fb`, which made `spec` and `plan` legal in `active`
  for the same reason. The issue's follow-up comment asked `start` to refuse;
  the precedent chose a warning, and so does this.
- **Request only while the spec is missing** (above): my own call, recorded in
  the spec.
- **Review finding 5, a design question:** adopted.
- **Rejected:** the shared-helper suggestion (above).
