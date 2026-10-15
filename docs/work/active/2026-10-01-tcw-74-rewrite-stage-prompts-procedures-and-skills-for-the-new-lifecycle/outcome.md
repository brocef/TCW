# Outcome — TCW-74: rewrite stage prompts, procedures and skills for the new lifecycle

Implemented on `work/2026-10-01-tcw-74-rewrite-stage-prompts-procedures-and-skills-for-the-new-lifecycle`,
made from `epic/tcw-3.0` at `58da5913`, one commit per plan task, `7a2feaf5`
to `5ef74446`. Task 15 (mutation checks) found no gap, so it has no commit.
`capabilities.yaml` and this file are on main.

Tests were run per task against the changed areas, never as a full suite, in a
private virtual environment pointed at the worktree, with the worktree as the
current folder. The final run covered the nine standing files
(`test_cli_contract.py`, `test_cli_help_standard.py`, `test_static_guards.py`,
`test_cli_handler.py`, `test_tree_store_raises.py`, `test_no_node.py`,
`test_ledger_3_0.py`, `test_documented_cli_surface.py`,
`test_doc_allowance.py`), all of `tests/work/`, and every other file this item
touched: 2652 passed, 8 skipped (5 in `test_procedure_verb.py` and 2 in
`test_documentation_prompt.py`, all listed in `tests/not_ported.py` before
this item, and the live Jira check, which runs by hand). `pytest --collect-only -q`
collects 4349 tests with no error. No skip naming TCW-74 remains.

## What was built

| Task | Commit | What |
| --- | --- | --- |
| 1 | `7a2feaf5` | `tcw/work/passages.py`: backend passages (`<!-- backend: <name> -->` … `<!-- /backend -->`) filtered to the project's backend when a prompt or procedure is composed, and removed entirely outside a project. |
| 2 | `a6753b80` | The eight stage prompts (`review.md` and `qa.md` new, `verify.md` deleted, the rest rewritten), and a loader that refuses a missing, empty or extra prompt file. |
| 3 | `65603925` | The header ("This text ran no checks") and the closing line around a stage prompt, and the item's slug in place of every `<slug>`. |
| 4 | `3c7a973f` | The unconfigured-prompt fixture re-captured from the 3.0 output. |
| 5 | `51d092fd` | The procedure set: `unattended-work`, `triage-issues`, `documentation-sync`, `create-work`, `audit-backlog`, `search`, `pause-work`. `post-mortem`, `consolidate-plans`, `decompose`, `delegation` and `skills/work/references/procedures/` deleted. |
| 6 | `781894e6` | The `work` skill, `commands.md` and `tags.md` rewritten; the lifecycle references, `transitions.md`, `hooks.md`, `epic-deltas.md`, `cross-node-deltas.md` and the `work-stage` skill deleted. |
| 7 | `7e80fbc7` | The four command skills rewritten; `commands-verify-work` deleted. |
| 8 | `9ca5a5f9` | The capabilities, taxonomy, setup (with the new `references/jira.md`), work-create, extras and documentation-sync skills; `post-mortem` skill deleted. |
| 9 | `15fae707` | `agents/reviewer.md` replaces `verifier.md`; `post-mortem.md` deleted; `backlog-auditor.md` reads the procedure; `skills/README.md` and the Codex manifest. |
| 10 | `02124618` | `tests/doc_vocabulary.py` (the shared 2.x vocabulary table) and `tests/test_shipped_text.py`; the allowance list shrunk; the `Missing`-record exemption deleted. |
| 11 | `acd91237` | `tests/test_skill_flow.py`: the 3.0 product flow. |
| 12 | `5ef74446` | The eval harness (by one helper agent, reviewed by me before committing), `tests/fixtures/eval_grading/` deleted, the agent guide's eval section updated. |
| 13 | `95ed370b` | The records: three skill capabilities and three Features removed, fourteen descriptions rewritten. |
| 14 | `546dd792` | Release-notes and changelog entries; release-integrity scenario row 4. |

## Acceptance criteria

