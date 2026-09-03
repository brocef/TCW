# `tcw work nodes` hides a registered child that keeps no work store

The topology command should show the graph as registered. A child that keeps no
board is still a child, and printing `children: (none — leaf)` for a node that
has one is simply false.

What should be true when this is done:

- Registered children are all listed, each marked when it keeps no work store —
  the same treatment the parent line already gets.
- A node with genuinely no registered children still prints `(none — leaf)`.
- Nothing else changes: `child_nodes` keeps meaning "children with a board",
  which is what the cross-node operations need.

## Notes

Asked for reference material; none provided beyond the session itself. The
reproduction is in `intake.md`.

This is the children half of the `tcw work nodes` change made in
[The epic owner walk stops at a parent that has no work store](tcw://W/2026-09-03-the-epic-owner-walk-stops-at-a-parent-that-has-no-work-store),
which fixed the parent line and left this one.
