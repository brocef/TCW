# TCW — agent working guide

**TCW** (Taxonomy · Capabilities · Work) is a storage-abstracted framework for describing and evolving a software project along three axes, exposed through one CLI, `tcw`, with three subcommand groups (`tcw taxonomy | capabilities | work`). This guide governs all work in this repo.

- **Framing, roadmap, and bootstrap checklist:** [`docs/PLAN.md`](docs/PLAN.md).
- **Component designs (source of truth):** [`docs/specs/`](docs/specs/) — `2026-06-18-taxonomy-design.md`, `2026-06-18-work-sdlc-design.md`. Read the relevant spec before changing a component's model; if a change diverges from the spec, update the spec in the same change — never let code and design drift.

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
- The three components are **one system**: taxonomy is the nouns, capabilities the behaviors, work the verbs. They link by loose, one-directional pointers (capability→term, work→capability/term) and never duplicate each other.
- Python with type hints; pytest over `tmp_path` git repos. Use the ABC + adapter pattern for stores; extract the shared tree-store core only once two components are real (don't pre-abstract).
