# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Removed

- **`tcw work stage <id> <ref>` — the bare form is gone.** It is `tcw work stage
  begin <id> <ref>`, byte-identical in output, gates, and exit codes. No alias
  and no deprecation period: the old spelling is registered as a hidden
  per-stage-id parser that resolves nothing, names both replacement verbs on
  stderr, and exits 2 as the usage error it is. See
  [`docs/migration-guide-1.X-to-2.0.0.md`](../migration-guide-1.X-to-2.0.0.md).

## Added

- **`tcw work stage prompt <id> [<ref>]`** — a stage's instructions without
  entering the stage. Runs no legality check and no `pre` bindings, so it answers
  on an item the stage is not legal for, which `begin` correctly refuses. It
  still resolves `file:` and `generate:` bindings, because that is how the text
  is produced at all; the guarantee is that TCW runs no check of its own, not
  that no process starts.
  - The work item reference is optional and changes what resolves. Without one,
    `when:` conditions never match, `generate:` receives a null item, and the
    body token falls back to its no-body text. With one, all three resolve
    against that item — and a `<project-id>/<slug>` qualifier reads *that* node's
    `prompt:` bindings rather than the anchor node's.
  - An illegal stage prints anyway: the instructions on stdout, a `note —` line
    on stderr naming the statuses the stage runs in, exit 0. stdout stays
    byte-pure for a caller piping it.
  - `inbox` refuses a work item on both verbs, each with its own message.
  - `--no-exec` is rejected by `prompt`, because suppressing `file:` and
    `generate:` would leave the incomplete instructions the verb exists to
    produce. The message names `tcw work stage begin --no-exec` instead.
- **`skills/tcw-work-stage`** — a Claude-only skill that composes a stage into
  one document: `lifecycle/stage-<id>.md` followed by the output of
  `tcw work stage prompt <id> [<item>]`, both injected with `` !`cmd` ``. Takes
  `stage` and `item` as named arguments.
  - Both injected commands end `|| true`. A non-zero exit aborts the whole skill
    invocation and the model is shown *nothing* — not an error — so an unknown
    stage or slug would render as silence. Tolerating the exit puts the CLI's own
    message in front of the reader instead.
  - No `2>&1` is needed: injection captures stderr as well as stdout, so
    `prompt`'s illegal-stage note arrives with the instructions rather than being
    lost.
  - `allowed-tools` declares both commands. An injected command that is not
    pre-approved aborts the invocation the same silent way.
  - It reads with `prompt` and therefore runs no gate, which is the hazard of
    composing a stage this way. The skill names `tcw work stage begin` as the
    verb that enters, and `test_skill_lifecycle_parity.py` fails if it stops.
  - Claude-only by construction, and an ergonomic rather than a route: the seven
    routers still name `begin`, so a Codex user runs the two commands and loses
    nothing but the concatenation.
- **`tcw work stage begin inbox`** — `inbox` was the one stage in `STAGE_IDS`
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
  positionals. `begin` is the former `_stage` unchanged; `prompt` resolves the
  store via `_store()` with no reference and `_resolve()` with one, then shares
  the tail. The unknown-stage error names the verb it was reached through.
- **The tail of both verbs is one function.** `_stage_tail` covers everything
  from the pre-check block through the final `print(res.text)` — the two copies
  had already drifted, and the comment explaining why the `--no-exec` plan goes
  to stderr existed in only one of them.
- The `--no-exec` plan header names `tcw work stage begin <id>`. It printed
  `tcw work stage <id>`, which is no longer a command.
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
- All seven stage documents now instruct rather than describe: "Get your
  instructions on how to produce the output by running `tcw work stage begin
  <id> <slug>`."
- **Every agent-facing surface says `begin`.** The seven routers, `SKILL.md`,
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
  the binding-command literal is `f"tcw work stage begin {stage_id}"`, so a
  router naming the bare form or `prompt` fails the check; the `inbox` branches
  are gone from the section-order and binding-command checks; path constants
  resolve under `lifecycle/`; the ordinal and reachability sweeps use `rglob`,
  and reachability matches each file by its path relative to `references/`.
- `tests/cli/scenarios/` — 03, 04, 05, and 11 restate their `tcw work stage`
  invocations with the verb.
