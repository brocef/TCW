# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- Built-in stage prompt for `inbox` (`tcw/work/prompts/inbox.md`). `inbox` was
  the one stage in `STAGE_IDS` that shipped no default instructions, so its
  methodology lived only in the plugin's `stage-inbox.md` and was unavailable to
  a PyPI-only install.
- `skills/tcw-work/references/lifecycle/default/README.md` — where the built-in
  prompts live, why they ship with the package rather than the skill, how to
  read one, and the precedence between a built-in and a project's `prompt:`
  bindings.
- `docs/guide/work.md`, `docs/guide/taxonomy-and-capabilities.md`,
  `docs/guide/multi-repo.md`, `docs/guide/configuration.md`,
  `docs/guide/web-viewer.md`, `docs/guide/linking-and-validation.md` — the
  reference material extracted from README.md, each with an H1 and cross-links.
- `docs/releasing.md` — the PyPI/Trusted-Publishing procedure, moved out of the
  README because it serves maintainers rather than users.

## Changed

- `tcw work stage` accepts `inbox`. The work item reference is now optional
  (`nargs="?"`): required for the other six stages, refused for `inbox`, each
  with its own message. The `inbox` path resolves the store via `_store()`,
  skips the item lookup and status-legality check, and calls `resolve_prompts`
  with `item=None`.
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
  instructions on how to produce the output by running `tcw work stage <id>
  <slug>`."
- **README.md restructured from a reference manual into an adoption pitch.**
  Reduced from 1628 to ~320 lines. The opening now leads with the problem, a
  runnable worked example across all three axes, the multi-repository case, an
  explicit adoption-cost section, and a corrected storage-abstraction claim; the
  reference material moved into `docs/guide/`. `Status` was rewritten from
  build-phase archaeology (“Phases 1–5”, “work Spec 2”) into a table of what is
  built and an explicit statement of what is not.
- **`tests/test_documented_cli_surface.py`** now checks `docs/guide/work.md`
  rather than `README.md` for `tcw work stage` and `tcw work scaffold`, matching
  where those verbs are now documented. The forward-direction check needs no
  change: `_doc_files()` discovers the new guides through `git ls-files`.

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

- `tests/test_shipped_prompts.py` — `SHIPPED` is `set(STAGE_IDS)`;
  `test_every_stage_but_inbox_ships_a_prompt` became
  `test_every_stage_ships_a_prompt`.
- `tests/test_stage_verb.py` — `test_inbox_is_rejected_with_its_reason` and
  `test_inbox_still_ships_no_prompt` replaced by
  `test_inbox_refuses_a_work_item_argument` and
  `test_inbox_prints_its_prompt_with_no_item`. Each asserts the superseded
  message is absent, so neither can pass while the old refusal still prints.
- `tests/test_skill_lifecycle_parity.py` — `ROUTER_IDS` is now `STAGE_IDS`; the
  `inbox` branches are gone from the section-order and binding-command checks;
  path constants resolve under `lifecycle/`; the ordinal and reachability sweeps
  use `rglob`, and reachability matches each file by its path relative to
  `references/`.
