# Outcome — Route agents to tcw-work-stage for stage instructions and validate its arguments

Implemented in the worktree on branch
`work/2026-09-16-route-agents-to-tcw-work-stage-for-stage-instructions-and-validate-its-arguments`.
Editing `tcw/` began after `tcw work start`, so from then on the work system was
maintained by editing `docs/work/` files directly, as `CLAUDE.md` requires.

## What shipped, task by task

| Task | Commit | What |
| --- | --- | --- |
| 1. Harness detection | `c9f1e788` | `tcw/harness.py`: `ancestor_programs()` (`ps`, then `/proc`; never raises) and `detect()` (nearest `claude`/`codex` ancestor, then `CODEX_*` variables, else Claude). `tests/test_harness.py`. |
| 2. `validate` verb | `bfd3e07c` | `tcw work stage validate [words…]` in `tcw/work/cli.py`; metavar `{prompt,gate,validate}`; `commands.md` row; `tests/test_stage_validate.py`; `test_stage_verb.py:730` updated. |
| 3. Injection | `2b909c63` | Validation section and injected line ahead of `tcw-work-stage`'s heading; parity test that it is the first injected command. |
| 4. `tcw-work` routing | `92e478dc` | Bold routing note, stage table without document links, "Finding your place" and gate bullet reworded, `lifecycle/default/README.md` deleted, parity tests inverted. Body 59 of 60 lines. |
| 5. Other skills | `6a6ff900` | Six skills invoke `tcw-work-stage`; `tcw-verifier` names the `verify` stage; `documentation-sync` step numbers 4/6/9 → 1/3/5. |
| 6. Capabilities | `a7417639` | `capabilities.yaml` (`changed:` three paths); descriptions of `work/run-a-lifecycle-stage`, `skills/tcw-work-stage`, `skills/tcw-work`. `tcw capabilities check` exits 0. |
| 7. Documentation | `4b04b846` | `README.md` stage row, `docs/guide/configuration.md` paragraph, `docs/changelogs/upcoming.md`, `docs/release-notes/upcoming.md`. |
| Review fixes | `c54c72c3`, `cd2534f8`, `d5cda34f` | See "What the plan or spec got wrong". |

## Test result

`pytest` (bare, as CI runs it) on `c54c72c3`: **3398 passed** in 12m29s. The
two later commits change only Markdown. The previous full run had caught one
failure, `test_every_subprocess_declares_its_stdin[harness.py]`, which
`c54c72c3` fixed.

Each new test was watched red first, and each guard was checked by breaking
what it guards:

- searching for `claude` before the nearest match turns the nesting test red;
- deleting the `inbox`-with-item rule turns `test_inbox_refuses_an_item` red;
- moving the injected line below the heading turns the ordering test red;
- re-adding one stage link turns the stage-document guard red.

`test_a_dash_word_after_the_separator_is_judged_not_parsed` passed on its first
run, because argparse already honours `--`. It pins the pairing of `--` on the
skill line with that behaviour.

## Verification outside the suite

1. **Claude Code, live (criterion 10).** Run from a seeded scratch node (`evals/seed_fixture.py --customized`) with the eval runner's isolation settings, `--plugin-dir <worktree>`, and `--add-dir <worktree>`. The session's init event listed only `tcw@inline` from the worktree. The rendered skill text was read from each session transcript.
   - No arguments: the skill loaded. The Skill Invocation Error and "No arguments were given." appeared above the heading.
   - `nope`: the error and "`nope` is not a stage; …" appeared.
   - `spec <slug>`: no validation text. Claude Code put `(Bash completed with no output)` in its place.
   - `spec <slug> for issue #12 don't`, after the review fix: the skill loaded normally, and the extra words were dropped.
2. **Codex (criterion 11).** Not run. The account had hit Codex's usage limit. The user confirmed on 2026-09-16 that the Codex process is named `codex`, and asked that no Codex session be run.
3. **Older CLI.** Against `tcw-cli` 2.3.0 in a throwaway virtual environment, `tcw work stage validate spec x 2>/dev/null || true` printed 0 bytes and exited 0. The bare command exits 2 with argparse's "invalid choice".
4. **Adversarial review** of the combined diff: NOT DONE, with three significant findings. All three were confirmed and fixed (below). Its non-blocking notes on detection misses were accepted as the spec's stated risk: a Claude Code binary started by its version path shows as `2.1.273`, and an npm install runs as `node`.

