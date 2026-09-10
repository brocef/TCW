# `tcw work list` should say how many inbox entries each node holds

Raw intake sitting in a node's `inbox/` is invisible on the board: an inbox entry
is not a work item, so it has no row, and nothing else in `tcw work list` hints
that requests are waiting. A node can accumulate delegations and escalations
nobody has looked at while its board reads as fully triaged.

## What was asked

That `tcw work list` also say how many inbox items there are, for each project it
lists.

## What shipped in this session

Implemented directly, without driving the lifecycle through the CLI, because this
session edits `tcw/` — the working guide's exception. Recorded here instead.

- `tcw work list` prints `→ inbox: <n> entr(y|ies) awaiting triage` on **stderr**
  after the board, for the current node, with the `tcw work inbox list` command
  that reads it.
- `--include-descendants` prints one line per node holding entries, each named by
  its canonical project ID, in the same order as the board's group headers. The
  command hint is printed only for the current node, since that is the only inbox
  it reaches.
- A node with an empty inbox prints nothing.
- The count comes from the store's existing `inbox_list()` operation, so no new
  abstraction surface was introduced and any store that can list an inbox can
  count one.
- stdout is unchanged: the counts are not board rows, so a caller piping the
  board still sees one `|`-delimited line per work item.

Docs updated: `README.md`, `docs/guide/work.md`, the `View the board` capability,
`skills/tcw-work/references/commands.md`, and both `upcoming.md` working files.

## Left for triage

- **Should `tcw serve` and the web viewer show the same counts?** The board and
  the web app are meant to answer the same question, and the viewer has no notion
  of the inbox at all today. Out of scope for the ask as written.
- **Should the count be addressable rather than only readable?** There is no way
  to list another node's inbox from here — `tcw work inbox list` reads the current
  node — so a descendant's count names a number the reader cannot act on without
  changing directory.
