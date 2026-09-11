# Outcome — Measure lifecycle prompt injection, and evaluate the plugin skills

**This pass built the instrument. It did not run it.** Tasks 1–6 and 13 landed;
tasks 7–12 and 14's live half are deferred by decision, not by blockage. The
injection question is not answered here — the thing that can answer it exists,
is guarded, and has been mutation-checked.

## What shipped

| Task | Commit | What |
| ---- | ------ | ---- |
| — | `11ca4dd7` | Plan revised against seventeen multi-review findings |
| 1 | `1dd67879` | `evals/seed_fixture.py` — the fixture node, control variant |
| 2 | `5d90b749` | Nonce layer, `--customized`, and the two assets |
| 3 | `43597dbd` | `tests/test_eval_fixture.py` — 22 assertions over both variants |
| 4 | `6f426422` | `evals/evals.json`, `evals/coverage.py`, and the coverage guard |
| — | `b34e59c0` | Documentation entries in the fixture, so B10 has a trigger to fire |
| 5 | `1c8399ce` | `evals/run_evals.py` and its 20 tests |
| 6 | `e57a59db` | `evals/grade.py`, 14 tests, four example run directories |
| — | `0e9acaae` | Untrack generated grading output |
| 13 | `8800f839` | Changelog entry and the `AGENTS.md` pointer |

Sixty-four new tests across four modules, plus the committed example runs.

## Test result

```
2593 passed in 1190.65s
```

No failures, no skips, against a measured baseline of **2529 passed** on this
checkout at `b831afd9`. Green here means 2593; see below for why the plan's
recorded baseline was wrong.

`tcw validate` exits 0. `python evals/coverage.py` reports 14 shipped skills,
all covered, exit 0.

## What the plan or spec got wrong

Seventeen findings came out of the multi review before any code was written, and
the plan was rewritten against them first (`11ca4dd7`, whose Revision record
carries all seventeen with how each was checked). Six of those would have made
the harness measure the wrong thing:

- **A `skill` binding cannot carry a nonce.** It resolves to `Invoke the <name>
  skill.` and never reads the body — which need not exist. Probe-confirmed
  against a binding naming a skill that was never created.
- **A `generate` hook receives an envelope, and `item` is `null` without a work
  item reference.** The plan cited the projection function, which produces only
  the inner value.
- **`skills/` holds 14 directories, not 9.**
- **The treatment arm would have loaded the marketplace clone**, a different
  commit with auto-update on.
- **The isolation map needs the union of two settings files**, nine keys.
- **The recorded pytest baseline was wrong in both directions.**

Four more things the *plan as revised* still got wrong, discovered while
building it. These are this document's own findings, not the review's:

1. **The determinism claim was still too strong.** Two control runs are not
   byte-identical. Four things vary, and the two nobody had named are a randomly
   minted capability id and the `started` timestamp. None is read by grading,
   which queries through the CLI rather than diffing trees. Recorded in the
   seeder's docstring.
2. **Lifecycle bindings cannot be appended to the node config.** `tcw work tags
   add` has already written a `work:` key, and a second one makes the whole file
   fail to parse with `duplicate key: 'work'`. Both config writes now go through
   one merge helper.
3. **The fixture declared no documentation entries, so B10 had nothing to fire
   on.** `tcw work docs` reports that plainly rather than failing, so the case
   would have graded against an empty trigger set and read as a skill that
   touched no documentation when there was none to touch. Found by the subagent
   that built task 4, verified, and fixed in `b34e59c0`.
4. **The grader read the gate invocation as a manual fallback.** The fenced
   fallback does name `tcw work stage gate`, but the gate prints a legality
   result and never the instructions, so it cannot be where a nonce came from.
   Including it marked every well-behaved run as fallback-sourced — because
   running the gate first is exactly the behaviour case A7 exists to reward. The
   committed example fixtures caught this on their first run.

One change to the test set beyond the plan: **A5 invokes the generic composing
skill rather than `tcw-post-mortem`.** I5 asks what an agent does with a stage
that asks nothing, and the router it would fall back on is the composing skill's
first block, so the composer has to be in play. `tcw-post-mortem` stays covered
by B9.

## The probe, and what it settled

Two one-turn invocations, `$0.31` total, run before task 1.

| | treatment | baseline |
| --- | --- | --- |
| `plugins` | one entry, path = this checkout, `version: 2.0.2` | `[]` |
| foreign plugin skills | none | none |
| `SessionStart` hook | fires, exit 0, stdout empty | fires, exit 0, stdout empty |

**Acceptance criterion 5 is met**, not deferred. The marketplace clone loaded in
neither arm. Residue is identical in both and therefore constant: twenty
built-in and user-level skills, the user's global instructions file, and
`memory_paths.auto` — the last of which the spec does not name and should.

The probe also produced the real stream format, so task 6's example
transcripts are built against a capture rather than a guess.

## Mutation checks, recorded

Every assertion family was broken before it was trusted, and each red was read
for *why* rather than *that*.

| Broken | What went red |
| ------ | ------------- |
| Drop the `file` binding | The seeder's own post-condition, naming the defect |
| Drop it, and disable that post-condition | Exactly one test, the right one |
| Un-silence `postmortem` | The silence assertion, on the byte count |
| Strip the documentation entries | The new docs guard, on empty output |
| Bare directory under `skills/` | *Nothing* — which is why the plan's original mutation was wrong |
| Directory with a `SKILL.md` | The coverage gate, naming the skill |
| An undeclared predicate | The vocabulary guard, naming it |
| Axis B swaps the fixture | The fixture-constant test |
| Read one settings file | The union test *and* the checkout test |
| Fold capped runs into the denominator | Both accounting tests |
| Give the baseline arm the plugin | The toggle test |
| Ignore provenance | The fallback test |
| Absent nonce → injected | The unknown-provenance test |
| Drop the ordering requirement | The ordering test |
| Evidence-free verdict passes | The evidence test |
| Restore the gate to the fallback list | Both injected-provenance tests |

