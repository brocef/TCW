# Plan: separate lifecycle stage information from stage prompts

Five code/document tasks, then one documentation block. Every task ends at a
commit boundary where `pytest -q` is green — which is the constraint that
decided the grouping below, not tidiness.

**Baseline, measured at the end of the `plan` stage** so "green" means something
specific: `pytest -q` → 2168 passed in 559s; `tcw validate` → exit 0;
`tcw capabilities check` → exit 0. The suite takes just over nine minutes, so
budget for that at each of the five commit boundaries rather than skipping it.

## Sequencing constraint that shaped this plan

Three of the tasks below look separable and are not:

- Moving the reference files breaks `tests/test_skill_lifecycle_parity.py` and
  `tests/test_documentation_sync_wiring.py` from the moment the first `git mv`
  runs until their path constants follow. Move, test-paths, and link-rewrite are
  therefore one commit (Task 1).
- Rewriting `stage-inbox.md` into a short pointer is only correct once
  `tcw work stage inbox` works, and flipping the parity test's `ROUTER_IDS` to
  include `inbox` is only green once that document is under 40 lines and shares
  no sentence with a prompt that must already exist. Prompt, CLI, router, and
  tests are therefore one commit (Task 3).

## Task 1 — move the reference files and rewrite every link

**Creates/modifies:**

- `git mv` into `skills/tcw-work/references/lifecycle/`: `stage-inbox.md`,
  `stage-request.md`, `stage-spec.md`, `stage-plan.md`, `stage-implement.md`,
  `stage-verify.md`, `stage-postmortem.md`
- `git mv` into `skills/tcw-work/references/procedures/`: `decompose.md`,
  `delegation.md`, `audit-backlog.md`, `consolidate-plans.md`
- `tests/test_skill_lifecycle_parity.py` — `stage_doc()` resolves under
  `REFS / "lifecycle"`; `test_no_stage_document_exists_for_an_unknown_id` globs
  that folder; `test_no_reference_filename_carries_an_ordinal` and
  `test_the_router_routes_to_every_reference_file` switch `glob` → `rglob`, and
  the latter matches each file by its path relative to `references/` so a link
  written `references/lifecycle/stage-spec.md` counts as reaching it
- `tests/test_documentation_sync_wiring.py` — the two `LIFECYCLE_REFS` paths
  gain `lifecycle/`
- Link rewrites, with the count found by the grep in the spec's criterion 11:
  `skills/tcw-work/SKILL.md`, `skills/tcw-post-mortem/SKILL.md`,
  `skills/tcw-triage-issues/SKILL.md`, `skills/documentation-sync/SKILL.md`,
  `skills/tcw-plugin/SKILL.md`, `agents/tcw-verifier.md`,
  `commands/tcw-verify-work.md`, `commands/tcw-plan-work.md`,
  `commands/tcw-drive-work-to-completion.md`, `commands/tcw-triage-issues.md`,
  `commands/tcw-process-inbox.md`
- Relative links **inside** the moved files: `stage-*.md` cross-reference
  `epic-deltas.md`, `delegation.md`, `decompose.md`, and `commands.md`, all of
  which are now at a different depth. `delegation.md` and `decompose.md` are
  siblings from `procedures/` but `../` away from `lifecycle/`; the rest are
  `../`. Every one is checked, not assumed.

**Do the moves before touching any file's contents**, in their own `git mv`
calls, so rename detection survives.

**Proves it:** `pytest -q` green. The spec's criterion 11 grep prints nothing.
`git log --follow skills/tcw-work/references/lifecycle/stage-spec.md` reaches
commits from before this item (criterion 9).

**Covers:** criteria 1, 9, 11, 12.

## Task 2 — the pointer sentence in the six existing routers

**Modifies:** `skills/tcw-work/references/lifecycle/stage-request.md`,
`stage-spec.md`, `stage-plan.md`, `stage-implement.md`, `stage-verify.md`,
`stage-postmortem.md`.

In each `## Purpose`, replace the clause "`tcw work stage <id> <slug>` prints
the methodology; this document carries only what the CLI cannot" with:

> Get your instructions on how to produce the output by running
> `tcw work stage <id> <slug>`.

Each document keeps its own one-line statement of what the stage is for — that
line is the `Purpose` section and is not the clause being replaced. The dropped
explanation of the division of labour is restated once in `SKILL.md` in Task 5,
not seven times here.

