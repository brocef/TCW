---
name: documentation-sync
description: Use when completing a coding task and deciding whether documentation needs updating. Use when code changes have been made and you need to check if README, changelog, guides, or other docs should reflect those changes. Use when a project has documentation entries — from `tcw work docs`, or a `## Documentation Sync` section in its CLAUDE.md — and a change may have fired one. Use after completing development work to update release notes and changelogs. Use when offering to cut a new version of a project.
allowed-tools: Bash(tcw *), Bash(cat *)
dynamic_skill: true # which skills a project may override, and why: ../README.md
---

# Documentation Sync

After completing code changes, get the project's documentation entries and evaluate each one's trigger before reporting the task complete.

**Ask `tcw work docs --json` first.** It returns `{"schema", "source", "entries"}`, and `source` tells you which world you are in without guessing:

- `"config"` — the entries are declared in `tcw-config.yaml` under `work.documentation`, validated by `tcw validate`, and the `entries` array is authoritative. Use it and read no Markdown.
- `"agent-guide"` — the project has declared nothing, so fall back to the legacy convention: a `## Documentation Sync` section in the project's `CLAUDE.md` / `AGENTS.md`, holding a bullet list of `- path [Trigger] — description`.

Outside a TCW node the command does not exist; use the legacy convention directly. If neither is present, ask the user whether to add entries — read the `tcw-configure` skill's `docs-sync.md` to walk them through it.

This is a cross-cutting process skill: it does not drive a `tcw` axis, it governs when docs must move with code. In a TCW project the `tcw-work` lifecycle invokes it at three points:

| Lifecycle point        | What this skill does                                                                                                                                                                                       | Reference                                                     |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| **`plan`**             | Predict which triggers will fire and name a doc task for each — scheduled as one block at the _end_ of the plan.                                                                                           | `tcw-work` → `references/lifecycle/stage-plan.md` step 1      |
| **End of `implement`** | The documentation gate. Once every plan task is done and the suite is green, make **one** pass over the finished diff, answer every fired trigger, and commit the doc updates before writing `outcome.md`. | `tcw-work` → `references/lifecycle/stage-implement.md` step 3 |
| **After `complete`**   | Offer the version options; run the cut if the user picks a bump.                                                                                                                                           | `tcw-work` → `references/lifecycle/stage-verify.md` step 5    |

One pass at the end, not per-task: docs written mid-implementation describe a shape the change no longer has by the time it lands. `verify` then reviews code and docs together instead of accepting a diff whose docs are still pending.

## The Documentation Sync Section — the fallback form

This is the **fallback**, not the recommended form. In a TCW node, declare the entries in `tcw-config.yaml` under `work.documentation` instead: `tcw validate` checks their shape, `tcw work docs` prints them, and `tcw work stage prompt plan` / `implement` put them in front of the agent directly, so the gate does not depend on anyone remembering to open a file and parse prose. The `tcw-configure` skill's `docs-sync.md` walks through both forms.

Use the section below when the project is **not** a TCW node, or when the user prefers Markdown. Project owners add it to their `CLAUDE.md`:

```markdown
## Documentation Sync

Before reporting any code change complete, invoke the `documentation-sync` skill to evaluate the entries below. When writing an implementation plan, include explicit documentation-update tasks for every entry whose trigger is expected to fire.

- `README.md` [Public-API] — Public consumption, high-level, written for maximum human readability
- `docs/changelogs/upcoming.md` [Any-Code-Change] — Developer changelog; technical, grouped by category
- `CLI_GUIDE.md` [Public-CLI-API] — Updated when CLI behavior changes
- `docs/api.md` [Only-Breaking] — Only updated for breaking changes
```

The opening directive is a hint: it tells the agent to invoke this skill before reporting code-change work complete. It is not a hard guarantee — sessions that don't touch code can ignore it. But for any session that does change code, the directive is what surfaces the trigger-evaluation step instead of letting it slip.

Each entry has three parts:

1. **File path** — the document to potentially update
2. **Trigger** (in brackets) — when this file needs updating
3. **Description** — what the file is for and how to write updates for it

!`tcw work procedure prompt documentation-sync 2>/dev/null || cat "${CLAUDE_PLUGIN_ROOT}/tcw/work/procedures/documentation-sync.md" || true`

## Document command summary

The commands below are automatically executed by the Claude Code harness, and
their output is the rest of this procedure: evaluating triggers, planning doc
tasks, and offering a version.

```sh
# Get the procedure, composed with this project's text
tcw work procedure prompt documentation-sync
# Only if that command fails (not a TCW node, or no tcw CLI): TCW's own text
cat <plugin>/tcw/work/procedures/documentation-sync.md
```

If your harness did not run them, run them yourself and follow the output in
place of the line above. `references/` in that output means this skill's
`references/` folder. Where the entries come from, and the lifecycle points
above, still apply whatever that output says.
