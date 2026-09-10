# Plan — Measure lifecycle prompt injection, and evaluate the plugin skills

> **Rewritten 2026-09-10 alongside the spec.** The phase list is reordered
> around the spec's two axes rather than around one test set, and axis A is
> sequenced to be independently shippable.

Six phases. **Axis A — injection fidelity — is the deliverable that must land**;
axis B extends the same instrument to skill lift and can be cut to a follow-up
without leaving anything half-built. Phases 1–2 are independent of each other;
3 needs both; 4 needs 3; 5 needs 4. Phase 6 is independent and can start any
time.

Not a staged-DAG plan: the phases are small and tightly coupled — grading is
written against the same assertions the test set declares — so splitting into
`plan/<id>.md` documents would add indirection without reducing loaded context.

---

## Phase 1 — Fixture seeder, with the customization flag

**Touch:** `evals/seed_fixture.py` (new), `evals/assets/` (new)

Build one throwaway seeded TCW node at a destination path. Follow the pattern in
`tests/test_skill_flow.py::repo()` — `git init`, set `user.email`/`user.name`,
then scaffold. Prefer `tcw.store.fs.init` over shelling out for the scaffold
step, matching that file; use `subprocess` for verbs with no convenient
store-level equivalent.

Seed, in order:

1. Fake product source — `src/reports.py`, `src/billing.py`, `README.md`
   (a small billing/reporting app), committed.
2. `tcw init --id demo-app`.
3. Taxonomy — `Invoice` and `Report` vocabulary; `Report Viewing` feature with
   `--vocab report`.
4. Capabilities — `reports/view` (`Supported`, `Feature=report-viewing`,
   `Subject=report`) and `billing/download-invoice` (`Missing`,
   `Subject=invoice`).
5. Work — a backlog item; plus an active item whose `capabilities.yaml` declares
   `new: [billing/download-invoice]`, with `spec.md`/`plan.md` written, started,
   and its implementation already committed. This primes the completion gate to
   fail closed (B3).
6. `docs/work/inbox/slow-login.md` — an untriaged raw request (B2).
7. A completed item carrying a defect found after the fact (B9).
8. `tcw work tags add bug perf docs cli`.

**Then, under `--customized` only**, the axis A layer:

- Mint one nonce per binding kind. Long enough not to arise by chance, never
  written to any file the agent can read except the binding itself, and recorded
  to `manifest.json` beside the node so grading knows what to look for.
- Write `work.lifecycle.stages` into the node's `tcw-config.yaml` by hand — no
  verb declares bindings — with the spec's mapping: `file` on `spec`, `blob` on
  `plan`, `generate` on `implement`, `skill` on `verify`, `blob: ""` on
  `postmortem`, `builtin: true` alongside each.
- Write the assets each binding names, into the node: the `file` doc, the
  `generate` script, the `skill` the `skill` binding points at. The `generate`
  script must build its requirement from a value it **reads out of the node at
  run time**, so its nonce exists in no committed text and cannot be reproduced
  by an agent that read the repository instead of the prompt.
- `tcw validate` must exit 0 on the customized node, and
  `tcw work stage prompt <stage>` must contain the matching nonce for each of
  the four sighted stages and be byte-empty for `postmortem`. Assert this in the
  seeder itself: a fixture whose bindings do not resolve measures nothing, and
  finding that out during grading wastes a whole run.

Without `--customized` the same seeder produces the control node — one flag, so
the two cannot drift apart.

Determinism: fixed slugs where possible, fixed git identity, no timestamps in
content. Two runs produce identical trees apart from the date-prefixed slugs the
CLI mints and the nonces, which are in the manifest.

**Guard:** add `tests/test_eval_fixture.py` — seed both variants into `tmp_path`
and assert each validates, that the primed states hold (one active item with an
unflipped `Missing` capability, one inbox entry), and that the customized
variant's stage prompts carry their nonces while the control's do not. This is
what stops CLI drift from silently rotting the harness, and the nonce half is
what stops a binding-schema change from rotting axis A specifically.

## Phase 2 — Test set, derived from the shipped surface

**Touch:** `evals/evals.json` (new), `evals/coverage.py` (new)

The spec's eight axis A cases and ten axis B cases. Each entry: `id`, `axis`,
`skill` or `stage`, `prompt`, `arms`, `assertions`.

