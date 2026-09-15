# Spec — Make eval checks measure what the agent did

## Capability changes

None.

- The eval harness is contributor tooling for measuring this project's own
  skills. It isn't something a TCW user can do, and no capability in
  `docs/capabilities/` describes it.
- No taxonomy entry is touched.

## Problem

1. **`files_changed_exactly` measures commits, not changes.**
   - `p_files_changed_exactly` (`evals/grade.py:338-343`) runs
     `git diff --name-only HEAD~1 HEAD`, but its declaration says "against the
     seeded HEAD" (`evals/evals.json:158-163`).
   - An agent that edits the right file but doesn't commit fails.
   - If the agent made no commit at all, the check compares the seeder's own last
     commit instead.
   - A commit that also touches another file fails, even when the extra file was
     committed separately and earlier.
   - Case B10 relies on this check today (`evals/evals.json:764` onward).
2. **Routing checks can't tell reading from mentioning.**
   - `transcript_contains` and `transcript_absent` search `_texts()`
     (`evals/grade.py:84-106`). That list includes every text, content and input
     field of every message, tool call and tool result.
   - When a loaded skill's body *mentions* a document path, it passes
     "`transcript_contains <path>`" even though the agent never opened that
     document.
3. **Fixture variants are a true/false flag.**
   - `seed(dest, customized=False)` (`evals/seed_fixture.py:348`) and
     `variant_for(case, arm) -> bool` (`evals/run_evals.py:112-119`) can express
     only "customized" or "control".
   - There is no fixture for a repository that doesn't use TCW yet.
   - A case cannot choose its fixture.

## Goals

1. `files_changed_exactly` compares the working tree, including untracked
   non-ignored files, with the commit the seeder left, so it no longer matters
   whether the agent committed.
2. Two new predicates, `tool_input_contains` and `tool_input_absent`, look only at
   tool-call inputs. Those are the commands the agent ran and the files it
   opened.
3. Fixture variants are named (`customized`, `control`, `bare`), and a case can
   pick one with an optional `fixture` key.
4. Every change is covered by tests that fail against today's code, and bare
   `pytest` stays green.

## Non-goals

- New or changed eval cases, other than keeping B10 correct under the fixed check.
  The cases that use the new predicates and the `bare` fixture are in
  `2026-09-14-restructure-tcw-s-skills-…`.
- Running the paid harness.
- Making `runner: codex` work. `run_evals.py`'s `command()` always runs `claude`,
  which the parent's third review noted as a separate defect.
- Checking `invokes` during grading. That is a separate defect, from the same
  review.

## Design

### D1 — `files_changed_exactly` against the seeded commit

- **The seeder records its commit.** `seed()` returns `seeded_head`, the output of
  `git rev-parse HEAD` after its last commit, in its manifest.
- **The runner passes it on.** `run_one` (`evals/run_evals.py:157` onward) copies
  `manifest["seeded_head"]` into the run entry it writes to `timing.json`, next to
  `fixture`.
- **The grader uses it.** It computes the changed set as the union of:
  - `git diff --name-only <seeded_head>`, which compares the working tree with that
    commit and so includes committed and uncommitted changes;
  - `git ls-files --others --exclude-standard`, which lists untracked, non-ignored
    files.

  A run entry without `seeded_head`, such as a run recorded before this change,
  gets a failing verdict that says so. It does not quietly fall back to the old
  behavior.
- **Declaration and B10.** The predicate's `reads` text in `evals/evals.json` says
  exactly this. B10's `paths` list is re-read against it, and changed only if the
  corrected check shows the list was wrong.

### D2 — Predicates over tool-call inputs only

- **Helper.** A new helper in `evals/grade.py` yields, in order, the JSON
  serialization of the `input` of every content block whose `type` is
  `tool_use`. Assistant text, user messages and tool *results* are excluded.
- **Predicates.**
  - `tool_input_contains(text)` passes when some tool input contains `text`.
  - `tool_input_absent(text)` passes when none does.
  - Both are registered exactly like the existing transcript graders, and declared
    in `evals/evals.json` `predicates` with `family: transcript`, `args: ["text"]`,
    and a `reads` line.
- **What they measure.** The agent opening a file shows up as a `Read` tool input
  (`file_path`), or as a shell command (`cat …`) in a `Bash` tool input. Both are
  caught.

