# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- **Procedures** — non-stage instruction text a project may replace.
  `PROCEDURE_IDS` (`tcw/store/base.py`): `unattended-work`, `triage-issues`,
  `documentation-sync`, `post-mortem`, `create-work`, `audit-backlog`,
  `consolidate-plans`, `decompose`, `delegation`, `search`. Defaults ship as
  `tcw/work/procedures/<id>.md` (package data), verbatim copies of the matching
  skill body or `skills/tcw-work/references/procedures/*.md`;
  `tests/test_shipped_procedures.py` fails if a copy and its source diverge.
  `load_builtins()` returns them as `Builtins.procedures`, refusing a missing or
  empty file like a stage prompt (shared `_load_texts`).
- **`work.procedures`** config: `parse_procedures()` (pure), one plain binding
  list per id with `PROMPT_KINDS`, parsed by `_parse_binding_list` with role
  `procedure`; an empty list is refused. `LifecyclePolicy.procedures` /
  `.procedure(id)`, filled by `FsWorkStore.lifecycle_policy()`; problems and
  `file:` checks reported through `lifecycle_problems()`.
- **`resolve_procedure()`** (`tcw/work/resolve.py`): the `builtin` floor and
  composition of `resolve_prompts`; `generate:` hooks see role `procedure`.
- **`tcw work procedure prompt <id> [ref] [--no-exec]`**: no bookend, no status
  note, no harness check. When every binding was skipped by its `when:`, a note
  goes to stderr (exit 0, empty stdout).

- **`tcw work stage validate [words…]`** (`tcw/work/cli.py`): reports whether a
  `tcw-work-stage` invocation's arguments are ones `tcw work stage prompt` would
  accept — a known stage id, no item for `inbox`, otherwise an optional
  reference resolving to exactly one item; status is not judged. Valid: no
  output, exit 0. Invalid: a Markdown usage error plus the reason on stdout,
  exit 1 (`_resolve`'s stderr message is captured into the reason). Under a
  harness other than Claude Code, a notice that injected commands must be run
  by hand is printed first, even when valid.
- **`tcw/harness.py`**: `ancestor_programs()` walks the process's ancestors via
  `ps`, falling back to `/proc`, and never raises; `detect()` returns the
  nearest `claude`/`codex` ancestor's harness, else `other` when
  `CODEX_THREAD_ID`, `CODEX_SANDBOX` or `CODEX_SESSION_ID` is set, else
  `claude`.
- **`skills/README.md`**: the two rules deciding whether a project may replace
  what a shipped skill says — Rule 2 (a document with no procedure of its own
  has nothing to override), checked first, then Rule 1 (TCW owns the shape of
  what is produced, the project owns the conduct) — why a project cannot add a
  procedure id of its own, and a verdict with a reason for every `SKILL.md`,
  every file under a skill's `references/`, and every `agents/*.md`.
- **`dynamic_skill: true|false`** in the frontmatter of all sixteen
  `skills/*/SKILL.md`, as a top-level key with a trailing comment pointing at
  `../README.md`. Read by people only; neither harness acts on it. `true` for
  `tcw-extras-autonomous-work`, `tcw-extras-triage-issues`,
  `documentation-sync`, `tcw-post-mortem`, `tcw-work-create` and
  `tcw-work-stage`; `false` for the rest. No skill body changed.
- **`tests/test_dynamic_skill_marker.py`**: fails when a shipped skill,
  reference document or agent has no verdict row (or more than one), when a row
  names no shipped file, when a skill lacks `dynamic_skill` or its comment, or
  when the value disagrees with the row's verdict.

## Changed

- `resolve_prompts` delegates to a private `_compose()` shared with
  `resolve_procedure`; stage resolution is unchanged.

- `skills/tcw-work-stage/SKILL.md` injects
  `` tcw work stage validate -- $stage $item 2>/dev/null || true `` ahead of its
  heading. `2>/dev/null` keeps an older `tcw` without the verb silent; named
  arguments rather than `$ARGUMENTS`, because extra words reaching the shell
  unquoted could make the line exit non-zero and cancel the skill load.
- `skills/tcw-work/SKILL.md` and `references/commands.md` no longer link or name
  the `references/lifecycle/stage-*.md` documents. The router sends agents to
  `tcw-work-stage` in an emphasized note; `commands.md` gains a `validate` row.
- `tcw-commands-plan-work`, `tcw-commands-verify-work`,
  `tcw-commands-process-inbox`, `tcw-commands-drive-work-to-completion`,
  `tcw-post-mortem` and `tcw-extras-triage-issues` invoke `tcw-work-stage`
  instead of reading stage documents. `agents/tcw-verifier.md` names the
  `verify` stage rather than its file.
- `skills/tcw-work/references/procedures/delegation.md`, `epic-deltas.md` and
  `commands.md` no longer describe "the stage documents" as what to follow or
  hand a subagent; they name the stage as `tcw-work-stage` delivers it.
- `stage` subparser metavar is `{prompt,gate,validate}`.
- `skills/tcw-work-stage/SKILL.md` headings renamed: "How to work it" →
  "Lifecycle stage contract", "What this project asks for" → "Stage
  instructions", "Before you act on any of that" → "Stage pre-checks" (now one
  line: run `tcw work stage gate` if not done). The command block moved to a
  "Document command summary" section listing the injected commands in order,
  with `gate` shown separately as the one to run yourself. `evals/grade.py`
  `BLOCK_HEADINGS` and the `evals/evals.json` case text follow the new headings.
- `skills/tcw-extras-autonomous-work/SKILL.md` injects
  `` tcw work procedure prompt unattended-work || true `` in place of its
  "The advisors" and "Checkpoint map" sections, which now exist only in
  `tcw/work/procedures/unattended-work.md`; that default lost the title,
  opening, "Ask once", hard blockers and audit trail, which stay in the skill.
  The skill gains a fixed "What an advisor must be" section (independent,
  read-only, two wanted, answers weighed not counted), a "Document command
  summary" fallback, and `allowed-tools` / `compatibility` frontmatter
  describing the default (`Bash(tcw *)`, `Bash(codex *)`, `Bash(git merge *)`,
  `Agent`, `SendMessage`). "the two advisors" → "the advisors" and "both
  call" → "all of them call". `tests/test_shipped_procedures.py` treats a
  source containing `tcw work procedure prompt <id>` as converted and asserts
  none of the default's paragraphs remain in it; new
  `tests/test_unattended_work_skill.py`.

## Fixed

- `skills/documentation-sync/SKILL.md` cited steps 4, 6 and 9 of the stage
  documents; they are steps 1, 3 and 5.

## Removed

- `skills/tcw-work/references/lifecycle/default/README.md`, which pointed at
  `tcw/work/prompts/*.md` — files that ship with the Python package, not the
  plugin.

## Internal

- `tests/test_skill_lifecycle_parity.py`: the router test now asserts that
  nothing in `tcw-work` outside `references/lifecycle/` names a stage document,
  the orphan check exempts `references/lifecycle/`, and new tests require the
  bold `tcw-work-stage` note and the validation line as the stage skill's first
  injected command. New `tests/test_harness.py` and
  `tests/test_stage_validate.py`. `tests/test_eval_grading.py` checks that the
  grader's block headings appear in the stage skill.
