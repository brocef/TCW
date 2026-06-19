# TCW — implementation plan (INDEX)

The big-picture spine for building **TCW** (**T**axonomy · **C**apabilities · **W**ork): a storage-abstracted framework for describing and evolving a software project along three axes, exposed through one CLI, `tcw`, with three subcommand groups (`tcw taxonomy | capabilities | work`) over a shared store core.

- **The rules (how to work):** [`../../AGENTS.md`](../../AGENTS.md) — the prime directive (the abstraction litmus test) governs every change. Read it first.
- **The why (how we got here):** [`../DESIGN-HISTORY.md`](../DESIGN-HISTORY.md) — the decision log behind the design.
- **The what + when (this folder):** one file per build phase, below. Each phase doc is the **single source of truth** for its component — design *and* build steps together.

## The three components

| # | Component | Is | What it is |
|---|---|---|---|
| 1 | **Taxonomy** | the nouns | the *things* an app deals with (domain entities) |
| 2 | **Capabilities** | the user stories | what a user can do with them — each a miniature user story |
| 3 | **Work** | the changes | edits to capabilities (product), machinery (technical), or the project itself (meta) |

They link by **loose, one-directional pointers** (capability→term, work→capability/term) and never duplicate each other. Capabilities are the user-facing surface; **work is the change layer that edits capabilities and machinery over time** — not a peer "verb."

## Build order = dependency order

The components are **numbered 1/2/3 by dependency** — capabilities reference taxonomy, and work references both — and they are **built in that same order**, so nothing is ever built against a stub:

- **Taxonomy** first — it depends on nothing; the other two point at its terms.
- **Capabilities** second — it depends only on taxonomy (its `check` validates `Subject:` refs against the `TaxonomyStore`).
- **Work** last of the three — it references both taxonomy and capabilities.

Two non-component phases bracket the work: **scaffold** (Phase 1) lays down the package + CLI + store base, and the **shared tree-store core** (Phase 4) is extracted *after* taxonomy and capabilities — the two near-clone trees — so work can build on it.

So the build order is **scaffold → taxonomy → capabilities → shared core → work → beyond**, the phase numbering below.

## Phases & status

| Phase | Doc | Delivers | Status |
|---|---|---|---|
| 1 | [phase-1-scaffold](phase-1-scaffold.md) | `pyproject`, package layout, abstract store base, `tcw` CLI + `tcw init` | ✓ built |
| 2 | [phase-2-taxonomy](phase-2-taxonomy.md) | `tcw taxonomy` + `FsTaxonomyStore`, local-path `extends` | spec ✓ · build ✓ |
| 3 | [phase-3-capabilities](phase-3-capabilities.md) | `tcw capabilities` + `FsCapabilitiesStore`, `Subject`↔taxonomy `check` | spec ✓ · build ✓ |
| 4 | [phase-4-shared-core](phase-4-shared-core.md) | extract the common bounded-tree store primitive | ✓ built |
| 5 | [phase-5-work](phase-5-work.md) | `tcw work` + `FsWorkStore`, single-node state machine + DoD gate | spec ✓ · build ☐ |
| 6 | [phase-6-beyond](phase-6-beyond.md) | cross-node recursion, skill layer, remote adapters, tracker sync | ☐ deferred |

**Where we are now:** planning is **complete** — all three component specs are written and their open questions resolved (see each phase's "Resolved decisions"). **Phase 1 (scaffold) is built**: `tcw` installs, `tcw init` scaffolds the three component trees, `pytest` is green. **Next action: Phase 2 (taxonomy).**

> Tracking is a plain markdown table on purpose. Once `tcw work` (Phase 5) exists, TCW can dogfood its own `docs/work/` for tracking — but we do not build `tcw work` just to track building `tcw work`.

## Conventions decided for this repo

- **Distribution:** `pipx install` via the `tcw` console entry point (native Python packaging; no symlink hack — `tcw` is a real package). Detail in [phase-1](phase-1-scaffold.md).
- **Docs/release convention:** a single `CHANGELOG.md`; adopt a richer release-notes split only when there is something to release. Dogfood `docs/work/` for work tracking once Phase 3 lands.
- **Testing:** Python + type hints; pytest over `tmp_path` git repos (the pattern every phase uses).