### D3 — Named fixture variants

- **`seed(dest, variant="control")`** accepts `"customized"`, `"control"` or
  `"bare"`, replacing `customized: bool`.
  - `"customized"` and `"control"` behave exactly as `customized=True` and `False`
    do today.
  - `"bare"` writes and commits the fixture's code files only. It runs no
    `tcw init` and nothing after it, and returns a manifest with empty `items`,
    `nonces` and `stage_items`, plus `seeded_head`.
- **`main()`** keeps `--customized` and adds `--bare`.
- **`variant_for(case, arm) -> str`**:
  - returns `case["fixture"]` when present;
  - otherwise returns `"customized"`/`"control"` for axis A, as today, and
    `"customized"` for both axis B arms.

  Its callers (`evals/run_evals.py:157`, `:271`) pass and print the name.
- **Schema.** `evals/evals.json`'s `case_fields` documents `fixture` ("optional;
  a named fixture variant; only `bare` is used today").

## Acceptance criteria

1. A test builds a real git repository in a temporary directory, seeds and
   commits, records `seeded_head`, and asserts that `files_changed_exactly`:
   - passes for an uncommitted edit to exactly the expected file;
   - passes for a committed edit to exactly the expected file;
   - **fails** when an extra untracked, non-ignored file exists;
   - **fails** when the expected file is unchanged;
   - **fails** when the run entry has no `seeded_head`.

   Each of these tests fails against the grader as it stood before this item.
2. Tests using hand-built transcripts assert that `tool_input_contains <path>`:
   - passes when a `tool_use` block's input holds the path;
   - **fails** when the path appears only in a tool result or in assistant text.

   They also assert that `tool_input_absent` behaves as the mirror image, and
   **fails** with "no tool calls found" on a transcript that has no `tool_use`
   blocks at all.
3. `test_every_declared_predicate_has_a_grader` and
   `test_no_grader_exists_for_an_undeclared_predicate` pass, with both new
   predicates declared.
4. `tests/test_eval_runner.py` asserts:
   - `variant_for({"axis": "A"}, "customized") == "customized"`;
   - `variant_for({"axis": "A"}, "control") == "control"`;
   - `variant_for({"axis": "B"}, "with-skill") == "customized"`;
   - `variant_for({"axis": "B", "fixture": "bare"}, "no-skill") == "bare"`.
5. `tests/test_eval_fixture.py`:
   - seeds `"bare"` and asserts there is a `.git`, no `tcw-config.yaml`, empty
     `nonces` and `stage_items`, and a `seeded_head` equal to the repository's
     `HEAD`;
   - asserts `tcw validate` does not exit 0 there;
   - still passes its existing `control` and `customized` tests, called with the
     new keyword (today `seed(root, customized=True)` at `:38`).
6. `python -m evals.run_evals --axis b --dry-run` lists the same arms it listed
   before this item.
7. Bare `pytest` passes.

## Risks

- **Grades change for past runs.** A run directory recorded before this change has
  no `seeded_head`, so `files_changed_exactly` now fails there instead of giving an
  answer that was misleading anyway. The changelog entry says so.
- **B10's expected list may turn out wrong.** Measured properly, it could fail in
  an arm where it used to pass. D1 re-checks the list, but only a real run shows
  what agents change.
- **Tool input shape.** D2 assumes the `stream-json` transcript shape that
  `evals/grade.py` already parses: content blocks with `type: tool_use` and an
  `input` object. A transcript in another shape yields no tool inputs, so
  `tool_input_absent` would pass vacuously. The committed grading fixtures
  (`tests/fixtures/eval_grading/*/transcript.jsonl`) contain no tool calls, and
  there is no recorded run in `eval-runs/` to copy one from. So the tests use a
  hand-built block in Claude Code's documented `stream-json` shape
  (`{"type": "tool_use", "name": "Read", "input": {"file_path": …}}`).
  - **Not verified here:** that shape against a real run. The first paid run
    (`2026-09-11-run-the-eval-harness-…`) must confirm it, and this item's note on
    that item says so.
  - **Guard:** to keep a wrong shape from hiding, `tool_input_absent` fails with
    "no tool calls found" when a transcript has no `tool_use` blocks at all.
