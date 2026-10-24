# Searching the work items

Answer a described question about the board, such as "anything about the web
viewer" or "blocked CLI items, ignore the docs ones, highest priority first",
with a table the reader can act on. This is a read done by an agent: the CLI
has no search command, because deciding whether an item is _about_ the
question is a judgment no text match supplies. Ask the `work` skill for it;
under any harness, this document is the procedure.

## 1. Narrow with the CLI first

`tcw work list` is the candidate set, and its flags do for free what judgment
should not be spent on:

- `--stage <stage>` and `--tag <tag>` when the description names one. Each is
  repeatable and matches **any** of the values given, so "both tags" is a
  filter you apply yourself.
- `--all` when the question reaches finished work ("everything", "did we ever
  do this"). Without it the list leaves out items at `completed` and
  `discarded`, which silently drops what a "have we done this before" question
  is asking about.
- `--parent <item>` for an epic's children, and `--mine` or
  `--assignee <name>` when the question is about who.
- `--json` when you need the fields rather than the identifiers alone.

Each line `tcw work list` prints is an item's full identifier,
`<project>.work/<id-path>`: the ID of the project that owns the item, then its
folder's path in that project's work store. It names the item from any
project. For a question that spans related projects, add `--scope`: `up` adds
this project's ancestors, `down` its descendants, and `all` both (never a
sibling); `--project <id>` then keeps one of those projects' items.
`tcw project list` names this project and its related projects. Report every
item by its full identifier: a bare `<id-path>` names an item in the active
project only.

## 2. Read the requests only where the list cannot answer

`tcw work list --json` already carries each item's full identifier
(`full-id`), owning project (`owner`), stage, priority, title, tags, assignee,
parent and blockers. Most questions are answered from that alone; spend a read
only on a question it cannot settle.

When you need more, `tcw work show <item>` prints the item's request and its
comments, and `tcw work path <item> spec` and `tcw work path <item> plan` name
its documents; each takes the full identifier, whichever project owns it.
<!-- backend: filesystem -->

To choose which items to open, search under the folder `tcw work path`
prints for the question's words first, then read only the likely ones.
<!-- /backend -->
<!-- backend: jira -->

The request of each item is its ticket's description, which lives in Jira: to
choose which items to open, search Jira for the question's words, or read the
titles first and open only the likely ones.
<!-- /backend -->

Never build a path into the work store yourself.

## 3. Judge, do not match words

A word search chooses candidates; it does not decide the result. An item
belongs in the table when it is _about_ what was asked, whatever words it
used, and stays out when it only mentions the term in passing. Honor the
exclusions in the description as carefully as the inclusions: "ignore the docs
ones" is part of the question.

Sort as asked. With no sort named, order by how well each item answers the
question, and keep `tcw work list`'s own order among equals.

## 4. Report a table

One Markdown table:

| Item | Stage | Priority | Title | Tags | Notes |
| ---- | ----- | -------- | ----- | ---- | ----- |

`Item` is the full identifier. `Notes` holds what an item only sometimes has:
`blocked-by: <full identifiers>`, `assignee: <name>`,
`parent: <full identifier>`. Leave it empty otherwise. **Copy the cells from
`tcw work list --json`; never work them out yourself.**

Above the table, one line saying how the question was read: which flags were
used, and any reading the description left open. Below it, anything a cell
cannot hold: a near miss that was left out and why, or two items that look like
duplicates. No matches is an answer: say so plainly, naming what was searched,
rather than printing an empty table.
