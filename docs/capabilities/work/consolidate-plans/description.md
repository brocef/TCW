As a user, I ask the assistant to find planning documents that live outside the
TCW work system and convert them into TCW work items. This is an assistant-driven
migration rather than a `tcw` subcommand — deciding what counts as a plan and how
its content maps onto lifecycle artifacts needs judgment the CLI cannot supply —
so I reach it with `/tcw-consolidate-plans` in Claude Code. When I name no paths,
it searches sensible project-local planning locations while excluding
`docs/work/` so existing work items are not reimported.

For each accepted external plan it creates a backlog item, preserves the source
document's useful content as lifecycle artifacts, and reports the mapping from
old file to new work slug. Once migration succeeds I can have the old documents
deleted, so the TCW backlog becomes the durable planning source. Because that
step destroys files, it always confirms with me first.

Not yet reachable from Codex.
