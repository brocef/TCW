# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Removed

- **`tcw work stage <id> <ref>` — the bare form is gone**, and so is `begin`,
  which never shipped. The command is two verbs: `tcw work stage gate <id> <ref>`
  checks the stage and runs its `pre` bindings, `tcw work stage prompt <id>
  [<ref>]` prints the instructions. No alias and no deprecation period: the old
  spelling is registered as a hidden per-stage-id parser that resolves nothing,
  names both replacement verbs on stderr, and exits 2 as the usage error it is.
  See [`docs/migration-guide-1.X-to-2.0.0.md`](../migration-guide-1.X-to-2.0.0.md).
- **The prompt text no longer comes out of two commands.** `gate` prints none of
  it. The two used to emit byte-identical stdout, which is what made every view
  composing a stage out of both show the instructions twice, and what every piece
  of wording around them was written to excuse.

## Added

- **`tcw work stage prompt <id> [<ref>]`** — the only verb that prints a stage's
  instructions. Runs no legality check and no `pre` bindings, so it answers on an
  item the stage is not legal for, which `gate` correctly refuses. It still
  resolves `file:` and `generate:` bindings, because that is how the text is
  produced at all; the guarantee is that TCW runs no check of its own, not that
  no process starts.
  - The work item reference is optional and changes what resolves. Without one,
    `when:` conditions never match, `generate:` receives a null item, and the
    body token falls back to its no-body text. With one, all three resolve
    against that item — and a `<project-id>/<slug>` qualifier reads *that* node's
    `prompt:` bindings rather than the anchor node's.
  - An illegal stage prints anyway: the instructions on stdout, a `note —` line
    on stderr naming the statuses the stage runs in, exit 0. stdout stays
    byte-pure for a caller piping it.
  - It now **accepts** `--no-exec`, which it previously refused. The refusal's
    reason was that suppressing `file:` and `generate:` would leave incomplete
    instructions on stdout — true only if it printed any. It prints none: the
    plan goes to stderr and stdout stays empty. Refusing would have dropped the
    conditioned matched/skipped diagnostic from the CLI entirely, since `gate`
    reports only its own bindings.
- **`tcw work stage gate <id> [<ref>]`** — status legality, then the stage's
  `pre` bindings, and nothing else. Success is exit 0 with **empty stdout** and
  one line on stderr naming `prompt`; the exit code is the answer.
  - It resolves no prompt, not even to discard one, so a `generate:` binding does
    not run a script for output nobody reads.
  - `--no-exec` lists the `pre` checks it would run and no prompt entries.
  - Named `gate` rather than `begin` because the verb begins nothing: it runs no
    transition, writes no artifact, and changes no field, so a user who ran it
    and saw silence had nothing to tell them whether it worked. `gate` is the
    word this repository's own documents already use for what it runs. This is
    also the `pre` verb the split's intake specified and dropped for want of a
    caller — a reason now answered, since the prompt's own header names it and
    the composing skill runs it.
- `STAGE_NEXT_STEPS` is checked three ways, because it is prose asserting
  lifecycle facts and prose does not check itself: it covers every id in
  `STAGE_IDS`, every command it names resolves against the real parser (verb and
  stage id both, by longest matching prefix), and it names a transition **only**
  where `STAGE_STATUSES` says one is needed. The third caught `implement`, which
  named `tcw work submit` before `verify` — a transition `verify` does not
  require, since it is legal from `active` too, and one the `verify` instructions
  already own the decision about.
- **Generated bookends around every resolved prompt** (`bookend` in
  `tcw/work/resolve.py`, `STAGE_NEXT_STEPS` in `tcw/store/base.py`). A header
  naming that stage's `gate` invocation and saying the text ran no checks, and a
  footer saying what to do once the stage's output is written.
  - Generated rather than written into the seven prompt files: those are capped
    at 50 lines and `spec.md` is at 49, and navigation text repeated seven times
    drifts on the first edit that forgets one.
  - Applied by the CLI at print time, not inside `resolve_prompts`, which keeps
    its promise that a stage whose only binding does not match resolves to
    **nothing**. Wrapping that would turn silence into a header and footer around
    an empty middle, which reads as a stage that failed to resolve.
  - Wraps a project's own `prompt:` bindings too. Overriding what a stage says is
    not overriding where the lifecycle goes next.
  - The header is what replaces a guarantee this release gives up: once `gate`
    prints nothing, wanting the instructions no longer makes anyone run it, and
    the reminder has to reach every reader under either harness rather than only
    through the Claude-only composing skill.
  - `postmortem` renders "Nothing follows" rather than omitting the section, so a
    missing footer never reads as one that failed to resolve.
