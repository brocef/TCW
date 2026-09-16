# Plan — Compose the five tcw-work procedure documents from project bindings

Implements `spec.md`. Every task runs from the worktree root with
`PATH="$PWD/.venv/bin:$PATH"`, so `tcw` is this worktree's code.

The test change and each document's conversion must land in the same commit:
the drift test compares a default with its source, and a commit that moves text
out of one without the other is red. So task 1 writes the test machinery with
`CONVERTED` empty (green), and each conversion task adds its id to `CONVERTED`
in the commit that converts the document — watching the test go red first with
only the id added.

## Tasks

### 1. Test machinery for a converted document

Modifies `tests/test_shipped_procedures.py`.

- Add `CONVERTED: set[str] = set()` below `SOURCES`, with a comment saying a
  converted id's source now points at the command and must not carry a copy.
- Add `_paragraphs(text)`: blocks split on blank lines, whitespace-normalized,
  dropping headings (first line starts with `#`) and blocks under 40 characters.
- In `test_each_default_is_todays_text`, for `pid in CONVERTED`: assert the
  source contains `tcw work procedure prompt {pid}`, and that
  `_paragraphs(source) & _paragraphs(default)` is empty, naming the shared
  paragraphs in the failure. Otherwise the existing equality assertion.
- Add `test_the_backlog_auditor_reads_the_procedure`: `agents/tcw-backlog-auditor.md`
  contains `tcw work procedure prompt audit-backlog`, none of the six check names
  from spec criterion 3, and its `tools:` line contains `Bash`. Expected red
  until task 4 — so this test is added in task 4, not here.

Proves: `pytest tests/test_shipped_procedures.py -q` green (nothing converted yet).

### 2. Convert `delegation.md` (first, per the request)

Modifies `skills/tcw-work/references/procedures/delegation.md`,
`tcw/work/procedures/delegation.md`, `tests/test_shipped_procedures.py`.

1. Add `"delegation"` to `CONVERTED`; run the test; watch it fail on the missing
   command string (and shared paragraphs).
2. Default: `# Delegation`, a blank line, then `## What makes it correct` through
   the end of `## The shape this produces`, verbatim.
3. Document: `# Delegation`, the pointer paragraph, then the original `:3-26`
   with `:22` reworded, then `## Custom agents` with `:68-69` reworded (spec,
   "Criterion 8").
4. Test green; criterion-8 grep over the document prints nothing.

Proves: spec criteria 1, 2, 4, 5 for `delegation`.

### 3. Convert `audit-backlog.md`, `consolidate-plans.md`, `decompose.md`, `search.md`

One commit per document, each in the same three steps as task 2 (id into
`CONVERTED` and watch it fail; write default; write document), splitting per
the spec's "What is fixed, per document" table. Files per commit: the document,
its `tcw/work/procedures/<id>.md`, and `tests/test_shipped_procedures.py`.

For `decompose.md` the default keeps its bullet list with the one conduct bullet
(`:17-20`); the document keeps the two nesting bullets under a sentence
introducing them, and "Which path?" verbatim.

Proves: spec criteria 1, 2, 4, 5 for the four.

### 4. Stop the auditor carrying the checks

Modifies `agents/tcw-backlog-auditor.md`, `tests/test_shipped_procedures.py`.

1. Add `test_the_backlog_auditor_reads_the_procedure` (task 1's text); watch it
   fail on the missing command string.
2. Rewrite the agent as the spec's "The auditor agent" section says: description
   without the six checks; keep role, scope, "What you are given", "Hard limits";
   replace `:25-68` with a "What to check and how to report" section pointing at
   `tcw work procedure prompt audit-backlog <slug>`; closing line names the
   procedure id.
3. Test green; criterion-8 grep over the agent prints nothing.

Proves: spec criteria 3 and 4.

### 5. Ledger

Modifies `docs/work/active/<slug>/capabilities.yaml` (new, `changed:
skills/tcw-work`) and `docs/capabilities/skills/tcw-work/description.md` (one
sentence: a project may replace the text of these procedures, and of decomposing
and delegating, under `work.procedures`, with TCW's text as the default and the
safety rules kept).

Proves: `tcw capabilities check` exits 0 (spec criterion 8).

### 6. Targeted suite and the "nothing configured" proof

No file changes. Run `tests/test_shipped_procedures.py`,
`test_skill_lifecycle_parity.py`, `test_dynamic_skill_marker.py`,
`test_documented_cli_surface.py`, `test_skill_path_pointers.py`,
`test_plugin_manifests.py`, `test_procedure_config.py`,
`test_resolve_procedure.py`. Mutation check for spec criterion 2: paste one
default paragraph back into `search.md`, see the test fail naming it, edit it
back, confirm `git diff` is empty.

Build the composed reading per document — the document with the command's output
spliced in at the pointer — in the scratchpad, and diff against
`git show main:<path>`. Record in `outcome.md`.

### 7. Documentation Sync

- **`README.md` [Public-API]** — fires narrowly: the agent table row for
  `tcw-backlog-auditor` (`README.md:703`) lists the default's checks; reword to
  "Checks one backlog item against your project's backlog-audit procedure (by
  default: …)". No CLI surface change.
- **`docs/release-notes/upcoming.md` [Public-API]** — fires: one bullet at the
  end of "Replacing TCW's own procedures": auditing, consolidating, splitting,
  delegating and searching now read the project's replacement text.
- **`docs/changelogs/upcoming.md` [Any-Code-Change]** — fires: one bullet at the
  end of "Changed" (the five documents and the agent), one at the end of
  "Internal" (`CONVERTED` in the drift test).
- **`skills/<component>/SKILL.md` [Skill-Driven-Component]** — evaluate: no CLI,
  model, lifecycle or guardrail changes; `tcw-work/SKILL.md`'s links still
  resolve. Expected not to fire; not owned by this child regardless.
- **`skills/tcw-configure/references/<document>.md` [Configuration-Key-Change]**
  — does not fire: no key added or changed; `work.md` already lists the ids.
- **`docs/guide/jira.md` [Tracker-Change]** — does not fire.

One docs commit.

### 8. Full suite and `outcome.md`

Bare `pytest -q -p no:cacheprovider` once, in the background, on the final code
commit. Then write and commit `outcome.md` with the diff proof, decisions and
deferred live checks.

## Verification

What the suite cannot check:

- **That a reader follows the pointer.** Only a live session opening the
  document shows whether an agent runs the command before acting. Deferred to
  `verify`.
- **That a dispatched auditor runs the command and audits against a replaced
  procedure.** Needs a live Claude Code dispatch with a `work.procedures.audit-backlog`
  binding. Deferred to `verify`.
- **Codex reading the documents.** Deferred to `verify`.
- **"Nothing configured = today's text"** is shown by a diff, not a test,
  because `main` moves; task 6 records it.

## Notes

- **Gate refusal recorded.** `tcw work stage gate plan <slug>` exited 1: "'plan'
  is not legal for an item in 'active'; it runs in backlog". The pre-check the
  `plan` stage binds, `TCW_SLUG=<slug> python scripts/require_artifact.py spec`,
  was run by hand and exited 0.
- No blockers to record; siblings are parallel by design.
