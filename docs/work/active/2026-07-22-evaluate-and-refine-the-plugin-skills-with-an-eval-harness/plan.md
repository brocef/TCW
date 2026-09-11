# Plan — Measure lifecycle prompt injection, and evaluate the plugin skills

> **Revised 2026-09-10, during `implement`, before task 1.** A multi review of
> the first draft (adversarial agent, Codex, and the local model) produced
> seventeen findings, and a live probe settled three of them by measurement
> rather than argument. Every correction is recorded in **Revision record** at
> the end, with what was believed, what is true, and how it was checked. The
> task numbering is unchanged so the spec's criteria table still lines up.

Fourteen tasks in five groups. **Group A (tasks 1–7) is the deliverable that
must land**: it builds the instrument and answers the injection question. Group
B (8–10) extends the same instrument to skill lift. Group C (11–12) is the
review and refinement pass, D (13) documentation, E (14) the final check.

**This pass builds tasks 1–6 only.** Tasks 7–10 spawn graded agent runs and are
deferred to a later pass by decision, not by blockage. Task 5's isolation probe
is **already done** — see task 5 — so it is not a deferred cost.

The suite is green at every task boundary; each task says what proves it. Tasks
1 and 4 are independent and may run in either order; everything else is ordered
as written. Riskiest change first-in-isolation: the nonce layer (task 2) lands
after the seeder exists and carries its own guard before any agent is spawned
against it.

Not a staged-DAG plan. The tasks are small and tightly coupled — grading is
written against the assertions the test set declares — so `plan/<id>.md`
documents would add indirection without reducing loaded context.

## Baseline for "green"

Measured on this checkout at `b831afd9`, as an unprivileged user:

```
2529 passed in 592.21s
```

No failures, no skips. The first draft recorded 2446 passed / 4 failed / 9
skipped and described the four as environmental failures a root user cannot be
subject to. **That baseline came from a different environment and is wrong
here** — all four named tests pass locally. Re-capture the baseline before the
first commit of any later pass rather than trusting a number written down in a
previous one.

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
   `new: [billing/download-invoice]`, with `spec.md` **and `plan.md` and
   `outcome.md`** written, started, and its implementation committed — this
   primes the completion gate to fail closed for task 9's B3.
6. `docs/work/inbox/slow-login.md`, an untriaged raw request, for B2.
7. A completed item carrying a defect found after the fact, for B9.
8. `tcw work tags add bug perf docs cli`.

**`outcome.md` on the active item is new in this revision.** `STAGE_STATUSES`
(`tcw/store/base.py`) restricts `verify` to `active` and `review`, and the
verify case has to read an implementation outcome that exists. Without it, case
A4 verifies an item with nothing to verify.

**The case-to-item mapping is part of this task's contract**, not left implicit.
Stage legality is:

| Stage | Legal statuses | Fixture item the axis A case uses |
| ----- | -------------- | --------------------------------- |
| `spec` | `backlog` | the backlog item |
| `plan` | `backlog` | the backlog item |
| `implement` | `active` | the active item |
| `verify` | `active`, `review` | the active item (now carrying `outcome.md`) |
| `postmortem` | `review`, `completed` | the completed item |

Note that `tcw work stage prompt` itself does **not** refuse an illegal stage —
it prints a note to stderr and the instructions anyway. `tcw work stage gate` is
what refuses, and the agent cannot produce the artifact without passing it. The
mapping above is therefore about the artifact, not the prompt.

Determinism: fixed slugs where the CLI allows, fixed git identity, no timestamps
in content. Two runs produce identical trees apart from the date-prefixed slugs
the CLI mints. Under `--customized` the nonces differ too, by construction;
they are recorded to `manifest.json` rather than made stable.

### Task 2 — Nonce layer and the `--customized` variant

**Modifies:** `evals/seed_fixture.py`
**Creates:** `evals/assets/blast-radius.md`, `evals/assets/gen_requirement.py`
**Proves it:** the seeder's own post-condition, asserted before it returns — see below.

Under `--customized` only, add the axis A layer to the same node:

- Mint one nonce per **fingerprinted** binding kind: 16 hex characters from
  `secrets.token_hex(8)`, written only into the binding that demands it, and
  recorded to `manifest.json` **written at the node root, beside
  `tcw-config.yaml`**, so grading knows what to look for and knows where to find
  it.
