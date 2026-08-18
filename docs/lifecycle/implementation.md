<!-- Bound to the `implement` stage of `tcw work`; see `tcw-config.yaml`.
     Read as a continuation of TCW's built-in stage instructions, not on its own. -->

# Implementation rules

_Applies at `implement`. The design rules that govern what you build are in
[`abstraction.md`](abstraction.md), bound at `spec` and `plan`._

- Each component depends on an abstract **store interface** (`TaxonomyStore`, `WorkStore`, …) that the CLI and any skills talk to. Ship the **filesystem adapters** (`FsTaxonomyStore`, `FsWorkStore`) only; keep remote adapters (e.g. `JiraWorkStore`) possible but unbuilt. Never add an interface method that only the FS adapter could honor (run the litmus test first).
- The three components are **one system**: taxonomy is the nouns, capabilities the user stories (what a user can do), work the changes (to capabilities, machinery, or the project itself). They link by loose, one-directional pointers (capability→term, work→capability/term) and never duplicate each other.
- Python with type hints; pytest over `tmp_path` git repos. Use the ABC + adapter pattern for stores; extract the shared tree-store core only once two components are real (don't pre-abstract).
- **Skill authoring (progressive disclosure):** a `skills/<name>/SKILL.md` is a **thin router** — keep always-relevant judgment inline (the core lifecycle, the gates) and push genuinely rare sub-procedures into `skills/<name>/references/*.md` read on demand, each reached by a clear gate condition in the router (the `tcw-plugin` and `tcw-work` skills are the pattern). Only split once a skill's conditional detail is large enough to earn the indirection — for ~50-line, mostly-always-relevant skills it's a no-op; leave them inline.

## Beginning implementation

After planning concludes, and implementation is about to begin, use `tcw work start {work-item-slug}` to move it to the active status. This status transition should be the first implementation commit.

## Before reporting complete

Evaluate the Documentation Sync entries in [`../../AGENTS.md`](../../AGENTS.md)
by invoking the `documentation-sync` skill. That section stays in `AGENTS.md`
rather than moving here: the skill locates it by name in `CLAUDE.md`, so a copy
in this file would be a second copy, not a move.
