# Searching the work items

Answer a described question about the board — "anything about the web viewer",
"blocked CLI items, ignore the docs ones, highest priority first" — with a table
the reader can act on. This is an AI-driven read, and the CLI has no work-item
search verb to call: deciding whether an item is _about_ the question is the
judgment a match cannot supply. Claude users reach it as
`/tcw-work-search "<description>"`; under any harness, this document is the
procedure.

**It is read-only.** No transition, no `tcw work edit`, no file written. A search
that changed the board would make its own result untrustworthy.

## 1. Narrow with the CLI first

`tcw work list` is the candidate set, and its flags do for free what judgment
should not be spent on:

- `--status <status>` / `--tag <tag>` when the description names one. `--tag` is
  repeatable and matches **any**, so it cannot express "both tags" — filter that
  half yourself.
- `--all` when the request reaches closed work ("everything", "including
  completed", "did we ever…"). Without it the board hides `completed` and
  `discarded`, which silently drops the items a "have we done this before"
  question is asking about. `review` is live work and is never hidden.
- `-i` when the question spans connected projects. Descendant rows arrive
  qualified as `<project-id>/<slug>`; keep that qualifier in the output — a bare
  slug from another node does not address anything.

Read `tags.md` when a description names a category loosely, so a query for
"frontend" finds the node's actual `web` tag.

## 2. Read bodies only where the row cannot answer

A board row already carries slug, status, stage letters, priority, title, tags,
blockers, and the claimant of an active item. Most requests are answerable from
rows alone; spend a read only on a question the row cannot settle.

When you do need bodies, grep before reading. `tcw work path` with no slug prints
the store folder — search under it for the description's terms to choose which
items to open, then open those with `tcw work path <slug>` and read
`initial-request.md` **or** `intake.md` (an inbox-adopted item has only the
intake), plus `spec.md`, `plan.md`, `content.md` as the question needs.
`tcw work show <slug> --json` is the way to read one item's fields without
parsing prose. Never compose a store path yourself.

## 3. Judge, don't substring-match

Grep chooses candidates; it does not decide the result. An item belongs in the
table when it is _about_ what was asked, whatever words it used — and stays out
when it merely mentions the term in passing. Honour the exclusions in the
description as carefully as the inclusions: "ignore the docs ones" is part of the
query, not a hint.

Sort as asked. With no sort named, order by how well each item answers the
question, and keep `tcw work list`'s own order among equals.

## 4. Report a table

One Markdown table, carrying `tcw work list`'s columns:

| Slug | Status | Stages | Priority | Title | Tags | Notes |
| ---- | ------ | ------ | -------- | ----- | ---- | ----- |

`Notes` holds the segments a board row only sometimes prints —
`ready-to-close`, `blocked-by: <refs>`, and an active item's
`owner: <identity>` / `started: <timestamp>` — so nothing the board says is lost
to the table's fixed shape. Leave it empty otherwise.

**Transcribe the cells from `tcw work list`; never re-derive them.** Stage letters
in particular are computed from artifact presence, and a table that recomputes
them can disagree with the board it claims to be reporting.

Above the table, one line naming how the request was read — which flags were
used, and any reading the description left open. Below it, name anything worth
saying that a cell cannot hold: a near-miss that was excluded and why, or two
items that look like duplicates. No matches is an answer: say so plainly, with
the set that was searched, rather than printing an empty table.
