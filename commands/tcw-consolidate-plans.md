---
description: Find planning documents outside TCW work, migrate them into TCW work items, and remove the old documents after successful migration.
disable-model-invocation: true
---

Use the `tcw-work` skill. This is an AI-driven migration workflow, not a `tcw`
CLI subcommand.

Goal: examine planning documents that are not already in the TCW work system,
turn them into TCW work items with lifecycle artifacts, and delete the old
documents only after the new work items exist.

Input may be one or more folders/files to search, or no input. If the user gives
paths, search only those paths. If no paths are given, search sensible local
planning locations such as `docs/`, `plans/`, and `planning/`, excluding
`docs/work/`, generated folders, dependency folders, and VCS/tool caches.

Process:

1. Identify likely planning documents using filename, heading, and content cues
   such as plan, spec, proposal, roadmap, todo, followup, or implementation.
2. For each candidate, inspect the document and decide whether it is:
    - a real planning artifact that should become TCW work;
    - obsolete/no-op material that should be reported before deletion;
    - already represented by an existing TCW work item.
3. For each document that should migrate, create a backlog item with
   `tcw work new "<title>"`.
4. Write `initial-request.md` in the new item folder from the source document
   and source provenance.
5. If the source already has clear spec or plan sections, write `spec.md` and/or
   `plan.md`; otherwise leave those stages for normal TCW planning.
6. Report a source-to-slug mapping for every migrated document.
7. Delete the old source document only after its TCW item and artifacts have been
   written and verified. Use `git rm` for tracked files.

Keep the migration conservative. If a source document is ambiguous, do not delete
it; report what clarification or follow-up is needed.