| AC | Evidence |
| --- | --- |
| 1 The prompt set | `tests/test_shipped_prompts.py` (`test_the_prompts_are_exactly_the_stages_that_take_one`, `test_verify_is_gone`, the missing- and extra-file cases, the wheel case) |
| 2 Ceiling | `test_shipped_prompts.py::test_each_prompt_is_at_most_60_lines_for_each_backend` |
| 3 Content | the per-backend content tests in `test_shipped_prompts.py`; the Jira-filtered qa prompt read by hand: `--reason` appears only in the step addressed to the person deciding |
| 4 Backend passages | `tests/work/test_backend_passages.py` |
| 5 Header, footer, `<slug>` | `tests/work/test_stage_bookends.py` |
| 6 Procedures | `tests/test_shipped_procedures.py`, `tests/test_procedure_verb.py`, `tests/test_procedure_config.py` (`work.procedures.delegation` refused naming the known ids) |
| 7 Disposition table | `tests/test_shipped_text.py` (exact file set, injection fallback, pause skill, Codex manifest), `test_dynamic_skill_marker.py`, `test_plugin_manifests.py::test_the_codex_description_counts_the_skills_it_ships` |
| 8 No git, no 2.x vocabulary | `test_shipped_text.py` (git scan, git in `allowed-tools`, vocabulary scan with the shared table and TCW-74's extra patterns) |
| 9 Commands exist | `test_shipped_text.py::test_every_command_named_in_shipped_text_exists` and the allowance-shrink tests |
| 10 Capabilities skill reversal | `test_shipped_text.py::test_the_capabilities_skill_changes_records_with_the_code` |
| 11 Records | `tcw validate` on a copy of the worktree's records with a 3.0 config: 15 errors, every one a retired `Planning doc` field in a record this item does not own (listed below), none in a record it touched. The item's `capabilities.yaml`, in a scratch project holding those records, passes the records gate on `tcw work advance --dry-run` out of implement; with `skills/work-stage` put back it is refused (exit 3) naming it. `test_ledger_3_0.py`, `test_capability_ref_wording.py`. |
| 12 Evals | `tests/test_eval_*.py` (160 passed); `seed_fixture.py --customized` and `--bare` exit 0; `coverage.py` reports every skill covered; `run_evals --axis a --dry-run` lists A1–A7 with both qa cases (A6 control, A7 customized). No run without `--dry-run`. |
| 13 Product flow | `tests/test_skill_flow.py` |
| 14 Full suite | Not run, by the epic's instruction (targeted runs above). |
| 15 Entries | `docs/release-notes/upcoming/<item-folder>.md` and `docs/changelogs/upcoming/<item-folder>.md`, each starting with `##`; `test_upcoming_entries.py` |

## Verification by hand

In scratch projects with the branch's code and `HOME`/`XDG_CONFIG_HOME` in the
scratch folder: the flow `new` → `advance` ×3 → `capabilities.yaml` declaring
`billing/refund` → implement round → `advance --dry-run` refused while the
record was absent, refused while it was `Missing`, and moved into review once
it was `Supported`. `tcw work stage prompt qa <slug>` printed the header,
the text and the closing line with the slug filled in.
`tcw work procedure pause-work` and `create-work` outside any project print
their text with no passage markers.

## Mutation checks

Each guard below was broken on purpose; the named tests went red, and the
file was restored from git (checked with `git status` afterwards).

- "Commit the plan." appended to `tcw/work/prompts/plan.md`: the git scan red,
  naming `plan.md:55`.
- "outcome.md" appended to `skills/extras-autonomous-work/SKILL.md`, and
  `builtin: true` to `skills/work/SKILL.md`: the vocabulary scan red, naming
  each file, line and reason.
- `tcw work start <slug>` in `skills/work/SKILL.md`: the command check red,
  "no such command"; `tcw work procedure prompt pause-work`: red, "no such
  procedure: prompt".
- The backend filter keeping every passage: 16 red, including criterion 4's
  removal case.
- The footer keyed on `row.name == "qa"` instead of the backend's external
  stages: 4 red, including the stand-in backend case.
- The loader skipping a missing prompt file: the missing-file case red for
  every stage.
- `<slug>` replaced only once: the no-`<slug>`-left case red for every stage.
- The eval helper ran 26 mutations over the new grading predicates (judges not
  compared, verdict ignored, `decided-by` ignored or optional, scenario
  matched as plain text, declaration count ignored, oldest round read,
  `{item:}` not expanded, and the `evals.json` rules); each went red, and a
  qa item seeded with `judges: 0` is refused by TCW itself.

## 2.x tests deleted or rewritten

- Deleted: `tests/test_skill_lifecycle_parity.py` (the lifecycle references it
  compared are gone; the shipped-text tests replace it);
  `tests/test_configuration_text_home.py::test_tcw_work_keeps_only_the_runtime_tracker_text`
  and its unused `COMMANDS` constant (it read the old `commands.md`);
  `tests/fixtures/eval_grading/` (no test reads it now).
- Rewritten, skip removed: `tests/test_shipped_prompts.py`,
  `tests/test_shipped_procedures.py` (the source map and both agent checks
  replaced by checks that each agent reads its source at run time),
  `tests/test_skill_flow.py`, the five `tests/test_eval_*.py`,
  `tests/test_prompt_fallback.py` with its re-captured fixture.
- Updated: `test_procedure_verb.py` (backend-filtered default, `pause-work`,
  removed ids refused), `test_procedure_config.py`,
  `test_unattended_work_skill.py`, `test_documentation_sync_wiring.py`,
  `test_falsification_rule.py`, `test_documentation_prompt.py`,
  `test_documented_cli_surface.py` (the `Missing` exemption deleted),
  `test_doc_allowance.py` (a check for the new `REFUSED_VALUES`).

## Where the work differs from the plan

1. **The git scan's allowlist has one entry, not two.** The spec allowed
   `skills/taxonomy/SKILL.md`'s "file not tracked by git" clause; TCW-73
   removed that check (`taxonomy rm` now deletes untracked files), so the
   clause was deleted rather than allowed.
2. **The vocabulary scan allows two mentions of the Node.js runtime**
   (`Bash(node --version)` in the setup skill's tools, "Node 22.12" in
   `install.md`), which the shared `\bnodes?\b` pattern matches.
3. **Unattended decisions are recorded in the round being written** (implement
   round up to implement, the review or qa round there), not in "the newest
   implement round", because an implement round is written once.
4. **`tests/doc_allowance.py` gains `REFUSED_VALUES`** for
   `tcw work procedure prompt`, which parses (with `prompt` as the id) but is
   refused when run. The new command check reads the procedure id, so the
   configure skill, TCW-75's, needed this entry until it is rewritten. Four
   flag entries nothing names any more were removed.
5. **The command check does not require a subcommand.** Bare group names in
   prose (`tcw work`, `tcw capabilities`, `tcw --version`) are references to
   the group, not invocations.
6. **The plan prompt's "no longer believe" became "have stopped believing"**
   (the vocabulary scan), so the unconfigured-prompt fixture was re-captured a
   second time, in Task 10, with that one line changed.
7. **The eval qa cases run one arm each** (A6 control, A7 customized, since
   only the customized fixture has the person-decides binding), A6 also
   checks the verdict is `accepted`, and A4 keeps a `skill` binding on review
   so the arms still differ. **"Under both harnesses" is not done:** the
   runner launches only Claude, and its transcript predicates read Claude's
   format; Codex support would be separate work.
8. **The agent guide's eval section (`AGENTS.md`, which `CLAUDE.md` links
   to) was updated here**, at the lead's direction, though the plan gives
   `AGENTS.md` to TCW-76: it described the injected/fallback grading this
   item removed.

