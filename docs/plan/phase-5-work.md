# Phase 5 — Work (TCW component 3 of 3: the changes)

**Status:** spec ✓ · build ☐ not started
**Delivers:** `tcw work` + `FsWorkStore` — the single-node state machine + loose DoD gate (the work component's "Spec 1").
**Depends on:** Phase 1 (package/CLI), Phase 4 (shared tree-store core); references Phase 2 (taxonomy) and Phase 3 (capabilities) loosely — `capabilities.yaml` is an opaque blob in this phase.
**Build checklist:** `WorkStore` interface → `FsWorkStore` over `docs/work/` → the ten subcommands (B.2) → the state machine (B.3) → the loose DoD gate (B.6) → tests (B.8).

> Spec **and** build plan for component 3. Part A is the model; Part B is the buildable single-node tool; B.9 records the resolved open questions. The cross-node recursion, skill layer, and migration (this doc's "Spec 2/3/4") are deferred to [`phase-6-beyond`](phase-6-beyond.md). Framework rules: [`../../AGENTS.md`](../../AGENTS.md). Build order: [`INDEX.md`](INDEX.md).

**Date:** 2026-06-18
**Scope:** the full conceptual model (Part A) plus the buildable *core single-node tool* (Part B). Sibling components: [`phase-2-taxonomy`](phase-2-taxonomy.md), [`phase-3-capabilities`](phase-3-capabilities.md).

---

## Part A — The model (the constitution)

### A.1 Motivation

Today's flow scatters a unit of work across unrelated document trees with no single "where is this right now" spine:

```
docs/inbox/<dated>.md → docs/superpowers/specs/…-design.md → docs/superpowers/plans/….md
  → implementation → docs/changelogs|release-notes/upcoming.md → docs/FOLLOWUPS.md → tag → docs/inbox/.archive/
```

The five problems this design solves are facets of **one** missing thing — a durable, legible, per-node source of truth — plus the recursion that lets it scale:

1. The planning workflow is unclear and documents "jump" between trees (`inbox/` → `superpowers/specs/`).
2. Orchestrator-level work has no single source of truth and can't be paused/resumed cleanly across sessions.
3. The worktree discipline for concurrent agents is aspirational, not enforced.
4. Follow-up tracking (`FOLLOWUPS.md`) is a growing mutable log, poorly adopted, with a name mismatch in the skill that references it.
5. The cross-repo initiative model lives only in `ORCHESTRATOR-AGENTS.md`, is not codified in the plugin, and partially contradicts it.

### A.2 Nodes and recursion

The system is **infinitely recursive**. There is no special "org root" vs "repo" — only a **node**, and "orchestrator" / "project" are *roles a node plays relative to its neighbors*, decided by topology, not by a hardcoded path.

- **Node** = a directory that is a git repo **and** contains `docs/work/`. (The `docs/work/` directory is the opt-in marker — a single `test -d`.)
- **Parent** = nearest *ancestor* directory that is a node. **Children** = nearest *descendant* directories that are nodes (skipping intermediate non-node folders). A node with no child nodes is a leaf (local work only); a node with no ancestor node is the root.
- A node coordinating its children is acting as an **orchestrator**; the same node managed by *its* parent is a **project**. Both roles use the same mechanism.

**Layering:** **TCW** (the `tcw work` recursion layer) owns the *generic recursive mechanism*; each node's `AGENTS.md` supplies the *instantiation* (which children exist, the team-agent roster, node-local gates such as a consumer's publish-validation). This resolves concern #5: `tcw` codifies the machine, `AGENTS.md` codifies the wiring. A consumer's `ORCHESTRATOR-AGENTS.md` becomes "that node's config," not a parallel rulebook.

### A.3 Filesystem as state machine

**State is encoded by where a file lives, not by annotations inside a file that grows forever.**

```
docs/work/
  inbox/       raw human/agent requests — the drop zone and the inter-node channel
  backlog/     deferred / not-yet-started work items          (replaces FOLLOWUPS.md)
  active/      in-flight work items — "work these now"
  blocked/     parked on an external/sibling wait — not actionable
  completed/   frozen, finished work — never touched again
```

- **The index is `ls active/`.** There is no `INDEX.md` and no global ledger file to drift or to burn tokens reading. Cross-cutting queries are *generated on demand* (`rg`, `find`, `tree`), never stored.
- **Directories partition by *actionability*, not by workflow phase.** `inbox` = needs triage, `backlog` = not yet, `active` = work now, `blocked` = waiting, `completed` = done. Fine-grained phase ("planning / implementing / in-review") is a `phase:` field in `state.yaml`, not a directory — this freezes the directory set at five and prevents Jira-style workflow-soup.
- **A work item is a folder** that carries its own documents and moves through stages by changing its parent directory (a `git mv`). The "chaotic document movement" becomes the *one explicit mechanism*.
- **Completion = move the whole folder `active/<slug>/ → completed/<slug>/`.** "Completed" means *no further code changes will result from this item*. Therefore documentation-sync, version bumps, and capability reconciliation all run **before** the move. The folder is self-contained and frozen; git history is the permanent archive (no `.archive/`).
- **Future work = un-started items in `backlog/`.** Picking one up moves it to `active/`; dropping it deletes it. This replaces `FOLLOWUPS.md` entirely.

### A.4 Per-item state document

Each work item has **one state document, scoped to that item.** It may be as rich as desired (full history, a post-mortem of how it went) because it is bounded by the item — once the item reaches `completed/` it is never touched again. The forbidden pattern is a document scoped to *all* work (a global ledger), which grows without bound.

### A.5 Stable identity

The core mechanic is *moving folders*, so any reference by path breaks on the next transition. The **stable handle is the slug** (`YYYY-MM-DD-<kebab-title>`); references are by slug, and resolution is an abstract store operation — `resolve(stable_id) → item`, **not** a path computation. (Jira solved this with `PROJ-123`; we solve it with the slug.) `FsWorkStore` realizes `resolve` as a glob for the folder named `<slug>`, **bounded to the current node** (it does not descend into a child node's `docs/work/`) and erroring on multiple matches; a remote store realizes it as a lookup by key. A capability's `Planning doc:` pointer holds the slug and resolves through `resolve`, never a path — which is what lets the pointer survive when the store isn't the filesystem (A.11).

### A.6 Cross-node initiatives (epics)

One orchestrator work item ("epic") corresponds to many project work items ("tasks") across child nodes — some active, some blocked, some completed. *(This is the cross-node model; the tooling for it lands in **Spec 2** — Part B / Spec 1 is single-node.)*

```
workspace/                          ← node (git + docs/work/)
  docs/work/active/redesign-x/
      content.md  ← CONSOLIDATED rollup: slice table + dependency DAG + next-action
      spec.md     ← overview spec
      state.yaml  ← machine fields (type: epic, …)
  project-a/                        ← child node
      docs/work/active/redesign-x-slice-1/…
      docs/work/blocked/redesign-x-slice-2/…
  project-b/                        ← child node
      docs/work/completed/redesign-x-slice-3/…
```

(The exact cross-node file layout is finalized in Spec 2; it reuses the Part B format split — `content.md` for the rich rollup, `state.yaml` for machine fields.)

- Each child slice's `state.yaml` carries one back-pointer field: `initiative: redesign-x`.
- **Child folders are ground truth; the orchestrator's rollup (`content.md`) is a consolidated interpretation, reconciled at session start** by scanning each child node's `docs/work/**` for `initiative: redesign-x`. (Same "git/briefings win over the ledger" principle already in `ORCHESTRATOR-AGENTS.md`, now mechanical.) The rollup is bounded because it is scoped to one initiative.
- **Inbox is the inter-node channel.** Writing *down* into a child's `docs/work/inbox/` = **delegate**; writing *up* into the parent's `docs/work/inbox/` = **escalate**. Symmetric. A repo agent that discovers cross-repo scope escalates by dropping an inbox doc one level up and flagging the human to start an orchestrator session — respecting the boundary that a repo-spawned agent does not write to the parent's tracking tree directly.

### A.7 Capabilities as the product axis of work

The former `capabilities-sdlc` skill is **absorbed**, not coupled-to. It bundled two things, and they split cleanly:

- Its **process half** — the planning gate (`## Capability changes` opens every spec), contradiction-detection (at the moment of change), the capability doc-sync trigger — is exactly what the work lifecycle subsumes. It becomes *structural* here instead of convention-with-no-CI-backstop.
- Its **artifact half** — the capability format, the status taxonomy, the **bounded `docs/capabilities/` tree**, the two-layer (per-repo / product) model, and product-layer coordination — is the **standing capability ledger** — the always-current layer. It is now the standalone **`tcw capabilities`** component ([`phase-3-capabilities`](phase-3-capabilities.md)), not docs folded under this skill. *(Layout reconciliation: capabilities live in a bounded tree, not scattered `**/capabilities.md` — see the capabilities spec A.2.)*

**A work item declares its effect along three explicit axes** (all open `content.md`; any may be empty):

- **Product changes** — capability deltas: new / updated / removed user-facing capabilities.
- **Technical changes** — changes to the *application's machinery* with no user-facing delta (refactor, infra, perf, tech-debt, dependency).
- **Meta changes** — changes to the *project itself, not the application*: planning/docs, CI, repo tooling, the framework. (Even when a node's deliverable *is* a tool or framework, meta-work is the apparatus around building it — distinct from the application's own machinery.)

A feature carries product (and usually technical); a refactor is technical-only; a docs/CI/tooling change is meta-only; a bug references a capability and branches (below). Which sections are non-empty *is* the classification — there is no separate `type` field. This makes "planning relates to capabilities" literal and required, not a convention.

**The standing ledger is the system's only mutable survivor.** Capability files describe *current intended product state*; they persist independent of any work item, and a completed item's product delta is *applied* to them. Everything else freezes in `completed/`; the ledger keeps describing the present — correct, because the present is the one thing that must stay live.

**Two pointers bind work to capability:**

- **Forward (capability → work):** a `Missing` capability's `Planning doc:` pointer holds the realizing work item's **stable ID** (slug), resolved through the store's `resolve` (A.5) — so it survives even when the work-store is remote.
- **Back (work → capability):** the work item's `capabilities.yaml` lists the capability files it touches and their intended status transitions, as **identifiers into the `docs/capabilities/` tree** (capabilities spec A.6/A.8).

The binding is a **pointer, not a transaction.** With `FsWorkStore` the work item and the capability live in the *same* repo, so a single commit can land code + the capability flip + the work-item move atomically (an A.11 bonus). When the work-store is remote (Jira) the ledger still lives in the code repo — two different stores — so the binding is **best-effort** (apply the delta, then transition the ticket; no cross-system atomicity). The ledger is therefore always filesystem-resident and independent of the `WorkStore`.

Neither owns the other: a `Missing` capability can exist with no work item yet (pure intent); a technical-only item has no capability pointer.

**The lifecycle handshake** ties transitions to ledger operations:

| Work transition | Ledger operation | Authority |
|---|---|---|
| `new` (has a product delta) | declare it in `## Product changes`; new capabilities recorded **Missing** with `Planning doc:` = slug | the planning gate, now structural |
| during `active` | contradiction-detection at the moment of change | the change author |
| `complete` (DoD "capabilities reconciled") | apply the delta to the ledger: `Missing → Supported`, body/scope edits, `Supported → Omitted`. This is the same evaluation the old capability doc-sync trigger performed | the DoD gate |

Because `completed` means "no further code changes," reconciling the ledger is the final pre-freeze step rather than a follow-up. The gate is **loose** (B.6): `complete` forces the operator to *acknowledge* reconciliation; it does not verify it. (A hard gate is the deferred hook below.)

**The bug branch** (the old "capabilities don't track bugs → use FOLLOWUPS" rule, resolved — bug-tracking lives in work items):

- **Pure regression** (a `Supported` capability whose implementation broke): technical-only, no product delta; DoD just confirms the ledger entry still matches the restored behavior.
- **Discovery fix** (documented `Supported` but never actually worked) or **capability-change-disguised-as-bug**: carries a product delta; the planning gate applies and completion may edit the ledger entry/status.

**Recursion maps the two ledger layers onto the two work layers:** an epic ↔ the orchestrator-node's product-layer `docs/capabilities/`; a task ↔ the leaf-node's `docs/capabilities/`. The product-layer coordination protocol (a per-repo agent asking the orchestrator for canonical wording) **is** the escalate/delegate inbox channel of A.6 — an epic completing flips the product-layer entry; a task completing flips the co-located one.

**Two backlogs, complementary not merged:** `**Status:** Missing` (the capability-backlog: what we want) and `ls backlog/` (the work-backlog: queued changes) are two lenses, linked by ID when both exist. No dedup, no derivation.

**Coupling, stated precisely:** the *systems* are unified (one owner, absorbed). The *tool's* relationship to capability prose stays mechanism-only — it reads `capabilities.yaml` pointers, never capability prose; the ledger spec owns content/format/status. The `complete` DoD gate is **loose** (acknowledged, not externally verified — B.6); a **hard gate** (refuse `complete` unless the declared capability files appear in the item's commit range) is a deliberate future hook, not built now.

### A.8 Concurrency and worktrees

Concurrency safety = **dispatch discipline + worktrees**, not an in-file lock:

- The human avoids spinning up two orchestrators on the same work; an orchestrator dispatches **one work item per agent** to avoid two agents on the same item.
- The **worktree invariant** covers the orthogonal case: two agents working *different* items in the *same* repo node would collide on the working tree, so each active item gets its own git worktree. (Tool support — `tcw work start --worktree` — lands in **Spec 2**, alongside the rule for which checkout owns `docs/work/` writes.)
- **Transition atomicity is not guaranteed.** The model assumes **one writer per node** (the dispatch discipline above); the `FsWorkStore` `git mv` is not locked against a concurrent `tcw work` invocation. A remote store may offer server-side transactions; the FS adapter relies on single-writer discipline, not a lock.

### A.9 Jira mapping and explicit non-features

This is a recursive, OS-native Jira. Mapping:

| Jira | Ours |
|---|---|
| Issue/ticket | work-item folder |
| Status / board columns | the five status directories |
| Epic → Story → Sub-task | recursive nodes + `initiative:` back-pointer |
| Comments / history | `state` doc log + git + broker/inbox |
| Attachments | artifacts in the work folder |
| JQL / board view | `tcw work list` query (the FS adapter adds `rg` / `find` / `tree`, generated, never stored) |
| Notifications / watchers | inbox (async) + broker (live) |
| Permissions | node write-boundary |
| Stable issue key | the slug |

**Deliberately refused (ceremony with no place in an AI flow):** sprints, boards, velocity, story points, burndown, time tracking, SLAs, due dates, watcher matrices, custom-field/screen/scheme configuration, and a conditional workflow engine. (The `/schedule` integration covers the rare "do this at a time" need.)

### A.10 Design principles

- **Files stay plain markdown/YAML in git; the CLI is a safe accessor, not a gatekeeper.** A human (or any agent) can always read/edit the files directly; the tool guarantees invariants *when used*. In the default adapter, the filesystem is the database (see A.11).
- **No daemon, no database, no server, no web UI.** The tool is a thin typed wrapper over git + a folder of markdown. If it grows a server of its own, we've lost the plot — a future external-tracker adapter talks to *that* tracker's API; we still ship none.
- **Mechanism vs. judgment.** Correctness properties (structure, legal transitions, slug integrity, the DoD gate, link resolution) live in the *tool*. Judgment (when to create/decompose/escalate, what the spec says, when to resume) lives in *skills* that teach agents to drive the tool.

### A.11 Abstract spine, filesystem leverage

The model is defined in an abstract vocabulary — **item · status · transition · stable ID · reference · node relation · query · body/fields/attachments**. The filesystem is the *default realization* (Part A describes it concretely), and the `WorkStore` interface (Part B) keeps the model swappable so it can run against an external tracker where one is already in use — the enterprise-portability requirement. Filesystem superpowers — work co-located with code, **one atomic commit landing code change + capability status flip + work-item transition**, grep/diff/PR-review legibility, atomic `mv` as transition — are leveraged as **bonuses on top**, never as load-bearing assumptions the abstract vocabulary can't express. (A.7's capability binding, for instance, *degrades* to best-effort when the store is remote — it does not break.)