- **`inbox` reaches both verbs** — it was the one stage in `STAGE_IDS`
  that shipped no default instructions, so its methodology lived only in the
  plugin's `stage-inbox.md` and was unavailable to a PyPI-only install. It now
  ships a built-in prompt (`tcw/work/prompts/inbox.md`), takes no work item
  reference, and reports one as a mistake rather than guessing at it.
- `skills/tcw-work/references/lifecycle/default/README.md` — where the built-in
  prompts live, why they ship with the package rather than the skill, how to
  read one, and the precedence between a built-in and a project's `prompt:`
  bindings.
- `docs/migration-guide-1.X-to-2.0.0.md` — the one break, the check-for-it grep,
  and what `prompt` adds.
- `docs/guide/work.md`, `docs/guide/taxonomy-and-capabilities.md`,
  `docs/guide/multi-repo.md`, `docs/guide/configuration.md`,
  `docs/guide/web-viewer.md`, `docs/guide/linking-and-validation.md` — the
  reference material extracted from README.md, each with an H1 and cross-links.
- `docs/releasing.md` — the PyPI/Trusted-Publishing procedure, moved out of the
  README because it serves maintainers rather than users.

## Changed

- **`pstg` is a subparser group** holding `prompt` and `begin` rather than two
  positionals. `prompt` resolves the store via `_store()` with no reference and
  `_resolve()` with one; `gate` resolves the item, checks legality, runs the
  checks. The unknown-stage error names the verb it was reached through.
- **`_stage_tail` is `prompt`'s alone**, and its `run_checks` flag is gone. It
  was extracted because the two verbs shared a tail; `gate` now resolves no
  prompt, so they share nothing, and a parameter one caller never passes is
  worse than two functions.
- Each `--no-exec` plan header names the verb that printed it, so a reader
  copying one out of a log runs the command that produced it.
- `load_builtins()` ships `sorted(STAGE_IDS)` rather than
  `sorted(set(STAGE_IDS) - {"inbox"})`.
- `STAGE_STATUSES["inbox"]` stays `()` and is no longer read as a refusal — the
  branch in `_stage` is selected by stage id.
- `skills/tcw-work/references/` regrouped. The seven `stage-*.md` documents moved
  to `references/lifecycle/`; `decompose.md`, `delegation.md`,
  `audit-backlog.md`, and `consolidate-plans.md` moved to
  `references/procedures/`. Moved with `git mv`, so `git log --follow` still
  reaches their earlier history. Every inbound link was rewritten.
- `stage-inbox.md` is a four-section router under the 40-line ceiling like its
  six siblings, keeping only what the CLI cannot say: non-delegability, the
  enforcement markers, and the pointers to plugin-only documents.
- All seven stage documents name both verbs: "Check the stage with `tcw work
  stage gate <id> <slug>`, then read what to produce with `tcw work stage prompt
  <id> <slug>`." Both, because naming only the reading verb would leave a Codex
  reader — who gets no context injection and so no skill — with no route to the
  gate at all.
- **Every agent-facing surface names the right one of the two.** Where the
  meaning was the refusal it says `gate`; where the meaning was the instructions
  — the documentation entries arriving inline, the built-in floor, the body
  substitution — it says `prompt`. The seven routers, `SKILL.md`,
  `commands.md`, `hooks.md`, `documentation-sync`, `AGENTS.md`, three capability
  descriptions, and the docstrings in `templates.py`, `resolve.py`,
  `store/base.py`, and `require_artifact.py`. `prompt` appears only where reading
  rather than entering is meant. Nothing under `ARCHIVAL` was touched: past
  changelogs, release notes, and `docs/work/` record what was true when written.
- `run-a-lifecycle-stage` states the refusal guarantee applies to `begin`, and no
  longer claims `tcw work stage inbox` is refused.
- **README.md restructured from a reference manual into an adoption pitch.**
  Reduced from 1628 to ~320 lines. The opening now leads with the problem, a
  runnable worked example across all three axes, the multi-repository case, an
  explicit adoption-cost section, and a corrected storage-abstraction claim; the
  reference material moved into `docs/guide/`. `Status` was rewritten from
  build-phase archaeology (“Phases 1–5”, “work Spec 2”) into a table of what is
  built and an explicit statement of what is not.
- **`tests/test_documented_cli_surface.py`** now checks `docs/guide/work.md`
  rather than `README.md` for `tcw work stage` and `tcw work scaffold`, matching
  where those verbs are now documented, and `DOCUMENTED_VERBS` carries both new
  spellings. The forward-direction check needs no change: `_doc_files()`
  discovers the new guides through `git ls-files`.

## Fixed

- `decompose.md` linked to `cross-node-epic.md`, which has never existed. It now
  points at `cross-node-deltas.md`, the document it meant.
- **Restored the README's missing headings.** `### Declaring which documents
track which changes` opened at line 1084 and the next `###` was at 1432, so
  the entire `tcw work` command reference, the Definition of Done, transition
  commits, and tags rendered inside a section about documentation entries — in
  every Markdown viewer and in GitHub's outline. The extracted
  `docs/guide/work.md` gives that material its own headings. This is the defect
  filed as
  `2026-08-18-close-the-readme-lifecycle-heading-so-it-stops-swallowing-the-rest-of-the-document`,
  which had moved since it was filed but was still present.
