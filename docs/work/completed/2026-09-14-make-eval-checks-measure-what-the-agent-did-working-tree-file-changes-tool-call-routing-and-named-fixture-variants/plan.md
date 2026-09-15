# Plan — Make eval checks measure what the agent did

Implements `spec.md`. "AC n" means the spec's acceptance criteria. Each task is
one commit, leaves bare `pytest` green, and writes its tests first. Before writing
the code, confirm those tests fail against the current code.

## Tasks

### Task 1 — `files_changed_exactly` against the seeded commit (D1)

**Tests**

Create `tests/test_eval_files_changed.py`. It uses a helper that runs `git init`
in `tmp_path`, commits one file, and returns a run dictionary
`{"fixture": str(tmp_path), "seeded_head": <sha>}`. It has five tests:

- an uncommitted edit to the expected file passes;
- a committed edit to it passes;
- an extra untracked file fails;
- an unchanged expected file fails;
- a run without `seeded_head` fails, and its evidence names the missing key.

**Code**

- `evals/seed_fixture.py`: at the end of `seed()`, add
  `manifest["seeded_head"]` from `git rev-parse HEAD`.
- `evals/run_evals.py`: in `run_one`, add `"seeded_head": manifest["seeded_head"]`
  to `entry`, beside `"fixture"`.
- `evals/grade.py` `p_files_changed_exactly` (`:338-343`):
  - read `run.get("seeded_head")`, and return a failing `_verdict` if it is
    absent;
  - otherwise build the union of `git diff --name-only <seeded_head>` and
    `git ls-files --others --exclude-standard`, run in `run["fixture"]`.
- `evals/evals.json` `predicates.files_changed_exactly.reads`: "the working tree
  (committed, uncommitted and untracked non-ignored files) differs from the seeded
  commit in exactly these paths."
- Re-read B10's `paths` (`evals/evals.json:764` onward) against the fixed
  meaning. Record in `outcome.md` whether it changed, and why.

**Proof**

- AC 1: the new tests pass.
- `tests/test_eval_grading.py`, `tests/test_eval_runner.py` and
  `tests/test_eval_fixture.py` pass.
- Bare `pytest` is green.

### Task 2 — `tool_input_contains` and `tool_input_absent` (D2)

**Tests**

Add them to `tests/test_eval_grading.py`, built from in-memory transcripts in the
`stream-json` shape `evals/grade.py:load_events` reads. Use one assistant message with
a `{"type": "tool_use", "name": "Read", "input": {"file_path": "/x/skills/tcw-setup/references/project.md"}}`
block, and one user message with a `tool_result` block whose `content` mentions
another path. The tests show:

- `tool_input_contains` finds the `Read` path;
- `tool_input_contains` does not find the path that is only in the tool result,
  or only in assistant text;
- `tool_input_absent` is the mirror of both;
- `tool_input_absent` fails with "no tool calls found" on a transcript with no
  `tool_use` blocks.

**Code**

- `evals/grade.py`: add `_tool_inputs(events)`, yielding `json.dumps(block["input"])`
  for each content block with `type == "tool_use"`. Add two graders registered the
  way the existing `transcript_*` graders are.
- `evals/evals.json` `predicates`: declare both, with `family: transcript`,
  `args: ["text"]`, and `reads` lines stating what they read and what they ignore.

**Proof**

- AC 2 and AC 3.
- Bare `pytest` is green.

### Task 3 — Named fixture variants (D3)

**Tests**

- `tests/test_eval_runner.py:48-59`: rewrite the two tests to assert the four
  values in AC 4.
- `tests/test_eval_fixture.py`:
  - `:38` becomes `seed(root, "customized")`;
  - add a `bare` fixture and a test for AC 5.

**Code**

- `evals/seed_fixture.py`:
  - `seed(dest, variant="control")`, where `"customized"` runs today's
    `customized=True` path, `"control"` runs today's default, and `"bare"` writes
    and commits the code files, then returns early with empty `items`, `nonces`
    and `stage_items`, plus `seeded_head`;
  - an unknown variant raises `ValueError`;
  - `main()` maps `--customized` and a new `--bare` flag.
- `evals/run_evals.py`:
  - `variant_for` returns a string, and `case.get("fixture")` wins;
  - `:157` calls `seed(fixture, variant_for(case, arm))`;
  - `:271` prints `fixture: {variant_for(case, arm)}`.
- `evals/evals.json` `schema.case_fields`: add `fixture`.

**Proof**

- AC 4 and AC 5.
- AC 6: run `python -m evals.run_evals --axis b --dry-run` before and after the
  change, and diff the arm lists. Record it in `outcome.md`.
- `python evals/seed_fixture.py --bare /private/tmp/<dir>` builds a repository
  with no `tcw-config.yaml`.
- Bare `pytest` is green (AC 7).

### Task 4 — Note on the eval-run item

Add one line under `## Notes` in
`2026-09-11-run-the-eval-harness-and-act-on-what-it-finds`'s
`initial-request.md`. It says that `files_changed_exactly` now compares against
`seeded_head`, so earlier run directories fail it; that two tool-input predicates
and a `bare` fixture exist; and that the first real run must confirm the
`tool_use` transcript shape D2 assumes.

**Proof:** committed, and `tcw validate` exits 0.

## Documentation Sync

Evaluated with `tcw work docs`.

- **`docs/changelogs/upcoming.md` [Any-Code-Change] — fires.** Add Task 5 at the
  end:
  - Changed: `files_changed_exactly` compares against the seeded commit, and old
    runs without `seeded_head` fail it. `seed()` and `variant_for` take variant
    names.
  - Added: `tool_input_contains`, `tool_input_absent`, the `bare` fixture, and the
    per-case `fixture` key.
- **`README.md` [Public-API] — expected not to fire.** The eval harness isn't
  described there. Re-check at the documentation pass.
- **`docs/release-notes/upcoming.md` [Public-API] — expected not to fire.** No
  user-facing change.
- **`skills/<component>/SKILL.md` [Skill-Driven-Component] — does not fire.** No
  component's CLI changes.
- **`CLAUDE.md` § Measuring the skill layer** is not a documentation entry, but it
  names the harness commands. Re-read it. If `seed_fixture.py`'s flags or a
  documented behavior changed, update it in task 5 and say so in `outcome.md`.

## Verification

The suite covers ACs 1–5 and 7. The rest is checked by hand and recorded in
`outcome.md`:

1. **AC 6:** the before-and-after diff of `--dry-run` output.
2. **Mutation checks.** For each new test, temporarily revert the matching code
   change and confirm the test fails, then restore it. Record which test failed
   and why.
3. **Not verified here:** the real `tool_use` shape in a live run, which is left to
   the eval-run item (task 4).

## Notes

- **Traceability.**
  - AC 1 → task 1.
  - ACs 2–3 → task 2.
  - ACs 4–6 → task 3.
  - AC 7 → every task.
  - Task 4 carries the spec's Risks note.
- **Ordering.** Tasks 1–3 touch different functions. Task 3 is last because it
  changes `seed()`'s signature, which task 1's manifest change must already be in.
- **Blocks** `2026-09-14-restructure-tcw-s-skills-…`, whose eval cases use tasks 2
  and 3. That blocker is recorded.