- Write `work.lifecycle.stages` into the node's `tcw-config.yaml` by hand — no
  verb declares bindings — with `builtin: true` first in every stage's list and
  the mapping below after it.
- Write the two assets the bindings name.

**The fingerprinted set is three kinds, not four.** `skill` is dropped from it:

| Kind | Bound to | Fingerprint |
| ---- | -------- | ----------- |
| `file` | `spec` | a node-relative doc requiring a `## Blast radius (<nonce>)` heading |
| `blob` | `plan` | inline text requiring the phase list to end with the nonce line |
| `generate` | `implement` | a script emitting a requirement derived from the work item it receives on stdin |
| `skill` | `verify` | **no nonce** — see below |
| `builtin` | every stage | present in all arms; the floor, not a fingerprint |
| `blob: ""` | `postmortem` | the silence case |

**Why `skill` carries no nonce.** `_resolve_one` (`tcw/work/resolve.py:193`)
resolves a `skill` binding to the literal string `Invoke the <name> skill.` and
nothing else. The skill's body is never read, and nothing validates that the
named skill exists — confirmed by probe against a binding naming a skill that
was never created. A nonce written into a fixture `SKILL.md` therefore cannot
appear in `tcw work stage prompt verify <item>`, and a `SKILL.md` sitting in a
throwaway fixture node is not a registered skill under any harness, so the agent
could not reach it either. The binding still gets declared, and case A4 becomes
a transcript-level reading (see task 4). **Recorded gap:** this pass makes no
claim about whether an agent acts on a resolved `skill` binding's pointer beyond
whether it tries. Nothing in the tree binds `skill` today.

**The `generate` script's input contract, corrected.** The first draft said the
script "reads the work item JSON on stdin" and cited `work_item_json`
(`tcw/work/projection.py:142`). That function produces only the **inner** value.
What the script actually receives is the envelope built by `hook_payload`
(`tcw/work/resolve.py:149`):

```json
{"item": {"slug": "...", "...": "..."}, "hook": {"role": "...", "kind": "generate", "...": "..."}}
```

Three consequences the script must honor, all probe-confirmed:

- Read `payload["item"]["slug"]`, not `payload["slug"]`.
- **`payload["item"]` is `null`** when the verb is called without a work item
  reference, which every per-stage skill documents and the parser accepts. The
  script needs a guard, not just the corrected key path.
- **A raise is not a missing section, it is a total render failure.**
  `_resolve_one` converts a `GenerateError` into a `ResolveError`, and the CLI
  prints to stderr and exits 1 with **no stdout at all**. Under the composing
  skill's `|| true` that is silent, so one bad script turns the whole
  `implement` stage into a false reading of failure mode I1 — the exact mode
  this item exists to detect. The script is therefore dependency-free, pins its
  interpreter rather than relying on a bare `python`, and **prints a degraded
  marker line instead of raising** on any unexpected input.

**What the computed nonce does and does not prove.** `run_generate` executes the
script with `shell=True` and `cwd=node_root` (`tcw/work/generate.py:108`), so
the script lives inside the node and an agent holding Read can simply open it.
The first draft called this "the one fingerprint an agent cannot produce by
reading the repository instead of the prompt". The claim that survives is
narrower and still worth having: **the nonce is in no committed TCW file**, so
it cannot come from repository knowledge or from training. The real confound is
the manual fallback (task 6), not an adversarial agent.

**Post-condition, asserted inside the seeder before it returns**, because a
fixture whose bindings do not resolve measures nothing and discovering it during
grading wastes a whole run:

- `tcw validate` exits 0 on the customized node.
- `spec`, `plan` and `implement` each have their matching nonce present in
  `tcw work stage prompt <stage> <item>`.
- `verify` contains the literal `Invoke the ` pointer line. **Not a nonce** —
  this is the corrected form of the assertion the first draft got wrong.
- `postmortem` produces **zero bytes**, while the same stage on the control node
  produces the bookended builtin floor.

### Task 3 — Fixture guard

**Creates:** `tests/test_eval_fixture.py`
**Proves it:** `pytest tests/test_eval_fixture.py` passes; mutation-checked by removing one binding from the customized variant and observing the nonce assertion fail.

