# Add tags to work items for filtering

## Requested outcome

Work items can carry one or more **tags** so that consumers of the library can
filter items by tag. The set of tags valid for a given TCW project is
**registered centrally in that project's `tcw-config.yaml`**; an item then
selects zero or more of those registered tags.

Example tags a project might register:

- `bug`
- `tech-debt`
- `stability-improvement`
- `new-feature`

Tags must surface in:

- **`tcw work list`** — visible per item, and usable as a filter
  (e.g. show only items carrying a given tag).
- **`tcw work show`** — visible on the item detail.
- **the web interface** (`tcw serve`) — visible per item, ideally filterable.

## Constraints

- **Abstraction litmus test:** a tag is just a named multi-value field on an
  item plus a registered vocabulary in node config — any store backend can
  realize it. Keep it in the abstract model (like `effort`/`complexity`),
  never a filesystem-only trick.
- Tags are **registered in `tcw-config.yaml`** (the node-root sentinel). This is
  the user's explicit choice for where the valid tag set lives. Note: today
  `FsWorkStore` does not read the node-root sentinel — it currently loads no
  config — so wiring that read path is part of the work.
- Follow the existing validated-field pattern (`effort`/`complexity` in
  `state.yaml`, normalized/validated on `new`/`edit`) rather than inventing a
  new mechanism.
- Keep the CLI surface consistent with existing `tcw work new` / `edit` /
  `list` flags.

## Non-goals

- No per-tag metadata beyond the tag name unless a real need surfaces
  (no colors, descriptions, or hierarchy in v1 — decide at spec time).
- Not a replacement for `priority`/`effort`/`complexity`; tags are an
  orthogonal, free-form-within-a-registered-set classification.
- No cross-node tag federation in v1 (each node registers its own set).

## Open questions for spec

1. **Validation strictness:** should an item tag that is not registered in
   `tcw-config.yaml` be rejected, or accepted with a warning? (Leaning:
   reject — the request says "all possible tags should be registered".)
2. **Registration UX:** manage the registered set via a CLI command
   (e.g. `tcw config tags ...` / `tcw work tags ...`), or hand-edit
   `tcw-config.yaml`? (Leaning: hand-edit for v1, plus `tcw validate` catching
   unknown tags on items.)
3. **CLI shape:** `--tag X --tag Y` (repeatable) vs `--tags X,Y` (comma list)
   for `new`/`edit`; and the `list` filter flag (`--tag X`, AND vs OR when
   repeated).
4. **`tcw-config.yaml` schema:** what key holds the registered tags
   (e.g. `work.tags:` vs top-level `tags:`), and flat list vs mapping.
5. **Docs sync:** which docs (`README`, changelogs, release notes,
   `tcw-work` SKILL) must update — resolve in the plan stage.

## Decisions already made

- Tags live in / are registered from `tcw-config.yaml`.
- Items can carry multiple tags.
- Tags must appear in `tcw work list`, `tcw work show`, and the web UI.
