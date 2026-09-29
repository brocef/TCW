# Refined outcome

**Accepted.** The user accepted the work on 2026-09-29.

## The decision

Every transition that prints a next step now names the real one. `new` and
`inbox accept` point at the request stage; `start` at the first stage the item
still needs, never at `tcw work complete`; `submit` at verify and `rework` at
implement, each also printing the item's new folder; and `complete --confirm`
prints the Definition of Done ticked, only once the item has closed. That covers
GitHub #68, #67 and point 1 of #58.

## Evidence

Checked in this session, against the branch's code, after the last code change
(`24f870dd`).

| # | Criterion | Result |
| - | --------- | ------ |
| 1 | `new` points at the request gate | run by hand: `→ next: run \`tcw work stage gate request 2026-09-29-thing\`` |
| 2 | `inbox accept` of a raw entry, same | `test_inbox_accept_points_at_the_request_stage` passes; no CLI verb adds a raw entry by hand |
| 3 | An epic, same | run by hand: `→ next: run \`tcw work stage gate request 2026-09-29-e\`` |
| 4 | `start` names the first stage still needed | run by hand for `spec`; the `plan`/`implement`/re-start/`--worktree`/qualified cases by `tests/test_transition_hints.py`, passing |
| 5 | `submit` names `review/<slug>` and the verify gate, no "delete" | run by hand, and on this item itself |
| 6 | `rework` names `active/<slug>`, `rework.md` and the implement gate | run by hand |
| 7 | `complete --confirm` prints the list ticked, then `completed` | run by hand: four `[x]` lines under the heading, no `[ ]` |
| 8 | `--already-integrated` refusal prints no checklist | run by hand: exit 1, no checklist |
| 9 | Without `--confirm`, unchanged | run by hand: unticked list, `Refused: …`, exit 1 |
| 10 | Transition-hint guard tests | `tests/test_stage_verb.py` and `tests/test_transition_hints.py`: 78 passed |
| 11 | Stale-wording search | finds nothing |
| 12 | Full suite, bare `pytest` | 4905 passed, 9 skipped, 4 failed — see below |

The four failures (`tests/test_check_versions.py`, three cases: an abandoned
process outlives the check; `tests/test_shipped_prompts.py::test_the_prompts_are_in_the_built_wheel`:
the wheel build fails with the container's system build tools) belong to the
Claude Code cloud container the suite ran in, not to this item: the same four
fail on untouched `origin/main` there, and none touches code this item changed.
Before the review fix, on the implementing machine, the suite was fully green
(4914 passed, 3 skipped).

`tcw validate`, `tcw capabilities check` and `tcw capabilities drift` all report
OK.

## Definition of Done

- **tests pass** — as above: everything this item touches passes; the four
  failures reproduce on `main` in the same container.
- **docs synced** — the `documentation-sync` skill was run over the finished
  diff; the guide, skills, capability descriptions, changelog and release notes
  were updated in Task 6, and the changelog again for the review fix.
- **capabilities reconciled** — eight capabilities under `changed:` in
  `capabilities.yaml`; check and drift OK.
- **reviewed** — an adversarial spec review, an adversarial code review (verdict:
  merge, with notes), and the user's acceptance.
- **originating GitHub issue answered and closed** — **deferred, deliberately.**
  GitHub #58, #67 and #68 stay open until a version carrying this fix is
  published, per this repo's `CLAUDE.md`: closing them sooner would tell the
  reporters it is fixed when they still cannot install it. Nothing is posted to
  an issue without the user approving the exact text. No version was cut.

## Follow-ups

- The child-relative folder printed for a qualified reference is recorded on
  `2026-09-29-make-a-stale-item-path-fail-loudly-complete-checks-for-the-verify-artifact-validate-finds-a-slug-under-two-statuses-and`.
- `start_next_stage` answering `verify` for an active item that already holds
  `refined-outcome.md` is a known, harmless difference, kept as is (see
  `outcome.md`).
