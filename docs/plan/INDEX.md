# TCW — implementation plan (INDEX)

The big-picture spine for building **TCW** (**T**axonomy · **C**apabilities · **W**ork): a storage-abstracted framework for describing and evolving a software project along three axes, exposed through one CLI, `tcw`, with three subcommand groups (`tcw taxonomy | capabilities | work`) over a shared store core.

- **The rules (how to work):** [`../../AGENTS.md`](../../AGENTS.md) — the prime directive (the abstraction litmus test) governs every change. Read it first.
- **The why (how we got here):** [`../DESIGN-HISTORY.md`](../DESIGN-HISTORY.md) — the decision log behind the design.
- **The what + when (this folder):** one file per build phase, below. Each phase doc is the **single source of truth** for its component — design *and* build steps together.

## The three components

| # | Component | Axis | What it is |
|---|---|---|---|
| 1 | **Taxonomy** | nouns | the *things* an app deals with (domain entities) |
| 2 | **Capabilities** | behaviors | what those things can do / their states |
| 3 | **Work** | verbs | how they change over time |

They link by **loose, one-directional pointers** (capability→term, work→capability/term) and never duplicate each other.

## Definition order ≠ build order (the thing that was confusing)

The components are **numbered 1/2/3 by *definition dependency*** — capabilities reference taxonomy, and work references both, so taxonomy must be *defined* first.

But they are **built in a different order**, for practical reasons:

- **Taxonomy is built before Work** — it is the simplest fully-specced tree, and Work points at its terms.
- **Capabilities is built last** — it hard-depends on Taxonomy (its `check` validates `Subject:` refs against the `TaxonomyStore`), and it is a near-clone of Taxonomy, so we build it *after* extracting the shared tree-store core (Phase 4), which only makes sense once two components already exist.

So the build order is **scaffold → taxonomy → work → shared core → capabilities → beyond**, which is the phase numbering below.

## Phases & status

| Phase | Doc | Delivers | Status |
|---|---|---|---|
| 1 | [phase-1-scaffold](phase-1-scaffold.md) | `pyproject`, package layout, abstract store base, `tcw` CLI + `tcw init` | ☐ not started |
| 2 | [phase-2-taxonomy](phase-2-taxonomy.md) | `tcw taxonomy` + `FsTaxonomyStore`, local-path `extends` | spec ✓ · build ☐ |
| 3 | [phase-3-work](phase-3-work.md) | `tcw work` + `FsWorkStore`, single-node state machine + DoD gate | spec ✓ · build ☐ |
| 4 | [phase-4-shared-core](phase-4-shared-core.md) | extract the common bounded-tree store primitive | ☐ blocked on 2 + 3 |
| 5 | [phase-5-capabilities](phase-5-capabilities.md) | `tcw capabilities` + `FsCapabilitiesStore`, `Subject`↔taxonomy `check` | spec ✓ · build ☐ |
| 6 | [phase-6-beyond](phase-6-beyond.md) | cross-node recursion, skill layer, remote adapters, tracker sync | ☐ deferred |

**Where we are now:** planning is **complete** — all three component specs are written and their open questions resolved (see each phase's "Resolved decisions"). Nothing is built yet. **Next action: Phase 1.**

> Tracking is a plain markdown table on purpose. Once `tcw work` (Phase 3) exists, TCW can dogfood its own `docs/work/` for tracking — but we do not build `tcw work` just to track building `tcw work`.

## Conventions decided for this repo

- **Distribution:** `pipx install` via the `tcw` console entry point (native Python packaging; no symlink hack — `tcw` is a real package). Detail in [phase-1](phase-1-scaffold.md).
- **Docs/release convention:** a single `CHANGELOG.md`; adopt a richer release-notes split only when there is something to release. Dogfood `docs/work/` for work tracking once Phase 3 lands.
- **Testing:** Python + type hints; pytest over `tmp_path` git repos (the pattern every phase uses).