## Left for other items

- **Records with the retired `Planning doc` field** that `tcw validate` will
  report once this repository's config is 3.0, none touched here:
  `capabilities/detect-capability-drift`, `cli/install-from-pypi`,
  `skills/configure`, `skills/extras-report`, `skills/taxonomy`, `web`,
  `web/choose-a-theme`, `web/editing`,
  `work/configure-the-work-store-location`,
  `work/declare-the-work-stores-home-repository`,
  `work/decompose-a-work-item-into-children`, `work/discard-a-work-item`,
  `work/manage-the-work-inbox`, `work/read-the-documentation-gate-for-a-change`,
  `work/retitle-a-work-item`.
- **Allowance-list entries still needed**, each named only by documents
  TCW-75 rewrites (README, `docs/guide/*`, `skills/configure/`), by
  `AGENTS.md` and `docs/lifecycle/implementation.md` (TCW-76), or by
  capability records other items own; `test_shipped_text.py` fails if any
  becomes named only by this item's files.
- **Documentation entries:** the release notes, changelog and skills entries
  fired and are done here. README (`Public-API`), `docs/guide/jira.md` and
  the guides, and `skills/configure/references/*.md` (the procedure ids,
  `procedure prompt`) are TCW-75's, as the plan says.
- **Observed, not changed:** `tcw work advance` out of spec and plan moves on
  with no spec or plan document written; no gate checks a stage's document.
  The stage prompts say to advance once the output is written.
