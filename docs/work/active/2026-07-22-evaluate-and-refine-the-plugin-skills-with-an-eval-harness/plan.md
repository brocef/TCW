# Plan — Measure lifecycle prompt injection, and evaluate the plugin skills

Fourteen tasks in five groups. **Group A (tasks 1–7) is the deliverable that
must land**: it builds the instrument and answers the injection question. Group
B (8–10) extends the same instrument to skill lift. Group C (11–12) is the
review and refinement pass, D (13) documentation, E (14) the final check.

The suite is green at every task boundary; each task says what proves it. Tasks
1 and 4 are independent and may run in either order; everything else is ordered
as written. Riskiest change first-in-isolation: the nonce layer (task 2) lands
after the seeder exists and carries its own guard before any agent is spawned
against it.

Not a staged-DAG plan. The tasks are small and tightly coupled — grading is
written against the assertions the test set declares — so `plan/<id>.md`
documents would add indirection without reducing loaded context.

---

## Group A — the instrument, and the injection answer

### Task 1 — Fixture seeder, control variant

**Creates:** `evals/seed_fixture.py`, `evals/__init__.py`
**Proves it:** `python evals/seed_fixture.py /tmp/probe && cd /tmp/probe && tcw validate` exits 0.

Build one throwaway seeded TCW node at a destination path, following
`tests/test_skill_flow.py:10` (`repo()`) — `git init`, set `user.email` and
`user.name`, then scaffold. Prefer `tcw.store.fs.init` over shelling out for the
scaffold step, matching that file; use `subprocess` for verbs with no convenient
store-level equivalent.

Seed, in this order:

1. Fake product source — `src/reports.py`, `src/billing.py`, `README.md`, a
   small billing/reporting app, committed.
2. `tcw init --id demo-app`.
3. Taxonomy — `Invoice` and `Report` vocabulary; a `Report Viewing` feature with
   `--vocab report`.
4. Capabilities — `reports/view` (`Supported`, Feature `report-viewing`,
   Subject `report`) and `billing/download-invoice` (`Missing`, Subject
   `invoice`).
5. A backlog item; plus an active item whose `capabilities.yaml` declares
   `new: [billing/download-invoice]`, with `spec.md` and `plan.md` written,
   started, and its implementation committed — this primes the completion gate
   to fail closed for task 9's B3.
6. `docs/work/inbox/slow-login.md`, an untriaged raw request, for B2.
7. A completed item carrying a defect found after the fact, for B9.
8. `tcw work tags add bug perf docs cli`.

Determinism: fixed slugs where the CLI allows, fixed git identity, no timestamps
in content. Two runs produce identical trees apart from the date-prefixed slugs
the CLI mints.

### Task 2 — Nonce layer and the `--customized` variant

**Modifies:** `evals/seed_fixture.py`
**Creates:** `evals/assets/blast-radius.md`, `evals/assets/gen_requirement.py`, `evals/assets/verify-skill/SKILL.md`
**Proves it:** the seeder's own post-condition, asserted before it returns — see below.

Under `--customized` only, add the axis A layer to the same node:

- Mint one nonce per binding kind: 16 hex characters from `secrets.token_hex(8)`,
  written only into the binding that demands it, and recorded to
  `manifest.json` beside the node so grading knows what to look for.
- Write `work.lifecycle.stages` into the node's `tcw-config.yaml` by hand — no
  verb declares bindings — with `builtin: true` first in every stage's list and
  the spec's mapping after it: `file` on `spec`, `blob` on `plan`, `generate` on
  `implement`, `skill` on `verify`, and `prompt: [{blob: ""}]` alone on
  `postmortem`.
- Write the three assets the bindings name. `gen_requirement.py` reads the work
  item JSON on stdin (`tcw/work/projection.py:142`) and derives its nonce from
  the item's own slug plus the run seed, so that nonce exists in no committed
  file.

**Post-condition, asserted inside the seeder before it returns**, because a
fixture whose bindings do not resolve measures nothing and discovering it during
grading wastes a whole run: `tcw validate` exits 0 on the customized node; each
of `spec`, `plan`, `implement`, `verify` has its matching nonce present in
`tcw work stage prompt <stage> <item>`; and `postmortem` produces zero bytes.

### Task 3 — Fixture guard

**Creates:** `tests/test_eval_fixture.py`
**Proves it:** `pytest tests/test_eval_fixture.py` passes; mutation-checked by removing one binding from the customized variant and observing the nonce assertion fail.

