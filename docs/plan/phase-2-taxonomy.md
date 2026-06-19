# Phase 2 — Taxonomy (TCW component 1 of 3: the nouns)

**Status:** spec ✓ · build ✓ (see *Build notes*, Part C)
**Delivers:** `tcw taxonomy` + `FsTaxonomyStore`, local-path `extends`.
**Depends on:** Phase 1 (package + CLI skeleton + node detection).
**Build checklist:** `TaxonomyStore` interface → `FsTaxonomyStore` over `docs/taxonomy/` → the six subcommands (B.2) → `extends` resolution (B.6) → `check` → tests (B.8).

> Spec **and** build plan for component 1. Part A is the model; Part B is the buildable tool; B.9 records the resolved open questions. Framework-wide rules: [`../../AGENTS.md`](../../AGENTS.md).
**Date:** 2026-06-18
**Scope:** the conceptual model (Part A) plus the buildable `tcw taxonomy` tool (Part B). Sibling components: [`phase-5-work`](phase-5-work.md), [`phase-3-capabilities`](phase-3-capabilities.md).

---

## Part A — The model

### A.1 Place in TCW

The system has three components, defined in dependency order — the `tcw` binary's three subcommand groups:

1. **`tcw taxonomy`** — the *things* an application deals with (domain entities/concepts). The **nouns**.
2. **`tcw capabilities`** — what a user can do with them, each a miniature user story. The **user stories**.
3. **`tcw work`** — the changes to those capabilities and to the machinery (and to the project itself). The **changes**.

Taxonomy comes first because the other two reference it: a capability describes the behavior of *something*, and a work item changes *something* — that something is a taxonomy term. Today that subject is only ever *inferred* from prose and surrounding language; taxonomy makes it an explicit, addressable registry + glossary. (`tcw` = taxonomy, capabilities, work.)

This spec covers the taxonomy component; `tcw capabilities` ([phase-3](phase-3-capabilities.md)) and `tcw work` ([phase-5](phase-5-work.md)) are the other two component specs.

### A.2 Terms form a forest

A **term** is a domain entity or concept. Terms are **hierarchical**: a term may contain child terms (sub-concepts, or the same word in a narrower context). The same leaf name can recur under different parents — `admin/permission` and `some-object/permission` are *different terms*.

