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

## Fixed

- `decompose.md` linked to `cross-node-epic.md`, which has never existed. It now
  points at `cross-node-deltas.md`, the document it meant.

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