Seed both variants into `tmp_path` and assert: each validates; the primed states
hold (one active item with an unflipped `Missing` capability and an `outcome.md`,
one inbox entry, one completed item); the customized variant's stage prompts
carry their nonces; and the control's do not. This is what stops CLI drift from
rotting the harness, and the nonce half is what stops a binding-schema change
from rotting axis A specifically.

Add the silence assertion as a **byte-level** check in both variants, since that
is the only form of it that is not vacuous:

```
customized postmortem → 0 bytes
control    postmortem → non-empty, bookended
```

Measured on a probe node at this revision: 0 bytes and 2401 bytes respectively.
Assert the shape, not the 2401, which moves whenever a builtin prompt is edited.

### Task 4 — Test set and the derived coverage gate

**Creates:** `evals/evals.json`, `evals/coverage.py`
**Modifies:** `tests/test_eval_fixture.py` (adds the coverage assertion)
**Proves it:** `pytest -k coverage` passes; mutation-checked by adding a directory under `skills/` **containing a minimal `SKILL.md`** and observing it fail.

`evals.json` holds the axis A cases and the ten axis B cases. Each entry: `id`,
`axis`, `skill` or `stage`, `prompt`, `arms`, `assertions`.

**Every assertion names a predicate from a declared vocabulary**, so assertions
are data and the grader is finite. The first draft left axis B assertions as
free prose, and several of them — orientation quality, "offer a reply for every
issue", ordering across three axes, "the right entries touched, no others" —
are not expressible in the two grader families task 6 defines. Declaring the
vocabulary is what surfaces that mismatch at authoring time instead of at
grading time.

**The coverage gate enumerates `skills/*/SKILL.md`**, matching the predicate
every guard in `tests/test_plugin_manifests.py` already uses (`:106`, `:130`).
A bare directory trips nothing, which is why the mutation above adds a file.

**Fourteen skills exist, not nine.** Five `tcw-work-stage-*` skills were added
after this item was specced. Coverage is claimed as follows:

| Skill | Covered by | Note |
| ----- | ---------- | ---- |
| `tcw-work-stage-spec` | A1 | the case invokes the per-stage skill |
| `tcw-work-stage-plan` | A2 | ditto |
| `tcw-work-stage-implement` | A3 | ditto |
| `tcw-work-stage-verify` | A4 | ditto |
| `tcw-work-stage` | A6, A7 | the generic composer |
| `tcw-work-stage-request` | **excluded** | `request` is the one stage whose job is asking the user questions, which a non-interactive harness cannot do. Its own file says so. There is no axis A `request` case. |
| `tcw-plugin` install/repair half | **excluded** | simulating a broken `tcw` install inside a subagent's environment is unsafe and would measure the simulation. B5 covers its orientation half. |
| the other eight | B1–B10 | as the spec's table |

**Which skill a case invokes is now fixed, not left to the prompt's phrasing.**
A1–A4 invoke the per-stage skill for their stage; A6 and A7 invoke the generic
one. Same case count, same run count, and four exclusions become real coverage.
`postmortem` has a case and no per-stage skill by design —
`tests/test_skill_lifecycle_parity.py:326` derives the per-stage set as the
stages minus `{inbox, postmortem}`.

**Axis A cases, revised.** Three of the eight no longer run two arms, because
the contrast is zero by construction and printing it invites someone to read
meaning into it.

| # | Stage | Arms | What it measures |
| - | ----- | ---- | ---------------- |
| A1 | `spec` | both | `file` nonce reaches the artifact (I2, I3, I4) |
| A2 | `plan` | both | `blob` nonce reaches the artifact (I4) |
| A3 | `implement` | both | `generate` nonce, computed (I4) |
| A4 | `verify` | both | the transcript shows the agent acted on the `Invoke the <name> skill.` pointer. The control has no such line; the treatment does. **Not a nonce check.** |
| A5 | `postmortem` | both | treatment resolves to zero bytes, control to the bookended floor; and **none of the other nonces appear** in the postmortem artifact (I5) |
| A6 | `spec` | **one** | both injected blocks present and non-empty (I1, I2) |
| A7 | `spec` | **one** | `tcw work stage gate` ran before the artifact (I6) |
| A8 | `spec`, Codex | **one** | the manual fallback commands were run by hand (I7) |

