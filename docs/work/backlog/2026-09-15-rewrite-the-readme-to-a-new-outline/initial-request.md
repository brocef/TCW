# Rewrite the README to a new outline

## What is wanted

`README.md` is completely rewritten to follow the outline below. The requester
considers the current structure bad: this is a restructure, not a touch-up.

In the outline, list items are section headers, except items starting with
"note:", which describe that section's purpose and contents.

```
- "TCW — Taxonomy · Capabilities · Work"
  - note: This is the foreword section; TCW summarized in one to two sentences
  - note: Current table is fine, although we can drop the "Lives in" column
- Contents
  - note: Table of contents for the rest of the document
- Problem Statement
  - note: can keep the current content
- Installation
  - Plugin
  - CLI
  - Cloud Environment Instructions
    - note: mention Claude Code and Codex cloud environments as examples
- Overview
  - note: this section should be a brief overview of the plugin as a whole
- Taxonomy
  - Overview
  - Usage
    - Skills
    - CLI
- Capabilities
  - Overview
    - Relationship to Taxonomy
  - Usage
    - Skills
    - CLI
- Work
  - note: This is going to be a very big section *and that is okay* as it is the most important part of the repo
  - Overview
    - Relationship to Capabilities and Taxonomy
  - Lifecycle
    - note: This should have a mermaid diagram showing the lifecycle stages
    - Jira integration
      - note: the Jira integration section should show exactly where it fits into the existing TCW work lifecycle
      - note: we should provide examples of the workflow if Jira integration is enabled
  - Usage
    - Skills
    - CLI
- TCW Local Web App
  - note: This section should cover everything about the `tcw serve` local server
- Documentation
  - note: This section should be a mapping of topics to their respective documents
  - note: Current documentation sections are fine, but move "Configuration" to the top of the table
  - note: If there are documentation files not mentioned, add them to this table, and we can also create new documentation files and add references in this table if needed
- Development
  - note: This is the section on how to work on the TCW project itself
  - (I'll leave these sections up to you to decide, whatever is typical for an open source project)
  - note: We'll probably want to mention that tcw and skill-cefailures plugins are both enabled for this repo in `.claude/settings.json`
- Further Reading
```

## Decisions the requester made during the request stage

These answer questions the outline left open, and amend it where noted.

1. **Content outside the outline is dropped.** The current README's "What it
   looks like", "Why many repositories is the case it is built for", "What it
   deliberately refuses", "What adopting it costs", "Who it's for", "Storage
   abstraction (the prime directive)", "Quickstart" and "Status" sections are
   removed, not folded in or moved to another document. The outline is the
   whole README.
2. **Jira reference detail moves to a new guide.** The README's Jira
   integration section shows where Jira fits in the work lifecycle and gives
   example workflows. The full reference — configuration keys, settings
   inherited from parent nodes, claiming, `link`/`unlink`, `sync`, comments,
   strict mode, and the known limits — moves to a new document in `docs/guide/`
   (for example `docs/guide/jira.md`), listed in the Documentation table.
3. **"Overview" means TCW as a whole**, not only the agent plugin: how the three
   axes, the CLI, the agent plugin and `tcw serve` fit together.
4. **A new "Skills and Agents" section is added to the outline**, placed after
   the Work section and before "TCW Local Web App". It describes the skills and
   agents that do not belong to a single axis: `tcw-setup`, `tcw-configure`,
   `documentation-sync`, `tcw-work-stage`, the `tcw-commands-*` skills, the
   `tcw-extras-*` skills, and the read-only review agents. Each axis's
   "Usage > Skills" covers only that axis's own skills.
5. **The lifecycle diagram shows both stages and statuses**: the stages
   (inbox → request → spec → plan → implement → verify → postmortem) and the
   status folders an item moves through (backlog, active, review, completed,
   discarded), with the transitions between them.
6. **The Documentation table lists user-facing documents only** — guides,
   migration guides, release notes and similar. Files only a contributor to TCW
   would read (for example `docs/lifecycle/harness.md`,
   `docs/lifecycle/implementation.md`, `docs/plan/`, `docs/releasing.md`) are
   referred to from the Development section instead.

### Added during the spec stage (2026-09-15)

7. **The README summarizes `tcw serve` and links to `docs/guide/web-viewer.md`**
   for the detail, rather than copying all of it. This narrows the outline's
   "cover everything about the `tcw serve` local server", so the two documents
   cannot drift apart as full copies.
8. **`skill-cefailures` is removed from this repository.** The requester no
   longer uses it. Its entry comes out of `.claude/settings.json`, and
   Development says only that the `tcw` plugin is enabled for this repository.
   This replaces the outline note about mentioning both plugins.
9. **`docs/guide/jira.md` gets its own documentation entry** in
   `tcw-config.yaml`, so that a future tracker change is flagged to update it.
   The Jira section of `docs/guide/work.md` went out of date because no such
   entry existed.

## Out of scope

- Keeping any current section the outline does not name (decision 1).
- Changing TCW's behavior. This is a documentation change.

## Notes

- Reference material: asked; none provided beyond the outline and the
  repository itself.
- The current README's "Status" and "Storage abstraction" sections say Jira
  adapters and tracker synchronization are not built, while its own Jira section
  documents them as shipped. Dropping both sections (decision 1) removes that
  contradiction; the rewrite should not reintroduce the claim.
- Nothing in the repository links to a README section anchor (checked for
  `README.md#` across Markdown, Python, YAML, JSON and TypeScript files outside
  completed work items), so renaming headings breaks no in-repo link.
- `tcw-config.yaml` describes the README's documentation entry as a
  "public-facing overview and `tcw` CLI usage (install, commands, quickstart)".
  Dropping the quickstart may mean that description needs updating too.
- The backlog item `2026-08-12-separate-the-agent-plugin-from-the-python-cli-source`
  would move where the plugin's skills live. If it lands first, skill paths
  linked from the README change; if this lands first, that item must update
  them.
