# Plan — Evaluate and refine the plugin skills with an eval harness

Five phases. Phases 1–2 are independent and can run in parallel; 3 needs both;
4 needs 3; 5 needs 4. Phase 6 (docs) is independent and can start any time.

Not a staged-DAG plan: the phases are small and tightly coupled (grading is
written against the same assertions the test set declares), so splitting into
`plan/<id>.md` documents would add indirection without reducing loaded context.

---

## Phase 1 — Fixture seeder

**Touch:** `evals/seed_fixture.py` (new)

Build one throwaway seeded TCW node at a destination path. Follow the pattern in
`tests/test_skill_flow.py::repo()` — `git init`, set `user.email`/`user.name`,
then scaffold. Prefer `tcw.store.fs.init` over shelling out for the scaffold
step, matching that file; use `subprocess` for the `tcw` verbs that have no
convenient store-level equivalent.

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
   fail closed (eval 3).
6. `docs/work/inbox/slow-login.md` — an untriaged raw request (eval 2).
7. `tcw work tags add bug perf docs cli`.

Determinism matters: fixed slugs where possible, fixed git identity, no
timestamps in content. Two runs of the seeder must produce identical trees apart
from the date-prefixed slugs the CLI mints.

**Guard:** add `tests/test_eval_fixture.py` — seed into `tmp_path`, assert the
node validates (`tcw validate` exits 0) and that the primed states hold (one
active item with an unflipped `Missing` capability, one inbox entry). This is
what stops CLI drift from silently rotting the harness; it reuses the existing
`tmp_path`-git-repo idiom, so it is cheap.

## Phase 2 — Test set

**Touch:** `evals/evals.json` (new)

Seven cases per the spec table. Each entry: `id`, `skill`, `prompt`,
`expected_output`, `assertions`.

Write prompts the way a real user types — file paths, product nouns from the
fixture, varied formality, at least one casual and one terse. They must be
substantive enough that an agent would genuinely benefit from consulting a
skill; one-step requests won't trigger skills regardless of wording and would
measure nothing.

Draft assertions now but treat them as provisional — the methodology is explicit
that you don't know what "good" looks like until the first outputs land. Expect
to revise them after phase 3 and before grading.

Case 6 (`tcw-report`) needs its negative assertion stated positively: *no new
item appears under `docs/work/`*. That is the failure mode worth catching.

## Phase 3 — Runner

**Touch:** `evals/run_evals.py` (new)

For each eval × arm: seed a fresh fixture, invoke `claude -p` with cwd set to
the fixture, capture stdout/transcript/timing, leave the mutated fixture in
place for grading.

The isolation map is the load-bearing detail — build it by reading the current
`enabledPlugins` from `~/.claude/settings.json` and forcing every key `false`,
then setting `tcw@tcw` per arm. Deriving it rather than hardcoding means a newly
installed plugin can't silently leak into future runs.

```
claude -p --settings '{"enabledPlugins": {<every plugin>: false, "tcw@tcw": <arm>}}' \
         --permission-mode acceptEdits --max-turns <N> \
         --output-format stream-json --verbose
```

`--output-format stream-json` gives the transcript and token/duration figures;
persist them as `timing.json` per run. Transcripts are not optional — the
methodology treats them as a primary signal for *why* something failed, and
phase 5 depends on reading them.

Assert isolation once at startup rather than trusting it: a probe run in each
arm confirming no foreign plugin skills and no injected SessionStart directives.
Fail loudly if that ever regresses.

Runs are independent — parallelize across evals, but cap concurrency so 14
concurrent agents don't thrash the machine or trip rate limits.

## Phase 4 — Grade and aggregate

**Touch:** `evals/grade.py` (new), scratchpad `iteration-1/`

Grade mechanically off each fixture's end state:

- item status/location (`tcw work list`, folder membership)
- `git log --oneline` ordering — did `start` precede the first code commit; did
  each lifecycle artifact get its own commit
- capability status and fields (`tcw capabilities show`)
- `tcw validate` exit code
- absence of hand-edits where a command existed (inspect diffs under `docs/`)

Write `grading.json` per run using the field names `text` / `passed` /
`evidence`. Every PASS carries concrete evidence quoted from the output — a
section heading with nothing under it is a FAIL.

Aggregate to `benchmark.json`: pass rate, time, tokens per arm, plus the delta
and a per-eval breakdown. With one run per eval there is no meaningful stddev —
report raw counts and say so rather than printing a variance field that means
nothing.

Then the analyst pass: drop assertions that pass in both arms (they inflate the
with-skill rate without reflecting skill value), and investigate any failing in
both before trusting them.

## Phase 5 — Review and refine

Present outputs and benchmark for human review before making any skill edit —
the numbers say *what* failed, the transcripts and your judgment say *why*.

Then refine, under three standing constraints:

- **Generalize.** A fix must be justifiable from the skill's purpose, not merely
  from a failing case. Reject anything that only satisfies these seven prompts.
- **Lean over exhaustive.** If a transcript shows wasted work, the instruction
  causing it is a candidate for deletion, not elaboration. Removing text is a
  legitimate outcome.
- **Explain the why.** Prefer "do X because Y causes Z" over an all-caps MUST;
  these skills already do this well and should stay that way.

Apply unambiguous fixes; surface judgment calls for decision rather than
deciding silently. Per `~/.claude/CLAUDE.md`, run one round of
`bllm-review-many` over the proposed skill diffs before presenting them, passing
the spec as `--context`; apply the clear improvements, surface the judgment
calls, and report anything dismissed with the reason.

Record in `outcome.md`, per skill, what the evidence supports — explicitly
including any skill that showed **no** measurable lift, and the fact that
`tcw-plugin`'s install/repair half is unmeasured by design.

## Phase 6 — Documentation sync

Independent of phases 1–5; can run any time.

- **`README.md`** [Public-API] — list all eight commands in the install section
  (add `/tcw-audit-work-backlog`, `/tcw-consolidate-plans`). While there, confirm
  whether `tcw-audit-work-backlog` lacking `disable-model-invocation: true` is
  intentional; if not, that is a separate one-line fix worth raising.
- **`docs/changelogs/upcoming.md`** [Any-Code-Change] — Added: the eval harness
  and its fixture guard. Changed: any skill refinements. Include the commit hash
  range.
- **`docs/release-notes/upcoming.md`** [Public-API] — only if a refinement
  changes user-visible skill behavior. A harness that ships in the repo but not
  in the wheel is not a user-facing change; say nothing rather than pad.
- **`skills/*/SKILL.md`** [Skill-Driven-Component] — the phase 5 refinements
  themselves.
- **`AGENTS.md`** — a short pointer that the skill layer is measured by `evals/`
  and how to re-run it. Without this the harness is undiscoverable and rots.
- Invoke `skill-cefailures:documentation-sync` before declaring the item
  complete, per repo policy.

---

## Verification

```sh
pytest                                   # incl. the new fixture guard
python evals/seed_fixture.py /tmp/probe  # seeder standalone
tcw validate                             # this node still sound after doc edits
python evals/run_evals.py --iteration 1  # full harness (long, costs tokens)
```

Reviewable evidence at completion: `benchmark.json` with a per-eval breakdown,
the graded runs, and the findings report in `outcome.md`.

## Commit sequence

`tcw work start` (first implementation commit) → seeder + guard → test set →
runner → grading/benchmark → refinements (one commit per skill touched) → docs.

Results in the scratchpad are never committed; only the instrument and the
conclusions.
