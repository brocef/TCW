# Refined outcome: split `tcw work stage` into `prompt` and `begin`

**Accepted** on 2026-09-10, verified against `f355e02` on
`feat/stage-gate-and-prompt-verbs`.

## The decision

Accepted. The verb this item shipped no longer exists under that name: a later
item on the same branch renamed `begin` to `gate` and narrowed it. That rename is
a deliberate supersession inside one unreleased version, not a regression, so the
criteria below are read against `gate` wherever they name `begin`.

Known defects are left unfixed, deliberately, and recorded in
`docs/work/inbox/2026-09-10-verification-findings-on-the-stage-verb-branch.md`.

## Evidence

| Check | Result |
| --- | --- |
| `tests/test_stage_verb.py` | 46 passed |
| `tcw validate` | exit 0, `validate OK` |
| `tcw capabilities check` | exit 0 |

The paired sentinel evidence the plan argued for is real and was reproduced
outside the suite. In a scratch node whose `plan.pre` runs
`sh -c 'touch sentinel.txt; exit 1'`, the reading verb exits 0 leaving no
sentinel, and the gate exits 1 with the sentinel written and stdout empty. The
two halves do guard each other: without the gate half, the reading half passes
just as well when the gate is broken and never runs at all.

## The hole this item's own outcome admitted is closed

`plan.md` recorded Tasks 3 and 4 as landed in `67edccd` when they had not: that
commit added helpers to `tests/test_stage_verb.py` and never called either, so
the reading verb shipped with zero tests and the sentinel evidence did not exist.
`outcome.md` corrected the record and `a743e9e` closed the hole.

Verified closed. All four areas are covered and green: the reading verb, the
illegal-status notice, node-qualified resolution, and the gate-non-execution
evidence.

## Criteria that do not hold

- **Criterion 6, byte-identical stdout from both verbs — genuinely unmet, by
  design.** The reading verb prints 2958 bytes where the gate prints 0 on the same
  legal stage. Item 4's criteria 1 and 4 require exactly this, and its spec gives
  the reason: identical output is what made every composed view print the
  instructions twice.
- **Criterion 14, `prompt` refusing `--no-exec` — unmet, by design.** It is now
  accepted: exit 0, zero bytes on stdout, plan on stderr. Item 4's spec says in so
  many words that it now accepts the flag, and gives the reason: the original
  refusal existed because suppression would leave incomplete instructions on
  stdout, and under the flag stdout is empty.
- **Criterion 9, byte-identical output against the pre-change binary —
  superseded.** The gate prints nothing, so there are no bytes to compare.
- **Criterion 16, the fixture never re-captured — superseded.** This item honoured
  it: its commit hand-edited the six `argv` arrays and added six lines with
  nothing removed. Item 4 re-captured the whole file, correctly, because the
  bookends move that text on purpose and the frozen bytes would otherwise assert
  something the release makes false. Both events and the rule governing them are
  recorded in the capture script's docstring and in `tests/test_prompt_fallback.py`.
- **Criterion 19, the version cut — deferred.** All five version-bearing files
  read `1.3.1`. The cut follows the completion of all four items.
- **Criterion 20, the changelog — fails at HEAD.** Five lines in
  `docs/changelogs/upcoming.md` still describe the release as containing `begin`.
  Deferred, see below.
- **Criterion 22, both capability descriptions — partial.**
  `run-a-lifecycle-stage` is correct throughout.
  `read-the-documentation-gate-for-a-change` is not: it names the reading verb
  three times and the gate zero times, and one of those three asserts a refusal
  the reading verb cannot perform. Deferred, see below.

## Capability reconciliation

This item's spec declared deltas to `work/run-a-lifecycle-stage` and to the
documentation-gate capability, but the item carries **no `capabilities.yaml`**, so
nothing pointed a reviewer at either file. Two capability descriptions were
changed on this branch and only one was ever declared.

That gap is the substance of the backlog item
`2026-08-21-nothing-enforces-a-spec-s-declared-capability-deltas-without-a-capabilities-yaml`,
and this is a concrete instance of the failure it predicts: the false statement in
the undeclared description survived every review of this branch.

`tcw capabilities check` exits 0, because it checks shape rather than truth.

## Deferred

- The five stale `begin` lines in `docs/changelogs/upcoming.md`. This is the
  changelog for the version about to be cut, so a reader would get a false account
  of the code they installed.
- The false statement in the documentation-gate capability description.

## Closeout

- **Merge route:** merged locally into `main`, no pull request.
- **Version:** 2.0.0 offered separately, after all four items complete.
- **Originating issue:** none.
- **Post-mortem:** the untested-verb hole is a real process finding, but this
  item's own outcome already diagnoses it. Not run.
