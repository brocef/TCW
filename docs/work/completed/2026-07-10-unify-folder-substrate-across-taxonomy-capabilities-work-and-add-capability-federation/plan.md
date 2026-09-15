# Plan — Unify folder substrate + capability federation

Spec: [`spec.md`](spec.md) → [`spec-phase-a.md`](spec-phase-a.md), [`spec-phase-b.md`](spec-phase-b.md). Capability deltas: [`capabilities.yaml`](capabilities.yaml).

**Method:** TDD throughout (pytest over `tmp_path` git repos, the repo norm). **Phase A must land fully before Phase B.** Within a phase, the store core lands first; CLI / serve / docs then proceed in parallel — but see the **import-coupling** note: A-T2/A-T4/A-T6 are not *individually* green (removing `CapabilityFile`/`add_entry` breaks package imports and serve at once), so they co-land as one green mergeable unit.

**Breaking change, intentional:** the capabilities CLI/store surface changes without a deprecation shim (`#heading`/`[state]`/`--folder`/`add_entry`/`collection` removed). Justified: pre-1.0 (v0.10.x), internal single-consumer surface, updated in lockstep with the skills/serve/tests in this same work item. No back-compat layer.

**Litmus discipline:** every new/changed `CapabilitiesStore` method is checked against "could a non-FS store honor this?" before it's added (table in B-T0). Both review passes verdicted the interface clean.

---

## Phase A — Unify the substrate

