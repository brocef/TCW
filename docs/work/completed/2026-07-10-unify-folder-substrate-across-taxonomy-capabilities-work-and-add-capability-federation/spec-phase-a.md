# Spec — Phase A: Unify the substrate

Index: [`spec.md`](spec.md). This phase re-bases capabilities onto the shared folder+path substrate and makes all three axes path-addressable. It contains **no federation and no body composition** (both Phase B) — but it establishes the folder anatomy, stable ids, and path addressing that Phase B needs.

## Proposed behavior

### A.1 Folder anatomy (shared)

A capability becomes a **folder**, matching taxonomy/work:

```
docs/capabilities/auth/providers/github/
  meta.yaml          # id + metadata fields (see A.2)
  description.md     # the body (the "As a user …" story)
```

- A capability's **path** is its folder path under `docs/capabilities/` (e.g. `auth/providers/github`). Path = stable identity for capabilities.
- Grouping is folder nesting (`auth/`), replacing today's "one file, many `## headings`."
- Common folder read/write (load `meta.yaml` + `description.md`, resolve by path, atomic write + stage) moves into `FsTreeStore` so taxonomy and capabilities share it. Keep the extraction minimal — only what both genuinely share (AGENTS.md: "extract the shared tree-store core only once two components are real"; it is a refactor of existing code, not a new abstraction layer).

### A.2 `meta.yaml` fields

Former inline `**Field:**` metadata moves into `meta.yaml` keys. The locked vocabulary (`CAP_FIELDS`, `CAP_STATUSES`, `CAP_PRIORITIES`, `CAP_LIFECYCLES` in `tcw/store/base.py`) is preserved. Additions/changes:

- **`id`** — opaque, immutable stable id (e.g. `cap-a1b2c3`). Assigned at `add`; **never derived from path or heading text** (the id is store-agnostic; conceptually a fresh opaque token). Immutable once assigned. Migration derivation is a one-time adapter detail (A.6), not part of the id's meaning.
- **`Subject`** — now **multi-valued** (a YAML list of taxonomy slugs). A single scalar is still accepted and treated as a one-element list. `check()` resolves *every* entry against the taxonomy (extends `_check_subject`).

`Status` keeps `CAP_STATUSES` (incl. `Omitted`, already present).

### A.3 Body

The effective body of a capability in Phase A is exactly its `description.md`. (Phase B generalizes this to prepend/append composition + inherited-body fallback; Phase A introduces none of that machinery, because Phase A has nothing to wrap.)

### A.4 Path addressing across T/C/W

- **Taxonomy** — already path/slug addressed; unchanged, keeps slugs.
- **Capabilities** — `add`/`show`/`list`/`set`/`check` take a **path** (`auth/providers/github`), replacing `file#heading` and `[state]` syntax. `#heading` and `[state]` addressing is removed.
- **Work** — gains path addressing as an **input locator** (see the open question in `spec.md`; the minimal specified form): a work command accepts `[<status>/]…/<slug>` in addition to a bare slug. Resolution extracts the slug from the **last** segment; a leading `<status>` segment, if present, must equal the item's current status (else error); intermediate nesting segments are ignored. The slug remains the resolved stable id; no change to transitions or storage.

### A.5 CLI surface (capabilities)

- `tcw capabilities add <path> [name] [-s status] [--body -]` — scaffold a capability folder (`meta.yaml` with a fresh `id` + `description.md`). `--folder` and flat/folder collision logic are removed (everything is a folder).
- `tcw capabilities show <path>` — print body + metadata (incl. `id`).
- `tcw capabilities list [--status S] [--namespace N]` — unchanged surface (Phase B adds origin/`--local-only`).
- `tcw capabilities set <path> --field K=V …` — update `meta.yaml` fields. A field value **replaces** the current value (no append); a multi-valued field (`Subject`) is passed comma-separated and replaces the whole list.
- `tcw capabilities check` — folder/`meta.yaml` validation + existing metadata/Subject/Feature checks; drops flat/folder-collision and state-variant checks.
- `tcw capabilities search <query>` — unchanged behavior over bodies.

