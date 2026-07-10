# Unify folder substrate across taxonomy/capabilities/work and add capability federation

## Requested outcome

Two linked goals, from a scenario the user gave: a **web server**, a **web frontend**, and a **mobile app**, where frontend and mobile talk to the same server and have near-identical user capabilities. Redeclaring capabilities in both risks unwanted product/UX divergence; but one client may be *behind* the other, so their capability sets should be shared yet allow per-project status/detail deltas.

1. **Capability federation** — let a TCW root's capabilities `extends` another's (like taxonomy). An inherited capability can be locally overridden (metadata) and extended (content); a project may add its own exclusive capabilities; a project may **not** delete an inherited capability, only mark it `Omitted`.
2. **Unified folder substrate** — put taxonomy, capabilities, and work on the same folder anatomy (`meta.yaml` + body + named attachment docs) and make all three **path-addressable**, for predictable/consistent paths. This is the codebase's own anticipated "Phase-4 shared tree-store core" — now due, since all three components are real.

## Decisions already made (brainstorming)

- **Sequencing / structure:** one centralized work item, phased spec. `spec.md` is an index that points to `spec-phase-a.md`, `spec-phase-b.md`. All in one item, not split into child items.
- **Attach key for overrides:** each capability carries an opaque **stable id** in `meta.yaml` (`id: cap-a1b2c3`), assigned at creation, immutable. Overrides key on the id (survives upstream re-wording). Backfilled during migration. Designed to be the future `tcw://` target.
- **Override model (folder-native):** a capability is a folder. Effective body = `prependedDocs…` + (local `description.md` if present, else inherited body) + `appendedDocs…`, where `prependedDocs`/`appendedDocs` are **explicit ordered lists** in `meta.yaml` (bounded named attachments, never a folder glob). So: override = supply own body; extend = supply only append/prepend docs; metadata override = child `meta.yaml` fields partial-merge over inherited ones (`Status: Missing`, `Omitted`, …).
- **Resolution:** overrides resolve *on read* (child stores a thin delta; upstream stays source of truth), via the same nested-store pattern taxonomy `extends` uses. Federation is per-component (capabilities extends capabilities). Inherited caps surface at their alias-qualified upstream position and are structurally read-only (no delete/relocate; only override / `Omitted`). `list` shows local + inherited merged with `origin` + effective status; `--local-only` restricts. Ambiguous id → error; dangling `overrides:` id → a `check` problem.
- **Multi-valued taxonomy link:** make the existing `Subject:` field **multi-valued** (it already resolves against the taxonomy in `check()`), rather than adding a parallel field.
- **Full folder re-base of capabilities** approved, including the one-time migration of `docs/capabilities/` (each `## heading` → a folder) + id backfill, and the CLI/skill/serve-viewer shift to path-addressed folders.
- **Work path model:** work is path-**addressable**, but its path is a status-relative *locator* (`active/…/slug`) — the **slug stays the stable id**, honoring "status is where it lives / atomic mv = transition." Only taxonomy/capabilities paths are stable identities. Taxonomy keeps its concise **slug** system alongside path addressing.

## Proposed phases

- **Phase A — Unify the substrate.** Extract the shared folder+path tree-store core; consistent folder anatomy + path addressing for T/C/W; re-base capabilities onto folders; migrate `docs/capabilities/` + backfill stable ids. Taxonomy keeps slugs.
- **Phase B — Capability federation.** `extends` for capabilities; override (field-merge) + prepend/append body composition; `overrides: <id>` resolution; `Omitted` semantics; multi-valued `Subject`.

## Constraints / non-goals

- **Abstraction litmus test governs everything** (AGENTS.md): every operation must be implementable by a non-filesystem store. `prependedDocs`/`appendedDocs` stay bounded named lists, not globs. Override deltas are abstract records keyed by upstream id, not FS tricks.
- **Out of scope (separate future spec):** ③ the `tcw://(namespace/)[T|C|W]/[path-or-slug]` URI scheme, `tcw validate`, and web-view link navigation. Phase A's stable ids are that spec's designed target, but none of it is built here.
- Do not break work's atomic-mv-as-transition model to force stable work paths.

## Open questions for spec planning

- Physical placement of a child's override entry in the FS adapter (mirrored upstream path vs a dedicated overrides area keyed by `(alias, id)`) — an adapter detail, but pick one in the spec.
- Whether taxonomy/work folder anatomy needs any change to converge, or capabilities simply adopts the already-shared shape.
- Exact reshaped `tcw capabilities` CLI surface (`add`/`show`/`list`/`set`/`check` + new `extends` + override/append affordances).
- Migration mechanics for existing multi-heading capability files, and how the stable-id backfill is made deterministic/reproducible.