**Proves it:** `pytest -q` green — in particular
`test_no_router_sentence_appears_in_its_prompt`, since the new sentence appears
in no prompt, and `test_each_router_stays_within_its_ceiling`, since the
replacement is not longer than what it replaces.
`git grep -c "Get your instructions on how to produce the output by running" -- skills/tcw-work/references/lifecycle/`
reports 6 (7 after Task 3).

**Covers:** criterion 8 (six of seven).

## Task 3 — ship the built-in `inbox` prompt and open the command to it

The one task with real risk. Written test-first: the assertions below are added
and confirmed red before any of the code changes land.

**Creates:** `tcw/work/prompts/inbox.md`.

Condensed from the current `stage-inbox.md` — which Task 1 moved and this task
overwrites, so **read the pre-Task-1 version side by side while writing it**
(`git show HEAD~2:skills/tcw-work/references/stage-inbox.md`, adjusted for
however many commits have landed). Carry over, as content rather than trimming
stock: the one-item-or-several judgment; the tag-vocabulary step; the
`inbox accept` naming rules and the `--title` override; the instruction to
collect links and attachments under `## References` with a reason each; the
instruction **not** to ask the requester for more here, because they are absent
and the `request` stage asks; and all three `Exit badly` branches (too vague to
title, duplicates an existing item, is really several items).

Leave out, because they are router material Task 3 keeps in the document:
delegability, the `[gated]`/`[judgment]` markers, and every named sub-skill —
`tests/test_shipped_prompts.py::test_no_prompt_names_a_sub_skill` refuses those
in a prompt, and a skill name means nothing to a user with no plugin.

Also leave out "run `tcw work lifecycle --stage inbox` and honor what it
reports": that instruction is circular inside the text the command prints, and
`test_no_prompt_tells_the_agent_to_ask_what_it_is_reading` refuses it.

Target 50 lines; if the material genuinely does not fit, the spec's first risk
applies — cut prose, never a rule, and say in `outcome.md` what was cut.

**Modifies:**

- `tcw/work/resolve.py:65` — `sorted(set(STAGE_IDS) - {"inbox"})` becomes
  `sorted(STAGE_IDS)`; the docstring above it, which explains the exclusion,
  is rewritten to say the set is now every stage.
- `tcw/work/cli.py:1455` — `pstg.add_argument("slug")` gains `nargs="?"`, and
  the parser's `help` says the reference is omitted for `inbox`.
- `tcw/work/cli.py` `_stage` — the `if not STAGE_STATUSES[step.id]:` refusal at
  785-790 becomes an `inbox` branch: resolve the store with `_store()`, skip the
  item lookup and the status-legality check entirely, run `pre` checks with
  `item=None`, and call `resolve_prompts(..., item=None)`. Before that branch,
  refuse `tcw work stage inbox <anything>` — "the `inbox` stage runs before an
  item exists and takes no work item" — and after it, refuse a missing reference
  for the other six. `STAGE_STATUSES["inbox"]` stays `()` in
  `tcw/store/base.py:954`; the branch is chosen by stage id, never by
  re-reading an empty tuple as "any status".
- `tests/test_shipped_prompts.py` — `SHIPPED` becomes `set(STAGE_IDS)`;
  `test_every_stage_but_inbox_ships_a_prompt` is renamed to
  `test_every_stage_ships_a_prompt` and asserts the set equals `STAGE_IDS` with
  `inbox` **in** it.
- `tests/test_stage_verb.py` — `test_inbox_is_rejected_with_its_reason` and
  `test_inbox_still_ships_no_prompt` are replaced by
  `test_inbox_prints_its_prompt_with_no_item` (exit 0, prompt on stdout, stderr
  empty) and `test_inbox_refuses_a_work_item_argument` (exit 1, stdout empty,
  stderr says the stage takes no work item).
  `test_each_row_is_what_the_lifecycle_contract_says` keeps `"inbox": ()` and
  gains a comment that the empty tuple now means "no item status applies", not
  "refused". The `for sid in STAGE_IDS if sid != "inbox"` config fixture at line
  233 is checked: it configures a `blob` per stage, and including `inbox` would
  change what the byte-identical-folder test at line 225 exercises — leave it
  excluded and comment why, since that test walks item folders and `inbox` has
  no item.