**The litmus test** governs every mechanism: *"Could a non-filesystem store implement this operation, even if less elegantly?"* Yes → it belongs in the model / the store interface. No (a filesystem trick with no abstract analog — reconstructing state from git log, globbing the folder as an open namespace, hard-coded paths in links, parent/child as literal directory ancestry) → it belongs in the FS adapter as a private detail, or it is redesigned. This discipline is codified as the project's prime directive in [`../../AGENTS.md`](../../AGENTS.md).

---

## Part B — Core single-node tool (Spec 1, buildable now)

### B.1 Scope

The **`tcw work`** subcommand group operating on the current node's work store. **Single node only** — no recursion, no skill layer, no migration, no capability *prose* parsing. Delivers: the directory contract, slug management, work-item folders, the three-axis (product/technical/meta) effect record, the legal-transition state machine, the loose DoD gate, and the on-demand queries.

**Architecture — the store interface.** The CLI (and, later, the skills) depends on an abstract **`WorkStore`** interface; concrete adapters realize it. Spec 1 ships exactly one adapter, **`FsWorkStore`** (the `docs/work/` filesystem-state-machine of Part A). The interface exists so a future `JiraWorkStore` (or any tracker) is a drop-in without touching the CLI or skills. Use the ABC + adapter pattern for stores (per `AGENTS.md`). What is *in* the interface vs. *beside* it is governed by the A.11 litmus test:

