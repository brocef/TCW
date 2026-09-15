# Outcome: split `tcw work stage` into `prompt` and `begin`

All six tasks shipped. The break is one rename, `prompt` is new, and the
migration guide covers both. Two of the plan's six tasks were recorded as landed
when they had not; that is the substance of what this outcome corrects.

## What shipped, task by task

| Task | Commit | What landed |
| --- | --- | --- |
| 1 — shared tail of `_stage` | `9194b2a` | `_stage_tail`, called by both paths |
| 2 — `prompt` and `begin`; bare form removed | `67edccd` | subparser group, hidden per-stage parser for the removed form, error prefixes, `--no-exec` accepted only by `begin` |
| 3 — illegal-status notice, node-qualified resolution | `67edccd` code, `a743e9e` tests | the code landed; **the tests did not** — see below |
| 4 — gate-non-execution evidence | `a743e9e` | **did not land in `67edccd` at all**; written here |
| 5 — documentation surface | `67edccd`, `81623de` | every agent-facing surface says `begin`; the capability description finished later |
| 6 — Documentation Sync, migration guide, version | `102dd42`, `9740f4c`, `81623de` | guide, both `upcoming.md` rewrites, capability rewrite; version cut last |

## The plan's own status note was wrong

`plan.md` gained a "Where this stands" section recording Tasks 3 and 4 as landed
in `67edccd`. They had not. That commit added `_prompt` and `_bare` helpers to
`tests/test_stage_verb.py` and **never called either**: the reading verb shipped
with zero tests, and the paired sentinel evidence the plan describes in detail
did not exist in the tree. Criteria 1–8 and 10–14 were unproven.

`a743e9e` writes them — thirteen tests, including the paired assertion the plan
argues for: a `pre` binding that touches a file and exits 1, where `prompt` exits
0 leaving no sentinel and `begin` exits 1 having written one. Confirmed capable
of failing by resolving `prompt` with `run_checks=True`, which fails exactly that
test and nothing else.

The lesson is narrow and worth naming: a helper written for tests that were never
written reads, at a glance, exactly like coverage.

## Acceptance criteria

| # | Result |
| --- | --- |
| 1 | Pass — `test_prompt_prints_the_built_in_for_every_stage_unconfigured`, all seven |
| 2 | Pass — `test_prompt_answers_for_an_item_in_any_status`, the full stage × status product |
| 3 | Pass — `test_prompt_runs_no_gate_and_begin_does`, first half |
| 4 | Pass — same test, second half; the halves guard each other |
| 5 | Pass — `test_prompt_says_so_on_stderr_when_the_stage_is_not_legal`; also confirmed by hand, exit 0 |
| 6 | Pass — `test_prompt_and_begin_print_the_same_bytes_where_begin_is_allowed` |
| 7 | Pass — `test_a_condition_matches_only_when_an_item_is_named` |
| 8 | Pass — `test_a_qualified_reference_reads_the_owning_nodes_bindings`, two nodes binding different text |
| 9 | Pass — `tests/fixtures/prompt_fallback/unconfigured.json` diff is six added `argv` lines, zero removed |
| 10 | Pass — the `begin` half of criterion 3/4's test asserts empty stdout on the failing gate |
| 11 | Pass — `test_the_bare_form_is_a_usage_error_naming_both_verbs`, exit 2 |
| 12 | Pass — `test_prompt_reports_its_own_errors_on_stderr_alone` |
| 13 | Pass — `test_prompt_refuses_a_work_item_for_inbox` and `test_begin_inbox_runs_the_stages_pre_bindings` |
| 14 | Pass — `test_prompt_rejects_no_exec_and_names_the_verb_that_takes_it` |
| 15 | Pass — `tests/test_documented_cli_surface.py` green; the repo-wide grep for the bare form outside `ARCHIVAL` returns nothing |
| 16 | Pass — `git show 67edccd -- …/unconfigured.json` is `6 ++++++`, no deletions |
| 17 | Pass — the literal is `f"tcw work stage begin {stage_id}"` |
| 18 | Pass — all seven routers; grep clean; criterion 16 covers the JSON |
| 19 | Deferred to the version cut, which follows completion |
| 20 | Pass — both files rewritten; neither claim survives |
| 21 | Pass — `docs/migration-guide-1.X-to-2.0.0.md`, every command in it run as shown |
| 22 | Pass — `run-a-lifecycle-stage` rewritten; `tcw capabilities check` exits 0 |
| 23 | Pass — `tcw validate` exits 0; suite green but for four pre-existing environment failures (below) |

