# Phase 4 — Shared tree-store core

**Status:** ☐ blocked on Phases 2 + 3
**Delivers:** the common bounded-tree store primitive extracted from `FsTaxonomyStore` and `FsWorkStore`, ready for `FsCapabilitiesStore` (Phase 5) to reuse.
**Depends on:** Phase 2 (taxonomy) **and** Phase 3 (work) must both be real first.

## Why this phase exists — and why *here*

`AGENTS.md` is explicit: *"extract the shared tree-store core only once two components are real (don't pre-abstract)."* Phases 2 and 3 deliberately ship their own `FsTaxonomyStore` / `FsWorkStore` with whatever each needs. This phase is where the duplication, now visible in real code, gets factored into one primitive — **after** two implementations exist to generalize from, **before** the third (capabilities) is written so it can reuse rather than re-duplicate.

This is a **refactor phase**, not a feature phase. No new `tcw` surface area; the CLI behaves identically before and after.

## What is genuinely shared (the candidate core)

The three components are structurally isomorphic — each is a **bounded tree of nodes**, where a node carries a **body + named fields + named attachments**, addressed by a **path/identifier resolved through the store**. The likely shared primitives:

- **Node model** — body + named fields (YAML) + named attachments, with reserved filenames bounding the namespace.
- **Path/identifier resolution** — `get(id)` / `resolve(id)` over a bounded tree (taxonomy's `admin/permission`, capabilities' `routes/login`, work's slug).
- **Tree walk + listing** — enumerate the bounded tree (never glob an open namespace — the prime directive).
- **Git plumbing** — `git add`/`git rm`/`git mv`, stage-by-default, optional `--commit` with a `tcw <component>: …` message.
- **Node detection** — walk up to the nearest git work-tree containing `docs/<component>/`, bounded to that node.

## What stays component-specific (do NOT pull into the core)

- Work's **status state machine** + legal-transition graph (taxonomy/capabilities have no transitions).
- Taxonomy's **`extends` federation**; capabilities' **orchestrator-relay** + identifier `[state]`/`#heading` grammar.
- Capabilities' **`Subject`↔taxonomy** cross-component check.

Run each candidate through the litmus test before promoting it. When unsure, leave it in the component — a wrong abstraction is more expensive than a little duplication.

## Done when

`FsTaxonomyStore` and `FsWorkStore` are re-expressed on the shared core with **no behavior change** (their existing test suites still pass green), and the core exposes exactly what Phase 5 needs — no speculative surface added "for later."