Thirteen runs instead of sixteen.

**Why A6 and A7 are single-arm.** `bookend` is applied whenever the resolved
text is non-empty (`tcw/work/cli.py:1054`), so it wraps the builtin floor in the
control exactly as it wraps bound text in the treatment. Both injected blocks
render in both arms and the gate reminder is present in both. These are absolute
readings, not deltas. **The stage is named `spec`, not "any"** — picking
`postmortem` would make block two empty in the treatment by design and read as
failure mode I2 for a reason that is not a defect.

**Why A1–A3 still run two arms.** Not because the control discriminates: a
16-character random nonce cannot appear in the control, so the control adds
nothing to the nonce assertion itself. What it buys is a **baseline artifact**,
which is how "the nonce is absent and the artifact is otherwise well-formed"
gets told apart from "the run fell over". That distinction is the finding this
item exists to produce. It is a qualitative baseline, not a discriminator, and
the results must say so.

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
**Creates:** `tests/test_eval_runner.py`
**Proves it:** `python evals/run_evals.py --axis a --case A6 --dry-run` prints the two arms' full command lines and the fixture paths without spawning anything; `pytest tests/test_eval_runner.py` passes. **The isolation probe is already done — see below.**

For each case × arm: seed a fresh fixture at the right variant, invoke the
harness with cwd set to the fixture, capture stdout, transcript and timing, and
leave the mutated fixture for grading.

**Axis A arms are the fixture variant** (`customized`, `control`); both hold the
skill. **Axis B arms are the plugin toggle.** The runner reads which contrast
applies from the case's `axis`, so nothing has to remember.

**Load the plugin from this checkout, not from the marketplace clone.** The
first draft's invocation set `"tcw@tcw": true`, which loads
`~/.claude/plugins/marketplaces/tcw` — a *different commit* from the working
tree, with `autoUpdate: true`, so the arm could shift underneath a sequential
run and no task-12 refinement would be visible until pushed. Probe-confirmed
fix: pass `--plugin-dir <repo root>` and leave `tcw@tcw` false in the map.

```
claude -p --plugin-dir <repo root> --settings <all-false map> \
         --permission-mode acceptEdits --max-turns 30 \
         --output-format stream-json --verbose
```

**Build the all-false map from every settings file, not "the settings file".**
Plugin enablement is split: seven keys in `~/.claude/settings.json`, two more in
`<repo>/.claude/settings.json`. Nine total at this revision. Reading only the
user file leaks one plugin into both arms; reading only the project file leaks
seven, **including the two the spec names as the contaminants the whole
isolation design exists to suppress**. Derive the union, force every key false,
and let `--plugin-dir` supply the treatment.

`--max-turns` is 30 for axis A, whose cases produce one artifact, and 60 for
axis B, whose cases walk several lifecycle stages. **A case that hits the cap is
recorded as `"capped": true` on its per-case entry in `benchmark.json`, and
capped cases are excluded from the pass-rate denominator and counted separately
in a `capped` field.** The first draft said capped was "recorded rather than
failed" and never said what reads it; a budget limit silently folded into a pass
rate reads as a skill defect.

Persist the stream as `transcript.jsonl` and the token and duration figures as
`timing.json`. Transcripts are the primary instrument for axis A, not a
debugging aid: I1 and I2 are visible nowhere else, and a run whose transcript
was not captured cannot be graded for them.

**Isolation is asserted mechanically from the `init` event, not by asking a
model.** The `system`/`init` event carries `plugins` and `skills` as structured
fields. Assert that `plugins` names exactly the checkout in the treatment arm
and is empty in the baseline, and fail the run loudly otherwise. Also record
`plugins[0].version` into `benchmark.json` so a later reader knows which code
was measured. Runs are sequential by default for reproducibility.

#### Isolation probe — run 2026-09-10, result recorded here

Two one-turn invocations, `$0.31` total. **Acceptance criterion 5 is met by this
probe**, and it is not a deferred cost.

