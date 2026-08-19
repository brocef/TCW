---
name: documentation-sync
description: Use when completing a coding task and deciding whether documentation needs updating. Use when code changes have been made and you need to check if README, changelog, guides, or other docs should reflect those changes. Use when a project declares documentation entries — in `tcw-config.yaml` under `work.documentation`, or as a `## Documentation Sync` section in its CLAUDE.md. Use after completing development work to update release notes and changelogs. Use when offering to cut a new version of a project.
---

# Documentation Sync

After completing code changes, get the project's documentation entries and evaluate each one's trigger before reporting the task complete.

**Ask `tcw work docs --json` first.** It returns `{"schema", "source", "entries"}`, and `source` tells you which world you are in without guessing:

- `"config"` — the entries are declared in `tcw-config.yaml` under `work.documentation`, validated by `tcw validate`, and the `entries` array is authoritative. Use it and read no Markdown.
- `"agent-guide"` — the project has declared nothing, so fall back to the legacy convention: a `## Documentation Sync` section in the project's `CLAUDE.md` / `AGENTS.md`, holding a bullet list of `- path [Trigger] — description`.

Outside a TCW node the command does not exist; use the legacy convention directly. If neither is present, ask the user whether to add entries — read `references/setup.md` to walk them through it.

This is a cross-cutting process skill: it does not drive a `tcw` axis, it governs when docs must move with code. In a TCW project the `tcw-work` lifecycle invokes it at three points:

| Lifecycle point        | What this skill does                                                                                                                                                                                       | Reference                                           |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| **`plan`**             | Predict which triggers will fire and name a doc task for each — scheduled as one block at the _end_ of the plan.                                                                                           | `tcw-work` → `references/stage-plan.md` step 4      |
| **End of `implement`** | The documentation gate. Once every plan task is done and the suite is green, make **one** pass over the finished diff, answer every fired trigger, and commit the doc updates before writing `outcome.md`. | `tcw-work` → `references/stage-implement.md` step 6 |
| **After `complete`**   | Offer the version options; run the cut if the user picks a bump.                                                                                                                                           | `tcw-work` → `references/stage-verify.md` step 9    |

One pass at the end, not per-task: docs written mid-implementation describe a shape the change no longer has by the time it lands. `verify` then reviews code and docs together instead of accepting a diff whose docs are still pending.

## The Documentation Sync Section

Project owners add this section to their `CLAUDE.md`:

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

## Evaluating Triggers

### Trigger Reference

| Trigger             | Fires When                                                                                                                                                                                                                                                                   | Example                                                                                                   |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `Public-API`        | Exported APIs, schemas, types, or public interfaces change — **excluding** any area covered by a more specific `Public-{Name}-API` entry in the same section                                                                                                                 | Renamed a function parameter, added a new export                                                          |
| `Public-{Name}-API` | Public interfaces change for a specific area of the codebase. `{Name}` is a descriptive label (not necessarily an exact folder path) that unambiguously identifies the area.                                                                                                 | `Public-CLI-API` fires when CLI flags/behavior change; `Public-Auth-API` fires when auth endpoints change |
| `Any-Code-Change`   | A **behavior-affecting** code change — anything that alters runtime behavior, build output, or visible API surface. **Does not fire** for cosmetic-only edits (formatting, whitespace, comments, lint autofixes, test-fixture rearrangement that doesn't change assertions). | Internal refactor, dependency bump that changes behavior, bugfix                                          |
| `Only-Breaking`     | Reverse-incompatible changes are introduced                                                                                                                                                                                                                                  | Removed a parameter, changed return type, dropped support                                                 |

**Partition rule for `Public-API` and `Public-{Name}-API`:** When a project declares both, the named entries carve their areas out of the generic `Public-API`. A CLI flag change fires `Public-CLI-API` only, not both. If no named entry covers the change, fall back to `Public-API`.

**Projects may define additional named triggers.** The four triggers above are a base vocabulary, not a closed set. A project can add its own bracketed trigger, defined by the entry's description, when none of the four fit. Read the definition where it's used and apply it literally. TCW's own entries, for example, define `[Skill-Driven-Component]` — "always update the matching driving skill (`tcw-work`, `tcw-capabilities`, …) whenever the component it drives changes: its CLI surface, model/fields, lifecycle, or guardrails" — a trigger that doesn't fit the `Public-{Name}-API` shape. Treat any such project-defined trigger as authoritative for that project.

**Public-surface judgment call:** A symbol may be technically exported (e.g., re-exported by a barrel file) but have no documented public consumer — no mention in README, no entry in changelogs, no external callers visible. Renaming such a symbol is a fuzzy case: it triggers `Public-API` literally, but the user-facing impact is zero. **Ask the user** before treating these as Public-API rather than auto-updating public docs for a change nobody outside the codebase will notice.

### How to Evaluate

For each of the project's documentation entries (`tcw work docs`, or the agent guide's `## Documentation Sync` section when `source` is `agent-guide`):

