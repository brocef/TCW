# Tidy what TCW-74's reviews left for the eval harness

Separate-change findings from TCW-74's verify review (2026-10-15). None blocks
the epic.

1. **The evals run only under Claude.** TCW-74's spec (Design 11) asks whether
   the lifecycle instructions reach an agent "under both harnesses". The runner
   (`evals/run_evals.py`) launches only `claude`, and its transcript checks read
   only Claude's stream format. Measuring Codex needs a second launcher, a
   reader for Codex's transcript, and the isolation check rewritten for
   Codex's plugin loading. TCW-74 accepted this as a cut, recorded in its
   outcome.
2. **B9's prompt describes a different defect from the seeded code.** The
   prompt says an empty report crashes, which `render_report` does not do; the
   seeded comment describes a `KeyError` on a malformed row. This was already
   true before TCW-74.
3. **`transcript_absent` passes on an empty or missing transcript**, unlike
   `tool_input_absent`, which guards against that (`evals/grade.py`). Used by
   A4's control arm.
4. **A7 cannot show that the qa binding mattered.** Its prompt itself says
   "rejected" and names the person, so `decided-by` could appear without the
   binding. A control arm for A7 would show that.