Seed both variants into `tmp_path` and assert: each validates; the primed states
hold (one active item with an unflipped `Missing` capability, one inbox entry);
the customized variant's stage prompts carry their nonces; and the control's do
not. This is what stops CLI drift from rotting the harness, and the nonce half is
what stops a binding-schema change from rotting axis A specifically.

### Task 4 — Test set and the derived coverage gate

**Creates:** `evals/evals.json`, `evals/coverage.py`
**Modifies:** `tests/test_eval_fixture.py` (adds the coverage assertion)
**Proves it:** `pytest -k coverage` passes; mutation-checked by adding a tenth empty directory under `skills/` and observing it fail.

`evals.json` holds the spec's eight axis A cases and ten axis B cases. Each
entry: `id`, `axis`, `skill` or `stage`, `prompt`, `arms`, `assertions`.

`coverage.py` enumerates `skills/`, subtracts the skills named by cases and
those in an explicit exclusion list (`tcw-plugin`'s install/repair half, with
its reason inline), and fails on a non-empty remainder. Wire it into pytest so
it fails on the day a tenth skill lands, not on the day someone reruns the
harness.

Axis A prompts are minimal and identical across arms, naming the stage and the
item and nothing else: anything extra is a second source for the agent's
behavior and the nonce stops discriminating. Axis B prompts are the opposite —
written the way a real user types, with file paths and product nouns from the
fixture, at least one casual and one terse, and substantive enough that an agent
would genuinely benefit from a skill.

Axis B assertions are provisional here and revised after task 8; axis A
assertions are not, because the nonce fixes what "pass" means in advance.

### Task 5 — Runner, Claude adapter

**Creates:** `evals/run_evals.py`
**Proves it:** `python evals/run_evals.py --axis a --case A6 --dry-run` prints the two arms' full command lines and the fixture paths without spawning anything; the isolation probe below passes.

For each case × arm: seed a fresh fixture at the right variant, invoke the
harness with cwd set to the fixture, capture stdout, transcript and timing, and
leave the mutated fixture for grading.

**Axis A arms are the fixture variant** (`customized`, `control`); both hold the
skill. **Axis B arms are the plugin toggle.** The runner reads which contrast
applies from the case's `axis`, so nothing has to remember.

Build the Claude isolation map by reading `enabledPlugins` from the settings
file and forcing every key `false`, then setting `tcw@tcw` per arm — derived,
not hardcoded, so a newly installed plugin cannot leak into future runs.

```
claude -p --settings '{"enabledPlugins": {<every plugin>: false, "tcw@tcw": <arm>}}' \
         --permission-mode acceptEdits --max-turns 30 \
         --output-format stream-json --verbose
```

`--max-turns` is 30 for axis A, whose cases produce one artifact, and 60 for
axis B, whose cases walk several lifecycle stages. A case that hits the cap is
recorded as capped rather than failed: the two are different findings and
conflating them would read a budget limit as a skill defect.

Persist the stream as `transcript.jsonl` and the token and duration figures as
`timing.json`. Transcripts are the primary instrument for axis A, not a
debugging aid: I1 and I2 are visible nowhere else, and a run whose transcript
was not captured cannot be graded for them.

Assert isolation at startup rather than trusting it: a probe run in each axis B
arm confirming no foreign plugin skills and no injected `SessionStart`
directives. Fail loudly if it regresses. Runs are sequential by default for
reproducibility.

### Task 6 — Grader, transcript and fixture reads

**Creates:** `evals/grade.py`
**Proves it:** graded against a hand-built run directory committed as `tests/fixtures/eval_grading/` — one passing and one failing example per assertion family; `pytest tests/test_eval_grading.py` passes.
**Also creates:** `tests/test_eval_grading.py`, `tests/fixtures/eval_grading/`

Two grader families.

**Transcript reads** — were both injected blocks present and non-empty,
identified by their headings (`## How to work it`, `## What this project asks
for`) rather than by content, which varies per node; did `tcw work stage gate`
run before the artifact was written; under Codex, were the three fallback
commands run by hand.

**Fixture end-state reads** — nonce presence per artifact per binding kind
against `manifest.json`; item status via `tcw work list` and `tcw work show`;
capability status and fields via `tcw capabilities show`; `tcw validate` exit
code; `git log --oneline` ordering for whether `start` preceded the first code
commit, whether each lifecycle artifact got its own commit, and whether
`tcw work scaffold` was used rather than hand-writing.

Query through the CLI rather than walking `docs/work/`, so the harness measures
a node rather than a directory layout. Write `grading.json` per run with `text`,
`passed` and `evidence`; every pass carries evidence quoted from the output, and
a heading with nothing under it is a fail.

