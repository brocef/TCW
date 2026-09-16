# Refined outcome — Route agents to tcw-work-stage for stage instructions and validate its arguments

## Decision

**Accepted** by the user on 2026-09-16, after one rework pass. The user reviewed
the reworked `tcw-work-stage` skill and approved completion and a local merge to
`main`.

## Evidence

- **Criteria.** The `tcw-verifier` assessment of the 14 acceptance criteria:
  - 12 pass;
  - criterion 10's live part is taken from `outcome.md`;
  - criterion 11 (a live Codex session) was not run, by the user's decision.
    The user confirmed the Codex program is named `codex`.
- **Full suite.** Bare `pytest` at `f977a74c` (after the rework): **3399
  passed** in 12m44s. Later commits change only lifecycle artifacts.
- **Live Claude Code renders**, recorded in `outcome.md`:
  - no arguments and an unknown stage show the Skill Invocation Error;
  - extra words containing `#` and an apostrophe no longer cancel the skill
    load;
  - the reworked headings render in order.
- **Older CLI.** `tcw-cli` 2.3.0 injects nothing from the new line.
- **Review.** An adversarial review returned three significant findings, all
  fixed in `c54c72c3` and `cd2534f8`. The verifier's two small documentation
  gaps were fixed in `e9787ec4`.
- **Ledger.** `tcw capabilities check` passes. The three `changed:` capabilities
  describe what shipped; there is no `new:` or `removed:` entry to flip.

## Rework

`rework.md` (`f28ee221`) asked for:

- renamed sections;
- a shortened pre-checks section;
- a separate command summary;
- the Codex hint kept;
- the eval grader kept in step.

All of it is done, as `outcome.md` § "Rework pass" records. The file is removed
here because a verdict is one artifact, not both. It remains in history at
`f28ee221`.

## Deferred follow-ups

No new items were filed; the user declined none, and none was requested.
Already on the board:

- `2026-09-15-drop-the-tcw-prefix-from-the-plugin-s-skill-and-agent-names`
  renames every skill this item touched.
- `2026-09-15-fill-codex-gaps-in-skills-and-give-each-skill-one-capability`
  covers the `<plugin>` placeholder in the command summary.

Known and accepted without an item:

- quoting `$stage`/`$item` on the two older injected lines;
- whether `ps` works inside the Codex macOS sandbox; the variable fallback
  covers it if not;
- the stage-document guard matching only file names.

## Closeout choices

- **Merge route:** a local merge of `work/<slug>` into `main` through
  `tcw work complete`, as the user approved. Nothing is pushed.
- **Documentation:** synced (README, configuration guide, changelog, release
  notes, skills, capability ledger).
- **Originating GitHub issue:** none; the item came from a chat request.
- **Version:** offered after `complete`, per the Definition of Done.
