# Spec — Unify folder substrate + capability federation

This is a **phased spec index**. Shared context lives here; each phase's detail lives in its own file:

- **Phase A — Unify the substrate:** [`spec-phase-a.md`](spec-phase-a.md)
- **Phase B — Capability federation:** [`spec-phase-b.md`](spec-phase-b.md)

Phase B depends on Phase A (federation is built on the folder+id substrate). Ship A first; B is layered on top.

## Capability changes

TCW dogfoods its own capabilities, so this work is a product delta to the `capabilities` component. Expected ledger entries (final wording set at the tcw-capabilities planning gate during `plan.md`):

- **New:** "Federate capabilities from another project" — a user runs `tcw capabilities extends <alias> <ref>` so this project inherits another's capabilities.
- **New:** "Override or extend an inherited capability" — a user overrides an inherited capability's metadata (e.g. `Status`) and/or composes its body (prepend/append docs, introduced in Phase B) without redeclaring it.
- **New:** "Address a capability by path" — capabilities are path-addressed folders with a stable id.
- **Changed:** "Add / show / list / set / validate a capability" — all shift from `file#heading` addressing to path-addressed folders; `list` shows inherited entries flagged by origin + effective status; `Subject` becomes multi-valued.
- **Removed:** state-variant (`with-`/`without-`) capabilities and `errors.md`/`states.md` sidecars (unused; dropped in the re-base).

## Problem

Two user-facing clients (web frontend, mobile app) over one server have near-identical capabilities. Redeclaring them in each project is redundant and lets the product/UX story silently diverge; but one client is often *behind* the other, so a shared set must still allow per-project status and per-project detail deltas. Today capabilities cannot be shared across projects at all (only taxonomy federates), and the capabilities component sits on a different storage model (flat/folder `.md` files with inline `**Field:**` metadata and `#heading` addressing) than taxonomy and work (folder + `meta.yaml` + `description.md`), so paths and addressing are inconsistent across the three axes.

## Goals

1. Capabilities can `extends` another project's capabilities, resolved on read (upstream stays source of truth).
2. A child can **override** inherited metadata (field-merge) and **compose** the inherited body (bounded prepend/append docs), or mark an inherited capability `Omitted`; a child cannot delete or relocate an inherited capability. A child may add its own exclusive capabilities.
3. Taxonomy, capabilities, and work share one folder anatomy and are all **path-addressable**; taxonomy additionally keeps its concise slug system.
4. Each capability has an opaque, immutable **stable id** — the durable override key and the designed target for the future `tcw://` scheme.

## Non-goals

- **③ is out of scope** — the `tcw://(namespace/)[T|C|W]/[path-or-slug]` URI scheme, `tcw validate`, and web-view link navigation are a **separate future spec**. This spec only guarantees the stable-id target exists.
- No change to work's "status is where it lives / atomic `mv` = transition" model. Work becomes path-*addressable* (locator `active/…/slug`); its slug stays the stable id. Work paths are **not** stable identities.
- No new taxonomy features; taxonomy's folder anatomy is the template others converge on, not itself reworked (beyond any minimal shared-core extraction).

## Constraints

- **Abstraction litmus test (AGENTS.md) governs every operation.** Federation, overrides, and body composition must be expressible in the abstract vocabulary (item · status · reference · body/fields/attachments) and honorable by a non-filesystem store. Filesystem realizations stay in the adapter.
- `prependedDocs` / `appendedDocs` are **explicit ordered lists** in `meta.yaml` — bounded named attachments, never "glob every `.md` in the folder."
- Override deltas are abstract records keyed by upstream **id**, not filesystem tricks; resolution reuses the nested-store pattern taxonomy `extends` already uses.
- Stable ids must be assigned deterministically enough that the migration/backfill is reproducible and reviewable in a PR.

## Current-state findings

- `FsTreeStore` (`tcw/store/fs.py:415`) is already the shared base for all three stores (`COMPONENT` dir, optional `CONFIG_NAME`, `_stage`/`_rm`, `from_node`). Convergence builds on it — it is not a greenfield extraction.
- **Taxonomy** already uses folder + `meta.yaml` + `description.md` and federates via `config.yaml` `extends: {alias → repo}` with read-through nested `FsTaxonomyStore`s and `origin`/`qualified` on `Term` (`tcw/store/fs.py:462-695`, `tcw/store/base.py:43-136`).
- **Capabilities** (`tcw/store/fs.py:834-1180`) use flat `.md` or folder `capabilities.md`, multi-`## heading` files, inline `**Field:**` metadata parsed into `Capability.fields`, and `file#heading` refs. It already has a `.config.yaml` hook (unused) and `CAP_STATUSES` already includes `Omitted`.
- **Dead machinery to drop:** state-variant files (`with-`/`without-` prefixes, `state-conventions` config) and `errors.md`/`states.md` sidecars — code exists (`_state_prefixes`, `_is_variant`, `_CAP_SIDECARS`) but **nothing on disk uses them**.
- **Migration surface:** ~36 capabilities across ~13 files under `docs/capabilities/`, a mix of flat files, folder `capabilities.md` entries, and folders holding both.
- **Consumers to update:** `tcw/capabilities/cli.py` (init/list/show/add/set/search/check), `tcw/serve/__init__.py` capability routes (`/api/capabilities`, `/api/capabilities/<ref>`), `skills/tcw-capabilities/SKILL.md`, README, changelog, release notes.

## Acceptance criteria (rollup)

- All Phase A + Phase B acceptance criteria pass (see phase files).
- `tcw taxonomy check`, `tcw capabilities check`, and the full test suite pass after migration.
- The abstract `CapabilitiesStore` interface gains no method that only the FS adapter could honor (litmus test applied per method in `plan.md`).

## Risks & dependencies

- **Migration risk** — converting the live `docs/capabilities/` tree in-repo. Mitigate with a scripted, reviewable, idempotent migration + a test asserting pre/post capability set equality.
- **Blast radius** — CLI/serve/skill all shift addressing simultaneously; a phased spec keeps A (substrate) reviewable before B (federation) lands.
- **Interface churn** — reshaping `CapabilitiesStore` risks smuggling FS-only semantics into the abstract spine; every new/changed method gets a litmus check in the plan.
- No related open work items conflict (this is the first federation work on capabilities).

## Resolved decisions (post-review)

- **Work path-as-input (Phase A A.4): KEEP, minimal form.** Dual review flagged it as near-YAGNI, but the user opted to keep a uniform "paths work everywhere" input surface. Minimal spec (A.4): extract the slug from the last segment; a leading status segment, if present, must equal the item's current status (else error); intermediate segments ignored. The slug remains the stable id.

## Related

- Deferred sibling spec: `tcw://` link protocol + `tcw validate` + web-nav (see this item's `initial-request.md`, §Out of scope).
