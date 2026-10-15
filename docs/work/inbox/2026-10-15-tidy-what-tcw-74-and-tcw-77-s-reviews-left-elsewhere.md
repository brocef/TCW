# Tidy what TCW-74's and TCW-77's reviews left elsewhere

Separate-change findings from the verify reviews of TCW-74 (stage prompts and
skills) and TCW-77 (web viewer), 2026-10-15. None blocks the epic.

## Viewer (`tcw serve`)

1. **Taxonomy and capability edits skip the stale check when no revision is
   sent.** `revision` is optional on PATCH (`tcw/serve/records.py`, the two
   update routes), so a hand-made request without it overwrites another
   writer's change. The 2.x server behaved the same.
2. **A symbolic link inside the work path lets a file save write outside the
   project.** Nothing checks that the resolved path stays inside the item
   folder. Editing with the CLI or an editor has the same exposure. Low.
3. **`_ANCHOR_CACHE` (`tcw/store/project.py`) now lives for the whole server
   process**, though its comment assumes one CLI run. Harmless today (a few
   keys, thread-safe access); fix the comment or scope it.
4. **The stage-name scan in `tests/serve/test_no_stage_names.py` misreads some
   TypeScript.** It skips expressions inside `${...}`, ignores unquoted object
   keys and member access (`tabs.review`), and reads a regex after a keyword as
   a string. Nothing is hidden today.
5. **`Conflict` (`web/client/src/ui/content-views.tsx`) nests a `<div>` inside
   a `<p>`**, and React logs a DOM-nesting warning in tests. Cosmetic.

## Commands named in passing

6. **Commands wrapped across a line inside backticks are never checked** by
   `tests/test_documented_cli_surface.py` (the BACKTICKED pattern), e.g.
   `tcw/work/procedures/audit-backlog.md` and `plan.md`. Both are valid today.

## Lifecycle

7. **`tcw work advance` moves an item out of spec and plan with no document
   written.** No gate checks that a stage's document exists. Decide whether it
   should.
8. **Unattended runs have no rule for an item sitting at request**, the one
   stage that asks the user. Neither the autonomous skill nor the
   unattended-work procedure says what to do.
