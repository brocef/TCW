# Implementation plan: Tag work items for filtering

Derived from `spec.md`. Follows the existing `effort`/`complexity` field pattern
throughout. TDD: write the failing test for each store/CLI behavior first.

## Phase 0 — Model + registry read path (foundation; do first)

Everything else depends on this. Single-threaded.

1. **`tcw/store/base.py`**
   - `WorkItem`: add `tags: list[str] = field(default_factory=list)`.
   - `WorkStore` ABC: add abstract methods
     - `registered_tags() -> list[str]`
     - `register_tags(tags: list[str]) -> list[str]` (returns new full set)
     - `unregister_tags(tags: list[str]) -> list[str]`
     - `check() -> list[str]` (work-node validation; empty = clean)
   - `create_work` / `update_work` signatures: add `tags` (create: `list[str] |
     None = None`; update: `tags=_UNSET`).
   - Add a `normalize_tag(value: str) -> str` helper = `slugify` + non-empty
     guard (mirrors `normalize_work_level`).

2. **`tcw/store/fs.py` — `FsWorkStore`**
   - Registry read/write against `self.node_root / "tcw-config.yaml"`:
     - `_config()` — tolerant `load_yaml` (absent/empty ⇒ `{}`); malformed
       raises with the config path named.
     - `registered_tags()` → sorted `config.get("work", {}).get("tags", [])`.
     - `register_tags`/`unregister_tags` → read-modify-write the `work.tags`
       list (normalized, deduped, sorted) via `dump_yaml`, then `_stage` the
       config file. **Decided:** accept comment loss on rewrite (`dump_yaml`
       replaces the file); not worth a comment-preserving YAML round-trip lib.
   - `_item_from_dir`: read `tags=state.get("tags") or []`.
   - `create_work` / `update_work`: normalize each tag; **reject** any not in
     `registered_tags()` with a clear `ValueError`; write `state["tags"]` (omit
     when empty, like `effort`). `update_work` supports add/remove semantics via
     the CLI layer passing the final list (store just sets the field).
   - `check()`: for each item, report `tags` not in the registered set
     (`"<slug>: unregistered tag '<tag>'"`).

**Verification:** `pytest tests/ -k "work and (tag or registry)"` (new tests);
`python -c "import tcw.store.fs"` import guard.

## Phase 1 — CLI (depends on Phase 0)

**`tcw/work/cli.py`**

1. `_tag(value)` argparse `type=` wrapper around `normalize_tag` (like
   `_work_level`).
2. `tcw work new`: `--tag` (`action="append"`, repeatable) → pass
   `tags=args.tag or []` to `create_work`.
3. `tcw work edit`: `--tag` (append) and `--untag` (append). Compute the final
   set = current tags ∪ `--tag` − `--untag`, pass via `update_work(tags=...)`.
4. `tcw work list`: `--tag` (append) filter — keep items whose tags intersect
   the requested set (OR / match-any). Apply in `_render_board` (filter the
   `items` list before grouping).
5. Display:
   - `_print_item`: add `tags: a, b` line when non-empty (after complexity).
   - `_render_board`: append tags to each row, e.g. ` | [a, b]` (only when
     present, to keep tag-less rows unchanged).
6. New `tags` subcommand group under `work`:
   - `tcw work tags list` → print `registered_tags()`, one per line.
   - `tcw work tags add <tag>...` → `register_tags`, print resulting set.
   - `tcw work tags rm <tag>...` → `unregister_tags`; warn listing items still
     carrying a removed tag (use `check()`/board scan), print resulting set.

**Verification:** `pytest tests/ -k "cli and tag"`; manual smoke:
`tcw work tags add bug && tcw work new "t" --tag bug && tcw work list --tag bug`.

## Phase 2 — Validation (depends on Phase 0; parallel with Phase 1)

**`tcw/validate.py`**
- `_components_to_check`: include `"work"` when `docs/work` exists (whole-node
  and path-under-`docs/work` cases).
- `_run_check`: add a `comp == "work"` branch →
  `[f"work check: {p}" for p in FsWorkStore.open(node_root).check()]`.