## What the plan or spec got wrong

- **`$ARGUMENTS` on the skill line was a mistake.** The spec said it "adds
  nothing new" to the shell exposure. It does: extra words reach the shell
  unquoted. A `#` comments out `|| true`, and an apostrophe or a parenthesis is a
  syntax error. Either way the line exits non-zero, which cancels the whole skill
  load, where before those words were silently dropped. The user chose
  `-- $stage $item`. The spec and plan were corrected in `d5cda34f`. `validate`
  still reports three or more words when run by hand.
- **"Exactly what `prompt` accepts" was false for one word.** `prompt` opens the
  store even with no item, so it refuses outside a work node. `validate` did not.
  Fixed in `c54c72c3`, with a test run outside a node.
- **Errors raised rather than printed escaped with nothing on stdout.** This
  covered `ValueError` from an interrupted claim, and `MultipleMatch` from
  resolving a locator. They now become the reason.
- **The filename sweep missed prose.** `delegation.md`, `commands.md:290` and
  `epic-deltas.md` described "the stage documents" as what to follow, without
  naming a file, so neither the grep nor the new test could see them. Reworded
  in `cd2534f8`. The guard is still filename-based, which remains its limit.
- **Criterion 10's "renders no validation text"** is only nearly true. Claude
  Code substitutes `(Bash completed with no output)` for an injected command that
  prints nothing.
- **The plan omitted `stdin=` on the `ps` call.** The repository's subprocess
  rule requires it. Found by the full suite.
- **The plan's live-check recipe needs `--add-dir`.** Claude Code refuses an
  injected `cat` of a file outside the session's directories. A plugin loaded
  from `--plugin-dir` elsewhere hits that; the installed plugin does not.
- **The spec's Codex process-chain risk** was settled by the user's
  confirmation, not by an observed chain. Whether `ps` works inside the Codex
  macOS sandbox is still unobserved. If it does not, detection falls back to
  `CODEX_THREAD_ID`/`CODEX_SANDBOX`.

## Notes

- The editable install points at the worktree. It must be re-pointed with
  `pip install -e /Users/brian/Projects/TCW` before `tcw work complete` removes
  the worktree.
- Related open items, unchanged:
  `2026-09-15-drop-the-tcw-prefix-from-the-plugin-s-skill-and-agent-names`
  (renames every skill touched here) and
  `2026-09-15-fill-codex-gaps-in-skills-and-give-each-skill-one-capability`
  (the `<plugin>` placeholder in the fallback block). Quoting `$stage`/`$item` on
  the two older injected lines remains separate work, as the spec says.

## Rework pass (from `rework.md`, 2026-09-16)

The user requested changes at `verify` (`f28ee221`). All five are done:

| Change | Commit |
| --- | --- |
| Headings renamed: Lifecycle stage contract, Stage instructions, Stage pre-checks. The pre-checks section is now one line naming `tcw work stage gate $stage $item`. | `89f5a62d` |
| "Document command summary" section: the injected commands in order (`validate`, `cat`, `prompt`), with `gate` in a separate block to run yourself. The requested text listed `gate` as automatic and omitted `validate`; the user chose the corrected version. | `89f5a62d` |
| Codex hint kept as one line under the summary ("in place of `$stage` and `$item`"). | `89f5a62d` |
| `evals/grade.py` `BLOCK_HEADINGS`, the `evals/evals.json` A-case text, and the grading fixtures follow the new headings. | `89f5a62d` |
| Changelog entry. | `0f61cdd2` |

**Found during the rework.** Nothing tied the grader's headings to the skill.
With the old headings left in `grade.py`, all 26 grading tests stayed green,
because the fixtures carry their own headings. Every live eval run would have
failed its blocks check instead. `test_the_grader_looks_for_the_headings_the_stage_skill_renders`
now ties the two; reverting `BLOCK_HEADINGS` turns it red.

**Checks.**
- The ten affected test files: 555 passed.
- A live Claude Code render (`plan` on a fixture item): the headings appear in
  the new order, with no failed shell command, and the pre-check line is filled
  in with the stage and item.
