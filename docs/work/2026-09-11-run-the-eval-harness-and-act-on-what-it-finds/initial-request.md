# Request — Run the eval harness and act on what it finds

## Where this came from

`2026-07-22-evaluate-and-refine-the-plugin-skills-with-an-eval-harness` built the
instrument and deliberately did not run it. This item is the other half: spend
the money, read the result, and act on it. Tasks 7 through 12 of that item's plan
carry the method; read them there rather than restating them here, but **not as
written** — the skill restructure made several of their references and counts
wrong (see _Corrections from the 2026-09-15 backlog audit_ below).

## Blocked on the harness defects

Blocked by
[`2026-09-15-eval-runs-under-this-checkout-grade-and-behave-wrongly`](tcw://W/2026-09-15-eval-runs-under-this-checkout-grade-and-behave-wrongly).
A paid run before that is fixed grades wrongly: the relative fixture path is
joined onto the run folder twice in `grade.py`, `run_one` never writes `items` to
`timing.json` so every `item_status` / `new_item_count` assertion reads an empty
mapping, and the axis B dry run refuses B12 when `--out` is inside this checkout.
Runs must use `--out` outside the checkout.

## What is already true, so nobody re-derives it

The harness lives in `evals/`, and `AGENTS.md` under _Measuring the skill layer_
carries the invocation. Four things were settled by probe rather than argument
and do not need re-establishing:

- **Isolation works and is asserted mechanically.** The runner reads the spawned
  session's `init` event and fails the run unless exactly this checkout loaded.
  Acceptance criterion 5 of the parent item is already met.
- **`--plugin-dir` is mandatory.** Enabling `tcw@tcw` loads the marketplace
  clone, a different commit that auto-updates. The runner passes the flag.
- **The isolation map is the union of two settings files**, nine keys at the time
  of writing, derived rather than hardcoded.
- **The stream format is captured**, and the grader's example fixtures are built
  against a real capture.

## Corrections to the parent spec, which is wrong in four places

The parent spec is left unedited as a record of what was promised. These are the
places it does not match what is true, all verified:

1. **Criterion 2 cannot be met as written.** It says "for every prompt binding
   kind", and a `skill` binding cannot carry a nonce: `_resolve_one` resolves it
   to `Invoke the <name> skill.` and never reads the named skill's body, which
   need not exist. Three kinds are fingerprinted. `skill` is a pointer-level
   observation and `builtin` is the floor. **Narrow the criterion in this item's
   spec rather than inheriting an unmeetable one.**
2. **The `generate` nonce is not unguessable from inside the fixture.**
   `run_generate` uses `cwd=node_root`, so the script is readable by any agent
   holding Read. The claim that survives is narrower and still useful: the nonce
   is in no committed file, so it cannot come from repository knowledge or from
   training.
3. **A5 as specced is vacuous.** "The silence opt-out invents nothing" is true in
   the control too, which has no project instructions anywhere. The real contrast
   is that the customized node resolves `postmortem` to zero bytes while the
   control falls back to the bookended builtin floor.
4. **A6 and A7 have no cross-arm contrast.** The bookend wraps the builtin floor
   in the control exactly as it wraps bound text in the treatment, so both blocks
   render in both arms. They are single-arm absolute readings, not deltas. The
   test set already reflects this.

The spec's residue list should also name `memory_paths.auto`, which is present
in both arms and therefore a constant rather than a confound.

## The thing most likely to produce a wrong answer

A nonce alone cannot say how it arrived. Every composing skill carries a fenced
fallback naming `tcw work stage prompt`, so an agent that runs it by hand
produces the nonce with the injection layer having done nothing. `grade.py`
reports every nonce as `injected`, `fallback` or `unknown`, and `unknown` is
never a pass. **Read the provenance field before concluding anything**, and treat
a run that is mostly `fallback` as a finding about the harness's reach rather
than as injection working.

## Scope

In: tasks 7 through 11 of the parent plan — the mutation checks that only a live
run can exercise, the axis A run, the Codex adapter, the axis B assertion
revision, the axis B run, and the findings report. This item ends with the
findings presented for review.

Out: **applying the refinements**, which is task 12 and now
`2026-09-11-refine-the-plugin-skills-and-lifecycle-prompts-against-the-eval-findings`,
blocked by this one. Splitting them keeps the measurement honest: an item that
both measures and fixes has an interest in what it measures.

Also out: changing the instrument's design. If a case turns out to measure the
wrong thing, fix that case and say so, but a rebuild is a different item.

## One harness improvement worth making here

`grade.py` implements one transcript ordering read, for whether the gate ran
before the artifact. A **general** ordering predicate is the same machinery, and
it would make B8's cross-axis ordering mechanical instead of unmechanized. It was
deliberately not added when the test set was written, because declaring a
predicate the grader had not committed to implement is the failure the assertion
vocabulary exists to prevent. If it lands, replace B8's `unmechanized` marker.

## Cost

Thirteen axis A runs and twenty-four axis B runs (twelve cases, two arms each),
at 30 and 60 turns. The parent item
never put a number on this and should have. Agree a ceiling before starting, and
record capped runs separately from failures — the runner already does.

## Related

- [`2026-09-11-validate-a-skill-prompt-binding-names-something-that-exists`](tcw://W/2026-09-11-validate-a-skill-prompt-binding-names-something-that-exists)
  — found while building the harness (first filed as an inbox note), not fixed
  because the parent spec's non-goals exclude `tcw` changes. It may become
  relevant if axis A's `skill` case behaves oddly.

## Corrections from the 2026-09-15 backlog audit

- **Parent plan Task 7** describes a mutation parametrised over "six
  near-identical files". The five per-stage skills were deleted;
  `tests/test_skill_lifecycle_parity.py` now has `COMPOSING_SKILLS = {None:
  STAGE_SKILL}`, one skill. Restate the mutation targets against the current test.
- **Task 9** names B6's skill as `tcw-report`; it is now `extras-report`.
  **Task 10** says B1–B10; there are twelve B cases.
- **Scope is bundled.** Task 8 (a Codex adapter) is new build work —
  `evals/run_evals.py` has no Codex path — and so is the general ordering
  predicate. At spec, set a dollar ceiling and decide whether either moves to its
  own item, and whether the unexercised `commands-*` skills are in scope.
- The heading says "act on what it finds"; the scope is "report" — applying
  fixes belongs to the refine item.

## Notes

- From `2026-09-14-make-eval-checks-measure-what-the-agent-did-…`:
  `files_changed_exactly` now compares the working tree with the `seeded_head`
  the runner records, so a run directory recorded before that change fails it
  (and B10 no longer lists `src/reports.py`); `tool_input_contains` and
  `tool_input_absent` read only tool-call inputs; a `bare` fixture and a per-case
  `fixture` key exist; and the first real run must confirm the transcript shape
  the tool-input predicates assume — content blocks with `type: tool_use` and an
  `input` object — because it was only checked against hand-built transcripts.

- **Eval cases changed** (2026-09-14-restructure-tcw-s-skills-setup-and-configure-skills-command-and-extras-skills-and-no-slash-commands): B11 (`configure`, "set up documentation tracking") and B12 (`setup`, `fixture: bare`, which can only run with `--out` outside this checkout) are new; B5 is retargeted to `cross-axis` over the `taxonomy` and `capabilities` skills; B4 and B8 gained `tool_input_absent` `setup/references/`; A1–A4 and A8 now invoke `work-stage`, and the axis A baseline may move, because the agent must now pass the stage as well as the item (if it passes only the item, the injected blocks fail quietly and nonces shift from `injected` to `fallback`); the four `commands-*` skills are excluded with no case yet, a gap to consider; `PARTIAL` gained `setup`, `configure` and `work-stage`.

## Folded in: 2026-09-15-eval-runs-under-this-checkout-grade-and-behave-wrongly

_Merged here during the 2026-09-24 backlog cleanup; the source was closed as superseded._

### Inbox manifest

- `2026-09-14-eval-runs-under-this-checkout-grade-and-behave-wrongly.md`

### Inbox body

## Eval runs under this checkout grade and behave wrongly

Found by the adversarial review of
`2026-09-14-make-eval-checks-measure-what-the-agent-did-…`. All four existed
before that item and are outside its scope.

1. **The fixture path is doubled when a default run is graded.** `run_one`
   (`evals/run_evals.py`) writes `"fixture": str(out / "fixture")`, and with the
   default `--out` (`eval-runs/iteration-1`) that path is relative.
   `grade_run` (`evals/grade.py`) joins it onto the run directory, so
   `python -m evals.grade eval-runs/iteration-1` looks for
   `eval-runs/iteration-1/B10/with-skill/eval-runs/iteration-1/B10/with-skill/fixture`.
   The comment "A live run writes an absolute path" is false for the default.
   Every check that reads the fixture is affected. Confirmed by reading the code;
   not run.
2. **Fixtures seeded inside this checkout sit under TCW's own project.** `tcw`
   finds `tcw-config.yaml` in parent folders, and Claude Code may load this
   repository's `CLAUDE.md`/`AGENTS.md` from parent folders too, in every arm.
   The bare fixture now refuses to seed inside a TCW project; the control and
   customized fixtures have their own config, but the instruction-file question
   is unverified.
3. **`manifest.json` sits in the agent's working folder and holds the axis A
   nonces.** It is now hidden from git through `.git/info/exclude`, but an agent
   can still read it and copy a nonce into an artifact. Writing it beside the
   fixture instead would remove both problems.
4. **Case B10's prompt describes a fix that is not in the fixture.** It says the
   user fixed an off-by-one in CSV export in `src/reports.py`; that file has no
   CSV export, and nothing is changed. An agent that checks `git diff` finds
   nothing to document. Committing the described fix as the seeder's last commit
   would make the prompt true. Also open: whether a bug fix that restores
   existing behaviour should fire `README.md`'s `Public-API` trigger at all.
5. **`run_one` never writes `items` to `timing.json`.** Its entry carries
   `nonces` and `stage_items` but not `items`, while `grade_run` reads
   `timing.get("items", {})`. So on a real run `item_status` and
   `new_item_count` read an empty mapping and grade wrongly. The committed
   grading fixtures under `tests/fixtures/eval_grading/` do contain `items`,
   which is why no test notices. Confirmed by reading the code (verification
   round 1 of the eval checks item).
6. **Check what `claude -p` itself writes into the fixture.**
   `files_changed_exactly` now counts every untracked file that isn't ignored,
   so anything the harness writes into its working folder is charged to every
   run. The first paid run should list `git status --porcelain --ignored` for one
   fixture and exclude whatever the harness, rather than the agent, left there.
7. **Reusing an `--out` folder can still stop a paid run partway.** `seed()`
   now refuses a fixture folder that is not empty, but `run_evals.main()` only
   checks bare arms up front. A run with `--axis b --out X`, after an earlier
   `--case B11 --out X`, spawns the new arms and then raises when it reaches
   B11's used folder. Moving the "fixture folder must be new or empty" check into
   the same up-front loop for every arm would stop it before anything runs.
   Found by both reviewers in verification round 2 of the eval checks item.

### Widened at triage (2026-09-15)

Two eval harness gaps from the skill restructure review were folded into this item
rather than opened as their own, because they are defects in the same harness
(`evals/coverage.py`, `tests/test_eval_coverage.py`, and cases B4 and B8).

### Folded in: from inbox entry `2026-09-14-guards-and-gaps-the-skill-restructure-review-left.md` (Guards and gaps the skill restructure's review left for separate changes)

2. **Nothing checks that `EXCLUSIONS` and `PARTIAL` in `evals/coverage.py` name
   skills that still ship.** A stale key (say a deleted skill) passes
   `tests/test_eval_coverage.py`.

6. **B4 and B8 only catch a wrong route into the `setup` skill.** Each asserts
   `tool_input_absent` `setup/references/`, as the spec asked. A B8 run ("Set
   it up.") that opened a `configure` document instead passes every mechanized
   check, although "set it up" there asks for a term, a capability and a work item,
   not a configuration change. This is a gap in the spec, not a departure from it;
   adding `tool_input_absent` `configure/references/` to both cases would close it.
