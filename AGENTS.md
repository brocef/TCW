# TCW — agent working guide

**TCW** (Taxonomy · Capabilities · Work) is a storage-abstracted framework for describing and evolving a software project along three axes, exposed through one CLI, `tcw`, with three subcommand groups (`tcw taxonomy | capabilities | work`). This guide governs all work in this repo.

- **Live status & pending work:** `tcw work` — this repo dogfoods its own work component (`docs/work/`); the historical build-phase tracker is retired.

## Generic instructions

- Git commit messages should not include any co-authoring content.

## Prime directive: the abstraction litmus test

TCW ships a filesystem-native default, but the **model is storage-abstracted** so it can run against an external tracker (Jira, a wiki, a graph DB) where one is already in use. That portability is the whole reason the system is viable at enterprise scale — do not trade it away for filesystem cleverness. Before adding or changing any operation, apply this test:

> **"Could a non-filesystem store implement this operation, even if less elegantly?"**
>
> - **Yes** → it belongs in the model / the abstract store interface.
> - **No** — it only works as a filesystem trick with no abstract analog → push it into the filesystem adapter as a private detail, or redesign it.

## Abstract spine, filesystem leverage

Express behavior in the abstract vocabulary — **item · status · transition · stable ID · reference · node relation · query · body/fields/attachments** — and let the filesystem _realize_ it. Filesystem superpowers are bonuses layered on top, never load-bearing assumptions of the model.

- **Leverage freely (bonuses):** docs co-located with code (one repo / worktree / PR / diff); one atomic commit carrying code change + status/capability change together; grep/diff/PR-review legibility; atomic `mv` as transition.
- **Keep out of the model (no abstract analog):**
    - Reconstructing current state from git history — _state is the status; git is archive._
    - Globbing a store folder as an open namespace — _bound it: body + named fields + named attachments._
    - Hard-coded paths in references — _use stable IDs / paths-within-the-store; resolve through the store._
    - Parent/child as literal directory ancestry outside the node-resolution layer — _express the relation abstractly; the FS adapter derives it from nesting._
    - Worktrees and `rg`/`find` queries — _filesystem-adapter local details, not store-interface operations._

## Work Planning and Implementation

**All work in this repository should be tracked by the `tcw work` system!**

When planning work, the spec document and implementation plan _must_ be placed inside the corresponding work item folder.

After planning concludes, and implementation is about to begin, use `tcw work start {work-item-slug}` to move it to the active status. This status transition should be the first implementation commit.

## Implementation rules

- Each component depends on an abstract **store interface** (`TaxonomyStore`, `WorkStore`, …) that the CLI and any skills talk to. Ship the **filesystem adapters** (`FsTaxonomyStore`, `FsWorkStore`) only; keep remote adapters (e.g. `JiraWorkStore`) possible but unbuilt. Never add an interface method that only the FS adapter could honor (run the litmus test first).
- The three components are **one system**: taxonomy is the nouns, capabilities the user stories (what a user can do), work the changes (to capabilities, machinery, or the project itself). They link by loose, one-directional pointers (capability→term, work→capability/term) and never duplicate each other.
- Python with type hints; pytest over `tmp_path` git repos. Use the ABC + adapter pattern for stores; extract the shared tree-store core only once two components are real (don't pre-abstract).
- **Skill authoring (progressive disclosure):** a `skills/<name>/SKILL.md` is a **thin router** — keep always-relevant judgment inline (the core lifecycle, the gates) and push genuinely rare sub-procedures into `skills/<name>/references/*.md` read on demand, each reached by a clear gate condition in the router (the `tcw-plugin` and `tcw-work` skills are the pattern). Only split once a skill's conditional detail is large enough to earn the indirection — for ~50-line, mostly-always-relevant skills it's a no-op; leave them inline.

## Harness compatibility (Claude and Codex)

TCW ships to **both** Claude Code and Codex, and their plugin standards differ: Claude's system is far richer, while Codex follows the [Agentskills specification](https://agentskills.io/specification.md). Both are first-class targets — a task a Claude user can accomplish, a Codex user must also be able to accomplish.

**Claude-only features are welcome as _enhancements_, never as the sole carrier of a requirement.** Dynamic context injection (`` !`cmd` ``), skill/command arguments, and hooks are Claude-only; their syntax is inert in Codex rather than fatal, so using them does not break a skill. That makes them safe to reach for — but only for ergonomics.

**Subagents are _not_ Claude-only.** Codex has them too — TOML agent definitions in `.codex/agents/`, model-driven spawning, parallel execution capped by `[agents] max_concurrent_threads_per_session` — and it "respects applicable `AGENTS.md` or skill instructions that request delegation" ([docs](https://learn.chatgpt.com/docs/agent-configuration/subagents)). So a skill may instruct delegation directly without a single-session fallback. The `agents/` **directory** is still Claude-specific packaging, which keeps the usual rule intact: a custom agent is an accelerator, and the skill document it accelerates must stand alone.

The rule that follows: **anything that must be guaranteed belongs in the `tcw` CLI**, which behaves identically under both harnesses. If a behavior only happens because Claude injected a line of context or fired a hook, a Codex user does not get it. Ask of every mechanism: _what does a Codex agent see here, and can it still finish the job?_ If the answer is no, the requirement is in the wrong layer.

Codex has no slash commands, so anything reachable via `commands/` must also be reachable by invoking the skill directly (the `tcw-plugin` skill is the existing pattern).

## Documentation Sync

Before reporting any code change complete, invoke the `documentation-sync` skill to evaluate the entries below. When writing an implementation plan, include explicit documentation-update tasks for every entry whose trigger is expected to fire.

- `README.md` [Public-API] — Public-facing overview and `tcw` CLI usage (install, commands, quickstart); plain, high-readability. Update when the public CLI surface or user-facing behavior changes.
- `docs/release-notes/upcoming.md` [Public-API] — User-facing release notes for the next version; plain language, no jargon or internal module names.
- `docs/changelogs/upcoming.md` [Any-Code-Change] — Developer changelog for the next version; technical, grouped (Added/Changed/Fixed/Removed/Internal).
- `skills/<component>/SKILL.md` [Skill-Driven-Component] — The driving skills (`tcw-work`, `tcw-capabilities`, …) that teach agents to operate each component through its CLI. Always update the matching skill whenever the component it drives changes — its CLI surface, model/fields, lifecycle, or guardrails — so the skill never drifts from the tool.

## Versioning

The version string is **duplicated across 5 files** — a release bumps _all_ of them in lockstep, not just `pyproject.toml`. Keep them identical. `tests/test_plugin_manifests.py` guards that they agree.

**Cut a release with `python scripts/cut_version.py <patch|minor|major|X.Y.Z>`** — it bumps all 5 files, rotates `docs/{changelogs,release-notes}/upcoming.md` → `v{version}.md` (recreating fresh `upcoming.md`), commits, and tags. It aborts on version drift; it does **not** push (publishing stays a human step). Write the changelog/release-note entries into `upcoming.md` _before_ running it. The 5 files:

1. `pyproject.toml` — `project.version`
2. `tcw/__init__.py` — `__version__`
3. `.claude-plugin/plugin.json` — `version`
4. `.claude-plugin/marketplace.json` — `plugins[0].version`
5. `.codex-plugin/plugin.json` — `version`

(`.agents/plugins/marketplace.json` deliberately carries **no** version — don't add one.)
