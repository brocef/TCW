# Phase 3 — Capabilities (TCW component 2 of 3: the user stories)

**Status:** spec ✓ · build ☐ not started
**Delivers:** `tcw capabilities` + `FsCapabilitiesStore` over the bounded `docs/capabilities/` tree; `Subject`↔taxonomy validation in `check`.
**Depends on:** Phase 1 (package/CLI), Phase 2 (taxonomy — `check` validates `Subject:` refs against the `TaxonomyStore`).
**Build checklist:** `CapabilitiesStore` interface → `FsCapabilitiesStore` → the five subcommands (B.2) → identifier resolution (A.6) → `check` incl. cross-component `Subject` validation → tests (B.7).

> Spec **and** build plan for component 2 — a capability is a **miniature user story** ("*as a user, I can…*"). Built **second, right after taxonomy**: it depends only on taxonomy (its `check` validates `Subject:` refs against the `TaxonomyStore`) and is its near-clone, so the shared tree-store core is extracted from the two (Phase 4) before work is built. Framework rules: [`../../AGENTS.md`](../../AGENTS.md). Build order: [`INDEX.md`](INDEX.md).

**Date:** 2026-06-18
**Scope:** the conceptual model (Part A) plus the buildable `tcw capabilities` tool (Part B). Sibling components: [`phase-2-taxonomy`](phase-2-taxonomy.md), [`phase-5-work`](phase-5-work.md). This spec formalizes the **artifact half** of the absorbed `skill-cefailures:capabilities-sdlc` skill (its v2 design) as a TCW component; the **process half** is already structural in the work lifecycle (the work phase's A.7).

---

## Part A — The model

### A.1 Place in TCW

The system has three components, defined in dependency order — the `tcw` binary's three subcommand groups:

1. **`tcw taxonomy`** — the *things* an application deals with. The **nouns**.
2. **`tcw capabilities`** — what a user can do with them, each a miniature user story. The **user stories**.
3. **`tcw work`** — the changes to those capabilities and to the machinery (and to the project itself). The **changes**.

Capabilities sit in the middle: a capability is a **miniature user story** about a taxonomy *thing* ("*as a user, I can …*"), and a work item realizes or changes a capability. Both links are loose, one-directional pointers — capability→term and work→capability (A.7, A.8). A capability is the **standing layer**: it states *what a user can currently do*, independent of any work item, and persists while work items freeze in `completed/`.

This spec covers the capabilities component. `tcw taxonomy` and `tcw work` are their own specs; this one references them rather than restating them.

### A.2 Capabilities form a bounded tree

All capability documentation in a node lives in **one tree rooted at `docs/capabilities/`** — never scattered across the code tree. This is the structural decision that makes capabilities isomorphic to taxonomy (`docs/taxonomy/`) and to work (`docs/work/`), and the one that satisfies the framework prime directive: a `CapabilitiesStore` can enumerate a **bounded namespace**; it must never "glob the code tree for `capabilities.md`" (the open-namespace anti-pattern the system guide bans).

- **Top-level folders are namespaces.** A recommended starter set — `routes/ components/ features/ api/ roles/ conditions/` — is illustrative, not fixed; a node extends it (`jobs/ cli/ webhooks/ …`) and documents its set in the node's config. The tree's shape *is* the project's logical structure.
- **The tree is the routing.** A capability's identity is its path under `docs/capabilities/` (`routes/login`, `api/auth/login`), exactly as a taxonomy term's identity is its path under `docs/taxonomy/`.

> **Co-location, reconciled.** Earlier TCW prose (work-sdlc A.7) described "co-located `capabilities.md`". The capabilities tree is *not* co-located with code — but the only load-bearing filesystem superpower, **one atomic commit landing code + a capability flip + a work-item transition**, needs only *same-repo*, not literal directory adjacency. It survives intact. (The work-sdlc spec's A.7 wording is reconciled to this layout.)

### A.3 Capability anatomy

A **capability file** is `# <Subject> — capabilities` holding one or more capabilities. A **capability** is a `## <name>` heading (natural-language imperative — "Sign in with Google", not `googleSignIn`) for one discrete user action, carrying:

- an **inline metadata block** — `**Field:** value` lines stacked immediately under the heading (no blank line), then a blank line, then the body;
- a **body** — 1–3 short paragraphs from the user's perspective (trigger · behavior · outcome). More than three paragraphs ⇒ it is probably two capabilities.

**File-vs-folder rule.** A capability is a **flat file** by default (`components/footer.md`). Promote to a **folder with an entry doc named exactly `capabilities.md`** only when siblings are required — state-variant files (A.6), sidecars (A.10), or sub-capabilities. The flat file is *renamed into* the folder on promotion; a flat file and a same-named folder are a collision (`check` flags it).

(Abstractly: a node in a tree carrying a body + named fields + named attachments — the same shape as a taxonomy term, see A.5.)

### A.4 Statuses, lifecycle, priority

Capability files describe **intended state**, exhaustively, with a **locked five-status set**:

- **`Supported`** — works today (default for anything implemented).
- **`Partial`** — supported with explicitly enumerated gaps; a `**Gaps:**` field lists what doesn't work (enumerable so a closed gap is a visible diff).
- **`Missing`** — desired, not built; the backlog signal (grep `**Status:** Missing`). Body names what unblocks it.
- **`Blocked`** — desired but cannot start on a specific external dependency; a `**Blocked by:**` field names it concretely. (Distinguished from `Missing` by *active* blockage.)
- **`Omitted`** — deliberately not supported; body gives the rationale and where the alternative lives.

Two orthogonal axes layer on top, both optional:

- **`Lifecycle`** (`Supported`/`Partial` only): `Experimental | Stable | Deprecated`. `Deprecated` carries `**Superseded by:** <ref>` when a successor exists.
- **`Priority`**: `P0 | P1 | P2 | P3`. Most useful on `Missing`/`Blocked`/`Partial` (how the backlog sorts).

The status vocabulary is **locked**: additions need a spec bump + explicit rationale. In particular **no `Broken`** (a broken `Supported` capability is a *bug* — a work item — not a status; intent is unchanged) and **no `In progress`** (that is the work item; a `Missing` capability whose `Planning doc:` points at an active item conveys it). This resists the universal "3 statuses become 17" inflation.

**The full metadata field set** (the locked vocabulary `check` validates):

| Field | Required? | Applies to | Format |
|---|---|---|---|
| `**Status:**` | Yes | All | `Supported`/`Partial`/`Missing`/`Blocked`/`Omitted` |
| `**Priority:**` | No | All | `P0`/`P1`/`P2`/`P3` |
| `**Lifecycle:**` | No | `Supported`/`Partial` | `Experimental`/`Stable`/`Deprecated` |
| `**Superseded by:**` | When `Deprecated` + successor | `Deprecated` | a cross-ref identifier (A.6) |
| `**Tracker:**` | No | All | comma-separated `<shortname>:<id>` |
| `**Subject:**` | No | All | a taxonomy term ref (A.7) |
| `**Roles:**` | No | All | comma-separated `roles/` slugs (OR-ed) |
| `**When:**` | No | All | comma-separated `conditions/` slugs (AND-ed; `!` negates) |
| `**Gaps:**` | When `Partial` | `Partial` | list of known holes |
| `**Blocked by:**` | When `Blocked` | `Blocked` | concrete dependency |

Unrecognized field names are `check` violations. The tool *reads* these fields (filter, resolve, validate) but does not enforce status business-semantics — that is judgment, left to skills and reviewers (A.12).

### A.5 Storage abstraction

Per the framework prime directive, the model is abstract and the filesystem is the default realization. A **`CapabilitiesStore`** interface — `list · get(id) · add(capability, namespace) · remove(id) · search · check` — is what the CLI depends on; `FsCapabilitiesStore` realizes it as the `docs/capabilities/` tree (Part B). A tree of named nodes (files/folders) with bodies, named fields, and cross-links is implementable by any backend (a graph DB, a wiki, a docs service), so the model passes the litmus test; remote backends are additive.

The interface is **deliberately near-identical to `TaxonomyStore`** — both are bounded trees of body + named-fields + named-attachments nodes. This is the basis for extracting a shared tree-store core once all three components are real (Part C; do not pre-abstract).

### A.6 Cross-references

A capability references another by an **identifier**, resolved through the store relative to `docs/capabilities/` — never a raw filesystem path (litmus test):

```
<namespace>/<path>[state][#heading-slug]
```

- **`<namespace>/<path>`** resolves to a flat file (`components/footer` → `components/footer.md`) or a folder's entry doc (`api/auth/login` → `api/auth/login/capabilities.md`). Flat-file lookup first, then folder-with-`capabilities.md`; both existing is a collision.
- **`[state]`** picks a state-variant sibling: `[icon]` → `with-icon.md`, `[!icon]` → `without-icon.md`, `[*]` → all variants. State variants exist only for promoted folders; the entry doc holds capabilities common to all states. The `with-`/`without-` convention is overridable per-node in config.
- **`#heading-slug`** is the GitHub-flavored slug of a `## Capability` heading. Same-file refs may use the anchor alone (`#sign-in-with-google`); cross-file refs use the full identifier. Sidecars are referenced by naming the sidecar file (`api/auth/login/errors#401-invalid-credentials`).

**Same-repo only.** A capability never references a path in another repo — see A.9. The `.md` extension and whitespace never appear in an identifier.

### A.7 The taxonomy seam (loose)

A capability optionally declares a **`Subject:`** = a taxonomy term ref (A.4). This is the **capability→term** pointer: "this behavior is *about* the `argument` noun." It is one-directional (a term never lists its capabilities — the noun stays behavior-agnostic), resolved-but-never-required, and validated by `check` against the `TaxonomyStore` (the one piece of genuine cross-component wiring — the taxonomy spec's A.7 capabilities seam, from the capabilities side). One **single** primary subject per capability (resolved per taxonomy spec B.6); secondary nouns live in the body.

### A.8 The work seam (loose)

The work↔capability binding is **defined in the work spec (A.7)** and only referenced here — neither component duplicates the other:

- **Forward (capability→work):** a `Missing` capability's `Planning doc:` pointer holds the realizing work item's **stable ID** (slug), resolved through the work store's `resolve`.
- **Back (work→capability):** the work item's `capabilities.yaml` lists the capability files it touches and their intended status transitions, as identifiers into this tree.
- **The lifecycle handshake:** `new` (declares a product delta → records `Missing` with `Planning doc:`) → `active` (contradiction-detection) → `complete` (the DoD "capabilities reconciled" gate applies the delta: `Missing → Supported`, scope edits, `Supported → Omitted`).

The binding is a **pointer, not a transaction** — atomic under the filesystem adapter (one commit), best-effort when the work store is remote. The capability ledger is always filesystem-resident, independent of the `WorkStore`. `tcw capabilities` reads these *pointers*, never work prose.

### A.9 Why capabilities share differently from taxonomy

The two components share across repos by **opposite** mechanisms, deliberately (the contrast stated from taxonomy's side in its A.6):

- **Capabilities forbid cross-repo references** and relay canonical wording through an **orchestrator** — because implementations *diverge* per platform (web and mobile realize the "same" capability differently); a direct link would couple implementations.
- **Taxonomy federates directly** (`extends`) because vocabulary is canonical-shared.

Capabilities are therefore **two-layered**, and the two layers map onto TCW's node recursion:

- **Per-node (leaf) layer** — each node's own `docs/capabilities/`, describing what *that* codebase lets a user do.
- **Product layer** — an orchestrator node's `docs/capabilities/` describing what *the product* lets a user do, platform-agnostic. A per-node agent does not read the orchestrator's tree; it asks the orchestrator for canonical wording over the inbox channel (the **product-layer coordination protocol**), and falls back to in-repo evidence + a `TODO: confirm wording` marker when coordination is unavailable.

The recursion maps cleanly: an **epic** completing flips the **product-layer** entry; a **task** completing flips the **leaf** entry. (Cross-node mechanics land with work Spec 2; this component only needs each node to own a `docs/capabilities/` tree.)

### A.10 Sidecars

Enumerable data that is *referenced from* capabilities lives in a **sidecar** beside the capability folder's `capabilities.md`, same document format. Two bounded types, both subject to the two-test rule (entries are *enumerable* **and** *referenced from* other capabilities):

- **`errors.md`** — `## <code>: <name>` per failure mode (most commonly an API endpoint).
- **`states.md`** — `## <state-name>` per UI/state-machine state.

More types (`events.md`, `metrics.md`, …) wait for concrete pull from a real project — prose first, sidecar only when both tests pass.

### A.11 Globals: roles and conditions

`roles/` and `conditions/` are first-class top-level namespaces. A capability's `**Roles:**` and `**When:**` fields reference their slugs (`roles/admin`, `conditions/authed`). `check` resolves them like any other reference. Complex policies stay in prose — the fields are flat OR/AND lists, not a boolean expression language (YAGNI).

### A.12 Design principles (shared with the framework)

- Plain markdown/YAML in git; the CLI is a safe accessor, not a gatekeeper; the store is the database.
- No daemon, no database, no server, no web UI.
- **Mechanism vs. judgment:** the tool owns structure, identity (path/identifier), reference resolution, field-vocabulary validation (`check`); humans/skills write capability *content* (names, bodies, statuses) and make the status *judgments*.
- **Abstract spine, filesystem leverage** + the litmus test. Recursion: each node owns its `docs/capabilities/`; cross-node sharing is **orchestrator-relay, not `extends`** (A.9).

---

## Part B — Core tool (`tcw capabilities`, buildable now)

### B.1 Scope

The `tcw capabilities` subcommand group: the `CapabilitiesStore` interface + the `FsCapabilitiesStore` adapter over `docs/capabilities/` in the current node. Single tree. **A safe accessor + validator** — the tool surfaces and structurally validates capabilities; it does **not** parse capability prose, enforce status business-semantics, or drive the lifecycle handshake (that is the work component + the skill layer). Out of scope: product-layer coordination (a skill-layer concern, the analog of work's deferred worktrees); tracker *sync* (deferred, Part C). Python, mirroring `tcw taxonomy` (argparse + PyYAML + `git` via subprocess); pytest with `tmp_path`.

### B.2 Command surface

```
tcw capabilities list [--status S] [--namespace N]   list capabilities as a tree, flagged by status
tcw capabilities show <id>                            read a capability (file, or a #heading)
tcw capabilities add <namespace/path> [name]          scaffold a file/heading  ·  -s/--status <S>
tcw capabilities search <query>                        search names + bodies
tcw capabilities check                                 validate identifiers, subject refs, metadata
```

### B.3 On-disk layout (`FsCapabilitiesStore`)

```
docs/capabilities/
  .config.yaml                 # trackers, namespace docs, state-convention overrides (optional)
  routes/
    login.md                   # simple capability → flat file
  api/
    auth/
      login/                   # has a sidecar → folder
        capabilities.md
        errors.md
  components/
    complex-styled-button/     # has state variants → folder
      capabilities.md
      with-icon.md
      without-icon.md
      states.md
  roles/admin.md
  conditions/authed.md
```

Reserved filenames: **`.config.yaml`** (root only), **`capabilities.md`** (a folder's entry doc), **`errors.md`** / **`states.md`** (sidecars). A capability's identity is its path/identifier relative to `docs/capabilities/`.

### B.4 File formats

- **`.config.yaml`** (root, optional) — `trackers: { shortname: url-template }`; optional `namespaces:` documentation; optional `state-conventions:` override of the `with-`/`without-` default. Project-shaped details only — it never redefines the locked status/field/grammar vocabulary.
- **Capability files** — `# <Subject> — capabilities`; `## <name>` + inline metadata block (A.4) + 1–3¶ body. No YAML frontmatter (inline per-capability metadata is sufficient).
- **Sidecars** — same skeleton, reserved names (A.10).

### B.5 Command behavior

- **`add`** — resolve the namespace/path; create the flat file (or, with a sidecar/variant flag, the folder + `capabilities.md`) seeded with the `# <Subject>` heading and one `## <name>` + `**Status:**` (default `Missing`) scaffold + piped stdin body. Refuse if the path already exists, or if adding a flat file would collide with an existing folder (and vice versa).
- **`list`** — walk the tree; print the namespace forest with each capability's status. `--status`/`--namespace` filter.
- **`show` / bare `<id>`** — resolve the identifier (A.6); print the metadata block + the head of the body (or the whole file for a bare file id).
- **`search`** — substring/keyword over capability names + bodies; report each hit by identifier.
- **`check`** — validate, exit non-zero on any problem:
  - every cross-reference identifier (A.6) resolves (no dangling, no flat/folder collision, valid `[state]`);
  - every `**Subject:**` ref resolves unambiguously against the **`TaxonomyStore`** (the cross-component seam — A.7);
  - every metadata field is in the locked vocabulary, and required-when fields are present (`Gaps` on `Partial`, `Blocked by` on `Blocked`, `Superseded by` on `Deprecated`-with-successor);
  - every `**Roles:**`/`**When:**` slug resolves under `roles/`/`conditions/`.

### B.6 Git behavior and node detection

- Operations `git add` / `git rm` and **stage** by default; `--commit` opts into a `tcw capabilities: …` commit. (Same stage-only default as `tcw taxonomy` / `tcw work`.)
- **Node detection:** walk up from cwd to the nearest git work-tree containing `docs/capabilities/`; operate there. None found → suggest `tcw init` (the unified scaffolder — taxonomy spec B.9 resolution).

### B.7 Testing

pytest over `tmp_path` git repos: `add` flat-file and promoted-folder; the flat/folder collision refusal; `list`/`search`/`show` over a small tree; identifier resolution across the three forms (flat, folder-entry, `[state]`, `#heading`); and `check` catching each failure class — a dangling identifier, a bad `Subject:` ref (against a stub taxonomy), an unknown field, a missing required-when field, an unresolved role/condition slug, and a flat/folder collision.

### B.8 Open questions

- `Subject:` cardinality if a future consumer genuinely needs multiple primary terms (single for now — A.7).
- Whether `check` should warn on a `Missing` capability whose `Planning doc:` slug no longer resolves (a dangling forward pointer) — or leave that to the work component. (Lean: warn only, the work component owns reconciliation.)
- Whether the recommended namespace set should ship as a seed in `tcw init` or stay purely illustrative.

---

## Part C — Place in the roadmap

Global build order: [`INDEX.md`](INDEX.md). Capabilities-local notes:

1. **This phase** — the capabilities component (`tcw capabilities`) + `FsCapabilitiesStore`, single bounded tree, `Subject`↔taxonomy validation in `check`.
2. **Shared tree-store core** — extracted in [`phase-4-shared-core`](phase-4-shared-core.md) from taxonomy + capabilities (the two near-clone trees), *before* work is built: the common bounded-tree primitive (body + named fields + named attachments + identifier resolution) they share. Don't pre-abstract — two real implementations justify it.
3. **Skill + product-layer coordination** — the orchestrator-relay protocol (A.9), the lifecycle-handshake driving (work "Spec 3"), and the `## Capability changes` planning gate as a skill (the process half, now structural in the work lifecycle) — deferred to [`phase-6-beyond`](phase-6-beyond.md).
4. **Tracker sync** — per-tracker adapters (Jira/GitHub/Linear) layered on the `**Tracker:**` shortname convention without changing the format — deferred to [`phase-6-beyond`](phase-6-beyond.md).
