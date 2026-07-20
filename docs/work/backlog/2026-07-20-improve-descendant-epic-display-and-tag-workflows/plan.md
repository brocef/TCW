# Plan — Descendant epic display and tag workflows

1. Refactor board-row rendering in `tcw/work/cli.py` so local boards retain
   parent nesting while aggregate boards construct one visible ownership forest
   across the anchor and registered descendants. Resolve initiative owners only
   through the item's local node and registered ancestors.
2. Add `-i` and `--incl-desc` aliases to the existing
   `--include-descendants` parser destination.
3. Extend `tests/test_work.py` with same-node and cross-node initiative hierarchy,
   qualified child indentation, no-duplicate, and alias cases; retain existing
   node grouping, filters, and parent nesting coverage.
4. Update `commands/tcw-plan-work.md`, `commands/tcw-audit-work-backlog.md`, and
   `skills/tcw-work/SKILL.md` with active tag-selection and maintenance guidance,
   centered on the existing `tcw work tags add|rm|list` commands.
5. Update the changed capability descriptions, `README.md`,
   `docs/release-notes/upcoming.md`, and `docs/changelogs/upcoming.md` for the
   public CLI/code Documentation Sync triggers.
6. Run targeted tests, the full pytest suite, `tcw capabilities check`,
   `tcw validate`, and `git diff --check`; record outcomes and reconcile both
   changed capabilities.
7. After user verification, complete the work item and cut the explicitly
   approved patch release with `python scripts/cut_version.py patch`.
