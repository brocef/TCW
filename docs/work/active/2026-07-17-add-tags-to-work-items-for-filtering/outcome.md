# Outcome: Tag work items for filtering

Work completed successfully. All five plan phases landed, plus one round of dual
review with fixes applied. Full test suite green (629 passed); CLI and web
verified end-to-end.

## What changed

Sequential execution, one commit per phase:

- **Phase 0 — model + registry** (`tcw/store/base.py`, `tcw/store/fs.py`):
  `WorkItem.tags: list[str]`; `normalize_tag()` (slugify + non-empty guard);
  `WorkStore` ABC gains `registered_tags`/`register_tags`/`unregister_tags`/`check`.
  `FsWorkStore` reads/writes the tag registry in the node-root `tcw-config.yaml`
  under `work.tags` (read-modify-write, preserving other keys), reads/writes item
  `tags` (omitted from `state.yaml` when empty), and rejects unregistered tags on
  create/update (**fail closed**).
- **Phase 2 — validation** (`tcw/validate.py`): the aggregate pass runs the work
  `check()`, flagging any item carrying a tag no longer registered.
- **Phase 1 — CLI** (`tcw/work/cli.py`): `tcw work tags {list,add,rm}`; `--tag` on
  `new`, `--tag`/`--untag` on `edit`, `--tag` filter (repeat = match-any/OR) on
  `list`; tags shown in `show` and board rows.
- **Phase 3 — web** (`tcw/serve/**`): `GET /api/work/tags`; POST/PATCH accept
  `tags` (unregistered → 422); create/edit editors render a registered-set
  checkbox multi-select; tags shown on the detail view and list rows.
- **Phase 4 — docs**: README, release notes, changelog, and `skills/tcw-work/SKILL.md`.

Scope held to the spec: the **web-side multi-select *filter* control** over the
board stays deferred to the sibling item
`2026-07-17-web-ui-multi-select-dropdown-filter-for-taxonomy-and-work-tags`,
which is blocked by this one and consumes the `GET /api/work/tags` endpoint
introduced here.

## Verification performed

- `pytest` — **629 passed**. New coverage in `tests/test_work_tags.py` (registry
  round-trip, reject-unregistered on create/update, apply/remove, list filter,
  stale-tag `check()` + `validate`, malformed/non-dict config) and a
  `TestWorkTags` class in `tests/test_serve_write.py` (endpoint + POST/PATCH 422).
- **CLI end-to-end** (throwaway repo): register (normalizes `Bug`→`bug`) → list →
  apply → reject unregistered (exit 1) → `list --tag` filter → `show` → edit
  tag/untag → `tags rm` → `tcw validate` flags the now-stale tag (exit 1). All pass.
- **Web end-to-end** (browser): registered-set checkbox multi-select renders in
  the editor; checking `bug` + Save persisted `tags: [bug]` to `state.yaml`;
  detail view and list rows show tags; PATCH with an unregistered tag → 422; no
  console errors. Stale-tag remediation verified: an item carrying a since-removed
  tag shows it as `tech-debt (unregistered)` (checked, flagged) — unchecking + Save
  cleared it and `tcw validate` returned clean.

## Review (dual)

Per the review rule, one round of dual review before this checkpoint:

1. **Subagent (targeted-code-reviewer)** — fail-closed guarantee verified sound on
   every path. Findings: one **Medium** (web editor couldn't see/remove a stale
   tag; any tag edit then failed with an opaque 422) and two **Low** malformed-
   config robustness nits (`registered_tags`/`_config` on a non-dict config value).
2. **`bllm-review-many` (qwen25)** — two "blocking" items about `tags=None` were
   **false positives** (both paths already guard `None`); one useful non-blocking
   item (guard non-list `tags` in `create_work`, mirroring `update_work`).

**Applied** (commit `11f2e30`): render stale/unregistered tags in the web editor
as removable flagged checkboxes; `_config()` raises a clear error on a non-mapping
config; `registered_tags()` tolerates a non-dict `work:` value; `create_work`
rejects a non-list `tags`; `tcw validate` reports (rather than crashes on) a
malformed node-root config, which isn't in its YAML-scan roots.

**Dismissed** (with reason): bllm's `tags=None` "blocking" items (already handled);
bllm's JS `Array.isArray` guard (`|| []` already covers null/undefined); wrapping
every component `check()` in try/except (kept the fix narrow to work, the only
check exposed to an unscanned config file).

## Deviations from plan

- Phase 2 (validate) committed before Phase 1 (CLI) — both depend only on Phase 0
  and touch disjoint files; ordering is immaterial. `check()` was added to the
  `WorkStore` ABC (as the plan specified) so validate could call it.
- Config comment loss on `dump_yaml` rewrite accepted as planned (the sentinel
  stub's comments are dropped when `work.tags` is first written).

## Follow-up notes (not yet TCW items — closeout decision)

- The blocked sibling item `…-web-ui-multi-select-dropdown-filter-…` is now
  unblocked at the API level (its `GET /api/work/tags` dependency shipped).
- No per-tag metadata, cross-node federation, or rename/migration tooling — all
  explicit non-goals for v1.
