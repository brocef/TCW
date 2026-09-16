# Auditing the backlog

**This page holds only the part of this procedure a project cannot replace.**
For the rest, run `tcw work procedure prompt audit-backlog` and follow what it
prints: this project's text if it configured one, TCW's own otherwise. The rule
on this page holds whatever it prints. If the command fails, say so rather than
working from memory.

## The approval rule

**Do not silently mutate, drop, complete, or move items.** Ask before performing
any cleanup, including tag registration and tag edits.

**Group the asks by kind** — one approval for the tag edits, one for the blocker
edges, one for the drops. A real audit produces a dozen or more candidate
actions; asking per item is unusable and asking once for everything is a blanket
yes on decisions that deserve individual thought. Drops and completions are
irreversible enough to name individually inside their group.

When the user approves, use TCW commands for state transitions and tag edits
wherever a command exists, and preserve useful context in the remaining or
replacement item.