| | treatment (`--plugin-dir` + all-false) | baseline (all-false only) |
| --- | --- | --- |
| `plugins` | one entry, `source: tcw@inline`, path = the passed directory, `version: 2.0.2` | `[]` |
| skills visible | 36 | 20 |
| foreign plugin skills | none | none |
| `SessionStart` hook | fires, exit 0, **stdout empty** | fires, exit 0, **stdout empty** |

The marketplace clone was loaded in neither arm. The two directive-injecting
plugins named in the spec injected nothing. **Residue, identical in both arms
and therefore constants rather than confounds:** twenty built-in and user-level
skills, the user's global instructions file, and the auto-memory path
(`memory_paths.auto`) — the last of which the spec does not name and should.

**The stream format is captured**, in
`<scratchpad>/probe2/arm{A,B}.jsonl`. A one-turn run emits ten events in a fixed
order: two `system`/hook events, `system`/`init`, `rate_limit_event`, three
`system`/`thinking_tokens`, the `assistant` messages, then `result` carrying
`duration_ms`, `total_cost_usd` and `num_turns`. Task 6 builds its fixtures
against this capture rather than against a guess.

**The runner gets a test**, which the first draft omitted. It parses
`evals.json`, spawns subprocesses and aggregates timing; if it silently drops a
transcript, every axis A reading is wrong in the same direction. Cover the
`evals.json` parse, the arm/variant selection from `axis`, the all-false map
construction from two settings files, and the capped-versus-failed accounting.

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
against `manifest.json` at the node root; item status via `tcw work list` and
`tcw work show`; capability status and fields via `tcw capabilities show`;
`tcw validate` exit code; `git log --oneline` ordering for whether `start`
preceded the first code commit and whether each lifecycle artifact got its own
commit.

**Every nonce assertion is reported as injected or fallback-sourced.** This is
the largest correction in this revision. Every composing skill, generic and
per-stage, ends with a fenced fallback telling the reader to run
`tcw work stage prompt <stage> <item>` by hand when a block looks empty. **An
agent that follows it produces the nonce with the injection layer having done
nothing.** Reading nonce presence and block presence as independent assertions
means a run where injection failed and the fallback rescued it grades
identically to one where injection worked — which would produce exactly the
wrong verdict, on the item's primary question. So for each nonce, record whether
the transcript shows a manual invocation of the prompt command **before** the
nonce first appears, and report the nonce accordingly. A nonce whose provenance
cannot be established is reported as `unknown`, never as a pass.

**Two claims the first draft made that the grader cannot support**, stated here
so nobody reads them into the results:

- **`git log --oneline` cannot establish tool provenance.** Identical commits
  result from compliant and non-compliant histories, so "no hand-edits where a
  command existed" and "`tcw work scaffold` was used rather than hand-writing"
  are dropped as assertions. What survives is commit *ordering*, which the log
  does show.
- **A7 cannot attribute gate compliance to the bookend.** Both arms carry the
  bookend, so it is not the variable. A7 observes that the gate ran, and that is
  all it may be reported as.

Query through the CLI rather than walking `docs/work/`, so the harness measures
a node rather than a directory layout. Write `grading.json` per run with `text`,
`passed`, `evidence` and, for nonce assertions, `provenance`; every pass carries
evidence quoted from the output, and a heading with nothing under it is a fail.

### Task 7 — Run axis A, mutation-check, and record the verdict

**Deferred to a later pass.** Tasks 1–6 land first; this is a decision about
sequencing cost, not a blockage.

**Creates:** scratchpad `iteration-1/` (never committed), and `outcome.md` gains its axis A section
**Proves it:** `benchmark.json` exists with a per-case breakdown for A1–A8, and every assertion carries a recorded mutation check.

Before trusting the run, **mutation-check every assertion**: confirm each fails
when the behavior it claims to observe is broken, then restore. Record the
check. An assertion that has never failed has not been shown to measure
anything.

**Both mutations the first draft proposed were wrong, and are replaced:**

- *"Delete a `|| true` from `skills/tcw-work-stage/SKILL.md:20`."* Removing the
  guard from a command that **succeeds** changes nothing at run time. Testing
  failure survival means making the command **fail**. Worse, the guard it
  targets is checked by `test_every_injected_command_survives_its_own_failure`,
  which the `@composing` decorator parametrises over **six** near-identical
  files (`tests/test_skill_lifecycle_parity.py:331`), so the edit turns the
  suite red rather than isolating one assertion.