**Verification:** `pytest tests/ -k validate`; `tcw validate` on a repo with a
stale tag reports it and exits non-zero.

## Phase 3 — Web (depends on Phase 0; parallel with Phases 1–2)

Backend read of `WorkItem.tags` is already free via `asdict`/`_jsonable`.

1. **`tcw/serve/__init__.py`**
   - `GET /api/work/tags` (place before the catch-all `/api/work/<slug>` route,
     next to the artifacts subresource) → `{"tags": work.registered_tags()}`.
   - POST create handler (`_post`, ~line 691): read `tags = body.get("tags",
     [])`, pass to `create_work`.
   - PATCH handler (`_patch`, ~line 900): add `"tags"` to `work_field_keys`.
   - Store `ValueError` for an unregistered tag already maps to a 4xx via
     `_map_store_error` — confirm the message is surfaced.
2. **`tcw/serve/static/app.js`**
   - `WORK_FIELD_DESCRIPTORS`: add `{ key: "tags", label: "Tags", type:
     "multiselect" }`; render a checkbox/multi-select group whose options come
     from `GET /api/work/tags` (fetch once on load / when opening the work
     editor). Draft/diff logic already keys on field name — arrays compare by
     value; ensure the change-detection handles list equality (send when
     changed).
   - Item detail: display `item.tags` (e.g. a chip row) when non-empty.
   - Create form: include tags for new items.
3. **`tcw/serve/static/style.css`**: minimal tag-chip styling.

**Scope:** display + edit only. The web multi-select *filter control* is the
sibling item `…-web-ui-multi-select-dropdown-filter-…` (blocked by this one),
which consumes `GET /api/work/tags`.

**Verification:** `tcw serve`, open an item, add/remove tags against the
registered set, confirm persistence and that an unregistered tag is rejected;
`read_console_messages` clean.

## Phase 4 — Docs sync (after code lands; documentation-sync skill)

- **`README.md`** — document `tcw work tags add|rm|list`, `--tag`/`--untag` on
  `new`/`edit`, `--tag` filter on `list`, and `tcw-config.yaml` `work.tags`.
- **`docs/release-notes/upcoming.md`** — user-facing "tag work items" entry.
- **`docs/changelogs/upcoming.md`** — Added (tags field, CLI, endpoint) /
  Changed (`list` column + filter) with the commit range.
- **`skills/tcw-work/SKILL.md`** — add tags to the quick-reference table and the
  model description (new field + `tags` subcommand group).
- Re-run the `documentation-sync` skill to confirm no trigger missed.

## Parallelization

- Phase 0 is the barrier — do it first, alone.
- Phases 1, 2, 3 are independent once Phase 0 lands (CLI / validate / web touch
  disjoint files). If parallelizing via subagents, one per phase.
- Phase 4 after all code phases.

## Touch-point summary

| File | Change |
|---|---|
| `tcw/store/base.py` | `WorkItem.tags`; ABC methods; `normalize_tag`; `create_work`/`update_work` sig |
| `tcw/store/fs.py` | registry read/write; read/write/validate tags; `check()` |
| `tcw/work/cli.py` | `--tag`/`--untag`/filter; `tags` subgroup; display |
| `tcw/validate.py` | wire the work `check()` |
| `tcw/serve/__init__.py` | `GET /api/work/tags`; POST/PATCH accept tags |
| `tcw/serve/static/app.js`, `style.css` | tags editor + detail display |
| `tests/` | registry round-trip, reject-unregistered, apply/remove, filter, stale-tag, web, **existing tag-less item unaffected (regression)** |
| docs (Phase 4) | README, release notes, changelog, SKILL |

## Verification (full)

- `pytest` (whole suite green).
- `tcw validate` clean on this repo (and flags a deliberately-stale tag in a
  temp fixture).
- `verify` skill: drive the CLI end-to-end (register → apply → list filter →
  show) and the web editor.

## Settled decisions

- **Config comment preservation:** accept comment loss when `dump_yaml`
  rewrites `tcw-config.yaml` (simplest; not worth a comment-preserving YAML
  library). Registered tags are the only `work.tags` content that matters.
- **Web endpoint:** narrow `GET /api/work/tags` (no broad `/api/config` exists).
