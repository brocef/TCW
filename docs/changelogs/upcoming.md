# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- Added an accessible, focused work-document tab component with lazy artifact
  loading, missing/error states, revision-aware refreshes, and component/browser
  regression coverage.

## Changed

- `init` (`tcw/store/fs.py`) now writes `.gitignore` rules for the resolved work
  folders when scaffolding the `work` component: `docs/work/<status>/*` plus a
  `!docs/work/<status>/.gitkeep` negation for each of `RESOLVED_STATUSES`. The
  `<dir>/*` form is required — git cannot re-include a file under an excluded
  parent directory. `run_init` reports the exclusion. Rules are appended
  line-wise by the new shared `ensure_ignored`, extracted from
  `ensure_worktree_ignored`; nothing is staged, matching the rest of `init`.
- This repo's own `.gitignore` moved to the same rules, restoring
  `docs/work/{completed,discarded}/.gitkeep` to the index.

- Replaced external-open controls for Initial Request, Spec, and Implementation
  Plan with first-class in-app rendering and editing while preserving other
  lifecycle artifact, plan-stage, and sidecar controls.

## Fixed

- `git_stage` skips gitignored paths instead of failing: with the resolved
  status folders ignored by default, `reconcile` staging an epic artifact that
  had already moved into `completed/` aborted with git's "paths are ignored"
  error.
- `git_mv`'s untrack branch passes `-f` to `git rm --cached`. A transition
  stages the item's own state before moving it, so the index legitimately
  differs from both HEAD and the worktree, which `git rm` otherwise refuses —
  surfacing as a failed discard through the `tcw serve` API. `--cached` still
  means the files stay on disk.