1. **Read the trigger** in brackets
2. **Assess your code changes** against the trigger definition
3. **If the trigger fires**, update the file according to its description
4. **If the trigger does NOT fire**, skip the file

Be precise: an internal refactor does NOT fire `Public-API`. A new optional parameter does NOT fire `Only-Breaking`. Match the trigger definition exactly.

### Including Doc Updates in Implementation Plans

Whenever you write an implementation plan for a project that has a `## Documentation Sync` section, surface doc-update work in the plan — do not leave it as an implicit follow-up. In a TCW project this is the **plan-gate** invocation: the predicted doc tasks belong in `plan.md`.

Pick one of two paths based on how concrete the planned scope is:

- **Concrete scope (feature, bugfix, well-defined refactor):** For each entry whose trigger you can confidently predict will fire, add a task that names the file (e.g., "Update `README.md` for the new `--verbose` flag").
- **Exploratory scope (investigation, "let's see what breaks," large refactors with unknown public-surface impact):** Add a single "Re-evaluate Documentation Sync triggers after implementation" task at the end of the plan rather than guessing per-file. Predicting per-file in this mode produces a misleading plan.

The point is to keep doc work visible — either as named-file tasks upfront, or as one explicit re-evaluation gate. Either is fine; an unmentioned doc update is what isn't.

## Companion references (read on demand)

These workflows are deeper than the core trigger-evaluation loop and live as references so they only load when actually needed:

| Reference                                    | Load when                                                                                                                                                                                                        |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `references/release-notes-and-changelogs.md` | The project uses the opt-in `docs/release-notes/` + `docs/changelogs/` structure AND you're writing entries, rotating `upcoming.md`, running the version cross-check, or migrating an existing `CHANGELOG.md`.   |
| `references/setup.md`                        | The project's `CLAUDE.md` has no `## Documentation Sync` section and the user wants to add one, or you need to create tracked files that don't exist yet.                                                        |
| `references/cut-version.md`                  | The user picked a `patch`/`minor`/`major` bump from the completion options below and you're running the version cut — choosing the bump size, bumping every version-bearing file, rotating, committing, tagging. |

## When to offer version and changelog options

After a substantial set of changes has settled — a feature, a bug fix, a refactor, a docs sweep, or any combination the user clearly considers "done" — present the user with these four options:

1. Major version bump
2. Minor version bump
3. Patch version bump
4. Keep the current version and update the applicable changelog files

"Changelog files" means the release-note and developer-changelog working files among the project's documentation entries (`tcw work docs`, or its `## Documentation Sync` section when `source` is `agent-guide`), such as `docs/release-notes/upcoming.md` and `docs/changelogs/upcoming.md`. Update only the files whose triggers fire.

**A fifth option appears only when the last version was cut but never published.** Before presenting the list, run this skill's gate script from inside the repo:

```bash
scripts/unpushed-version.sh          # optional arg: tag glob, default 'v*'
```

Read the **exit code**, not the prose: `0` foldable · `1` not foldable (no tag, already published, or nothing since it) · `2` the remote was unreachable — ask the user rather than guessing. It prints one `STATUS:` line and, when foldable, the tag and the commits that would join it.

On `0`, that release exists nowhere but this machine, so the work since it can still join it. Offer:

5. Fold the changes since `{tag}` into `{tag}` itself — re-dating the release rather than cutting a second one on top of it

Read `references/cut-version.md` → "Folding into an unpushed version" to run it. Don't offer the fold when the intervening work is larger than the version it would be folded into can honestly carry — a feature folded into a patch is a mislabeled release; recommend a fresh bump instead. Never fold into a published tag: rewriting a tag other people may have fetched is off the table, which is what the gate exists to prevent. That judgment is yours; the script only answers _whether the tag is still local_.

Don't offer mid-flow, and don't offer for trivial in-isolation edits. Don't change the version unless the user selects `major`, `minor`, or `patch`. For those three choices, read `references/cut-version.md` — it starts by deferring to **the project's own version-cut process** (every project bumps differently; its `CLAUDE.md` / Versioning section names the files and the script) and falls back to the manual ritual only when the project has none. For the keep-current-version choice, leave version-bearing metadata, tags, and working-file names unchanged and update the applicable changelog files in place.

## Common Mistakes

These are trigger-evaluation slips. Mistakes specific to release-notes/changelog work live in `references/release-notes-and-changelogs.md`.

| Mistake                                                      | Fix                                                                                          |
| ------------------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| Skipping doc updates under time pressure                     | Triggers are objective — evaluate them regardless of urgency                                 |
| Treating `{Name}` in `Public-{Name}-API` as an exact path    | It's a descriptive label — `Public-CLI-API` could refer to `src/cli/`, `lib/commands/`, etc. |
| Hardcoding one project's version-cut command into this skill | Defer to the project's own Versioning section; this skill stays portable                     |
