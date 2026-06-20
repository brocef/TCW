# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Work items can now span repositories

Work is no longer single-repo. Any folder that is a git repo with a `docs/work/`
is a **node**, and nodes nest: a repo inside another is a "child," the outer one
its "parent."

- **Epics across repos.** Mark a work item an epic with `tcw work new --epic`,
  then point tasks in other repos at it with `--initiative <epic>`. Run
  `tcw work reconcile <epic>` to gather every linked task into a live rollup —
  a status table, the capability changes each task carries, and what's ready to
  work next — written straight into the epic.
- **Pass requests between repos.** `tcw work delegate <child> "<title>"` drops a
  request into a child repo's inbox; `tcw work escalate "<title>"` sends one up
  to the parent. Both only ever write to the inbox, never to another repo's
  tracked work.
- **See the layout.** `tcw work nodes` shows the current repo's parent and child
  nodes.
- **Isolated work with `--worktree`.** `tcw work start <item> --worktree` runs an
  item in its own git worktree and branch, so its code changes stay separate
  until merged back. The board stays accurate throughout, and finishing the item
  cleans the worktree up.
