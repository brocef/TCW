# Outcome — Make eval checks measure what the agent did

`<base>` (the commit that last touched `plan.md`): `d47cbc14`. The branch started
from `fe735d94`; the item was started at `51ed1cf8`.

## What shipped, task by task

| Task | Commit | What |
| --- | --- | --- |
| start | `51ed1cf8` | `tcw work start` |
| 1 (D1) | `6a6c4863` | `files_changed_exactly` compares the working tree plus untracked non-ignored files with `seeded_head`; the seeder records it, the runner copies it into `timing.json`, `grade_run` passes it on; B10's paths re-read |
| 2 (D2) | `4c9635b3` | `tool_input_contains` and `tool_input_absent`, declared in `evals/evals.json` |
| 3 (D3) | `ee728c5d` | `seed(dest, variant)` with `customized`/`control`/`bare`, `--bare`, `variant_for` returns a name and honours a case `fixture` key, `case_fields.fixture` |
| 4 | `49a4b93b` | Note on `2026-09-11-run-the-eval-harness-and-act-on-what-it-finds` |
| 5 (docs) | `e9d4aa3b` | Changelog entry; `AGENTS.md` (which `CLAUDE.md` links to) gains the `--bare` command line |
| review fixes | `e0d90231` | See "Review" below |
| review docs | `55c7009d` | Changelog updated for the review fixes |
| follow-up | `1b16d6e9` | Inbox note for four defects the review found outside this item |

## Test result

- Bare `pytest` at `1b16d6e9`: **2833 passed** in 656 s.
- `python -m pytest` at `1b16d6e9`: **2833 passed** in 679 s.
- Bare `pytest` at `e9d4aa3b` (before the review fixes): 2828 passed. Before
  any change (`51ed1cf8`): 2812 passed.
- The intermediate commits `6a6c4863`, `4c9635b3`, `ee728c5d` and `49a4b93b`
  were each checked with every test module that imports `evals`
  (`test_eval_files_changed`, `test_eval_grading`, `test_eval_runner`,
  `test_eval_fixture`, `test_eval_coverage`, `test_tracker_absent`), all green,
  not with the full suite, which takes eleven minutes. Nothing else in the
  repository imports `evals`, and no file outside `evals/`, those tests and
  `docs/` changed.
- `import tcw` from the worktree root, and under bare `pytest` here, resolves to
  this worktree's `tcw/`. The `tcw` command on PATH runs the primary checkout's
  code; this item changes nothing under `tcw/`.

## Acceptance criteria