- **Scratch folders:** another agent shared this session's scratch folder and
  reused `$S/p1`; this item's scratch work moved to `$S/tcw74/`.

## Review round 1

Three adversarial reviewers read the change; the orchestrator accepted the
findings below as this change's. Each was checked against the code before it
was fixed. Fixed on the item branch in `ed5e2eb4` (code), `e411e681` (skills,
procedures, records) and `a55d9662` (eval harness).

**Code and prompts**

- **N1, a misspelled passage marker pair passed silently.** Confirmed:
  `<!-- backend:jira -->` matched neither marker and reached every backend as
  an HTML comment. Fixed: in `tcw/work/passages.py` a whole line starting
  `<!--` that mentions `backend` (any letter case) and is neither marker
  exactly is a `BackendError` naming the line. Tests added for three
  misspellings, and a test that no built-in prompt or procedure keeps a
  marker-like line after filtering, for each backend and for none.
- **N3, a removed procedure id got only "unknown procedure".** Confirmed.
  Fixed: `_REMOVED_PROCEDURES` in `tcw/work/config.py` adds where each went,
  from spec Design 5.1 (`post-mortem` → `work.stages.postmortem.prompt`,
  `decompose` → `work.stages.plan.prompt`, `delegation` → the work skill and
  `tcw work new --project`, `consolidate-plans` → `tcw work new`). The comment
  above `PROCEDURE_IDS` no longer claims configuration never breaks. Tests for
  all four, and that a misspelling gets no hint.
- **N4, the git-grant test read only the first `allowed-tools:` line.**
  Confirmed. Fixed: it reads parsed front matter (a list or a comma string),
  and a new test checks agents' `tools:` the same way.

**Skills, procedures and records**

- **B1:** `create-work.md`'s Jira passage now says an unadopted inbox ticket
  cannot take `tcw work comment`, so the addition goes in the report.
- **B2:** the drive, process-inbox, triage-issues, setup, plan-work,
  documentation-sync, run-a-lifecycle-stage and extras-autonomous-work records
  corrected, with the release notes and changelog. The extras-autonomous-work
  skill description now uses the procedure's wording ("a read-only subagent on
  the strongest model the harness can start"). The changelog also gains lines
  for N1 and N3.
- **B3:** `skills/setup/references/jira.md` says file items are not seen once
  the backend is Jira, so finish or discard them first.
- **B4:** the "reviewer that did not write the code" rule moved into
  `tcw/work/prompts/review.md` (a "Who reviews" paragraph), not the work
  skill. Reason: the skills README's Rule 1 makes "which review" project
  conduct, and the unattended-work procedure already said "run the review
  stage as its prompt says: a read-only reviewer", which the prompt did not
  say until now. The drive skill now points at the prompt, which keeps its
  "fixed (Rule 2)" verdict true; its record says "with TCW's own review text".
- **B5:** the work skill's "Finding your place" covers the inbox: no
  handoff, `tcw work stage prompt inbox` with no slug.
- **B6:** the work skill's qa row says a round is still written when a person
  decides (with `decided-by`), and only a backend that keeps qa produces
  findings without a round.
- **Process-inbox and the request prompt's closing advance:** the skill says
  not to run it.
- **Unattended work with no round:** the procedure's audit-trail row and the
  skill's audit-trail section say decisions go in the findings comment, or the
  report if none is posted. Spec Design 7's extras-autonomous-work row is
  updated to match.
- **Node.js:** `skills/setup/SKILL.md` drops `Bash(node --version)` and the
  Node requirement; `references/install.md` says TCW, `tcw serve` included,
  needs no Node.js. The two vocabulary allowances for those phrases are gone,
  so that list is empty, as the spec intended. On this branch alone
  `tcw/serve/` still checks Node (TCW-77 removes it), so the text is right
  only once both land.