- `tests/test_skill_lifecycle_parity.py` — `ROUTER_IDS` becomes `STAGE_IDS`;
  the `inbox` branches drop out of
  `test_every_stage_document_has_the_sections_in_order` and
  `test_every_stage_document_names_the_harness_neutral_binding_command`; the
  module docstring's note about `inbox` keeping its own methodology is rewritten.
- `skills/tcw-work/references/lifecycle/stage-inbox.md` — rewritten as a router
  under 40 lines with four sections (`Purpose`, `Inputs`, `Produce`, `Steps`),
  carrying the Task 2 pointer sentence as `tcw work stage inbox` with no
  reference. `Produce` keeps the words "no lifecycle artifact"
  (`test_a_stage_producing_nothing_says_so_explicitly`). `Steps` keeps: not
  delegable because interactive (`../procedures/delegation.md`), the
  `inbox accept` `[gated]` marker, and the pointers to `tcw-triage-issues` and
  `../procedures/decompose.md`.

**Proves it:** `pytest -q` green. Then, run by hand and recorded in
`outcome.md`:

```sh
tcw work stage inbox                      # exit 0, prompt on stdout, stderr empty
tcw work stage inbox some-slug            # exit 1, stdout empty
python -c "from tcw.work.resolve import load_builtins; print(sorted(load_builtins().stage_prompts))"
wc -l tcw/work/prompts/inbox.md           # <= 50
```

Criterion 4 — that `tcw work stage spec <slug>` still prints exactly what it
printed before — is the regression this task is most likely to cause, since it
moves the branch that runs ahead of every stage. It is already guarded twice:
`tests/test_stage_verb.py` compares all six stages against `load_builtins()`,
and `tests/test_prompt_fallback.py` pins the output against a fixture captured
before any of this existed. Neither is modified by this task; if either goes red
the branch is in the wrong place.

**Covers:** criteria 1, 2, 3, 4, 5, 6, 7, 8 (the seventh document).

### Running the lifecycle while the lifecycle is under change

This task edits `tcw/work/cli.py` and `tcw/work/resolve.py` against an editable
install, so the `tcw` binary driving this work item **is** the code being
changed. Sequence the status moves clear of the edits:

- `tcw work start <slug>` before Task 1, while the tree is clean.
- No `tcw work` command is run between the first edit in Task 3 and its green
  `pytest -q`. If one is needed and behaves oddly, that is the change under
  test, not the store — stop and re-run the suite rather than working around it.
- `tcw work submit` / `complete` only after Task 6, on a green tree.

## Task 4 — the defaults note

**Creates:** `skills/tcw-work/references/lifecycle/default/README.md`.

States: the built-in prompts live at `tcw/work/prompts/*.md` inside the
installed `tcw` package; they are there and not here because `pyproject.toml`
ships only the `tcw*` packages, so a project that installs from PyPI without the
plugin must still get them; read one with `tcw work stage <id> <ref>` (no
reference for `inbox`); a project's own `prompt:` bindings replace the built-in
outright, and `builtin: true` in that list puts it back, composed in declaration
order. Points at `../../hooks.md` for the binding shapes rather than restating
them, and reproduces no prompt body.

**Proves it:** criterion 10 by inspection; `pytest -q` green, which requires
Task 5's `SKILL.md` mention — so Tasks 4 and 5 share a commit.

**Covers:** criterion 10.

## Task 5 — `SKILL.md`

**Modifies:** `skills/tcw-work/SKILL.md`.

The stage table's seven links and the `## Read on demand` list get the new
paths (done in Task 1); this task adds the two things Task 1 could not:

- The `lifecycle/default/README.md` pointer, folded **inline** into the existing
  `## Always` bullet that already ends "→ `hooks.md`", so no line is added.
  `test_the_router_routes_to_every_reference_file` requires the file be named
  here.
- One sentence stating the division of labour that Task 2 removed from six
  documents: the CLI carries the methodology, the reference document carries
  what the CLI cannot.

The body is at exactly its 60-line budget today. If either addition pushes it
over, the rule the test states applies — extract into a reference, never grow.

**Proves it:** `pytest -q` green, including
`test_the_router_stays_within_its_line_budget` and
`test_the_router_routes_to_every_reference_file`. Re-run the body-line count:

```sh
python -c "from pathlib import Path; t=Path('skills/tcw-work/SKILL.md').read_text().splitlines(); print(len(t[t.index('---',1)+1:]))"
```

**Covers:** criteria 1, 16.

## Task 6 — Documentation Sync

One pass over the finished diff, after Tasks 1–5, per the skill's rule. All four
of this project's entries were evaluated; three fire and one is a two-file
update.

| Entry | Trigger | Fires? |
| --- | --- | --- |
| `README.md` | `[Public-API]` | **Yes** — the public CLI surface changes: `tcw work stage` takes a stage that previously errored, and its reference argument is now optional. |
| `docs/release-notes/upcoming.md` | `[Public-API]` | **Yes** — same change, in user-facing words. |
| `docs/changelogs/upcoming.md` | `[Any-Code-Change]` | **Yes** — behavior-affecting code change in `resolve.py` and `cli.py`. |
| `skills/<component>/SKILL.md` | `[Skill-Driven-Component]` | **Yes** — `tcw-work` drives the component whose CLI surface changed. Its `SKILL.md` is Task 5; its `references/commands.md` is the same skill's CLI table and is updated here. |

**Modifies:**

- `README.md` — the `tcw work stage` paragraph at ~805, and the sentence at 759
  that says TCW ships built-ins for "the six lifecycle stages (`inbox` runs
  before an item exists, so it has none)". Both become seven, and the paragraph
  gains the no-reference form.
- `skills/tcw-work/references/commands.md:27` — the table row
  `` `tcw work stage <id> <slug> [--no-exec]` `` gains the `inbox` form.
- `docs/release-notes/upcoming.md` — plain language, no internal module names:
  that `tcw work stage` now answers for the inbox too, and how to run it.
- `docs/changelogs/upcoming.md` — grouped entries. *Added:* the built-in `inbox`
  prompt. *Changed:* `tcw work stage` reference argument optional; the
  `tcw-work` skill's `references/` regrouped into `lifecycle/` and
  `procedures/`, with the moved paths listed so a reader of this changelog can
  find them.

**Deliberately not modified:** `docs/migration-guide-0.21.X-to-1.0.0.md:184`,
which says TCW ships instructions for six stages. That document is pinned by its
own filename to what 1.0.0 shipped, and it was true then. Rewriting it would
make it describe a release it is not about. Recorded here so the omission is a
decision rather than a miss.

**At `complete`, not here:** the `work/run-a-lifecycle-stage` capability
description (spec criterion 15). Its two stale claims — six shipped defaults,
and `tcw work stage inbox` refused — are rewritten as the item's final
pre-freeze step, which is where the ledger flip belongs. The back-pointer is
already filed in this item's `capabilities.yaml`.

**Proves it:** `pytest -q` green, in particular
`tests/test_documented_cli_surface.py`, which parses every `tcw …` invocation
out of every non-archival Markdown file and fails on a verb or flag that does
not exist — so a README example written wrong is caught. Then `tcw validate`
(criterion 13) and `tcw capabilities check` (criterion 14).

**Covers:** criteria 1, 13, 14, and the scheduling half of 15.

## Verification

What the suite cannot check, to be done by hand at `verify`:

1. **The condensed `inbox` prompt still carries every rule.** Read
   `tcw/work/prompts/inbox.md` against
   `git show <pre-Task-1-sha>:skills/tcw-work/references/stage-inbox.md` and
   confirm each of the six carried-over items listed in Task 3 survived. No test
   can check this; the line ceilings only prove it is short.
2. **The pointer sentence reads as an instruction in context.** Open two of the
   rewritten routers and confirm the `Purpose` section still says what the stage
   is for, rather than having been reduced to the pointer alone.
3. **`tcw work stage inbox` output is usable.** Run it in this repository and in
   a scratch node with no lifecycle configuration, and confirm both print
   something an agent could act on. The suite checks the exit code and the
   stream, not whether the text is any good.
4. **The moved files' internal relative links resolve.** Task 1 rewrites them;
   nothing in the suite follows a relative Markdown link. Click through or
   resolve each `](../` and `](` target in the eleven moved files.

## Notes

No blockers. This item depends on nothing and blocks nothing, so no
`tcw work edit --blocked-by` is needed.

The three inbox entries sitting in `docs/work/inbox/` are unrelated to this item
and are left alone.