1. **AC 1:** `tests/test_eval_files_changed.py`. All five named tests failed
   against the old `HEAD~1 HEAD` check, each for its own reason: the uncommitted
   edit saw `['README.md']` (the seeder's last commit), the committed edit saw
   `[]` (an empty later commit), and the extra-untracked, unchanged-file and
   missing-`seeded_head` tests all passed wrongly. The seeding helper takes the
   file the seeder's last commit touches as an explicit argument, because that
   decides whether a test could pass against the old check by accident.
2. **AC 2:** `tests/test_eval_grading.py`. Before the code existed, the tests
   failed on the missing functions, and the same test asserted
   `transcript_contains` *does* find a path mentioned only in a tool result,
   which is the defect.
3. **AC 3:** both registry tests pass with both predicates declared.
4. **AC 4:** `tests/test_eval_runner.py`, plus the `with-skill` arm of a
   `fixture: bare` case.
5. **AC 5:** `tests/test_eval_fixture.py::test_the_bare_variant_is_a_repository_that_does_not_use_tcw`;
   the existing `customized` fixture now calls `seed(root, "customized")`.
6. **AC 6:** `python -m evals.run_evals --axis b --dry-run` output before (at
   `51ed1cf8`) and after (at `ee728c5d`) is byte-identical under `diff`: 20 arm
   lines, the same fixtures, the same commands. Axis A still prints
   `fixture: customized` / `fixture: control`.
7. **AC 7:** bare `pytest` passes (above).

`python evals/seed_fixture.py --bare /private/tmp/evalA-bare` built a repository
holding `README.md`, `src/` and `manifest.json`, with no `tcw-config.yaml` and a
clean `git status`. `--bare --customized` is refused by argparse.

## Mutation checks

Each was applied by hand, the named test watched go red for the stated reason,
and the change reverted.

| Broken | Red test | Why it went red |
| --- | --- | --- |
| `grade_run` no longer copies `seeded_head` | `test_grading_a_run_directory_carries_seeded_head_to_the_check` | evidence "the run entry has no `seeded_head`" |
| the `ls-files` half of the union removed | `test_an_extra_untracked_file_fails` | `stray.txt` not counted, verdict passed |
| the seeder no longer excludes `manifest.json` | `test_a_freshly_seeded_node_shows_no_changes[control, customized]` | `changed ['manifest.json'], expected []` |
| `_tool_inputs` also yields `tool_result` content | `test_a_path_only_mentioned_is_not_an_opened_file[…docs-sync.md]` | the result-only path counted as opened |
| `_tool_inputs` also yields `text` blocks | the `[…work.md]` case of the same test, and the no-tool-calls test | the prose-only path counted, and prose counted as a tool call |
| the "no tool calls found" guard removed | `test_tool_input_absent_fails_when_there_are_no_tool_calls_at_all` | `absent` passed vacuously |
| `tool_input_absent` renamed in `evals.json` | both registry tests | declared-but-unimplemented and implemented-but-undeclared |
| `variant_for` ignores `fixture` | `test_a_case_can_name_its_fixture` | `'customized' == 'bare'` |
| B10 given `"fixture": "Bare"` | `test_every_named_fixture_is_a_variant_the_seeder_builds` | `'Bare'` not in `VARIANTS` |

The review-fix tests (`test_a_seeded_head_git_cannot_resolve_fails_with_git_s_error`,
`test_a_missing_fixture_folder_fails`, `test_a_rename_counts_the_same_however_the_agent_moved_the_file`,
`test_a_bare_fixture_inside_a_tcw_project_is_refused`) were written first and
failed against the code before `e0d90231`: the first two passed wrongly with an
empty change list, the rename saw only `src/renamed.py`, and the bare seed did
not raise.

## B10's path list

**Changed.** `src/reports.py` was removed; `README.md` and
`docs/changelogs/upcoming.md` remain. The prompt says the user already fixed a
bug in `src/reports.py`, but the seeded fixture contains no such change, so
compared with the seeded commit that file appears only if the agent edits a file
the user says is done. It could not have passed under the old check either
without the agent editing it. The case's `note` says so.

## What the plan or spec got wrong

1. **`grade_run` needed changing.** The plan says the grader reads
   `run.get("seeded_head")`, but `grade_run` builds the `run` dictionary from
   selected `timing.json` keys, so `seeded_head` never reached the predicate.
   One line was added, with a test.
2. **The seeder's `manifest.json` is untracked.** `seed()` writes it after its
   last commit, so the planned union of `git diff` and `git ls-files --others`
   would list it in every run, and B10 (and the downstream item's B11,
   `files_changed_exactly ["tcw-config.yaml"]`) would fail for every agent. The
   seeder now appends `/manifest.json` to the fixture's `.git/info/exclude`, in a
   helper `_record` that the full and bare paths share.
3. **Task 4 said "under `## Notes`"**, and the eval-run item's
   `initial-request.md` had no such section. One was added at the end.
4. **The plan's `--customized`/`--bare` mapping** didn't say what both flags
   together mean; they are a mutually exclusive argparse group.
5. **The plan did not anticipate the review fixes** below, the most important
   being that a bare fixture inside a TCW project is not bare.

`plan.md` itself was left as approved; the differences are recorded here.

## Review

`adversarial-code-reviewer` on `fe735d94..e9d4aa3b`. It verified that every new
test failed against the old code for the reason named. Its verdict was NOT DONE.
Each finding was checked against the code before acting.

**Belongs to this change**

1. **HIGH — a bare fixture under TCW's own checkout is not bare. Accepted.**
   Verified: seeding `--bare` into `eval-runs/probe/fixture` inside this worktree
   and running `tcw validate` there printed `validate OK`, because
   `find_node_root` searches every parent folder. `seed()` now raises
   `ValueError` for a bare fixture whose parent is inside a TCW project, before
   building anything. Consequence for the downstream item: bare cases must run
   with `--out` outside this checkout. That is in the changelog.
2. **MEDIUM — git failures read as an empty change list. Accepted.** A
   `seeded_head` git cannot resolve, or a missing fixture folder, gave
   `changed []`, which passes a case expecting no changes. The check now runs
   git itself and fails with git's error text; `--` follows the commit.
3. **LOW — renames counted differently by how the file was moved. Accepted.**
   Verified with a staged `git mv`, which reported only the new path. Added
   `--no-renames`, and `-z` on both commands so unusual paths aren't quoted.
4. **LOW — a case's `fixture` value is never checked before a paid run.
   Accepted in part.** Added a test that every `fixture` is in `VARIANTS`.
   Rejecting `fixture` on axis A was not added: no case does it, and the spec
   allows any case to name one.
5. **LOW — evidence truncation and JSON escaping. Narrowed.**
   `ensure_ascii=False` added, so a non-ASCII search text can match. The
   140-character evidence cut was left: it only shortens a failing verdict's
   quote, which already names the tool call's index. Newline-spanning and
   relative-path matches are inherent to substring matching and are the
   downstream cases' concern.
6. **NOTE — the no-tool-calls guard fails an honest run that made no tool calls.
   No change.** That is the spec's chosen trade-off.

**Needs a separate change**, all four pre-existing and recorded in
`docs/work/inbox/2026-09-14-eval-runs-under-this-checkout-grade-and-behave-wrongly.md`:

- A. a default run's relative fixture path is doubled by `grade_run`, confirmed
  by reading the code;
- B. `manifest.json`, holding the axis A nonces, sits in the agent's working
  folder;
- C. fixtures under this checkout may load its `CLAUDE.md`/`AGENTS.md`;
- D. B10's prompt describes a fix that isn't in the fixture.

The reviewer also noted the untested `init.templateDir` case, where a template
without `info/` would make the exclude write fail. Not acted on: git's default
template has it, and nothing here sets one.

## Verification round 1

The verifier checked the multi review's findings against the code (Codex and the
adversarial reviewer both said NOT DONE) and asked for five fixes. Each test
below was written first and watched fail against the code at `b8ef8ab9`, for the
reason given. Then each fix was reverted by hand, the test watched go red again,
and the fix restored.

