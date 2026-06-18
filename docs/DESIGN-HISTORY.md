# TCW — design history & decision log

The narrative companion to the component specs in [`plan/`](plan/): *how* the TCW design came to be and *why* the major decisions were made. The specs state the conclusions; this captures the reasoning and the path that produced them. The original brainstorming, dual review, and refinement happened inside the `skill-cefailures` repo (June 2026) and are preserved in its git history; this is the distilled account.

## Where it started

The work began as a request to **evaluate and redesign the SDLC** embodied by the `skill-cefailures` plugin's skills — the flow where work arrives as inbox documents, an agent picks it up (in a project repo, or at the org root as an "orchestrator"), the superpowers plugin drives spec/plan/execution, and work ends with a version cut + documentation sync.

Five concerns motivated it:

1. The planning workflow was unclear and documents "jumped" between unrelated trees (`docs/inbox/` → `docs/superpowers/specs/` → plans → changelogs → `FOLLOWUPS.md` → archive) with no "where is this right now" spine.
2. Orchestrator-level work had no single source of truth and couldn't be paused/resumed cleanly across separate sessions.
3. The worktree discipline for concurrent agents was aspirational, not enforced.
4. Follow-up tracking (`FOLLOWUPS.md`) was a growing, poorly-adopted mutable log — with a literal name mismatch in the skill that referenced it.
5. The cross-repo initiative model lived only in `ORCHESTRATOR-AGENTS.md`, was not codified in the plugin, and partially contradicted it.

The insight that unlocked everything: these five are facets of **one** missing thing — a durable, legible, per-node source of truth — plus the **recursion** that lets it scale.

## The work component: a filesystem-native state machine

The first design was a work-tracking system built on a few load-bearing ideas:

