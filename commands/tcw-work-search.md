---
description: Search the TCW work items by description — what to look for, what to ignore, how to sort — and report the matches as a table with the board's columns.
---

Use the `tcw-work` skill and follow
[`references/procedures/search.md`](../skills/tcw-work/references/procedures/search.md),
which is the whole procedure: narrowing with `tcw work list`'s own flags before
spending a read, grepping the store folder to choose which bodies to open,
judging relevance rather than substring-matching, and the table to report.

The arguments are a description of the search, not flags: what to look for,
optionally what to ignore, and optionally how to sort. Read all three out of
whatever the user wrote.

This is an AI-driven read, and the CLI has no work-item search verb to call. It
changes nothing: no transition, no edit, no file written.

$ARGUMENTS