### A-T1. Shared folder read/write in `FsTreeStore` (refactor, no behavior change)
- Pull the folder-node read/write taxonomy already uses (load `meta.yaml` + `description.md`, resolve by path, atomic write + `_stage`) up into `FsTreeStore` (`tcw/store/fs.py:415`) as shared helpers. Taxonomy switches to them with **zero behavior change** — its existing tests are the safety net for the extraction.
- Keep it minimal: only what taxonomy and capabilities genuinely share (AGENTS.md — refactor, don't invent a layer).
- **Touch:** `tcw/store/fs.py`. **Verify:** `pytest tests -k taxonomy` unchanged.

### A-T2. Capability model + folder adapter (replaces file+heading)
- `tcw/store/base.py`: reshape `Capability` — drop `file_id`/`heading_slug`/`ref`; add `path`, `id`, `origin="local"`, `qualified`. **Remove `CapabilityFile` and `add_entry`**; drop the `heading_slug=` param from `get_capability_detail`/`update_capability`. Keep `CAP_*`.
- `tcw/store/fs.py` `FsCapabilitiesStore`: rewrite `get`/`list_all`/`search`/`add`/`remove`/`set`/`check`/`get_capability_detail`/`update_capability` against folders. **Delete dead code:** `_state_prefixes`, `_is_variant`, `_CAP_SIDECARS`, the state/flat/`capabilities.md` branches of `_resolve_file`, `parse_capability_file`, `_set_inline_fields`, `_set_cap_body`, `_IDENT_RE`, `_FIELD_RE`. Fix the `from .base import … CapabilityFile` import (`fs.py:27`).
- **Grouping vs capability gate (correctness):** the folder walk must treat a directory as a capability **iff it contains `meta.yaml`**; a pure grouping directory (e.g. `docs/capabilities/capabilities/`) is skipped. A folder may be *both* a capability and a grouping parent (e.g. `web/` with `meta.yaml` nesting `web/editing/`). Do **not** reuse taxonomy's "every dir is a node" walk (`_local_slugs`, `fs.py:503-505`) unchanged.
- Stable-id mint for `add`: opaque token (`cap-` + hex from `uuid4`), **not** path-derived; unique within the store.
- `Subject`: parse scalar-or-list; `set --field Subject=a,b` replaces the list; `check` resolves every entry.
- **Existing-test migration (required):** rewrite `tests/test_capabilities.py` (old model throughout — `[state]` variants `:87,96`, `#heading` `:223,234`, `file_id`/`heading_slug` `:104-113`); delete the 6 `add_entry` tests in `tests/test_store_editor.py:662-998`; fix `tests/test_environment_hardness.py:192` (`folder=True`, `c.file_id`). New tests: folder CRUD, path resolution, grouping-gate, multi-valued Subject, id uniqueness.
- **Litmus:** path-addressing, `meta.yaml` fields, opaque `id` all abstract. ✓

### A-T3. Migration script + backfill (destructive → made safe)
- One-time script under `scripts/` (mirror `scripts/cut_version.py`), **dry-run by default, `--apply` to write** (mirrors `tcw work consolidate-plans`). Runs against a **clean git tree** — git is the rollback; nothing is committed until the diff is reviewed. Conversion:
  - multi-heading file → folder per heading (`<file>/<heading-slug>/`); single-heading flat/`capabilities.md` → collapse to the file's own path.
  - inline `**Field:**` → `meta.yaml`; `Subject` scalar → 1-element list; body → `description.md`.
  - id = `cap-` + first 6 hex of `hashlib.sha1(f"{file_id}#{heading_slug}".encode())`; assert no duplicate `(file, heading_slug)` and **fail loudly** on any hash collision.
- **Order:** convert → run the equality assertion → only then delete old files (the assertion **gates** deletion, in-process). 
- **Tests:** full-`CAP_FIELDS` set equality pre/post (normalizing `Subject` scalar→1-list so it doesn't spuriously fail) + every entry has a unique id + ids re-derive identically from a preserved snapshot + a synthetic duplicate-heading input fails loudly + `--dry-run` writes nothing.
- Run `--apply` on the live tree; commit migrated `docs/capabilities/` as one reviewable data commit (also migrates the two just-declared `Missing` entries).
- **Touch:** `scripts/migrate_capabilities_to_folders.py`, `docs/capabilities/**`, `tests/`.

### A-T4. CLI surface (capabilities) — co-lands with A-T2
- `tcw/capabilities/cli.py`: `add <path>` (no `--folder`), `show`, `list`, `set <path> --field …`, `search`, `check` — path-addressed; drop `#heading`/`[state]` parsing (`:73-74,166,169`).
- **Tests:** CLI end-to-end per command.

### A-T5. Work path-input (minimal, status-prefix only)
- **Real touch point:** `resolve_qualified_work_ref` (`tcw/store/fs.py:181-217`) already claims `/`-bearing refs for `sub/proj/<slug>` cross-node addressing. A-T5 intercepts **there**, not only in `cli.py`.
- **Discriminator (explicit design decision):** a ref is a *status-locator* iff its **first segment ∈ `WORK_STATUSES`** (`inbox|backlog|active|completed`) — then take the slug from the **last** segment, require the status segment to equal the item's current status (else error), ignore intermediate segments. Otherwise it stays a `sub/proj/<slug>` node ref. Documented edge case: a subproject literally named after a status is not addressable via the bare status-prefix form (use the bare slug) — acceptable.
- **Tests:** `my-slug`, `active/…/my-slug`, wrong-status-segment error, `sub/proj/<slug>` still resolves (no regression against `test_*` for qualified refs).

### A-T6. Serve viewer (capabilities) — co-lands with A-T2
- `tcw/serve/__init__.py`: capability GET routes → path addressing; detail returns `id` + body; drop `_RE_CAPABILITY_REF`/`#`/`ref` (`:99-103`). **Rework the create path:** `POST /api/capabilities` is built around the removed `collection`/`add_entry` (`:807-844`) — rewrite to path-create.
- `tcw/serve/static/app.js` (real scope, not a footnote): `cap.ref`/`editor.ref` (`:531,756`), `encodeURIComponent(item.ref)` detail/PATCH URLs (`:779,1683`), list rows keyed on `item.ref`/`item.file_id` (`:1326-1344`), `renderCapability` (`:1680-1710`), capability editor (`:2009-2049`), and the `collection`-based create form `renderCapabilityCreate` (`:2435-2490`).
- **Tests:** update `tests/test_serve_write.py` `file_id` asserts (`:178,737,844`); serve route tests for path addressing + create.

### A-T7. Phase-A docs sync
- `skills/tcw-capabilities/SKILL.md` — path addressing, folder model, multi-valued Subject, removed `--folder`/`#heading`. **[Skill-Driven-Component]**
- `README.md` — capabilities CLI usage. **[Public-API]**
- `docs/release-notes/upcoming.md` + `docs/changelogs/upcoming.md` (Changed/Removed; commit range via `git rev-parse --short HEAD`). **[Public-API / Any-Code-Change]**

---

## Phase B — Capability federation

### B-T0. Interface-addition litmus table (record before coding)
| New/changed op | Abstract meaning | Non-FS store honors it by |
|---|---|---|
| `extends_add/remove(alias, ref)` | register/drop a federation edge | an alias→store-locator record |
| `origin`/`qualified` on `Capability` | provenance of a resolved item | tagging each returned item with its source |
| **`get_by_id(id)` within a store** | resolve an opaque id to its capability | a keyed `id → item` lookup (each alias store scans its ids) |
| override resolution in `get`/`list_all`/`get_capability_detail` | merge a local delta onto an upstream item by id | keyed `upstream-id → delta` lookup + field/body merge |
| create/update override record (`overrides:<id>` + deltas) | attach a delta to an upstream reference | insert a delta row keyed by the upstream id |
| body composition (prepend/description/append) | ordered assembly of named parts | concatenate named parts in declared order |
- The opaque-`id` lookup (row 3) is the one op taxonomy's slug resolution doesn't already cover — name it explicitly; it's still litmus-clean (a keyed lookup).

### B-T1. Federation plumbing (mirror taxonomy)
- `.config.yaml` `extends: {alias→ref}`; nested `FsCapabilitiesStore` per alias with a `_seen` cycle guard (mirror `FsTaxonomyStore.__init__` `fs.py:471-478` + the `check` cycle report `fs.py:624-632`). `extends_add`/`extends_remove` + `get_by_id`.
- CLI `tcw capabilities extends <alias> <ref>` / `--rm <alias>`. **Guard** `extends` against `DEFAULT_SUBCOMMAND="show"` mis-dispatch (mirror taxonomy's guard + `test_taxonomy.py:336`).
- **Tests:** extends add/rm, inherited read-through, cycle refusal + `check` report (**A→B→C→A**), deep **A→B→C→D** `origin`/`qualified`, the `extends`-not-mis-dispatched-as-show guard.

### B-T2. Override + composition resolution
- Local reverse index `upstream-id → override-folder` (folders whose `meta.yaml` has `overrides:`); such folders are deltas, never standalone caps. Resolve `overrides:` id across aliases via `get_by_id` (bare; `alias/<id>` to disambiguate; `AmbiguousRef` on multi-alias).
- Field partial-merge over inherited (**absent** inherits, **`null`** clears, else overrides); body composition `prepend + (local description.md ?? inherited) + append`. `remove` on `origin!=local` raises.
- `list_all` merges local + inherited + effective status (`Omitted` shown, not filtered); `--local-only`. `search` spans composed bodies.
- **Tests:** status override, body replace/append/prepend, `null`-clears-field, Omitted visible, remove-inherited raises, ambiguous/dangling/local-target override, **composition when upstream `description.md` is empty/absent** (prepend/append only).

### B-T3. Validation (`check`)
- Add: dangling/ambiguous/local-target `overrides:`; prepend/append doc existence + no-unlisted-extra-`.md`; federation cycle; locked vocabulary on override folders.
- **Tests:** one case per new problem class.

### B-T4. Serve + Phase-B docs sync
- Serve: show `origin`/effective status, render composed body, expose inherited entries — extends the same `app.js`/route sites reworked in A-T6.
- Docs: `skills/tcw-capabilities/SKILL.md` (extends, override, composition, federated-cap planning-gate + ledger-flip wording) **[Skill-Driven-Component]**; `README.md` **[Public-API]**; release-notes + changelog (Added) **[Public-API / Any-Code-Change]**.

---

## Parallelization & dependencies
- **A → B strictly sequential.**
- Within A: A-T1 → A-T2 → A-T3. A-T4/A-T6 **co-land with A-T2** (shared import surface — none is individually green); A-T7 follows; **A-T5 is fully independent** (touches only work-ref resolution) and may run anytime.
- Within B: B-T0 → B-T1 → B-T2 → B-T3; B-T4 after B-T2.

## Verification (per phase, before proceeding)
- Full `pytest` green (incl. the migrated existing tests — A-T2/A-T6).
- `tcw taxonomy check`, `tcw capabilities check` clean.
- Phase B: a two-repo `extends` smoke test via the `verify` skill — sibling repos under `tmp_path` with `../base` relative refs + `extends_add`, mirroring the taxonomy federation harness (`test_taxonomy.py:289-341`).
- `tests/test_plugin_manifests.py` unaffected until a version bump.

## Documentation-sync tasks (triggers expected to fire)
- **[Skill-Driven-Component]** `skills/tcw-capabilities/SKILL.md` — A-T7 + B-T4.
- **[Public-API]** `README.md`, `docs/release-notes/upcoming.md` — A-T7 + B-T4.
- **[Any-Code-Change]** `docs/changelogs/upcoming.md` — A-T7 + B-T4 (commit ranges).
- Run the `documentation-sync` skill before completion.

## Closeout (not part of implementation)
- **Reconcile capabilities:** flip `capabilities/federate` and `capabilities/override-inherited` to `Supported` and apply the `changed:` edits — at `tcw work complete`. **Note:** this item's `capabilities.yaml` back-pointers use pre-migration `#heading` refs (`capabilities#add-a-capability`); after A-T3 they are path-addressed (`capabilities/add-a-capability`) — flip using the post-migration path form.
- Offer a version bump via `python scripts/cut_version.py` (likely **minor** — additive CLI surface + migration; 5-file lockstep enforced).
- `tcw work start <slug>` is the implementation boundary — run it (with `spec.md`/`plan.md` committed) as the first implementation commit, before any code edit. `--worktree` recommended given the blast radius.