### Task 7 — Run axis A, mutation-check, and record the verdict

**Creates:** scratchpad `iteration-1/` (never committed), and `outcome.md` gains its axis A section at the `implement` stage
**Proves it:** `benchmark.json` exists with a per-case breakdown for A1–A8, and every assertion carries a recorded mutation check.

Before trusting the run, **mutation-check every assertion**: delete a `|| true`
from `skills/tcw-work-stage/SKILL.md:20`, drop one binding from the customized
node, remove the gate call from a transcript fixture — confirm each assertion
fails, then restore. Record the check. An assertion that has never failed has
not been shown to measure anything, which is how the parity guard at
`tests/test_skill_lifecycle_parity.py:323` came to pass on a file with the
warning it defended deleted.

Then run axis A and read the result against the four verdicts the spec fixes in
advance, under the harness-compatibility rule. Assertions failing in both arms
are investigated as broken before anything is concluded from them.

---

## Group B — skill lift

### Task 8 — Codex adapter, or an explicit unsupported result

**Modifies:** `evals/run_evals.py`
**Proves it:** either the isolation probe passes under Codex and A8 grades, or `benchmark.json` carries `{"harness": "codex", "supported": false, "reason": "…"}` and the reason names what could not be held constant.

Probe how to make the TCW skill available in one arm and unavailable in the
baseline while holding model, workspace, permissions and other instructions
constant. Record the exact invocation and known residue beside the Claude probe.

Codex carries I7 alone — it is the only harness where the manual fallback is the
live path — so an unsupported adapter is a recorded gap in axis A, not merely a
thinner axis B. If a clean matched pair cannot be established, fail the adapter
explicitly rather than reporting Claude-only measurements as cross-harness
evidence. Both adapters emit the same transcript, timing, token, exit-status and
fixture-location fields; runner-specific fields live under a namespaced key.

### Task 9 — Revise axis B assertions against first outputs

**Modifies:** `evals/evals.json`
**Proves it:** every revised assertion carries a one-line note saying which first-run output motivated the revision.

Run axis B once, read the outputs, and revise. You do not know what "good" looks
like until the first outputs land, which is why task 4 wrote these provisionally.
B6 (`tcw-report`) needs its negative assertion stated positively: *no new item
appears under `docs/work/`*.

### Task 10 — Run axis B and aggregate

**Creates:** scratchpad `iteration-1/` axis B runs
**Proves it:** `benchmark.json` reports pass rate, time and tokens per arm with the delta and a per-case breakdown for B1–B10.

With one run per case there is no meaningful stddev — report raw counts and say
so rather than printing a variance field that means nothing.

---

## Group C — review and refine

### Task 11 — Present for review before editing anything

**Creates:** nothing
**Proves it:** the user has seen the benchmark and transcripts and said which findings to act on.

The numbers say *what* failed; the transcripts and judgment say *why*. No skill
or prompt edit is made before this.

### Task 12 — Apply refinements, one commit per file touched

**Modifies:** whichever of `skills/*/SKILL.md`, `tcw/work/prompts/*.md`, `tcw/work/resolve.py`, `tcw/store/base.py` the findings justify
**Proves it:** `pytest` green after each commit; every injection-layer fix carries a new pytest guard, mutation-checked.

Findings route by kind, and the plan keeps them apart:

- **A nonce that never arrives is a defect in the injection layer**, not a prose
  problem. It is fixed in `skills/tcw-work-stage/SKILL.md`, in the resolver, or
  in the binding schema, and it earns a pytest guard rather than a wording
  change.
- **A nonce that arrives and is ignored is a prose problem** in the bookend
  (`tcw/work/resolve.py:386`) or the routers — the agent read it and did not act.
- **Axis B findings are skill-wording refinements.**

Three standing constraints on any refinement: it must be justifiable from the
skill's purpose rather than merely from a failing case; deletion is a legitimate
outcome where a transcript shows wasted work; and prefer "do X because Y causes
Z" over an all-caps MUST. Run one round of `bllm-review-many` over the proposed
diffs with the spec as `--context` before presenting them, apply the clear
improvements, surface the judgment calls, and report anything dismissed with the
reason.

---

## Group D — Documentation Sync

### Task 13 — Answer every fired trigger in one pass

Evaluated at this stage against `tcw work docs` (source: `config`, so the
entries are authoritative). One entry fires for certain; three depend on what
group C finds, which is genuinely exploratory, so they get a re-evaluation gate
rather than a guessed-at file list.

