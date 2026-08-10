# Consolidating external plans

Find planning documents that live outside the TCW work system, migrate them into
work items, and remove the old documents only after the migration succeeds. This
is an AI-driven migration workflow, not a `tcw` subcommand — there is no `tcw
work consolidate-plans`. Claude users can reach it as `/tcw-consolidate-plans`;
under any harness, this document is the procedure.

## The two rules, before any step

**Start only when asked.** Do not begin a consolidation run on your own
initiative — not while doing adjacent work in `docs/`, not as a tidy-up pass, not
because you noticed a stray `plans/` folder. The user asks for it, or it does not
run.

**Never delete a source without a grouped, itemized approval.** Present every
document proposed for deletion by path, with its destination slug, as **one** ask
covering the whole run. Not one ask per file — that is unusable on a real run —
and not a blanket "may I clean up?", which is a yes to decisions the user has not
seen. Deletion happens after the answer, never before.

## Deletion is limited to what git can give back

Delete only files git has **already committed**, and only with `git rm`. A source
that is untracked, or tracked with uncommitted modifications, is **reported and
left in place**: its content exists nowhere else, so removing it is
unrecoverable. Two checks decide it, and anyone can re-run them:

| Check                                 | Meaning                                                                             |
| ------------------------------------- | ----------------------------------------------------------------------------------- |
| `git ls-files --error-unmatch <path>` | exit 0 → tracked; non-zero → untracked, do not delete                               |
| `git status --porcelain <path>`       | empty → committed as-is, deletable; any output → uncommitted changes, do not delete |

Report the skipped files with the reason. Committing someone else's stray file
just to make it deletable is not your call.

## Scope

Input may be one or more folders/files to search, or nothing. If the user gives
paths, search only those paths. If no paths are given, search sensible local
planning locations such as `docs/`, `plans/`, and `planning/`, excluding
`docs/work/`, generated folders, dependency folders, and VCS/tool caches.

## Process

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
7. Only then ask for the grouped deletion approval above, and delete approved
   sources that pass both git checks with `git rm`.

Keep the migration conservative. If a source document is ambiguous, do not delete
it; report what clarification or follow-up is needed.
