# Rework — tcw-work-stage wording and structure

Requested by the user at `verify` on 2026-09-16. The implementation is otherwise
accepted as assessed. These are changes to `skills/tcw-work-stage/SKILL.md` and
what depends on its wording.

## What still has to change

1. **Shorten "Before you act on any of that" to the essentials.** It becomes a
   section that says to run `tcw work stage gate $stage $item` if that has not
   been done already.
2. **Rename the headings.**
   - "How to work it" → "Lifecycle stage contract"
   - "What this project asks for" → "Stage instructions"
   - "Before you act on any of that" → "Stage pre-checks"

   Update the intro paragraph that names the two blocks to match.
3. **Move the command block into its own section, "Document command summary".**
   The user chose a corrected version of the requested text:
   - the automatically executed block lists what Claude Code actually runs, in
     order: `validate`, `cat`, `prompt`;
   - `gate` goes in a separate block, marked as not run automatically, to be run
     by the reader (see "Stage pre-checks").

   The requested text said all three commands, including `gate`, run
   automatically, and it left out `validate`.
4. **Keep the Codex hint as one line under the summary.** If the harness did not
   run the commands, run them yourself, using the stage and work item named in
   the request in place of `$stage` and `$item`.
   `test_the_manual_fallback_says_where_the_arguments_come_from` guards it.
5. **Keep the eval grader in step with the renamed headings.**
   `evals/grade.py` `BLOCK_HEADINGS`, the `evals/evals.json` A-case text, and
   the grading fixtures under `tests/fixtures/eval_grading/` match the old
   headings.

## Done when

- The parity tests, the eval grading tests, and the seven test files from
  `verify` pass.
- The skill renders in a live Claude Code session with the new headings.
- The changelog notes the heading and section changes.
