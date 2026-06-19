# TCW — agent working guide

**TCW** (Taxonomy · Capabilities · Work) is a storage-abstracted framework for describing and evolving a software project along three axes, exposed through one CLI, `tcw`, with three subcommand groups (`tcw taxonomy | capabilities | work`). This guide governs all work in this repo.

- **Plan, build order, and live status:** [`docs/plan/INDEX.md`](docs/plan/INDEX.md) — the spine; one file per build phase.
- **Component designs (source of truth):** [`docs/plan/`](docs/plan/) — `phase-2-taxonomy.md` (the nouns), `phase-3-capabilities.md` (the user stories), `phase-5-work.md` (the changes). Each phase doc is the component's design **and** build plan. Read the relevant phase before changing a component's model; if a change diverges, update the phase doc in the same change — never let code and design drift.

## Generic instructions

- Git commit messages should not include any co-authoring content.

## Prime directive: the abstraction litmus test

TCW ships a filesystem-native default, but the **model is storage-abstracted** so it can run against an external tracker (Jira, a wiki, a graph DB) where one is already in use. That portability is the whole reason the system is viable at enterprise scale — do not trade it away for filesystem cleverness. Before adding or changing any operation, apply this test:

> **"Could a non-filesystem store implement this operation, even if less elegantly?"**
> - **Yes** → it belongs in the model / the abstract store interface.
> - **No** — it only works as a filesystem trick with no abstract analog → push it into the filesystem adapter as a private detail, or redesign it.

## Abstract spine, filesystem leverage

Express behavior in the abstract vocabulary — **item · status · transition · stable ID · reference · node relation · query · body/fields/attachments** — and let the filesystem *realize* it. Filesystem superpowers are bonuses layered on top, never load-bearing assumptions of the model.

- **Leverage freely (bonuses):** docs co-located with code (one repo / worktree / PR / diff); one atomic commit carrying code change + status/capability change together; grep/diff/PR-review legibility; atomic `mv` as transition.
- **Keep out of the model (no abstract analog):**
  - Reconstructing current state from git history — *state is the status; git is archive.*
  - Globbing a store folder as an open namespace — *bound it: body + named fields + named attachments.*
  - Hard-coded paths in references — *use stable IDs / paths-within-the-store; resolve through the store.*
  - Parent/child as literal directory ancestry outside the node-resolution layer — *express the relation abstractly; the FS adapter derives it from nesting.*
  - Worktrees and `rg`/`find` queries — *filesystem-adapter local details, not store-interface operations.*

## Implementation rules

- Each component depends on an abstract **store interface** (`TaxonomyStore`, `WorkStore`, …) that the CLI and any skills talk to. Ship the **filesystem adapters** (`FsTaxonomyStore`, `FsWorkStore`) only; keep remote adapters (e.g. `JiraWorkStore`) possible but unbuilt. Never add an interface method that only the FS adapter could honor (run the litmus test first).
- The three components are **one system**: taxonomy is the nouns, capabilities the user stories (what a user can do), work the changes (to capabilities, machinery, or the project itself). They link by loose, one-directional pointers (capability→term, work→capability/term) and never duplicate each other.
- Python with type hints; pytest over `tmp_path` git repos. Use the ABC + adapter pattern for stores; extract the shared tree-store core only once two components are real (don't pre-abstract).

## Documentation Sync

Before reporting any code change complete, invoke the `skill-cefailures:documentation-sync` skill to evaluate the entries below. When writing an implementation plan, include explicit documentation-update tasks for every entry whose trigger is expected to fire.

- `README.md` [Public-API] — Public-facing overview and `tcw` CLI usage (install, commands, quickstart); plain, high-readability. Update when the public CLI surface or user-facing behavior changes.
- `docs/release-notes/upcoming.md` [Public-API] — User-facing release notes for the next version; plain language, no jargon or internal module names.
- `docs/changelogs/upcoming.md` [Any-Code-Change] — Developer changelog for the next version; technical, grouped (Added/Changed/Fixed/Removed/Internal), with commit hash ranges (`git rev-parse --short HEAD`).
