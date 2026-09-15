# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- **`tcw-work-create` skill** (`skills/tcw-work-create/`): turns one idea into
  exactly one outcome (`created`, `amended`, `revised`, `already tracked`,
  `already in progress`, `deferred to inbox`, `needs decision`). It runs in three
  modes (interactive, delegated to a subagent from a brief, unattended), searches
  from the primary checkout's board when run inside a linked worktree, and
  records blockers, `## Origin` and `## References` in the new item's
  `intake.md`. Its read-only overlap search is `references/find-overlap.md`,
  which also reads `tcw work inbox list`.
- **Eval case B13.** A remark made in passing about slow sign-in, with one new
  fact, while the fixture's active item is being worked. It must invoke
  `tcw-work-create`, read the inbox, change only
  `docs/work/inbox/slow-login.md`, and create no item.
- Taxonomy Feature `tcw-work-create-skill` and capability
  `skills/tcw-work-create`.

## Changed

- `tcw-commands-plan-work` runs `tcw-work-create` before `request` for a chat
  request with no existing item. `tcw-configure`'s `docs-sync.md` files deferred
  follow-up work through it, not a bare `tcw work new`. `tcw-work`'s router
  points at it.
- `tests/test_eval_grading.py`: a `CASE_ROUTING` row may name the assertion it
  pins by its search text, for a case with two assertions of the same predicate.
- The Codex manifest describes sixteen skills.
