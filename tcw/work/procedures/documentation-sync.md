## Evaluating Triggers

### Trigger Reference

| Trigger             | Fires When                                                                                                                                                                                                                                                                   | Example                                                                                                   |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `Public-API`        | Exported APIs, schemas, types, or public interfaces change — **excluding** any area covered by a more specific `Public-{Name}-API` entry in the same section                                                                                                                 | Renamed a function parameter, added a new export                                                          |
| `Public-{Name}-API` | Public interfaces change for a specific area of the codebase. `{Name}` is a descriptive label (not necessarily an exact folder path) that unambiguously identifies the area.                                                                                                 | `Public-CLI-API` fires when CLI flags/behavior change; `Public-Auth-API` fires when auth endpoints change |
| `Any-Code-Change`   | A **behavior-affecting** code change — anything that alters runtime behavior, build output, or visible API surface. **Does not fire** for cosmetic-only edits (formatting, whitespace, comments, lint autofixes, test-fixture rearrangement that doesn't change assertions). | Internal refactor, dependency bump that changes behavior, bugfix                                          |
| `Only-Breaking`     | Reverse-incompatible changes are introduced                                                                                                                                                                                                                                  | Removed a parameter, changed return type, dropped support                                                 |

**Partition rule for `Public-API` and `Public-{Name}-API`:** When a project declares both, the named entries carve their areas out of the generic `Public-API`. A CLI flag change fires `Public-CLI-API` only, not both. If no named entry covers the change, fall back to `Public-API`.

**Projects may define additional named triggers.** The four triggers above are a base vocabulary, not a closed set. A project can add its own bracketed trigger, defined by the entry's description, when none of the four fit. Read the definition where it's used and apply it literally. TCW's own entries, for example, define `[Skill-Driven-Component]` — "always update the matching driving skill (`work`, `capabilities`, …) whenever the component it drives changes: its CLI surface, model/fields, lifecycle, or guardrails" — a trigger that doesn't fit the `Public-{Name}-API` shape. Treat any such project-defined trigger as authoritative for that project.

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
| the `configure` skill's `docs-sync.md`   | The project's `CLAUDE.md` has no `## Documentation Sync` section and the user wants to add one, or you need to create tracked files that don't exist yet.                                                        |
| `references/cut-version.md`                  | The user asked to cut a version and you're running it — choosing the bump size, bumping every version-bearing file, rotating, committing, tagging. See "When the user asks to cut a version" below. |

## When the user asks to cut a version

A version cut happens because the user asked for one. Nothing here volunteers
it, and a finished change is not a reason to raise it.

When they do ask, first settle **whether this is a new version at all**. Run
this skill's gate script from inside the repo:

```bash
scripts/unpushed-version.sh          # optional arg: tag glob, default 'v*'
```

Read the **exit code**, not the prose: `0` foldable · `1` not foldable (no tag,
already published, or nothing since it) · `2` the remote was unreachable — ask
the user rather than guessing. It prints one `STATUS:` line and, when foldable,
the tag and the commits that would join it.

On `0` the last release exists nowhere but this machine, so the work since it
can still join it rather than becoming a second release stacked on top. Say so,
and let the user choose between folding and a fresh bump — read
`references/cut-version.md` → "Folding into an unpushed version" to run the
fold. Don't propose the fold when the intervening work is larger than the
version it would join can honestly carry; a feature folded into a patch is a
mislabeled release, so recommend a fresh bump instead. Never fold into a
published tag: rewriting a tag other people may have fetched is off the table,
which is what the gate exists to prevent. That judgment is yours; the script
only answers _whether the tag is still local_.

For a fresh bump, the user's `major` / `minor` / `patch` choice drives it. Read
`references/cut-version.md` — it starts by deferring to **the project's own
version-cut process** (every project bumps differently; its `CLAUDE.md` /
Versioning section names the files and the script) and falls back to the manual
ritual only when the project has none.

Updating the changelog files is **not** part of a version cut and does not wait
for one. The release-note and developer-changelog working files among the
project's documentation entries (`tcw work docs`, or its `## Documentation Sync`
section when `source` is `agent-guide`) — such as `docs/release-notes/upcoming.md`
and `docs/changelogs/upcoming.md` — are answered by the documentation gate at
the end of `implement`, like any other entry whose trigger fired. Work
accumulates there until a cut is asked for.

## Common Mistakes

These are trigger-evaluation slips. Mistakes specific to release-notes/changelog work live in `references/release-notes-and-changelogs.md`.

| Mistake                                                      | Fix                                                                                          |
| ------------------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| Skipping doc updates under time pressure                     | Triggers are objective — evaluate them regardless of urgency                                 |
| Treating `{Name}` in `Public-{Name}-API` as an exact path    | It's a descriptive label — `Public-CLI-API` could refer to `src/cli/`, `lib/commands/`, etc. |
| Hardcoding one project's version-cut command into this skill | Defer to the project's own Versioning section; this skill stays portable                     |
