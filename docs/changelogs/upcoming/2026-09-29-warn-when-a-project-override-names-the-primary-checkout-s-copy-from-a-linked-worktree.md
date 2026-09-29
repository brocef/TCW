## Added

- `ProjectOverride.warning`: set when an override took effect but may not be
  what was meant. The filesystem registry sets it in `_reconcile_overrides`,
  via `_other_branch_warning`, when a linked worktree's `TCW_PROJECT_<ID>`
  names the primary checkout's copy of a project that the worktree also holds
  under the same id. `tcw validate` prints it under the override line. It is
  never counted as a problem, and the override is still followed as stated.
