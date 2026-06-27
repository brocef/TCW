# Audit Work Backlog — capabilities

## Audit and prune the work backlog
**Status:** Missing
**Planning doc:** 2026-06-27-audit-and-prune-the-work-backlog

As a user, I run `tcw work audit-work-backlog` to review backlog items and get a
structured cleanup report. The command identifies items that look completed,
stale, outdated, misplaced, duplicated, blocked without a useful next step, or
too vague to implement safely.

The audit does not silently mutate work items. It reports recommended actions,
including complete, drop, revise, split, move to another TCW node, or keep as-is,
so an agent or user can prune the backlog while preserving reviewable decisions.