### The four failures, none this item's

`test_atomic_write_preserves_prior_on_failure`,
`test_atomic_write_temp_cleanup_on_failure`,
`test_an_unwritable_target_reports_and_prints_no_path` — this container runs as
uid 0, and `chmod`-ing a directory read-only does not stop root writing to it.
`test_the_prompts_are_in_the_built_wheel` — its `pip wheel
--no-build-isolation` fails on this image's Debian-patched setuptools before
reading anything. All four fail identically on `main`.

## The hand checks the plan listed

- **The stderr notice reads as a warning.** It does: `note — 'plan' is not legal
  for an item in 'active'; it runs in backlog. Printing its instructions anyway
  because you asked to read them, not to enter the stage.` It names what it did
  and why, and the exit code is 0.
- **The migration guide is accurate.** Every command in it was run. The removed
  form's message matches the guide's quoted block; the check-for-it grep covers
  all seven ids in `STAGE_IDS` and returns nothing outside archival paths.
- **The fixture was hand-edited, not re-captured.** `git show` on that commit:
  six insertions, zero deletions, all inside `argv` arrays.
- **Is `prompt` worth its cost?** Answered, not deferred. It has a second caller
  that is not its author: `skills/tcw-work-stage`, which composes a stage
  document with `prompt`'s output into one read. That skill is only possible
  because `prompt` resolves without gating — `begin` would run the gate and print
  nothing for exactly the stage being asked about. Tracked as
  `2026-09-09-compose-a-lifecycle-stage-into-one-skill-document`.

## Defects found and fixed inside this item

**The `--no-exec` plan header printed the removed form.** It said `tcw work stage
<id>:`, a spelling 2.0.0 rejects, so a reader copying it out of a log got a usage
error. `--no-exec` is accepted only by `begin`, so the prefix can only be
`tcw work stage begin <id>`. Fixed in `7fadf58` with a test that fails on the old
string.

**The capability description stated two things that were no longer true.** It
said TCW ships defaults for six stages and that `tcw work stage inbox` is
refused — the sibling item's inbox prompt falsified both — and it described one
command where there are two, never naming the reading verb. Rewritten in
`81623de`. Task 5 had listed the second of those as its own work and it was
missed; the first was the sibling item's `capabilities.yaml` deferral, which said
the body would be rewritten at completion.

**`default/README.md`'s "Reading one" section named `begin`.** A section whose
whole subject is reading rather than entering, pointing at the entering verb.
Fixed with the rewrite of both `upcoming.md` files.

## Notes

Nothing shipped between this item and
`2026-09-01-separate-lifecycle-stage-information-from-stage-prompts-in-the-tcw-work-skill-references`,
so this item owned reconciling the release notes both had written. Both
`upcoming.md` files were rewritten rather than appended to: they carried the
sibling's claims that inbox "is the one stage you run without naming a work item"
and that "Every other stage is unchanged and still takes its work item", and this
release makes the first true only of `begin` and the second the break itself.

The `2.0.0` cut is deliberately the last step, after all three items complete —
`AGENTS.md` sequences it that way, and `cut_version.py` rotates the two
`upcoming.md` files this item spent its last task writing.


## Superseded within the same release

`begin` never shipped. `2026-09-09-make-stage-begin-the-gate-alone-and-bookend-the-prompt-with-its-lifecycle-position`
renamed it to `gate` and stopped it printing the instructions, both before 2.0.0
was cut, so what a user migrates from is 1.x's bare form to two verbs in one
edit.

Three findings above are the reason that item exists, and they read differently
now:

- **Criterion 6 — the two verbs print byte-identical stdout.** Recorded here as
  a pass, and it was: the criterion asked for exactly that. It was also the
  defect. Identical output is what made every view composing a stage out of both
  show the instructions twice, and what the stage documents' wording was twice
  rewritten to excuse. `gate` prints none of it.
- **The `--no-exec` header fix.** Still correct, and now moot in its particulars:
  both verbs take the flag, and each header names the verb that printed it.
- **"Is `prompt` worth its cost?"** Answered twice over. Its second caller, the
  composing skill, is joined by the CLI itself — `gate`'s success line names
  `prompt` as the verb that prints, so the split is now load-bearing inside the
  tool and not only in the plugin.

The acceptance criteria above were all met on the tree that existed when they
were written. They are not re-asserted against `gate`; that item carries its own.
