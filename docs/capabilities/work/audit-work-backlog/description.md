As a user, I ask the assistant to audit my backlog and get a structured cleanup
report. This is an assistant-driven review rather than a `tcw` subcommand — the
judgment it needs is not something the CLI can supply — so I reach it by asking,
or with `/tcw-audit-work-backlog` in Claude Code. It works the same under either
harness.

The audit identifies items that look completed, stale, outdated, misplaced,
duplicated, blocked without a useful next step, or too vague to implement safely.
It also reports dependencies an item states in prose but never recorded, so the
board stops showing blocked work as ready to pick up.

The audit does not silently mutate work items. It reports recommended actions,
including complete, drop, revise, split, move to another TCW node, or keep as-is,
so an agent or user can prune the backlog while preserving reviewable decisions.