- **In `WorkStore` (every adapter implements):** create · transition · query · get · set-field · link. The status vocabulary and the legal-transition graph live in the **core**, not the adapter — the adapter only *effects* a transition the core has already deemed legal.
- **Beside it (local, FS-flavored — not store operations):** worktree/branch creation, node-detection by directory walk, `rg`/`find`/`tree` power queries. The CLI wires these to the active node locally; they are absent from the portable interface.

Home: this repo (the `tcw` package). Language: Python (argparse + PyYAML + `git`/`git worktree` via subprocess). Tests: pytest with `tmp_path` git repos.

### B.2 Command surface

```
tcw work init                          create docs/work/{inbox,backlog,active,blocked,completed}/
tcw work new "<title>"                 → creates backlog/<slug>/ (content.md + state.yaml); prints slug
tcw work list [--status S]             the board (reads dir listing + state.yaml)
tcw work show <slug>                   resolve slug→item; print state + body
tcw work path <slug>                   print current path of a slug (the stable-ID resolver)
tcw work start <slug>                  inbox|backlog → active/
tcw work block <slug> --on <slug|"…">  active → blocked/ (writes/updates links.yaml)
tcw work unblock <slug>                blocked → active/ (refuses if any blocker unresolved)
tcw work complete <slug> --resolution <R> --confirm   active → completed/ (DoD gate)
tcw work drop <slug>                   inbox|backlog → deleted (git rm)
```