| # | Fix | Commit | Test, and why it was red |
| --- | --- | --- | --- |
| 1 | `_record` also excludes `__pycache__/` and `.pytest_cache/` | `7aa8ba3e` | `test_a_freshly_seeded_node_shows_no_changes[control, customized, bare]` (now covers `bare`): `changed ['.pytest_cache/…', 'src/__pycache__/reports.cpython-314.pyc'], expected []` |
| 2 | `refuse_bare_inside_a_project()` in `evals/seed_fixture.py`, used by `seed()` and by `run_evals.main()` for every bare arm before the dry run or the run loop; exits 1 | `7aa8ba3e` | `test_a_bare_case_under_a_tcw_project_is_refused_before_anything_runs`: the dry run returned 0 and listed commands. Counterpart `test_a_bare_case_outside_any_tcw_project_passes_the_check` |
| 3 | `seed()` refuses a `dest` that exists and is not empty, for every variant, before writing | `7aa8ba3e` | `test_a_folder_that_is_not_empty_is_refused[control, customized, bare]`: `bare` did not raise and committed the stray `tcw-config.yaml`; `control`/`customized` raised only later, from `tcw init`'s conflicting-id check, after `git init` and a commit |
| 4 | the `ls-files` call runs with `-c core.excludesFile=<null device>` | `7aa8ba3e` | `test_the_grading_machine_s_global_ignore_file_is_not_read` (a global config through `GIT_CONFIG_GLOBAL` ignoring `stray.txt`): verdict passed, `stray.txt` hidden |
| 5 | git output read as bytes, split on `\0`, decoded with `os.fsdecode` | `7aa8ba3e` | `test_a_carriage_return_in_a_file_name_survives`: `changed ['new\nname.txt', …], expected ['new\rname.txt', …]` |

- **Callers of `seed()` checked for non-empty folders.** The test fixtures use
  `tmp_path_factory.mktemp`, which gives an empty folder, or a path that does
  not exist yet. `run_one` seeds `<out>/<case>/<arm>/fixture`, which is new
  unless `--out` is reused, and reuse is now refused, as intended.
- **git accepts `-c core.excludesFile=/dev/null`.** `git status` ran with it,
  exit 0, nothing on stderr.
- **The axis B `--dry-run` output** is still byte-identical to the pre-item
  capture.
- **Recorded in the inbox note, not fixed here** (`a7546294`): `run_one` never
  writes `items` to `timing.json`; and the first paid run should list
  `git status --porcelain --ignored` for one fixture, to find what `claude -p`
  writes there.
- **Rejected by the verifier, so left as is:** backslash or quote search texts
  against JSON-escaped input; an empty `text` argument passing; submodules.
- **Tests:** the six eval test files give 111 passed at `7aa8ba3e`.
- **Changelog:** `882e43a0`.

## Documentation sync

From `tcw work docs` (source: config).

- `docs/changelogs/upcoming.md` [Any-Code-Change] — **fired.** Added and Changed
  entries, including that old run directories now fail `files_changed_exactly`.
- `README.md` [Public-API] — **did not fire.** `README.md` never mentions the eval
  harness; it is contributor tooling, not public CLI surface.
- `docs/release-notes/upcoming.md` [Public-API] — **did not fire.** No change a
  TCW user sees.
- `skills/<component>/SKILL.md` [Skill-Driven-Component] — **did not fire.** No
  component's CLI, model, lifecycle or guardrails changed.
- `CLAUDE.md` § Measuring the skill layer (not an entry; the plan asked for a
  re-read) — `seed_fixture.py` gained `--bare`, so one command line was added.

## Not verified here

- The real `stream-json` tool-call shape the tool-input predicates assume. The
  eval-run item's note says the first real run must confirm it.
- Whether B10's reduced path list matches what agents actually change; only a
  paid run shows that.
