# Set Up Documentation Sync

Read this when the project's `CLAUDE.md` has no `## Documentation Sync` section and the user wants to add one, or when you need to create tracked files that don't exist yet.

If the project's `CLAUDE.md` has no `## Documentation Sync` section, ask the user: "Would you like to set up a Documentation Sync section in your CLAUDE.md?"

If they agree, help them fill it out by asking:
1. **Which files** should be kept in sync with code changes? (e.g., README.md, CHANGELOG.md, guides)
2. **What trigger** applies to each file? Offer the base triggers from the "Trigger Reference" table in this skill's `SKILL.md` (`Public-API`, `Public-{Name}-API`, `Any-Code-Change`, `Only-Breaking`), and note that a project may define its own named trigger where none of those fit.
3. **What description** should guide how updates are written for each file?

Then add the section to their CLAUDE.md in the format shown under "The Documentation Sync Section" in `SKILL.md`. **Always include the opening directive line** that tells the agent to invoke the `documentation-sync` skill — without it, future sessions may see the file list but skip the trigger-evaluation logic.

## Create Tracked Files (and Folders) That Don't Yet Exist

After adding the section, create any tracked files — **and their parent directories** — that don't already exist so the agent has somewhere to write on the first trigger fire. Use the conventional initial content for each:

- **`docs/release-notes/` and `docs/changelogs/` directories**, each containing an `upcoming.md` file — create the directories if they don't exist; both `upcoming.md` files start with just a `# Upcoming` heading. Apply this only when the project's section lists the per-version structure (some projects use only GitHub Releases or a single root `CHANGELOG.md` — don't impose this layout if it isn't listed).
- **Other listed files** (e.g., guides, CLI docs) — only create stubs if the user explicitly asks; otherwise leave them for the user to author.

## Deferred follow-up work → track it as work items, not a doc

Some documentation-sync setups elsewhere include a standing `docs/FOLLOWUPS.md` log for code-related work deferred out of a task. **In a TCW project, don't add that file** — deferred follow-up work is tracked as first-class work items instead. When a task leaves code-related TODOs (post-migration cleanups, hardening skipped for scope, test-coverage gaps, deferred refactors), create a backlog item:

```
tcw work new "<deferred item>"
```

This keeps deferred work in the same board the rest of the project's work lives in, subject to the same lifecycle, rather than in a parallel markdown log. (Things that depend on a person doing something out-of-band — smoke tests, manual QA, stakeholder sign-off — don't belong in either place; they go in a PR description or a message to the relevant person.)

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Not creating the changelog file if it doesn't exist | If the file is listed in Documentation Sync, create it if missing |
| Omitting the opening directive line | The skill must be reloaded each session; the directive is what triggers that |
| Adding a `docs/FOLLOWUPS.md` log in a TCW project | Track deferred code work as `tcw work` backlog items instead |