**Eval harness**

- **E1:** confirmed: the spawned agent ran the first `tcw` on PATH. Fixed:
  `agent_env()` puts `Path(sys.executable).parent` first on the agent's PATH;
  `spawned_tcw()` finds that `tcw`, asks its interpreter where `tcw` imports
  from, and `timing.json` records both, with an isolation problem when it is
  not this checkout. `--dry-run` prints it too. `evals.grade` now prints
  isolation problems and exits non-zero for any. AGENTS.md's eval section
  says the runner pins both the plugin and the `tcw`, and no longer says
  isolation problems fail the run on their own.
- **E2:** B13's `tool_input_contains "inbox"` is now `"tcw work list"`, which
  `find-overlap.md` tells the agent to run; the CASE_ROUTING comment updated
  and a test added.
- **E3:** new predicate `ran_stage_prompt`: the call's result must not be an
  error and must carry `This text ran no checks.`, or, with `empty: true`,
  succeed with no output (A5 customized). A1-A7 use it; the old test now
  builds tool results.
- **E4, "under both harnesses" was dropped with no follow-up named.** Not
  fixed in this item, by the orchestrator's decision: a Codex launcher, a
  reader for Codex's transcript and an isolation check for Codex's plugin
  loading are a project of their own, and criterion 12 does not require them.
  Filed as item 1 of
  `docs/work/inbox/2026-10-15-tidy-what-tcw-74-s-reviews-left-for-the-eval-harness.md`.
- **E5:** each QA scenario needs a line naming it and no other scenario.
- **E6:** B3 asserts `tool_input_contains "tcw work advance"`.
- **E7:** `tcw/work/layout.py` gains `split_front_matter` and a public
  `front_matter`; the grader and the shipped-text test use them, and the
  grader's copy is gone.
- **E8:** "node" → "project" in both files.

**Mutation checks this round:** disabling the misspelled-marker check (3
cases red); keeping marker lines in the output (the no-marker test red for
each backend); dropping the removed-procedure hint (4 red); a multi-line
`allowed-tools` list with `Bash(git *)` in a skill and `Bash(git log *)` in
an agent's `tools` (both red, naming the grant); dropping the PATH pin and the
import check in the runner (5 red, including the real probe tracing the
installed release); `ran_stage_prompt` ignoring the result (4 red: no result,
failed call, silenced case, A6 with a failed call); the scenario check
counting any line that names a scenario (the two new one-line cases red).
Each restored and green afterwards.

**Tests run:** the standing guard files, the shipped text, prompt, procedure,
skill and plugin manifest tests, the procedure config and verb tests, the
backend passage, compose, config, Jira bookend and layout tests, and every
`tests/test_eval_*.py`: 1099 passed, 5 skipped, plus 177 eval tests passed.
`pytest --collect-only -q` is clean.

## Review round 2 (confirming)

One confirming reviewer read the fixes (`5ef74446..a55d9662`) and found every
round-1 finding fixed except that E4's disposition was not recorded (now
above), and one new defect the N1 fix introduced. Its verdict was NOT DONE on
those two points only.

- **The N1 check rejected ordinary comments.** Any whole line starting `<!--`
  that mentioned "backend" anywhere was an error, so a project prompt file
  with a header comment such as `<!-- This prompt is shared by every backend. -->`
  made `tcw work stage prompt` exit 1. Fixed by the orchestrator in `0e30fca5`:
  only a comment that opens with the word `backend` (after an optional `/`) is
  treated as a misspelled marker. Test added for three prose comments; with
  the old check restored, all three go red. The four misspellings still fail.
  Spec Design 3.3 now lists the rule.

Both points were narrow enough that the orchestrator fixed them without a
further review round. Approved under the epic's rule that passing
adversarial review is approval; the owner reviews the epic as a whole at its
end.

Noted by the confirming reviewer and left for other work: README still says
`tcw serve` needs Node.js (TCW-75's notes); a clearer reason when the eval
runner cannot identify the spawned `tcw`'s interpreter, and a test pairing a
failed stage-prompt call with an unrelated call whose output carries the
header (both small, in the eval-harness inbox entry).
