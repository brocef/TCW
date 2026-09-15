# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Filing new work without duplicates

- **New `tcw-work-create` skill.** When an agent notices something worth
  tracking in the middle of other work — a bug found in passing, a follow-up a
  review left behind — or you ask it to file something, it first checks your
  board and your work inbox. If the work is already tracked, it adds anything
  new to that item instead of opening a duplicate; if not, it creates the item
  with its blockers, reference material and where it came from.
- It can run in the background as a helper: it asks you, through the agent you
  are talking to, before revising a planned item, and uses sensible defaults only
  when you have asked the agent to work without checking in.
- Work noticed inside a separate worktree still lands on your main board, where
  every session can see it.
