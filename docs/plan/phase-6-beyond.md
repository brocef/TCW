# Phase 6 — Beyond (deferred)

**Status:** ☐ deferred — not scheduled; recorded so the path is on file.
**Depends on:** the three components (Phases 2, 3, 5) shipped and dogfooded.

Everything the three component specs mark "later." Nothing here is built until the single-node core is real and in use. Grouped by source; each item links back to the spec section that defines it.

## Cross-node / recursion (work "Spec 2") — ✓ built

**Status:** ✓ built — spec/plan/build in [`docs/work/.../cross-node-recursion-work-spec-2`](../work/active/2026-06-19-cross-node-recursion-work-spec-2/).

Node discovery; epics + `initiative:` back-pointers; `reconcile` (scan child nodes → consolidated rollup); escalate/delegate over the inbox channel; `tcw work start --worktree` + the checkout-ownership rule (resolved: the "split" model — transitions on the primary checkout/trunk, in-flight edits on the work branch, merge-back on complete). The two-layer × two-layer capability mapping is realized **surface-only**: `reconcile` reads each task's `capabilities.yaml` and lists the deltas in the rollup; the product-layer ledger _flip_ and canonical-wording _coordination_ stay the Spec 3 skill layer below. _(phase-5-work A.2, A.6, A.8; Part C #2.)_

## Skill layer + capabilities process (work "Spec 3") — ✓ built

**Status:** ✓ built — spec/plan/build in [`docs/work/.../skill-layer-capabilities-process-work-spec-3`](../work/active/2026-06-19-skill-layer-capabilities-process-work-spec-3/).

The `tcw work` driving skill — recursive process-inbox, resume, decompose, three-axis / product-first planning, the lifecycle handshake; the capabilities **process** half (the `## Capability changes` planning gate, contradiction-detection) and the **product-layer coordination** protocol as skills. Shipped as two Claude Code skills (`skills/tcw-work`, `skills/tcw-capabilities`) plus the one tool affordance the handshake needed — `tcw capabilities set` (the ledger-flip mechanism). The capabilities _artifact_ is already its own component (Phase 3) — this was only the process/skill layer. _(phase-5-work Part C #3; phase-3-capabilities A.9, Part C #3.)_

## Remote store adapters

The whole point of the abstract store interfaces. All purely additive — the interfaces already exist:

- **`JiraWorkStore`** (or any external tracker) for `WorkStore`. _(phase-5-work Part C, "beyond the roadmap".)_
- **Remote `extends`** for taxonomy — git/URL source types with version-pinning + fetch/cache, and the source-relative resolution transitivity rules. _(phase-2-taxonomy A.5, B.9.)_
- **Tracker sync** for capabilities — per-tracker adapters (Jira/GitHub/Linear) on the `**Tracker:**` shortname convention. _(phase-3-capabilities Part C #4.)_

## Consumer migration (work "Spec 4" — downstream, not work in this repo)

Retiring `skill-cefailures`'s `FOLLOWUPS.md`, `process-inbox` commands, and standalone `capabilities-sdlc` skill in favor of `tcw`; redirecting Proposit's doc-sync entries and reconciling its `AGENTS.md`/`ORCHESTRATOR-AGENTS.md`. **This is work for `tcw`'s consumers**, tracked in those repos. _(phase-5-work Part C #4.)_

## Deferred hooks (recorded, not scheduled)

- **Hard DoD gate** — refuse `tcw work complete` unless declared capability files appear in the item's commit range. _(phase-5-work A.7, B.9.)_
- **Typed taxonomy relations** (`is-a`, `part-of`) beyond freeform `relatesTo`. _(phase-2-taxonomy B.9.)_
- **Additional capability sidecars** (`events.md`, `metrics.md`) — wait for a real project to pull them. _(phase-3-capabilities A.10.)_