Coverage is **computed, not declared**: `coverage.py` enumerates `skills/`,
subtracts the skills named by cases and those in an explicit exclusion list
(`tcw-plugin`'s install/repair half), and fails on a non-empty remainder. A
hand-kept table is how the Codex manifest came to undercount its own skills with
no test noticing, and silent partial coverage is the outcome this item exists to
prevent. Wire the same check into pytest so it fails on the day a tenth skill
lands, not on the day someone reruns the harness.

Write axis B prompts the way a real user types — file paths, product nouns from
the fixture, varied formality, at least one casual and one terse. They must be
substantive enough that an agent would genuinely benefit from a skill; one-step
requests won't trigger skills regardless of wording and would measure nothing.

Axis A prompts are the opposite: minimal and identical across arms, naming the
stage and the item and nothing else. Anything extra in the prompt is a second
source for the agent's behavior, and the nonce stops discriminating.

Draft axis B assertions now but treat them as provisional — you don't know what
"good" looks like until the first outputs land. Expect to revise after phase 3.
B6 (`tcw-report`) needs its negative assertion stated positively: *no new item
appears under `docs/work/`*.

## Phase 3 — Harness-neutral runner with Claude and Codex adapters

**Touch:** `evals/run_evals.py` (new)

For each case × harness × arm: seed a fresh fixture at the right variant, invoke
the selected harness with cwd set to the fixture, capture
stdout/transcript/timing, and leave the mutated fixture in place for grading.
Keep fixture creation, result paths, and grading independent of harness-specific
command lines.

**Axis A arms** are the fixture variant: `customized` and `control`. Both hold
the skill. **Axis B arms** are the plugin toggle. The runner takes the arm
definition from the case's `axis`, so nothing has to remember which contrast
applies where.

For Claude, the isolation map is load-bearing — build it by reading the current
`enabledPlugins` from the settings file and forcing every key `false`, then
setting `tcw@tcw` per arm. Deriving it rather than hardcoding means a newly
installed plugin cannot silently leak into future runs.

```
claude -p --settings '{"enabledPlugins": {<every plugin>: false, "tcw@tcw": <arm>}}' \
         --permission-mode acceptEdits --max-turns <N> \
         --output-format stream-json --verbose
```

`--output-format stream-json` gives the transcript and token/duration figures;
persist them as `timing.json` per run. **Transcripts are the primary instrument
for axis A, not a debugging aid** — I1 and I2 are only visible there, and a run
whose transcript was not captured cannot be graded for them.

Assert isolation once at startup rather than trusting it: a probe run in each
axis B arm confirming no foreign plugin skills and no injected SessionStart
directives. Fail loudly if that regresses.

Add the Codex adapter after a probe establishes how to make the TCW skill
available in one arm and unavailable in the baseline while keeping model,
workspace, permissions, and other instructions constant. Codex carries A8 alone
— it is the only harness where the manual fallback is the live path — so an
unsupported Codex adapter is a recorded gap in axis A, not merely a thinner
axis B. Record the exact invocation and known residue beside the Claude probe.
If current Codex cannot provide a clean matched pair, fail that adapter with an
explicit unsupported result rather than reporting Claude-only measurements as
cross-harness evidence.

Both adapters emit the same transcript, timing, token, exit-status, and fixture
location fields. Runner-specific fields live under a namespaced metadata key.

Runs are independent. Default to sequential execution for reproducibility and
resource safety; bounded concurrency may be an opt-in after isolation works.

## Phase 4 — Grade and aggregate

**Touch:** `evals/grade.py` (new), scratchpad `iteration-1/`

Two grader families.

**Transcript reads** (axis A, I1/I2/I6/I7):

- Were both injected blocks present and non-empty, identified by their headings
  rather than by their content, which varies per node.
- Did `tcw work stage gate` run before the artifact was produced.
- Under Codex, were the three fallback commands run by hand.

**Fixture end-state reads** (both axes):

- **Nonce presence** per artifact, per binding kind, against `manifest.json` —
  the axis A core, and the single read that separates I3 from I4.
- Item status via `tcw work list` / `tcw work show`, capability status and
  fields via `tcw capabilities show`, `tcw validate` exit code. Query through
  the CLI rather than walking `docs/work/`, so the harness measures a node
  rather than a directory layout.
- `git log --oneline` ordering — did `start` precede the first code commit; did
  each lifecycle artifact get its own commit; did the agent use
  `tcw work scaffold` rather than hand-writing the artifact.

Write `grading.json` per run using `text` / `passed` / `evidence`. Every pass
carries concrete evidence quoted from the output — a heading with nothing under
it is a fail.

Aggregate to `benchmark.json`: pass rate, time, tokens per arm, plus the delta
and a per-case breakdown. With one run per case there is no meaningful stddev —
report raw counts and say so rather than printing a variance field that means
nothing.

**Mutation-check every assertion before trusting the run.** Break the behavior
each one claims to observe — delete a `|| true`, drop a binding from the
customized node, remove the gate call — confirm the assertion fails, restore.
Record the check. This is stronger than the old rule of dropping assertions that
passed in both arms, and it exists because a parity guard in this repository
passed on a file with the warning it defended deleted. Assertions failing in
both arms are investigated as broken before iteration 2.

## Phase 5 — Review and refine

Present outputs and benchmark for human review before making any edit — the
numbers say *what* failed, the transcripts and your judgment say *why*.

Axis A findings route differently from axis B findings, and the plan should not
blur them:

- A nonce that never arrives is a **defect in the injection layer**, not a prose
  problem. It is fixed in `skills/tcw-work-stage/SKILL.md`, in the resolver, or
  in the binding schema, and it earns a pytest guard rather than a wording
  change.
- A nonce that arrives and is ignored is a **prose problem** in the bookend or
  the router — the agent read it and did not act.
- Axis B findings are skill-wording refinements, under the three standing
  constraints below.

Refine under three constraints:

- **Generalize.** A fix must be justifiable from the skill's purpose, not merely
  from a failing case. Reject anything that only satisfies these prompts.
- **Lean over exhaustive.** If a transcript shows wasted work, the instruction
  causing it is a candidate for deletion, not elaboration. Removing text is a
  legitimate outcome.
- **Explain the why.** Prefer "do X because Y causes Z" over an all-caps MUST;
  these skills already do this well and should stay that way.

Apply unambiguous fixes; surface judgment calls for decision rather than
deciding silently. Run one round of `bllm-review-many` over the proposed diffs
before presenting them, passing the spec as `--context`; apply the clear
improvements, surface the judgment calls, and report anything dismissed with the
reason.

Record in `outcome.md`, per skill and per binding kind, what the evidence
supports — explicitly including anything that showed **no** measurable effect,
and the fact that `tcw-plugin`'s install/repair half is unmeasured by design.
**If axis A reports that customization does not change the artifact, that is the
headline finding and gets stated plainly**, not softened into a refinement list.

## Phase 6 — Documentation sync

Independent of phases 1–5; can start any time. Entries per `tcw work docs`.

- **`docs/changelogs/upcoming.md`** [Any-Code-Change] — Added: the eval harness,
  its fixture guard, and the derived coverage check. Changed: any refinement
  from phase 5. Include the commit hash range.
- **`docs/release-notes/upcoming.md`** [Public-API] — the harness ships in the
  repo, not the wheel, so it earns no note. A **stage-prompt** refinement does
  ship in the wheel and always earns one, and so does any change to how bindings
  resolve if phase 5 produces one.
- **`README.md`** [Public-API] — touch only if a refinement changes documented
  skill behavior or the binding surface.
- **`skills/*/SKILL.md`** and **`tcw/work/prompts/*.md`**
  [Skill-Driven-Component] — the phase 5 refinements themselves. The prompts are
  in the touched set: they carry the methodology the skills used to.
- **`AGENTS.md`** — a short pointer that the skill layer is measured by `evals/`
  and how to re-run it. Without this the harness is undiscoverable and rots.
- Invoke the `documentation-sync` skill before declaring the item complete, per
  repo policy.

---

## Verification

```sh
pytest                                          # incl. fixture guard + coverage check
python evals/seed_fixture.py --customized /tmp/probe
tcw work stage prompt spec <item>               # run in /tmp/probe: nonce present?
tcw validate                                    # this node still sound after doc edits
python evals/run_evals.py --axis a --iteration 1
python evals/run_evals.py --axis b --iteration 1 # long, costs tokens
```

Reviewable evidence at completion: `benchmark.json` with a per-case breakdown,
the graded runs with their transcripts, the mutation-check record, and the
findings report in `outcome.md`.

## Commit sequence

`tcw work start` (first implementation commit) → seeder + guard → nonce layer +
its guard → test set + coverage check → runner → grading/benchmark → axis A
findings and any injection-layer fix (one commit each) → axis B refinements (one
commit per skill touched) → docs.

Results in the scratchpad are never committed; only the instrument and the
conclusions.