### B.3 State machine

```
        new
         │
         ▼
   inbox / backlog ──start──► active ──complete──► completed   (frozen; no exit)
         │                   ▲    │
        drop                 │    └──block──► blocked
       (delete)              └────unblock────────┘
```

- Illegal transitions are **refused** — that is the enforcement (e.g. `completed → *`, `blocked → completed`).
- `completed/` is a sink. Reopening = a *new* item that links to the old one; history is never un-frozen.
- `drop` is only legal from `inbox`/`backlog` (you don't silently delete in-flight or finished work).

### B.4 File formats

A work item is a folder named exactly `<slug>`. Inside:

- **`content.md`** — the human-readable body. It opens with the item's **three-axis effect** (A.7), which replaces capabilities-sdlc's convention-only planning gate with a structural one:
  - `## Product changes` — capability deltas: new / updated / removed user-facing capabilities (empty for non-product work).
  - `## Technical changes` — application-machinery changes with no user-facing delta.
  - `## Meta changes` — changes to the project itself (planning, CI, tooling, the framework), not the application.
  Over the item's life `content.md` is joined by `spec.md`, `plan.md`, and any artifacts. The tool does not parse this prose. *(Abstractly: the item's body + named attachments — see A.11.)*
- **`state.yaml`** — machine-readable metadata. Status is **not** stored here (status = the directory / store-status). Fields:
  - `slug` (string, immutable) · `title` · `phase` (free-text, e.g. `planning`) · `created` (date) · `resolution` (set on completion: `done|wontfix|duplicate|superseded`) · `dod` (optional acknowledged-checklist record). *(No `type` field — the product/technical axis classifies. `worktree`/`branch` arrive with `--worktree` in Spec 2.)*