- **Removed a contradiction between two README sections.** The storage-
  abstraction section claimed portability to external trackers “is what makes it
  viable at enterprise scale” while `Status` listed those adapters as unbuilt.
  The section now states plainly that only filesystem stores ship today.

## Internal

- `tests/test_stage_verb.py` — `_cli` invokes `begin`, `_prompt` and `_bare` are
  its siblings for the new verb and the removed form. Adds the paired
  gate-non-execution evidence: a node whose `plan.pre` creates a sentinel, where
  `prompt` exits 0 leaving no sentinel and `begin` exits 1 having written one.
  Without the `begin` half the `prompt` half passes just as well when the gate is
  broken and never runs at all. `test_inbox_is_rejected_with_its_reason` and
  `test_inbox_still_ships_no_prompt` are replaced by
  `test_inbox_refuses_a_work_item_argument` and
  `test_inbox_prints_its_prompt_with_no_item`; each asserts the superseded
  message is absent, so neither can pass while the old refusal still prints.
- `tests/fixtures/prompt_fallback/unconfigured.json` — the six recorded `argv`
  arrays gained the verb **by hand**; the frozen `stdout` is untouched, and the
  diff is six added lines with nothing removed. Re-running `capture.py` would
  have overwritten the recorded output with what the code does now, destroying
  the back-compatibility evidence the file exists to hold, and the suite would
  still have passed.
- `tests/test_generate_hook.py` — `test_a_grandchild_does_not_survive_the_timeout`
  polls for the grandchild to disappear instead of sleeping 0.5s once. The kill
  is synchronous but reaping is not, and the fixed wait failed about one run in
  three under load. It still fails at its deadline when the grandchild genuinely
  survives.
- `tests/test_shipped_prompts.py` — `SHIPPED` is `set(STAGE_IDS)`;
  `test_every_stage_but_inbox_ships_a_prompt` became
  `test_every_stage_ships_a_prompt`.
- `tests/test_skill_lifecycle_parity.py` — `ROUTER_IDS` is now `STAGE_IDS` and
  `test_every_stage_document_names_the_harness_neutral_binding_command` requires
  **both** `f"tcw work stage gate {stage_id}"` and
  `f"tcw work stage prompt {stage_id}"`, so a router that drops either fails; the `inbox` branches
  are gone from the section-order and binding-command checks; path constants
  resolve under `lifecycle/`; the ordinal and reachability sweeps use `rglob`,
  and reachability matches each file by its path relative to `references/`.
- `tests/fixtures/prompt_fallback/unconfigured.json` — **re-captured**, which is
  the opposite of what the split did to it and for the opposite reason. That file
  froze the prompt bytes to prove a change did not move them; the bookends move
  them on purpose, so the old bytes would have asserted something false. The
  capture script's docstring now records both events and the rule: re-capture
  only when a release intends the text to move, and say which release did it.
  The recorded stdout also normalizes the item's slug to `<slug>`, because the
  bookends quote the reference back and a slug carries its creation date — the
  fixture would otherwise have expired at midnight rather than when the text
  changed.
- `tests/cli/scenarios/` — 03, 04, 05, and 11 restate their `tcw work stage`
  invocations with the verb.