### A.6 Abstract-interface delta

Folder-per-capability makes the file+heading model obsolete. Explicit before/after (litmus-checked per item in `plan.md`):

- **`Capability`** — loses `file_id`, `heading_slug`, `ref` (`= file_id#heading_slug`); gains `path` (stable identity), `id` (opaque stable id), and `origin`/`qualified` (Phase B). `status` property preserved.
- **`CapabilityFile`** (a file holding many caps) — **removed**; `get()` returns a single `Capability` for a path (not a `CapabilityFile`).
- **`add_entry(collection, name, …)`** — **removed** (its whole reason was multi-entry files).
- **`get_capability_detail` / `update_capability`** — drop the `heading_slug=` disambiguator param (a path resolves to exactly one capability).
- **Consumers rewritten:** `tcw/capabilities/cli.py` (`#`-splitting, `--folder` at :73-74,166,169), `tcw/serve/__init__.py` capability routes (`#`/`ref` addressing at :99-103), and any `heading_slug()` usage tied to entry identity.

### A.7 Migration + id backfill

A scripted, one-time migration (runnable once, committed as data):

1. For each existing capability entry, create a capability folder:
   - **Multi-heading file** (`work/capabilities.md` with several `## X`) → one folder per heading: `work/<heading-slug>/`.
   - **Single-heading flat or `capabilities.md` file** (e.g. `work/audit-work-backlog.md`, ~half the live tree) → **collapse**: the file's own path becomes the folder (`work/audit-work-backlog/`); the heading segment is dropped (no redundant double-nesting).
   Write `meta.yaml` (inline fields → keys; `Subject` scalar → one-element list) + `description.md` (the block body).
2. Assign each a stable `id` = `cap-` + first 6 hex of `hashlib.sha1(original_ref)` where `original_ref = file_id#heading_slug`. This is **reproducible** from a stashed pre-migration tree (fixed inputs → fixed ids), so the PR diff is reviewable. Uniqueness relies on `heading_slug()` being unique **within** each source file — verified true on current data (zero duplicate headings across all 13 files); the migration asserts this and **fails loudly** on any collision rather than silently disambiguating.
3. Delete the old flat/`capabilities.md` files and the dead state-variant/sidecar handling code (`_state_prefixes`, `_is_variant`, `_CAP_SIDECARS`).
4. An equality test asserts the migrated set matches the pre-migration set over the **full `CAP_FIELDS`** (name, Status, body, Subject, Feature, Priority, Planning doc, …) — not just `(name, status, body)` — and that every entry received a unique `id`.

(Note: "reproducible ids" and "idempotent re-run" are distinct — after step 3 removes the sources, a re-run is vacuously a no-op; reproducibility means re-deriving identical ids from a preserved pre-migration snapshot.)

## Acceptance criteria

- Every capability under `docs/capabilities/` is a folder with `meta.yaml` (incl. a unique `id`) + `description.md`; no flat `.md`, `capabilities.md`, `with-`/`without-`, `errors.md`, or `states.md` files remain.
- `tcw capabilities show <path>` renders `description.md`; a single-heading source collapses to a single folder (no double-nested path).
- `Subject` accepts a list; `set … --field Subject=a,b` replaces the list; `check` resolves each entry against the taxonomy.
- `tcw capabilities add auth/x` creates a folder with a fresh opaque `id`; two `add`s never collide.
- A work command resolves both `my-slug` and `active/…/my-slug` to the same item; a wrong leading status segment errors; transitions/tests unchanged.
- `Capability` no longer exposes `file_id`/`heading_slug`/`ref`; `CapabilityFile` and `add_entry` are gone; serve + CLI no longer use `#` addressing.
- Migration re-derives identical ids from a pre-migration snapshot; the full-`CAP_FIELDS` equality test passes; a simulated duplicate heading makes the migration fail loudly.
- Shared folder read/write lives in `FsTreeStore`; `FsCapabilitiesStore` and `FsTaxonomyStore` no longer duplicate it. `tcw capabilities check`, `tcw taxonomy check`, and the suite pass.