- A term's **identity is its path** — the chain of ancestor local-names from the taxonomy root. The slug *is* that path (`admin/permission`).
- Leaf names are unique only **among siblings**; the path disambiguates globally. (Contrast the work-sdlc's node-unique slugs — taxonomy needs no "resolve anywhere / error on duplicate" rule, because the path *is* the address.)
- **Addressing is by path.** A bare leaf (`permission`) is convenience sugar, valid only when unambiguous.

### A.3 Term anatomy

Each term carries:

- **name** — display form ("Admin Permission").
- **slug / path** — its identity (`admin/permission`).
- **description** — long-form prose (what the thing *is*).
- **metadata** — small fields, including **`relatesTo`**: cross-links to other terms that pertain to this one in a non-obvious way (across the hierarchy).
- **attachments** — optional supplementary docs/images.
- **children** — sub-terms.

(Abstractly: a node in a tree with name · description · metadata · attachments · children.)

### A.4 Storage abstraction

Per the framework prime directive (the litmus test in the system guide), the model is defined abstractly and the filesystem is the *default realization*. A **`TaxonomyStore`** interface — `list · get(path) · add(term, parent) · remove(path) · search · check` — is what the CLI depends on; `FsTaxonomyStore` realizes it as nested directories under `docs/taxonomy/` (Part B). A tree of named nodes with cross-links is implementable by any backend (a graph DB, a wiki, a glossary service), so the model passes the litmus test; remote backends are additive.

### A.5 Federation via `extends`

Taxonomies **compose**: one can extend others to import shared vocabulary.

- The taxonomy-root config (`config.yaml`) declares `extends: { <alias>: <repo-root-path> }`. The **consumer chooses each alias**; the path points at another **repo root** (the tool looks for `docs/taxonomy/` inside it).
- Each alias is a **named namespace**; the local taxonomy is the default, unprefixed namespace. Multiple `extends` entries → multiple namespaces, so a project can import several shared taxonomies cleanly.
- **No silent merge.** A local `Some/Term` and an imported `shared/Some/Term` are *distinct terms in distinct namespaces*, never merged or overwritten. Conflicts can only arise in a *consumer* (a shared repo is self-contained); the namespace keeps them apart, so the author disambiguates by qualifying with the alias.
- **Source types: local path first.** A sibling-repo path (`../shared-docs-repo`) covers a co-checked-out workspace entirely. Remote sources (git/URL) — which need fetch, cache, and **version-pinning** so the vocabulary doesn't shift underneath you — are a documented future source type. Abstractly `extends` is a list of upstream source refs; each adapter resolves them its own way.

### A.6 Why taxonomy shares differently from capabilities

The two components share across repos by *opposite* mechanisms, deliberately:

- **Capabilities forbid cross-repo references** and relay canonical wording through the orchestrator — because implementations *diverge* per platform (web vs mobile realize the "same" capability differently); direct links would couple implementations.
- **Taxonomy wants one canonical definition imported everywhere** — "Argument" must mean the same thing in every repo. So direct federation (`extends`) is correct, and it *supersedes* any orchestrator-relay model for taxonomy.

Vocabulary is canonical-shared; behavior is locally-divergent. Same framework, opposite sharing models, for principled reasons.

### A.7 The capabilities seam (loose)

Taxonomy is the **root noun** the other two hang off, by loose one-directional pointers:

- A **capability** optionally declares a **`subject`** = a taxonomy term (by ref). A work item may likewise reference the terms it touches.
- The pointer is capability→term (and work→term), never the reverse: a term stays behavior-agnostic — it doesn't list its capabilities — so the noun is independent of what's done with it. The tool can *resolve* a subject ref but never *requires* one — the same loose-coupling style as work↔capabilities.

### A.8 Design principles (shared with the framework)

- Plain markdown/YAML in git; the CLI is a safe accessor, not a gatekeeper; the store is the database.
- No daemon, no database, no server, no web UI.
- **Mechanism vs. judgment:** the tool owns structure, identity (path), reference resolution, federation, and validation (`check`); humans/skills write term *content* (names, descriptions, relationships).
- **Abstract spine, filesystem leverage** + the litmus test (the framework guide). Recursion: each node has its own `docs/taxonomy/`; cross-node sharing is `extends`, not nesting.

---

## Part B — Core tool (`tcw taxonomy`, buildable now)

### B.1 Scope

The `tcw taxonomy` subcommand group: the `TaxonomyStore` interface + the `FsTaxonomyStore` adapter over `docs/taxonomy/` in the current node. Single taxonomy + **local-path** `extends`. Out of scope: remote source types; capabilities/work integration beyond storing and resolving `subject` refs. Python, mirroring the `tcw work` core (argparse + PyYAML + `git` via subprocess); pytest with `tmp_path`.

### B.2 Command surface

```
tcw taxonomy list [--local]            list terms as a tree, each flagged by origin (local | <alias>)
tcw taxonomy add <name> [description]  create a term  ·  -s/--slug <path>   -p/--parent <path>
tcw taxonomy show <path>               read a term (also the default: `tcw taxonomy <path>`)
tcw taxonomy rm <path>                 remove a local term (refuses on an inherited one)
tcw taxonomy search <query>            search names + descriptions (incl. inherited)
tcw taxonomy check                     validate aliases + every reference
```

### B.3 On-disk layout (`FsTaxonomyStore`)

```
docs/taxonomy/
  config.yaml                  # root config: extends: { <alias>: <repo-root-path> }, + settings
  <term>/
    meta.yaml                  # name, relatesTo: [refs], small fields
    description.md             # long-form prose
    *.{md,png,txt,…}           # attachments
    <child-term>/
      meta.yaml
      …
```

Reserved filenames: **`config.yaml`** (root only), **`meta.yaml`**, **`description.md`**. Any other file in a term dir is an attachment. A term's slug is its directory path relative to `docs/taxonomy/`.

### B.4 File formats

- **`config.yaml`** (root) — `extends: { alias: repo-root-path }`; reserved for taxonomy-wide settings. A distinct name from per-term `meta.yaml`, so the root config is never confused with a term.
- **`meta.yaml`** (per term) — `name` (display); `relatesTo` (list of term refs); optional small fields.
- **`description.md`** — the term's prose body.

### B.5 Command behavior

- **`add`** — resolve the parent path (`-p`, default root); slug = `-s` or the slugified name, appended to the parent path; create the term dir with `meta.yaml` (seeded `name`) and `description.md` (seeded from the `description` arg or piped stdin). Refuse if the path already exists locally.
- **`list`** — walk the local tree and the resolved `extends` taxonomies; print the forest with each term's origin (local or `<alias>`). `--local` restricts to local terms.
- **`show` / bare `<path>`** — resolve the ref (B.6); print `meta.yaml` + the head of `description.md`.
- **`rm`** — remove a **local** term dir (stage the deletion). Refuse on an inherited term (edit it at its source). Warn if other local terms `relatesTo` it.
- **`search`** — substring/keyword over names + description prose, across local + inherited; report each hit by its qualified path.
- **`check`** — validate: every `extends` path exists and contains `docs/taxonomy/`; no alias cycles; no duplicate aliases; no alias collides with a local top-level term; every `relatesTo` and capability `subject` ref resolves unambiguously (no dangling, no ambiguous-bare). Report problems; exit non-zero on any.

### B.6 Reference resolution

A reference is `[<alias>/]<path>`. Resolution:

1. **Prefixed** (`shared/Some/Term`) → that aliased taxonomy's term. Unambiguous by construction.
2. **Bare** (`Some/Term`):
   - local defines it → **the local term** (bare always means local when local has it);
   - else exactly one extended taxonomy defines it → that one (normalized to `<alias>/Some/Term`);
   - else (none, or two-or-more) → **ambiguous**; the author must qualify. `check` flags it.

References *inside an imported term* (its `relatesTo`, its prose) resolve in **that term's authoring namespace** — so a shared repo's internal cross-refs keep working when imported, and a consumer needn't re-declare the shared repo's own upstreams.

### B.7 Git behavior and node detection

- Operations `git add` / `git rm` and **stage** by default; `--commit` opts into a `tcw taxonomy: …` commit. (Same stage-only default as `tcw work`.)
- **Node detection:** walk up from cwd to the nearest git work-tree containing `docs/taxonomy/`; operate there. None found → suggest `tcw taxonomy init` (or the umbrella `tcw init`).

### B.8 Testing

pytest over `tmp_path` git repos: term add + nesting + slug=path identity; `rm` refuses inherited; `list`/`show` resolve a local-path `extends` and flag origin; the three resolution branches (local-wins-bare, unique-extended, ambiguous-error); `check` catches a cycle, a duplicate alias, an alias/local-top-level collision, a dangling ref, and an ambiguous-bare ref.

### B.9 Resolved decisions

- **`relatesTo`** — **freeform list of refs** now. Typed relations (`is-a`, `part-of`) are deferred until a consumer needs them (YAGNI; the tool reads pointers, humans write meaning).
- **`add` description input** — **inline arg + piped stdin**; no `$EDITOR` (avoids TTY handling; mirrors `tcw work new`).
- **Capability `subject`** — **single** primary term per capability; secondary nouns live in the capability body. (Mirrored in the capabilities spec A.7.)
- **`init`** — **a unified `tcw init`** (not `tcw taxonomy init`) scaffolds whichever component trees you name, defaulting to all three. Lives in **Phase 1** (`phase-1-scaffold.md`).
- **Source-relative resolution transitivity (B.6)** — **deferred to remote `extends`** (Phase 6). The authoring-namespace rule stands as stated; the deep rebasing edge cases are pinned down when git/URL sources land.

---

## Build notes (Phase 2)

Built: `TaxonomyStore` ABC + `Term` (`tcw/store/base.py`); `FsTaxonomyStore` over `docs/taxonomy/` (`tcw/store/fs.py`); the six subcommands + bare-path `show` sugar (`tcw/taxonomy/cli.py`); 16 tests (`tests/test_taxonomy.py`) covering add/nesting/slug-identity, inherited-rm refusal, origin-flagged `list`, the three resolution branches, and every `check` failure class (cycle, duplicate alias, alias/local collision, dangling + ambiguous `relatesTo`, missing path). `tcw taxonomy check` is green on a clean tree.

Shared FS helpers added to `fs.py` (`find_node`, `load_yaml`/`dump_yaml`, `git_stage`/`git_rm`, `slugify`) are the Phase-4 shared-core candidates — left in `fs.py` for now (don't pre-abstract).

**Deliberate simplifications (recorded so they don't read as bugs):**
- **Bare-*leaf*-anywhere sugar not implemented.** Addressing is by path; `get("permission")` resolves a top-level term, not a deep `admin/permission`. The path *is* the address (A.2); B.6's three namespace-resolution branches (local-wins / unique-extended / ambiguous) are fully implemented.
- **Prefixed-ref + `list` go one `extends` level deep.** Deep transitive federation (an alias's own `extends`) is the deferred remote-`extends` transitivity (B.9 / Phase 6); local-path single-level works.

## Part C — Place in the roadmap

Taxonomy-local notes:

- **Done since first draft:** the framework reframe (`WORK-SDLC.AGENTS.md` → this repo's [`../../AGENTS.md`](../../AGENTS.md); `work` → `tcw work`; the `tcw` umbrella) and the capabilities component spec ([`phase-3-capabilities`](phase-3-capabilities.md)) — both shipped.
- **Shared tree-store core** — extracted in [`phase-4-shared-core`](phase-4-shared-core.md), once taxonomy + work both exist (don't pre-abstract).
- **Remote `extends`** (git/URL sources with version-pinning) — deferred to [`phase-6-beyond`](phase-6-beyond.md).
