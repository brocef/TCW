# Spec: Tag work items for filtering

## Capability changes

- **New:** `work/tag-a-work-item` (seeded `Missing`, Planning doc → this item).
  A user registers a project's valid tags, applies them to items, sees them in
  `show`/`list`/web, and filters the board by tag.
- **Changed:** `work/view-the-board` — `tcw work list` gains a tags column and a
  `--tag` filter. Its description must be updated at completion.

Both are recorded in this item's `capabilities.yaml`.

## Problem

Work items have no way to be classified by kind (bug, tech-debt, new-feature,
…). Consumers of the library want to **filter** items by such a classification.
`priority`/`effort`/`complexity` are single-value estimation signals and don't
fit — this is an orthogonal, multi-value, project-defined label set.

## Goals

1. A work item can carry **zero or more tags**.
2. The **valid tag set is registered per-project** in the node's
   `tcw-config.yaml`; only registered tags may be applied (**fail closed**).
3. Tags are managed, applied, displayed, and filtered through the existing
   `tcw work` CLI, and shown/editable in the `tcw serve` web UI.

## Non-goals

- No per-tag metadata (color, description, hierarchy) — tags are plain strings.
- No cross-node tag federation — each node registers its own set.
- Tags do **not** affect board ordering (like effort/complexity).
- No renaming/migration tooling for tags in v1 (register + apply + filter only).

## Decisions (locked with the user)

- **Validation:** applying an unregistered tag is **rejected** with an error;
  `tcw validate` flags any item carrying a tag no longer registered.
- **Registration UX:** a **CLI command** manages the set —
  `tcw work tags add|rm|list` — writing to `tcw-config.yaml`.
- **Tag shape:** plain lowercase-slug strings (reuse `slugify`-style
  normalization for consistency; see Open items).

## Proposed behavior

### Config schema (`tcw-config.yaml`, node root)

```yaml
work:
  tags:
    - bug
    - tech-debt
    - stability-improvement
    - new-feature
```

Namespaced under `work:` so other components can add their own config later.
Absent/empty ⇒ no registered tags ⇒ every `--tag` is rejected until one is
registered. `FsWorkStore` gains a read path to the node-root sentinel (it reads
no config today).

### Registration CLI

- `tcw work tags list` — print the registered tags, one per line.
- `tcw work tags add <tag> [<tag> ...]` — add to the set (normalized,
  deduped, sorted); idempotent.
- `tcw work tags rm <tag> [<tag> ...]` — remove from the set. Removing a tag
  still applied to items is allowed but leaves those items "stale" (caught by
  `tcw validate`); print a warning listing affected items.

### Applying tags

- `tcw work new "<title>" --tag <tag>` — repeatable; each validated against the
  registered set (reject unknown).
- `tcw work edit <slug> --tag <tag> --untag <tag>` — repeatable add/remove;
  `--tag` validated, `--untag` just removes.
- Stored in `state.yaml` as `tags: [..]` (omitted when empty), mirroring how
  `effort`/`blocked_by` are conditionally written. New `WorkItem.tags:
  list[str] = field(default_factory=list)`.

### Display

- `tcw work show` — a `tags: a, b` line (only when non-empty), alongside
  effort/complexity in `_print_item`.
- `tcw work list` — tags appended to each board row (e.g. a `[bug, tech-debt]`
  segment), and a `--tag <tag>` filter (repeatable = **match any**, OR).
- **Web** (`tcw serve`): `WorkItem.tags` already flows to JSON via `asdict`
  (`_jsonable`). Add `tags` to the PATCH `work_field_keys` allowlist and the
  POST create handler; add a `tags` multi-select field in the editor
  (`WORK_FIELD_DESCRIPTORS`) driven by the registered set, which the frontend
  fetches from a new read-only endpoint `GET /api/work/tags` (or a config
  endpoint). Display tags on the item detail. **Scope:** web *display + edit*
  only. The web-side **tag filter control** (multi-select dropdown over the
  board) is deferred to the sibling item
  `2026-07-17-web-ui-multi-select-dropdown-filter-for-taxonomy-and-work-tags`,
  which is blocked by this one and consumes the `GET /api/work/tags` endpoint
  this item introduces.

### Validation

- `tcw validate` reports each item tag not in the registered set as a problem
  (item slug + offending tag). Hook into the existing work-node validation pass.

### Cross-cutting behavior

- **Tag normalization (locked):** input tags are normalized with the existing
  `slugify` (lowercase, hyphenate) on both registration and application, so
  `Bug` and `bug` never diverge. Registration errors are surfaced; the CLI
  prints the resulting set after `add`/`rm`.