- **Filesystem as state machine.** A work item is a *folder*; its status is *which directory it lives in* (`inbox/backlog/active/blocked/completed`), changed by `git mv`. The index is `ls active/` — there is no global ledger file to drift or burn tokens (the banned anti-pattern, and the answer to concern #4).
- **Stable identity by slug.** Folders move, so references are by a stable slug, resolved to "wherever it now lives."
- **Per-item state, never global.** Each item owns one rich state document, bounded by the item and frozen on completion — so nothing grows without bound.
- **Recursion.** A "node" is any git repo with a `docs/work/`. "Orchestrator" and "project" are *relative roles*, not fixed paths; cross-node initiatives (epics) link a parent item to child items by an `initiative:` back-pointer; the inbox is the inter-node channel (write down = delegate, write up = escalate).

A pivotal decision: **make it a deterministic CLI tool, not a set of prose skills.** Correctness invariants (legal transitions, slug integrity, the DoD gate) are exactly the properties an LLM violates stochastically when merely *told* to follow them. Mechanism lives in the tool; judgment lives in skills that drive it. The framing crystallized as a **"recursive, OS-native Jira"** — with an explicit list of *refused* Jira ceremony (sprints, story points, burndown, SLAs, …).

## Capabilities, absorbed

The design had to reconcile with the existing `capabilities-sdlc` skill. The breakthrough was seeing that skill as **two bundled halves**:

- a **process half** — the planning gate, contradiction-detection, the doc-sync trigger — which is exactly what a work *lifecycle* subsumes; and
- an **artifact half** — the `capabilities.md` format, the `Supported / Missing / Omitted` taxonomy, the two-layer model — which is the **standing capability ledger**: the noun-at-rest.

Decision: **absorb it.** The process half becomes *structural* in the work lifecycle (a capability delta declared at item creation, reconciled at completion — no longer convention with no CI backstop); the artifact half re-homes under the tool as the ledger. A work item now declares its effect along **two explicit axes — product changes (capability deltas) and technical changes** — which made the old `type` enum redundant. Bugs became work items (resolving the old "capabilities don't track bugs → use `FOLLOWUPS`" rule). Coupling stays **loose**: pointers link the two; the tool never parses capability prose.

## Storage abstraction

A key requirement surfaced: to be useful at **enterprise scale**, where a tracker like Jira is already in use, the model must not be welded to the filesystem. Decision: the CLI talks to an abstract **store interface**; the filesystem is the *default adapter*; a Jira (or wiki, or graph-DB) adapter is a later drop-in. The filesystem is the design's identity and the source of unique superpowers (one atomic commit landing code + status + capability changes together), but those are *bonuses*, never load-bearing assumptions.

This produced the project's **prime directive — the abstraction litmus test:**

> *"Could a non-filesystem store implement this operation, even if less elegantly?"* Yes → it belongs in the model. No → it's a filesystem-adapter detail, or it gets redesigned.

The litmus test was codified in a standing working guide (now this repo's `AGENTS.md`).

## A dual review, and what it changed

The work spec was put through a deliberate **dual review** — an independent subagent critique plus a local-model first-pass (`bllm-review-plan`). It surfaced real issues and drove a refinement pass:

- **Dropped the `type` enum entirely** — the product/technical axis already classifies.
- **Deferred worktrees to a later spec** — the "which checkout owns `docs/work/`" problem was unsolved for a single-node first cut.
- **Reframed the capability binding as a pointer, not a transaction** — atomic under the filesystem adapter, best-effort when the store is remote; the ledger is always filesystem-resident, independent of the store. (This was the sharpest litmus-test catch: the "one atomic commit" superpower can't be load-bearing if a remote store can't provide it.)
- **Made slug resolution an abstract `resolve(stable_id)` operation** so a capability's `Planning doc:` pointer survives a remote store.
- Plus: reconciled the loose-gate wording, stated a single-writer concurrency contract, and pinned down slug / `unblock` / `drop` / `init` edge cases.

## The missing leg: taxonomy

Then came the realization that completed the system: **capabilities describe the behavior of *something*, but nothing named the something.** A reader had to *infer* the subject from prose and surrounding language. Applications always have *things* — entities worth a concrete glossary and ontology.

This produced the third component and the **triad**:

- **Taxonomy** — the *things* (nouns).
- **Capabilities** — what they can do (behaviors).
- **Work** — how they change (verbs).

Taxonomy decisions:

- **Terms form a forest; the slug *is* the path** (`admin/permission` ≠ `some-object/permission`). Addressing is by path; resolution is trivial because the path *is* the address.
- The same **store abstraction** and **prime directive** as work.
- **Federation via `extends`** — a taxonomy can import others. `config.yaml` maps a **consumer-chosen alias** to a source repo; each alias is a namespace; **no silent merge** (local and imported same-path terms stay distinct; the namespace disambiguates, and bare references mean the local term). Local-path sources first; remote (git/URL, with version-pinning) later.
- A crucial contrast: **taxonomy federates directly while capabilities relay through an orchestrator** — deliberately, because vocabulary is *canonical-shared* ("Argument" must mean one thing everywhere) while capabilities are *locally-divergent* (web and mobile realize the "same" behavior differently).

## TCW, and its own repo

The three components became one binary — **`tcw`** (Taxonomy, Capabilities, Work), ordered by definitional dependency — with three subcommand groups (`tcw taxonomy | capabilities | work`) over a shared store core. At that point the scope (a standalone CLI + framework) had clearly outgrown a plugin skill, so it was **extracted into this repo**. `skill-cefailures` becomes a *consumer* of `tcw` (installing the CLI like its broker, and folding its `capabilities-sdlc` skill into the capabilities component).

## Where it stands

- **Plan:** reorganized into phased build docs under [`plan/`](plan/), tracked by [`plan/INDEX.md`](plan/INDEX.md). All three component specs are written (taxonomy, capabilities, work), their open questions resolved, and the `work → tcw work` reframe applied.
- **Built:** nothing yet — planning is complete; execution starts at Phase 1 (scaffold). See [`plan/INDEX.md`](plan/INDEX.md).
