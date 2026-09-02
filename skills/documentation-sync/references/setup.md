# Set Up Documentation Sync

Read this when a project declares no documentation entries and the user wants to add some, or when you need to create tracked files that don't exist yet.

## Two forms — prefer config in a TCW project

**Recommended, in a TCW node:** declare the entries in `tcw-config.yaml` under `work.documentation`. `tcw validate` checks their shape, `tcw work docs` prints them, and `tcw work stage begin plan` / `tcw work stage begin implement` include them inline — so the gate does not depend on an agent remembering to open a file and parse prose.

```yaml
# tcw-config.yaml
work:
    documentation:
        - path: README.md
          trigger: Public-API
          description: >-
              Public-facing overview and CLI usage. Update when the public
              surface or user-facing behavior changes.
        - path: docs/changelogs/upcoming.md
          trigger: Any-Code-Change
          description: Developer changelog; technical, grouped by category.
```

Three required keys per entry, all non-empty strings. `path` need not exist yet — an entry naming a file the project intends to create is correct, and a placeholder like `skills/<component>/SKILL.md` is legal. `trigger` may be any project-defined name; only whitespace in it is rejected.

The same `path` may appear in **several entries with different triggers** — an entry is identified by the `(path, trigger)` pair, not by the file alone. That is how a file large enough for its sections to answer to different changes is declared: one `README.md` entry under `Public-CLI-API`, another under `Validation-Rules`. Only two entries agreeing on *both* path and trigger are rejected as duplicates.

**Fallback, and the only option outside a TCW node:** a `## Documentation Sync` section in the project's `CLAUDE.md`. Nothing validates it, and the entries are found by matching the heading — rename it and the gate silently stops working.

Ask the user: "Would you like to set up documentation entries?" and which form they want.

If they agree, help them fill it out by asking:

1. **Which files** should be kept in sync with code changes? (e.g., README.md, CHANGELOG.md, guides)
2. **What trigger** applies to each file? Offer the base triggers from the "Trigger Reference" table in this skill's `SKILL.md` (`Public-API`, `Public-{Name}-API`, `Any-Code-Change`, `Only-Breaking`), and note that a project may define its own named trigger where none of those fit.
3. **What description** should guide how updates are written for each file?

Then write the entries in the chosen form. For the config form, add the `work.documentation` block and run `tcw validate` to confirm it parses. For the Markdown form, add the section to their CLAUDE.md in the format shown under "The Documentation Sync Section" in `SKILL.md`, and **always include the opening directive line** that tells the agent to invoke the `documentation-sync` skill — without it, future sessions may see the file list but skip the trigger-evaluation logic. (The config form needs no such directive: `tcw work stage` puts the entries in front of the agent itself.)

## Create Tracked Files (and Folders) That Don't Yet Exist

After adding the section, create any tracked files — **and their parent directories** — that don't already exist so the agent has somewhere to write on the first trigger fire. Use the conventional initial content for each:

- **`docs/release-notes/` and `docs/changelogs/` directories**, each containing an `upcoming.md` file — create the directories if they don't exist; both `upcoming.md` files start with just a `# Upcoming` heading. Apply this only when the project's entries list the per-version structure (some projects use only GitHub Releases or a single root `CHANGELOG.md` — don't impose this layout if it isn't listed).
- **Other listed files** (e.g., guides, CLI docs) — only create stubs if the user explicitly asks; otherwise leave them for the user to author.

## Deferred follow-up work → track it as work items, not a doc

Some documentation-sync setups elsewhere include a standing `docs/FOLLOWUPS.md` log for code-related work deferred out of a task. **In a TCW project, don't add that file** — deferred follow-up work is tracked as first-class work items instead. When a task leaves code-related TODOs (post-migration cleanups, hardening skipped for scope, test-coverage gaps, deferred refactors), create a backlog item:

```
tcw work new "<deferred item>"
```

This keeps deferred work in the same board the rest of the project's work lives in, subject to the same lifecycle, rather than in a parallel markdown log. (Things that depend on a person doing something out-of-band — smoke tests, manual QA, stakeholder sign-off — don't belong in either place; they go in a PR description or a message to the relevant person.)

## Common Mistakes

| Mistake                                             | Fix                                                                          |
| --------------------------------------------------- | ---------------------------------------------------------------------------- |
| Not creating the changelog file if it doesn't exist | If the file is listed in Documentation Sync, create it if missing            |
| Omitting the opening directive line                 | The skill must be reloaded each session; the directive is what triggers that |
| Adding a `docs/FOLLOWUPS.md` log in a TCW project   | Track deferred code work as `tcw work` backlog items instead                 |
