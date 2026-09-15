## Inbox manifest

- `2026-09-14-rewrite-the-readme-to-a-new-outline.md`

## Inbox body

# Rewrite the README to a new outline

## Desired outcome

`README.md` is completely rewritten to follow the outline below. The current
document structure is bad; this is a restructure, not a touch-up.

In the outline, list items are section headers, except items starting with
"note:", which describe the section's purpose and contents.

## Outline

```
- "TCW — Taxonomy · Capabilities · Work"
  - note: This is the foreward section; TCW summarized in one to two sentences
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
      - note: the Jira integraiton section should show exactly where it fits into the existing TCW work lifecycle
      - note: we should provide examples of the workflow if Jira integraiton is enabled
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