- **Malformed/absent config:** the registry read is tolerant — an absent or
  empty `tcw-config.yaml` ⇒ empty set; a **malformed** file raises a clear
  error naming the config path rather than crashing a board render (mirror the
  `_safe_yaml` tolerance used for `state.yaml` where a read must never break
  listing, but fail loud on the mutating `tags add/rm` path).
- **Backward compatibility:** `WorkItem.tags` defaults to an empty list and is
  omitted from `state.yaml` when empty, so every existing tag-less item stays
  valid and simply matches no `--tag` filter. No migration is required.
- **Trust boundary (why no new auth):** `tcw` is a local single-user tool. The
  `tcw serve` mutation endpoints already gate writes behind loopback-origin +
  CSRF checks (`_validate_mutating_request`); the new tag endpoints/handlers
  inherit that path. The `tags add/rm` CLI edits `tcw-config.yaml` at the same
  trust level as every other `tcw work` write. No separate authorization model
  is introduced.

## Affected surfaces (current-state findings)

- `tcw/store/base.py` — `WorkItem` dataclass (add `tags`); a
  `registered_tags`/`register_tag`/`unregister_tag` trio on the `WorkStore` ABC
  (abstract-spine: a registered vocabulary + a multi-value item field, any
  backend can realize). `create_work`/`update_work` signatures gain `tags`.
- `tcw/store/fs.py` — `FsWorkStore._item_from_dir` (read `tags`),
  `create_work`/`update_work` (write `tags`, validate against registered set),
  and a node-root `tcw-config.yaml` read/write path for the tag registry
  (`load_yaml`/`dump_yaml` already exist; note `dump_yaml` rewrites the file and
  **drops the sentinel's comments** — acceptable, or re-emit a header).
- `tcw/work/cli.py` — `--tag`/`--untag` on `new`/`edit`; `--tag` filter on
  `list`; a `tags` subcommand group (`add`/`rm`/`list`); tags in `_print_item`
  and `_render_board`.
- `tcw/serve/__init__.py` — POST create + PATCH allowlist gain `tags`; new
  `GET /api/work/tags` endpoint for the registered set.
- `tcw/serve/static/app.js` (+ `style.css`) — tags editor + detail display.
- `tcw/validate.py` — stale-tag check.

## Acceptance criteria

1. `tcw work tags add bug` then `tcw work new "X" --tag bug` succeeds; the item's
   `state.yaml` has `tags: [bug]`.
2. `tcw work new "Y" --tag nope` (unregistered) exits non-zero with a clear
   error and creates nothing.
3. `tcw work edit <slug> --tag bug --untag old` adds/removes correctly.
4. `tcw work show` and `tcw work list` display the tags; `tcw work list --tag
   bug` lists only items carrying `bug`.
5. Web UI shows an item's tags and can edit them against the registered set;
   POST/PATCH reject unregistered tags with a 4xx.
6. `tcw validate` flags an item whose tag was later `rm`'d from the registry.
7. Existing tests pass; new tests cover registry round-trip, reject-unregistered,
   apply/remove, list filter, and the stale-tag validation.

## Risks / open items

- **Config comment loss (open):** `dump_yaml` rewrites `tcw-config.yaml`
  wholesale, discarding the sentinel stub's comments. Low impact; if
  undesirable, re-emit a one-line header on write. Decide in plan.
- **Web endpoint shape (leaning narrow):** `GET /api/work/tags` vs a broader
  `/api/config`; pick the narrow one unless a config endpoint already exists.
- Locked above: tag normalization (`slugify`), filter semantics (repeated
  `--tag` = OR / match-any), malformed-config handling, backward compatibility.

## Dependencies / related work

- No blockers. Independent of the sibling backlog item
  `2026-07-17-make-web-ui-tree-view-column-scroll-independently`.
- **Blocks** `2026-07-17-web-ui-multi-select-dropdown-filter-for-taxonomy-and-work-tags`
  — that item adds the web multi-select tag filter and consumes the
  `GET /api/work/tags` endpoint introduced here.

## Documentation sync (triggers expected to fire)

- `README.md` [Public-API] — new `tcw work tags` command + `--tag` flags.
- `docs/release-notes/upcoming.md` [Public-API] — user-facing tags feature.
- `docs/changelogs/upcoming.md` [Any-Code-Change] — Added/Changed entries.
- `skills/tcw-work/SKILL.md` [Skill-Driven-Component] — tags in the CLI surface
  / quick-reference; the model gained a field and a subcommand group.