**Fires now:**

- **`docs/changelogs/upcoming.md` [Any-Code-Change]** — the harness, the fixture
  guard and the derived coverage gate are behavior-affecting code. Grouped
  Added/Changed, with the commit hash range.

**Re-evaluate after task 12, because they fire only if a refinement lands:**

- **`docs/release-notes/upcoming.md` [Public-API]** — the harness ships in the
  repo, not the wheel, so it earns no note. A **stage-prompt** refinement does
  ship in the wheel and always earns one, and so does any change to how a
  binding resolves.
- **`README.md` [Public-API]** — touch only if a refinement changes the public
  CLI surface or documented user-facing behavior. The harness itself is
  contributor tooling and does not belong here.
- **`skills/<component>/SKILL.md` [Skill-Driven-Component]** — fires for every
  skill task 12 edits, and for `tcw-work-stage` specifically if the injection
  layer is what moved.

**Not a documentation entry, but still required:** a short pointer in
`AGENTS.md` naming `evals/` as how the skill layer is measured and how to re-run
it. It is not covered by the doc-sync gate, so it is stated here as its own
deliverable — without it the harness is undiscoverable and rots.

Invoke the `documentation-sync` skill once more at the end of `implement`, over
the finished diff, per repo policy.

---

## Group E — final check

### Task 14 — Full verification pass

**Proves it:** the Verification section below, run end to end.

---

## Verification

What the suite checks, and what it cannot.

**The suite checks** the fixture still seeds and validates, the nonces resolve in
the customized variant and not in the control, the coverage gate catches an
uncovered skill, and the grader returns the right verdicts on the committed
example run directories.

```sh
pytest                                              # incl. tasks 3, 4, 6 guards
python evals/seed_fixture.py --customized /tmp/probe
tcw validate                                        # this node, after doc edits
```

**The suite cannot check** any of the following, so each is verified by hand and
the result recorded in `outcome.md`:

1. **That the injected blocks actually render in a live agent's context.** No
   pytest assertion can observe another process's context window. Verified by
   reading `transcript.jsonl` for case A6 in both arms.
2. **That the isolation map really suppressed the foreign plugins.** Verified by
   the startup probe's own output, read by a human once per run, because a
   silently-merged settings file would make every axis B number wrong in the
   same direction.
3. **That each assertion bites.** Verified by the mutation checks in task 7, one
   per assertion, recorded with what was broken and which assertion failed.
4. **That a refinement generalizes rather than fitting these prompts.** Verified
   by review at task 11 against the skill's stated purpose, not by any test.
5. **Codex behavior**, if the adapter is unsupported. Recorded as an explicit
   gap rather than inferred from Claude.

Baseline for "green": `pytest` on this checkout currently reports 2446 passed,
4 failed, 9 skipped, and all four failures are environmental — a wheel-build
test and three that simulate permission failures a root user cannot be subject
to. Green means no regression against that baseline, not an absolute count.

## Self-review — criteria to tasks

Every acceptance criterion is covered by at least one task, and every task
traces back to a criterion.

| Criterion | Covered by |
| --------- | ---------- |
| 1 — harness runnable, invocation in `AGENTS.md` | 1, 5, 13 |
| 2 — per-kind nonce reported in both arms | 2, 6, 7 |
| 3 — per-case render check for both blocks | 5, 6, 7 |
| 4 — `benchmark.json` with per-arm deltas | 6, 10 |
| 5 — axis B arms verified isolated | 5 |
| 6 — harness fails on an uncovered skill | 4 |
| 7 — every assertion mutation-checked | 3, 4, 7 |
| 8 — findings report per skill and per binding kind | 7, 10, 12 |
| 9 — unambiguous fixes applied, judgment calls surfaced | 11, 12 |
| 10 — `pytest` green against the baseline | 3, 4, 6, 12, 14 |

Task 8 traces to criterion 8 by way of I7: the Codex result, supported or not,
is part of what the findings report must state. Task 9 traces to criterion 4,
whose per-case breakdown is meaningless if the assertions behind it were never
revised against real output.

## Commit sequence

`tcw work start` → seeder (1) → nonce layer (2) → fixture guard (3) → test set
and coverage gate (4) → runner (5) → grader and its fixtures (6) → axis A
findings and any injection-layer fix, one commit each (7, 12) → Codex adapter
(8) → axis B assertion revisions (9) → axis B refinements, one commit per skill
touched (12) → docs (13).

Results in the scratchpad are never committed; only the instrument and the
conclusions.
