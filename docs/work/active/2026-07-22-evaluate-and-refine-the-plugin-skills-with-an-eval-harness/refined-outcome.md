# Refined outcome — Measure lifecycle prompt injection, and evaluate the plugin skills

**Accepted**, as the instrument only. The user approved closeout on 2026-09-11
after reviewing the assessment, and chose a patch bump and a single follow-up
item.

## The decision, and what it covers

The harness, its guards and the documentation are accepted. The graded runs are
not part of this acceptance, because they did not happen.

```
2593 passed
```

Against a measured baseline of 2529 on this checkout: 64 new tests, no
regression, no skips. `tcw validate` exits 0. `python evals/coverage.py` reports
14 shipped skills, all covered, exit 0.

## Capability ledger, reconciled at closeout

**No delta, exactly as the spec predicted.** No `capabilities.yaml` sidecar, and
the two entries the spec named as in the blast radius both stay `Supported`:

| Capability | Status |
| ---------- | ------ |
| `work/run-a-lifecycle-stage` (`cap-f42255`) | Supported, unchanged |
| `work/configure-the-work-lifecycle` (`cap-b9711e`) | Supported, unchanged |

The spec's closeout condition was that a refinement changing *what* a skill
instructs an agent to do would need a body edit. No refinement landed, and
`git diff` confirms nothing under `tcw/`, `skills/`, `commands/` or `agents/`
moved. The harness is contributor tooling and earns no ledger entry of its own.

## Acceptance criteria, honestly

| # | Status |
| - | ------ |
| 1 — harness runnable, invocation in `AGENTS.md` | met |
| 2 — per-kind nonce reported in both arms | **not met, and unmeetable as written** |
| 3 — per-case render check | not met, instrument only |
| 4 — `benchmark.json` with deltas | not met |
| 5 — arms verified isolated | met, by probe |
| 6 — fails on an uncovered skill | met |
| 7 — every assertion mutation-checked | partial |
| 8 — findings report | not met |
| 9 — refinements applied | not met — see below |
| 10 — `pytest` green | met |

Five of ten unmet. **That is the deliberate shape of this pass, not a shortfall
discovered at verification.** The user chose to land the instrument and decide on
the runs separately, and the deferred half is now tracked.

**Criterion 2 is a spec defect, not merely unmet.** It says "for every prompt
binding kind", and a `skill` binding cannot carry a nonce: the resolver returns a
pointer and never reads the named skill's body. No run could satisfy it as
written. The spec is left unedited as a record of what was promised; the
correction lives in the follow-up item's request, where it will be acted on.

## Why no refinements were applied

The user asked, at closeout, for the refinements to be done and folded into this
version. They were not, and this is the one place this document disagrees with a
request rather than recording a decision.

Task 12 routes every refinement by a finding from a graded run. The plan says in
its own words that a missing nonce does not uniquely implicate the injection
layer and a delivered-but-ignored nonce does not uniquely implicate prose, so the
routing is *a hypothesis to test, not a diagnosis to act on*. With no run, there
is no finding, and any skill edit made now would be justified by nothing but
expectation — which is the failure the review spent seventeen findings guarding
against.

What this pass genuinely produced instead were **corrections**, and all of them
are landed:

- Four spec errors, verified, recorded in the follow-up item's request so the
  next pass starts from truth: criterion 2's unmeetability, the `generate`
  nonce's guessability from inside the fixture, A5's vacuity, and the absent
  cross-arm contrast on A6 and A7.
- One genuine defect in the injection layer, filed as
  `docs/work/inbox/skill-binding-names-are-never-validated.md`: a `skill` binding
  naming something that exists nowhere validates clean and still tells the agent
  to invoke it. Reproduced on a scratch node, with the transcript in the note.
  Filed rather than fixed because this item's spec lists `tcw` command-surface
  and store changes as a non-goal.

If the intent was to fix that defect in this version, it is a `tcw/` change and
therefore a different item by this spec's own boundary. Say so and it gets one.

## Deferred, and where it went

- `2026-09-11-run-the-eval-harness-and-act-on-what-it-finds` — tasks 7 through
  12: the mutation checks only a live run can exercise, both axes, the Codex
  adapter, the findings report, and refinements the evidence justifies. Carries
  the four spec corrections.
- `docs/work/inbox/skill-binding-names-are-never-validated.md` — the unvalidated
  `skill` binding.

## Closeout choices

- **Route:** committed directly to `main`. No branch and no pull request; the
  item was worked in the primary checkout.
- **Documentation:** evaluated against the finished diff, source `config`. Only
  `docs/changelogs/upcoming.md` [Any-Code-Change] fired, logged under Internal.
  `README.md` and `docs/release-notes/upcoming.md` did not, because nothing here
  ships in the wheel. `skills/<component>/SKILL.md` did not, because no component
  these skills drive changed. `AGENTS.md` gained the harness pointer, which the
  plan named as its own deliverable outside the doc-sync gate.
- **Version:** patch, 2.0.3. Nothing user-facing changed; the whole diff is
  contributor tooling, tests and documentation. `v2.0.2` is published, so folding
  was not available.
- **Post-mortem:** not offered. Verification surfaced no unforeseen problem — the
  review and the build surfaced plenty, and all of it is recorded in `plan.md`'s
  revision record and `outcome.md`.

## Notes

Two things worth carrying forward, both about method rather than this item.

**A guard passed on the thing it was written for, twice.** Once when a grader
mutation changed nothing because the test covering it exercised an early return,
and once when a commit-pattern guard filtered out precisely the broken shape it
existed to catch. Both were found by mutation checks, and neither would have been
found by reading the test. The rule that earns its place here is not "mutate
every assertion" but "read *why* it went red" — a mutation that changes nothing
is the signal.

**The multi review paid for itself before a line was written.** Six of its
seventeen findings would have made the harness measure the wrong thing, and three
of those were only settled by a `$0.31` probe. Reviewing the plan rather than the
code is what made them cheap.