- *"Add a tenth empty directory under `skills/`."* Trips nothing — every guard
  globs `skills/*/SKILL.md`. The directory must contain a minimal file.

Then run axis A and read the result against the four verdicts the spec fixes in
advance, under the harness-compatibility rule. Assertions failing in both arms
are investigated as broken before anything is concluded from them.

---

## Group B — skill lift

### Task 8 — Codex adapter, or an explicit unsupported result

**Deferred with task 7.**

**Modifies:** `evals/run_evals.py`
**Proves it:** either the isolation probe passes under Codex and A8 grades, or `benchmark.json` carries `{"harness": "codex", "supported": false, "reason": "…"}` and the reason names what could not be held constant.

Probe how to make the TCW skill available in one arm and unavailable in the
baseline while holding model, workspace, permissions and other instructions
constant. Record the exact invocation and known residue beside the Claude probe.

**Codex support for axis A does not depend on achieving axis B's contrast.**
Axis A needs the skill in *both* arms, so an inability to isolate an axis B
baseline under Codex does not block I7. The first draft conflated the two.
Codex carries I7 alone — it is the only harness where the manual fallback is the
live path — so an unsupported adapter is a recorded gap in axis A, not merely a
thinner axis B. If a clean matched pair cannot be established, fail the adapter
explicitly rather than reporting Claude-only measurements as cross-harness
evidence. Both adapters emit the same transcript, timing, token, exit-status and
fixture-location fields; runner-specific fields live under a namespaced key.

### Task 9 — Revise axis B assertions against first outputs

**Deferred with task 7.**

**Modifies:** `evals/evals.json`
**Proves it:** every revised assertion carries a one-line note saying which first-run output motivated the revision.

Run axis B once, read the outputs, and revise. You do not know what "good" looks
like until the first outputs land, which is why task 4 wrote these provisionally.
B6 (`tcw-report`) needs its negative assertion stated positively: *no new item
appears under `docs/work/`*.

Revising an assertion's parameters within a declared predicate costs the grader
nothing, so this does not invalidate task 6. What *would* invalidate it is an
assertion that needs a predicate the vocabulary does not have — which task 4 now
forces into the open at authoring time.

### Task 10 — Run axis B and aggregate

**Deferred with task 7.**

**Creates:** scratchpad `iteration-1/` axis B runs
**Proves it:** `benchmark.json` reports pass rate, time and tokens per arm with the delta and a per-case breakdown for B1–B10.

With one run per case there is no meaningful stddev — report raw counts and say
so rather than printing a variance field that means nothing.

---

## Group C — review and refine

### Task 11 — Present for review before editing anything

**Deferred with task 7.** **Creates:** nothing
**Proves it:** the user has seen the benchmark and transcripts and said which findings to act on.

The numbers say *what* failed; the transcripts and judgment say *why*. No skill
or prompt edit is made before this.

### Task 12 — Apply refinements, one commit per file touched

**Deferred with task 7.**

**Modifies:** whichever of `skills/*/SKILL.md`, `tcw/work/prompts/*.md`, `tcw/work/resolve.py`, `tcw/store/base.py` the findings justify
**Proves it:** `pytest` green after each commit; every injection-layer fix carries a new pytest guard, mutation-checked.

Findings route by kind, and the plan keeps them apart:

- **A nonce that never arrives is a defect in the injection layer**, not a prose
  problem. Fixed in the composing skills, the resolver, or the binding schema,
  and it earns a pytest guard rather than a wording change.
- **A nonce that arrives and is ignored is a prose problem** in the bookend
  (`tcw/work/resolve.py:386`) or the routers.
- **Axis B findings are skill-wording refinements.**

**A missing nonce does not uniquely implicate the injection layer, and a
delivered-but-ignored nonce does not uniquely implicate prose.** The routing
above is a hypothesis to test, not a diagnosis to act on. Confirm the layer
before editing it — the provenance field from task 6 is what makes that possible.

**The composing skill is now six files, not one.** An injection-layer fix
applied to `skills/tcw-work-stage/SKILL.md` alone leaves five near-identical
copies unfixed, and the parity guards are parametrised over all six.

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
  skill task 12 edits, and for the six composing skills specifically if the
  injection layer is what moved.

