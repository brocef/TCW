# Spec — Phase B: Capability federation

Index: [`spec.md`](spec.md). Depends on Phase A (folder anatomy, stable ids, path addressing). This phase adds cross-project inheritance with per-project overrides and body composition. It mirrors taxonomy `extends`, plus the override/compose semantics taxonomy does **not** have.

## Proposed behavior

### B.1 Federation (mirror taxonomy)

- `tcw capabilities extends <alias> <ref>` / `tcw capabilities extends --rm <alias>` — declare/drop a federation alias in `docs/capabilities/.config.yaml` (`extends: {alias → ref}`), refusing a duplicate alias or unresolvable ref. `ref` is opaque to the interface (a sibling-repo path for the FS adapter).
- On load, each alias resolves to a nested `FsCapabilitiesStore` (same pattern as `FsTaxonomyStore.extends`, `tcw/store/fs.py:471-478`). Inherited capabilities are read on demand.
- **Cycle guard (explicit):** federation resolution carries a `_seen` set of visited store roots and refuses to re-enter one, and `check` reports `extends '<alias>': cycle in capability federation` — mirroring taxonomy exactly (`tcw/store/fs.py:624-632`). Prevents infinite recursion on A→B→A.
- `Capability` gains `origin` (`"local"` or the alias) and a `qualified` path (`alias/path` when inherited, bare when local), mirroring `Term` (`tcw/store/base.py:57-62`).
- Per-component: capabilities `extends` is independent of any taxonomy `extends`.

### B.2 Body composition (introduced here)

A capability's `meta.yaml` may carry two **optional ordered lists of attachment filenames** in its own folder:

- `prependedDocs: [a.md, …]`
- `appendedDocs: [b.md, …]`

Effective body =

```
prependedDocs (in order)  +  (local description.md if present, else inherited description.md)  +  appendedDocs (in order)
```

These are **bounded named attachments**, never a folder glob (AGENTS.md). `check` flags a listed-but-missing file and a present-but-unlisted extra `.md` in a capability folder. For a purely local capability with no inherited body and no prepend/append docs, the effective body is just `description.md` (Phase-A behavior, unchanged).

### B.3 What a child may do to an inherited capability

An inherited capability is **structurally read-only** — a child cannot delete or relocate it. `remove` on an inherited (`origin != local`) path **raises**, mirroring taxonomy's `remove` refusing a non-local term. A child may only:

1. **Override metadata** — child `meta.yaml` fields **partial-merge over** the inherited ones (e.g. `Status: Missing`, or `Status: Omitted`). An **absent** key inherits; a key set to YAML **`null`** clears the inherited field to its default (mirrors taxonomy `update_term`'s None-clears semantics — the only way to drop an inherited optional field); any other value (including empty string / empty list) is an explicit override value.
2. **Compose the body** — supply a child `description.md` to **replace** the inherited body, and/or `prependedDocs`/`appendedDocs` to wrap it (B.2). Supplying only append/prepend docs keeps the inherited prose.
3. Add its own **exclusive** local capabilities (ordinary Phase-A folders, no `overrides:`).

### B.4 The override entry (uniform folder, no special area)

A child override is an **ordinary capability folder** whose `meta.yaml` carries **`overrides: <id>`** — the upstream capability's stable id (Phase A). There is no separate `.overrides/` store; an override folder lives at a child-chosen path like any capability, and its own Phase-A `id` identifies it locally.

Resolution:

- A folder **with** `overrides:` is a **delta**, not a standalone local capability — it never surfaces at its own path in `list`/`get`; it merges onto the inherited capability it targets, at that capability's alias-qualified position. A folder **without** `overrides:` is an ordinary local capability. (So the resolver builds a reverse index `upstream-id → override-folder` by scanning local folders. ponytail: O(n) scan over a few dozen folders — fine; add an index only if the tree ever grows large.)
- `overrides: <id>` is a **bare** id resolved across the child's `extends` aliases. An id that resolves through **more than one** alias raises `AmbiguousRef`; the author disambiguates by writing `overrides: <alias>/<id>`. An id resolving to **nothing** is a `check` problem (dangling override). An id pointing at a **local** capability is a `check` problem (must target an inherited one).

### B.5 Merged read model

- `get(path)` / `get_capability_detail` — for an inherited path, returns the composed effective capability (merged fields + composed body), flagged `origin`. On an ambiguous `overrides:` id, raises `AmbiguousRef` (does not return a partial result).
- `list_all` — local + inherited merged, each flagged `origin` + **effective status** (override wins). An un-overridden inherited capability appears verbatim at its `alias/path`. A capability whose effective `Status` is `Omitted` still appears in `list` (with status `Omitted`) — it is **not** filtered out; `--status Omitted` selects them. `--local-only` restricts to local.
- Inherited entries surface at their alias-qualified upstream position; overrides merge **onto** that position (they do not create a second path).
- `search` — spans local + inherited composed bodies.

### B.6 Validation

`tcw capabilities check` additionally:

- resolves every `overrides: <id>` (dangling → problem; ambiguous across aliases → problem; targets a local capability → problem);
- validates that any capability's `prependedDocs`/`appendedDocs` exist and that no unlisted extra `.md` sits in the folder (B.2);
- reports a federation cycle (B.1);
- applies the locked `CAP_FIELDS`/`CAP_STATUSES` vocabulary to override folders too.

### B.7 Abstract interface additions (`CapabilitiesStore`)

Mirror the taxonomy additions, litmus-checked per method in `plan.md`:

- `extends_add(alias, ref)` / `extends_remove(alias)`
- `origin` / `qualified` on `Capability`
- override resolution + body composition folded into `get` / `list_all` / `get_capability_detail`
- an operation to create/update an override record (`overrides: <id>` + field/body/attachment deltas) — expressed as "create a local override record for an upstream reference," not "write a file at a path."

## Acceptance criteria

- In a child repo that `extends` a parent's capabilities: `tcw capabilities list` shows the parent's capabilities flagged `origin=<alias>` with the parent's statuses; `--local-only` hides them.
- Overriding `Status` to `Missing` on an inherited capability makes the child report `Missing` while the parent still reports its own status (upstream unchanged).
- Supplying only an `appendedDocs` entry yields `show` = parent body + appended text; supplying a child `description.md` replaces the parent body; a `prependedDocs` entry prepends.
- Setting an inherited optional field to empty clears it; `Status: Omitted` marks it omitted and it still appears in `list`.
- `remove` on an inherited path raises; the capability cannot be deleted from the child.
- A `overrides:` id that resolves to nothing, resolves through two aliases, or points at a local capability each produce a distinct `check` problem; `get` on the ambiguous case raises `AmbiguousRef`.
- An A→B→A federation cycle is refused (no infinite recursion) and reported by `check`; A→B→C resolves with correct `origin`/`qualified` at each level.
- A listed-but-missing prepend/append doc, and a present-but-unlisted extra `.md`, are each a `check` problem.
- No `CapabilitiesStore` method added in this phase is FS-only (litmus test recorded in `plan.md`).
- Existing single-project capability behavior (no `extends`) is unchanged; the suite passes.
