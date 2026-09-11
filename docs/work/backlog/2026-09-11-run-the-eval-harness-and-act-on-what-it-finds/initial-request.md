# Request — Run the eval harness and act on what it finds

## Where this came from

`2026-07-22-evaluate-and-refine-the-plugin-skills-with-an-eval-harness` built the
instrument and deliberately did not run it. This item is the other half: spend
the money, read the result, and act on it. Tasks 7 through 12 of that item's plan
carry the method and are still accurate; read them there rather than restating
them here.

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

In: tasks 7 through 12 of the parent plan — the mutation checks that only a live
run can exercise, the axis A run, the Codex adapter, the axis B assertion
revision, the axis B run, the findings report, and refinements the evidence
justifies.

Out: changing the instrument's design. If a case turns out to measure the wrong
thing, fix that case and say so, but a rebuild is a different item.

## Cost

Thirteen axis A runs and twenty axis B runs, at 30 and 60 turns. The parent item
never put a number on this and should have. Agree a ceiling before starting, and
record capped runs separately from failures — the runner already does.

## Related

- `docs/work/inbox/skill-binding-names-are-never-validated.md` — found while
  building the harness, filed rather than fixed because the parent spec's
  non-goals exclude `tcw` changes. It may become relevant if axis A's `skill`
  case behaves oddly.