- **`capabilities.yaml`** — the machine-readable **back-pointer** for the product axis: the capability files this item touches and their intended status transitions (e.g. `{file: …, heading: …, from: Missing, to: Supported}`). Drives traceability and pointer resolution. The tool reads these *pointers*, never the capability *prose* (mechanism vs. judgment); in **Spec 1** it treats the file as an **opaque blob** — stored and surfaced, not acted on (applying the transitions to the ledger is the Spec-3 capabilities layer). Empty/absent for technical-only items.
- **`links.yaml`** — present for blocked/linked items. `blocked_on:` is a list of `{slug: …}` or `{external: "…"}`; optional `relates:` list. Kept separate from `content.md` so an "is this still blocked?" check reads only this small file.

**Slug rules:** `YYYY-MM-DD-<kebab-title>` from the creation date + title. Uniqueness is checked **within the node** via the store (`exists(slug)`, not a raw path test); collisions append `-2`, `-3`, … The slug is **frozen at creation** — `title` may later drift in `state.yaml`, but the slug never changes and there is no `tcw work rename`. It is the only cross-reference handle; `resolve` (A.5) errors if two folders ever carry the same slug.

### B.5 Command behavior

- **`init`** — create the five status directories, each holding a `.gitkeep` so the empty dirs survive commit/clone (idempotent — tops up a partial set). Refuse outside a git repo (suggest `git init`).
- **`new`** — generate the slug, create `backlog/<slug>/` with `content.md` (seeded from the title, the `## Product changes` / `## Technical changes` / `## Meta changes` scaffold, and any piped stdin) and `state.yaml`. Print the slug. (No empty `spec.md` is seeded — it is created only when an agent writes one.)
- **`list`** — walk the status directories, read each `state.yaml`, print a table (slug · status=dir · phase · title). `--status` filters.
- **`show` / `path`** — resolve the slug to its current item (A.5); `show` prints `state.yaml` + the head of `content.md`; `path` prints just the resolved path (for scripting/references).
- **`start`** — move `inbox|backlog → active`. *(The `--worktree` option is deferred to Spec 2 — see A.8.)*
- **`block`** — move `active → blocked`; append the `--on` target to `links.yaml` `blocked_on`.
- **`unblock`** — move `blocked → active`; **refuse** if any `blocked_on` entry is unresolved — a referenced slug whose item is not `completed` (checked via `resolve`/`get`, not a raw `completed/` path test), or an `external` entry still listed. A blocker slug that no longer resolves (it was dropped) counts as resolved, with a warning. `--force` overrides; `external` entries are cleared by hand-editing `links.yaml`.
- **`complete`** — the DoD gate (B.6); on pass, set `resolution`, move `active → completed`.
- **`drop`** — `git rm -r` the folder (only from `inbox`/`backlog`). If a capability's `Planning doc:` pointed at this slug, that forward pointer is left dangling; reconciling it is the capabilities component's job ([`phase-3-capabilities`](phase-3-capabilities.md)), not the work tool's.