**The first round of grader mutations found a gap in my own tests.** Treating an
absent nonce as injected changed nothing, because the test I thought covered it
was exercising an early return rather than the function being mutated. Two direct
provenance tests were added and both now bite. Watching a test go red is not
enough; this is what reading the reason buys.

The unguarded `generate` script deserves its own line, because it is the sharpest
evidence in the pass:

```
unguarded (as the plan first described it):  0 bytes, exit 1
hardened:                                 3259 bytes
```

Zero bytes is indistinguishable from the failure mode the whole harness exists
to detect. One bad fixture script would have produced the wrong verdict on the
item's primary question.

## What is deliberately not claimed

- **Nothing about whether injection actually reaches an agent.** No graded run
  happened. Criteria 2, 3, 4 and 8 are unmet by design.
- **Nothing about `skill` bindings** beyond that they resolve to a pointer. A
  named gap; nothing in the tree binds `skill` today.
- **Nothing about tool provenance.** Commit history cannot tell a hand-written
  artifact from a scaffolded one. Ordering survives and is all the grader claims,
  so the plan's hand-edit assertions were dropped.
- **No causal claim for the bookend.** Both arms carry it, so it is not the
  variable. A7 says the gate ran, and nothing more.
- **Seven axis B assertions cannot be expressed mechanically** and carry an
  explicit marker with the reason. They are counted as neither pass nor fail.
- **Criterion 7 is partial.** Every assertion *written in this pass* is
  mutation-checked. The assertions in `evals.json` that only a live run can
  exercise are not, and cannot be until task 7.

## Late findings, after the tasks were committed

The subagent that built task 4 reported ten findings on the plan, arriving after
its code had landed. Six were already handled. Four were not, and one was a real
defect:

1. **A `git_order` pattern that could never match.** B1 asserted a commit
   matching `start` precedes the first code commit. TCW writes
   `tcw work: <slug> → active`, and the bare verb appears nowhere in it, so the
   assertion would have failed every run regardless of what the agent did — and
   read as a skill defect. Fixed in `1c64d0ad`, with a guard.

   **The guard took two attempts, and the first was worse than useless.** It
   checked only patterns that already looked like a transition commit, which
   filtered out exactly the broken shape it existed to catch: reverting B1 to
   `start` left it green. It now also requires a bare lifecycle verb to match the
   log, which it cannot, so the mistake fails loudly. This is the second time
   this pass that a guard passed on the thing it was written for, and both times
   the mutation check is what found it.

2. **B7 is narrowed, deliberately.** The fixture has no GitHub remote and the
   harness has no network, so the skill's `gh` plumbing is unreachable. Its four
   issues are supplied inline, two actionable and two not. It measures triage
   judgement, not the plumbing. Recorded on the case.

3. **A5's two stage-prompt checks are not duplicates of the fixture guard**,
   though they look like it. The guard reads a freshly seeded node; A5 reads the
   node *after the agent has worked it*, under `acceptEdits`, where the agent
   could have edited `tcw-config.yaml`. They confirm the stage was still silent
   for that run, which is the only form of the claim grading can make. Both
   predicates keep their only user rather than being dropped.

4. **Two predicates expand task 6's stated families, and that is now explicit.**
   `transcript_contains` and `transcript_absent` are not among the three
   transcript reads the plan enumerates. Confirmed rather than inherited
   silently: the machinery is identical, and A4 cannot be stated without them now
   that the skill binding carries no nonce. A general *ordering* read would be
   the same kind of step and is deliberately still not taken, which is why B8
   stays unmechanized even though it is close to reachable.

## Notes

### Criteria status

| # | Status |
| - | ------ |
| 1 — harness runnable, invocation in `AGENTS.md` | met |
| 2 — per-kind nonce reported in both arms | instrument only |
| 3 — per-case render check | instrument only |
| 4 — `benchmark.json` with deltas | not met, deferred |
| 5 — arms verified isolated | **met by probe** |
| 6 — fails on an uncovered skill | met |
| 7 — every assertion mutation-checked | partial, see above |
| 8 — findings report | not met, deferred |
| 9 — refinements applied | not met, deferred |
| 10 — `pytest` green | met, 2593 passed |

### Spec edit needed at `verify`

Criterion 2 says "for every prompt binding kind", and `skill` cannot carry a
nonce. Three kinds are fingerprinted; `skill` is a pointer-level observation and
`builtin` is the floor. The spec should be narrowed to match rather than left
reading as a criterion that could be met.

### B8 is closer to mechanical than it is marked

The subagent flagged this rather than burying it, and it is right. `grade.py`
already implements one transcript ordering read. A general one is the same
machinery, and B8's cross-axis ordering would become mechanical. It was left
marked because inventing a predicate the grader had not committed to implement
is the exact failure the assertion vocabulary exists to prevent. If task 6 gains
a general ordering read, the marker should be replaced.

### Deferred, and why

Tasks 7–12 spawn 13 graded runs across two arms at 30–60 turns each. That is
real money and the user chose to land the instrument first and decide on the
runs separately. Nothing about tasks 1–6 depends on them, and deferring cost
nothing except the answer itself.