**Not a documentation entry, but still required:** a short pointer in
`AGENTS.md` naming `evals/` as how the skill layer is measured and how to re-run
it, **including the `--plugin-dir` requirement**, without which a contributor
silently measures the published clone. It is not covered by the doc-sync gate,
so it is stated here as its own deliverable — without it the harness is
undiscoverable and rots.

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
the customized variant and not in the control, the silence case produces zero
bytes against a non-empty control, the coverage gate catches an uncovered skill,
the runner parses its inputs and accounts for capped runs, and the grader returns
the right verdicts on the committed example run directories.

```sh
pytest                                              # incl. tasks 3, 4, 5, 6 guards
python evals/seed_fixture.py --customized /tmp/probe
tcw validate                                        # this node, after doc edits
```

**The suite cannot check** any of the following, so each is verified by hand and
the result recorded in `outcome.md`:

1. **That the injected blocks actually render in a live agent's context.** No
   pytest assertion can observe another process's context window. Verified by
   reading `transcript.jsonl` for case A6.
2. **That the isolation map really suppressed the foreign plugins.** **Done —
   see task 5's probe table.** Verified from the `init` event's `plugins` field
   in both arms, which is mechanical rather than a human read.
3. **That each assertion bites.** Verified by the mutation checks in task 7, one
   per assertion, recorded with what was broken and which assertion failed.
4. **That a refinement generalizes rather than fitting these prompts.** Verified
   by review at task 11 against the skill's stated purpose, not by any test.
5. **Codex behavior**, if the adapter is unsupported. Recorded as an explicit
   gap rather than inferred from Claude.
6. **Whether a nonce arrived by injection or by the manual fallback.** Partly
   mechanical via task 6's provenance field, but a transcript that establishes
   neither is reported `unknown` and read by a human.

Baseline for "green" is at the top of this document: **2529 passed** on this
checkout, no failures, no skips.

## Self-review — criteria to tasks

Every acceptance criterion is covered by at least one task, and every task
traces back to a criterion.

| Criterion | Covered by | This pass? |
| --------- | ---------- | ---------- |
| 1 — harness runnable, invocation in `AGENTS.md` | 1, 5, 13 | partly |
| 2 — per-kind nonce reported in both arms | 2, 6, 7 | instrument only |
| 3 — per-case render check for both blocks | 5, 6, 7 | instrument only |
| 4 — `benchmark.json` with per-arm deltas | 6, 10 | no |
| 5 — axis B arms verified isolated | 5 | **yes, done** |
| 6 — harness fails on an uncovered skill | 4 | **yes** |
| 7 — every assertion mutation-checked | 3, 4, 7 | partly |
| 8 — findings report per skill and per binding kind | 7, 10, 12 | no |
| 9 — unambiguous fixes applied, judgment calls surfaced | 11, 12 | no |
| 10 — `pytest` green against the baseline | 3, 4, 5, 6, 12, 14 | **yes** |

**Criterion 2 is narrowed by this revision** and the spec needs the same
narrowing at `verify`: it says "for every prompt binding kind", and `skill`
cannot carry a nonce. Three kinds are fingerprinted; `skill` is reported as a
pointer-level observation and `builtin` remains the floor. Recorded as a named
gap rather than quietly satisfied.

Task 8 traces to criterion 8 by way of I7: the Codex result, supported or not,
is part of what the findings report must state. Task 9 traces to criterion 4,
whose per-case breakdown is meaningless if the assertions behind it were never
revised against real output.

## Commit sequence

`tcw work start` → **plan revision (this document)** → seeder (1) → nonce layer
(2) → fixture guard (3) → test set and coverage gate (4) → runner and its test
(5) → grader and its fixtures (6) → `outcome.md`.

Then, in a later pass: axis A findings and any injection-layer fix, one commit
each (7, 12) → Codex adapter (8) → axis B assertion revisions (9) → axis B
refinements, one commit per skill touched (12) → docs (13).

Results in the scratchpad are never committed; only the instrument and the
conclusions.

---

## Revision record

Seventeen findings from a multi review on 2026-09-10 (an adversarial spec
reviewer, `codex exec` read-only, and `bllm review plan`), plus a live probe that
settled three of them by measurement. Listed as: what the first draft believed,
what is true, how it was checked.