### B.6 DoD gate (loose)

`tcw work complete` is the `active → completed` transition condition. Loose means the tool **forces the checklist to be seen and acknowledged**, but does not externally verify each item:

1. Read the node's DoD checklist — a built-in default, overridable by a node-local `docs/work/dod.yaml` (the tool parses the YAML list; absent → default). Default items: *tests pass · docs synced · capabilities reconciled · reviewed · version offered*. In Spec 1 every item is a free-text line the operator **acknowledges**; the tool verifies none of them (the capabilities item's ledger semantics arrive with Spec 3).
2. Print the checklist; require `--confirm` and a `--resolution` value. Without both, refuse and exit non-zero.
3. Record the acknowledgment + resolution in `state.yaml`, then `git mv` to `completed/`.

### B.7 Git behavior and node detection

- Every transition performs `git mv` (or `git rm` for `drop`) and **stages** the change; untracked files inside the item folder are staged first so `git mv` does not orphan them (refuse with a clear error on conflicting unstaged state). A `--commit` flag additionally commits with a conventional message (`tcw work: <verb> <slug>`); **default is stage-only** so the agent controls commit boundaries (a transition usually rides with related code/doc changes in one commit).
- **Node detection:** walk up from cwd to the nearest directory that is a git work-tree **and** contains `docs/work/`; operate there. Resolution and queries are bounded to *that* node — they do not descend into a child node's own `docs/work/`. If no node is found, error and suggest `tcw init`.

