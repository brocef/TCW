# Phase 6 — Beyond (deferred)

**Status:** ☐ deferred — not scheduled; recorded so the path is on file.
**Depends on:** the three components (Phases 2, 3, 5) shipped and dogfooded.

Everything the three component specs mark "later." Nothing here is built until the single-node core is real and in use. Grouped by source; each item links back to the spec section that defines it.

## Cross-node / recursion (work "Spec 2")

Node discovery; epics + `initiative:` back-pointers; `reconcile` (scan child nodes → consolidated rollup); escalate/delegate over the inbox channel; `tcw work start --worktree` + the rule for which checkout owns `docs/work/` writes; the two-layer × two-layer capability mapping (epic ↔ product-layer ledger, task ↔ leaf-node ledger). *(phase-5-work A.2, A.6, A.8; Part C #2.)*

## Skill layer + capabilities process (work "Spec 3")

The `tcw work` driving skill — recursive process-inbox, resume, decompose, three-axis / product-first planning, the lifecycle handshake; the capabilities **process** half (the `## Capability changes` planning gate, contradiction-detection) and the **product-layer coordination** protocol as skills. The capabilities *artifact* is already its own component (Phase 3) — this is only the process/skill layer. *(phase-5-work Part C #3; phase-3-capabilities A.9, Part C #3.)*

## Remote store adapters

The whole point of the abstract store interfaces. All purely additive — the interfaces already exist:

- **`JiraWorkStore`** (or any external tracker) for `WorkStore`. *(phase-5-work Part C, "beyond the roadmap".)*
- **Remote `extends`** for taxonomy — git/URL source types with version-pinning + fetch/cache, and the source-relative resolution transitivity rules. *(phase-2-taxonomy A.5, B.9.)*
- **Tracker sync** for capabilities — per-tracker adapters (Jira/GitHub/Linear) on the `**Tracker:**` shortname convention. *(phase-3-capabilities Part C #4.)*

## Consumer migration (work "Spec 4" — downstream, not work in this repo)

Retiring `skill-cefailures`'s `FOLLOWUPS.md`, `process-inbox` commands, and standalone `capabilities-sdlc` skill in favor of `tcw`; redirecting Proposit's doc-sync entries and reconciling its `AGENTS.md`/`ORCHESTRATOR-AGENTS.md`. **This is work for `tcw`'s consumers**, tracked in those repos. *(phase-5-work Part C #4.)*

## Deferred hooks (recorded, not scheduled)

- **Hard DoD gate** — refuse `tcw work complete` unless declared capability files appear in the item's commit range. *(phase-5-work A.7, B.9.)*
- **Typed taxonomy relations** (`is-a`, `part-of`) beyond freeform `relatesTo`. *(phase-2-taxonomy B.9.)*
- **Additional capability sidecars** (`events.md`, `metrics.md`) — wait for a real project to pull them. *(phase-3-capabilities A.10.)*