**Blocking — the first draft could not have worked as written**

1. **`skill` bindings cannot carry a nonce.** Believed a nonce in a fixture
   `SKILL.md` would appear in the stage prompt. `_resolve_one` returns
   `Invoke the <name> skill.` and never reads the body; the named skill need not
   exist. *Probe: bound a skill that was never created; output was the pointer
   line.* → task 2, task 4 (A4 restated).
2. **The `generate` stdin contract is an envelope.** Believed the script
   receives `work_item_json`'s output. It receives `{"item": …, "hook": …}`, and
   `item` is `null` without a work item reference. *Probe: a script printing its
   top-level keys returned `hook,item`, and `ITEM_IS_NULL=True` on the itemless
   path.* → task 2.
3. **`skills/` holds 14 directories, not 9.** The coverage gate as written would
   have failed on its first run. *Directory listing.* → task 4.
4. **The treatment arm would have loaded the marketplace clone, not this
   checkout** — a different commit, with `autoUpdate: true`. *Probe: with
   `--plugin-dir` plus the all-false map, `init.plugins` named the passed
   directory, `source: tcw@inline`.* → task 5. **Resolved to a runner flag.**
5. **The isolation map needs two settings files.** Believed one. Nine plugin
   keys are split seven and two. Reading either alone leaks. *Read both files.*
   → task 5.
6. **The recorded pytest baseline was wrong in both directions.** Believed 2446
   passed / 4 failed / 9 skipped, the four "environmental". *Ran the suite as an
   unprivileged user: 2529 passed, 0 failed, 0 skipped; all four named tests
   pass.* → Baseline section.

**Significant**

7. **The manual fallback confounds every nonce assertion.** Every composing
   skill tells the reader to run the prompt command by hand when a block looks
   empty. *Read all six skill files.* → task 6 provenance field. **The most
   consequential of the seventeen**: without it, injection-failed-and-rescued
   grades identically to injection-worked.
8. **A5 was vacuous.** "No project instruction appears" is true in the control
   too. *Probe: customized `postmortem` → 0 bytes, control → 2401 bytes.* →
   tasks 2, 3, 4.
9. **A6 and A7 have no cross-arm contrast**, and "any" stage was a trap. The
   bookend wraps the builtin floor in the control too. *Read
   `tcw/work/cli.py:1054`; confirmed by the byte counts above.* → task 4.
10. **The grader's two families cannot express several axis B assertions.** →
    task 4 declares an assertion vocabulary.
11. **The computed nonce is not unguessable from inside the fixture.**
    `run_generate` uses `cwd=node_root`, so the script is readable. The surviving
    claim is that it is in no committed file. → task 2.
12. **A broken `generate` script reads as failure mode I1**, not a missing
    section: `GenerateError` → `ResolveError` → stderr and exit 1, no stdout. →
    task 2 hardening.
13. **Three cited line numbers were stale and both mutation checks were wrong.**
    Cited `:323`, `:344`, `:365`; actual guards at 404, 427, 449. The `|| true`
    mutation turns the suite red because `@composing` covers six files; the
    empty-directory mutation trips nothing because guards glob
    `skills/*/SKILL.md`. *Read the test file and `tests/test_plugin_manifests.py`.*
    → task 7.
14. **The runner shipped with no test.** → task 5.
15. **"Capped rather than failed" had no consumer.** → task 5 defines the field
    and the denominator rule.
16. **The verify case had no `outcome.md` to verify.** *Read `STAGE_STATUSES`.*
    → task 1.
17. **The case-to-item mapping was never stated.** → task 1 table.

**Also recorded, not findings:** the `init` event exposes `plugins` and `skills`
as structured fields, so isolation is asserted mechanically rather than by asking
a model; the stream format is captured from a real run for task 6; and
`memory_paths.auto` is residue present in both arms that the spec does not name.

**Reviewer claims checked and rejected**

- *The determinism claim is broken by random nonces.* The spec already carves
  out both the nonces and the minted slugs, and task 1's sentence describes
  seeding that happens before nonces exist. Wording nit; task 1 now says so
  explicitly anyway.
- *The fourteen-task harness is unjustified against a smaller scripted probe.*
  Out of the scope set for the review; the item was already approved.