### B.8 Testing

pytest over `tmp_path` git repos (each test runs `git init` and sets `user.name`/`user.email`): slug generation + collision suffixing + immutability + multiple-match resolution error; every legal transition and a representative set of refused illegal ones; `completed/` is a sink; `unblock` refusal on an unresolved blocker and pass on a dropped one; `list --status` filter; `complete` refusal without `--confirm`; `slug→item` resolution *after* the folder has moved, and its boundedness to the node; malformed `state.yaml` handling; `init` `.gitkeep` persistence.

### B.9 Resolved decisions

- **`phase`** — **free-text** (e.g. `planning`); no fixed enum. Nothing in this phase sets it; a fixed enum is deferred to the skill layer (Phase 6) that would actually drive it.
- **DoD defaults** — the **five defaults stand** (*tests pass · docs synced · capabilities reconciled · reviewed · version offered*) and **every item is loose/acknowledged** in this phase. A node-local `docs/work/dod.yaml` overrides the list but cannot add *hard* (verified) items yet — the hard-gate hook stays deferred.

*(Resolved earlier, reflected in the body: `--commit` → stage-only; `type` → dropped (the product/technical/meta axes classify); `new` lands in `backlog/`; `content.md` seeded with the three-axis scaffold, no empty `spec.md`; worktree creation → Phase 6; DoD source → `docs/work/dod.yaml` + built-in default.)*

---

## Part C — Decomposition / roadmap

The work component decomposes into four sub-specs. **Spec 1 is this phase (Phase 3);** Specs 2–4 are deferred to [`phase-6-beyond`](phase-6-beyond.md). Global build order: [`INDEX.md`](INDEX.md).

1. **Spec 1 (this phase, Part B):** core single-node tool — the `WorkStore` interface + the `FsWorkStore` adapter + CLI.
2. **Spec 2 — Cross-node / recursion:** node discovery, epics, `initiative:` back-pointers, `reconcile` (scan children → consolidated rollup), escalate/delegate via inbox, `tcw work start --worktree` (+ the rule for which checkout owns `docs/work/` writes), and the two-layer × two-layer capability mapping (epic ↔ product-layer ledger, task ↔ leaf-node ledger; product-layer coordination over the inbox channel).
3. **Spec 3 — Skill + absorbed capabilities process:** the `tcw work` driving skill (recursive process-inbox, resume, decompose, three-axis / product-first planning, the A.7 lifecycle handshake). The capabilities **artifact** is already its own component ([`phase-3-capabilities`](phase-3-capabilities.md)); Spec 3 adds only the *process* skill, not a re-homing of artifact docs.
4. **Spec 4 — Consumer migration (downstream, not work in this repo):** retiring `skill-cefailures`'s `FOLLOWUPS.md` → `backlog/`, its two `process-inbox` commands → the recursive flow, and its standalone `capabilities-sdlc` skill → `tcw capabilities` + the Spec-3 process skill; redirecting Proposit's per-repo `CLAUDE.md` doc-sync entries; fixing `documentation-sync`'s follow-ups name mismatch; reconciling Proposit-App's `AGENTS.md` / `ORCHESTRATOR-AGENTS.md` to this model. This is **work for `tcw`'s consumers**, tracked in those repos — recorded here only so the migration path is on file.

**Beyond the roadmap (enabled, not built):** a `JiraWorkStore` (or other external-tracker) adapter — the `WorkStore` interface exists so this is purely additive.
