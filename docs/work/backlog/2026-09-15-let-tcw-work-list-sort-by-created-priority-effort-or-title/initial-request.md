# Let tcw work list sort by created, priority, effort or title

## Request

`tcw work list` should let the user choose how the board is sorted. Start with
four easy orderings:

- **creation time** (`created`)
- **priority**
- **effort**
- **title**, alphabetically

The requester has no preference on the command-line syntax and asked for
whatever is most common among command-line tools.

When a sort is chosen, the requester confirmed:

- **Child items stay nested under their parent**, and are sorted among their
  siblings.
- **Blocker ordering is dropped.** Today the board moves an item that blocks
  another above the item it blocks; a chosen sort replaces that ordering rather
  than working within it.

Requested together with
`2026-09-15-record-a-time-of-day-and-timezone-offset-in-every-timestamp-tcw-writes`,
which adds a time of day to `created`. The requester chose to track the two
changes as separate items. Sorting by creation time is useful without it (dates
alone, with some tie-break), and gets finer once it lands.

## Notes

- Reference material: asked; none provided.
- What the repository holds today, found while taking the request (context for
  `spec`, not decisions):
  - With no sort chosen, the board orders items by priority (highest first,
    unset last), then moves blockers ahead of what they block
    (`priority_order` and `topo_order` in `tcw/store/base.py`, applied by
    `WorkStore.board`).
  - `tcw work list` already takes `--status`, `--tag`, `--all` and
    `-i`/`--include-descendants`; the descendant form groups rows by node and
    nests across nodes.
  - Effort is one of `low`, `medium`, `high`, `very-high`, and may be unset.
    Priority is an integer, and may be unset.
- Open for `spec`, not settled by the requester: the exact option names (for
  example a `--sort <key>` option with a way to reverse it); the default
  direction of each ordering; where items with no priority or effort go; the
  tie-break when two items compare equal; and whether the board with no sort
  chosen stays exactly as it is today.

## Added 2026-09-16

Requested in chat, and folded into this item by the requester's decision: the
commands that emit lists of entities should **limit how many rows they print**,
alongside the ordering this item already covers.

The requester named `tcw work list` and `tcw work inbox list` as the ones they
could think of, then chose to apply it to **every list-emitting command** —
`tcw work list`, `tcw work inbox list`, `tcw taxonomy list`,
`tcw capabilities list`, and the `search` outputs — with one shared mechanism
rather than a per-command one, so the option spelling and the overflow wording
are written once.

Three parts:

- **A row limit per section.** Where a command's output is already divided
  into sections — `tcw work list -i` prints one per node, and
  `tcw work inbox list` is specced to print one per source — the limit applies
  to each section separately, not to the output as a whole.
- **The count in each section heading.** A heading says in parentheses how many
  rows that section emitted.
- **An overflow note.** When a section held more rows than the limit let it
  print, it ends with a line saying how many were withheld, in the shape "and
  X additional rows".

The requester chose **a per-run flag only** for the limit, over a
`tcw-config.yaml` default or an environment variable: a flag on each list
command with a hard-coded default, no configuration schema change and no
`tcw validate` shape check. A project cannot record a standing preference.

### Answers given when this was folded in

- **Scope:** every list-emitting command, one shared mechanism.
- **Configuration:** per-run flag only, with a hard-coded default.
- **Relation to this item:** fold in, rather than track separately. The
  requester was shown that this item is already at `plan` and that its spec
  names sorting other lists a non-goal, and chose the fold anyway.

### Open for `spec`, not settled by the requester

- The flag's name and spelling, and how a user asks for no limit at all.
- The default limit.
- Whether the count in a heading is the emitted count, the total, or both, and
  what an unsectioned command's heading is when it has none today.
- Whether the limit counts nested child rows separately from their parents in
  `tcw work list`, where children print indented under a parent.
- Whether the overflow note goes to stdout with the rows or to stderr.
- How limiting interacts with the sort this item already adds: which rows a
  limit keeps depends entirely on the order they are in.

## Added 2026-09-16 (sentinel, default and heading)

The requester settled three of the questions the section above left open for
`spec`, in chat while reviewing the first plan:

- **The no-limit sentinel is `-1`, not `0`.** `--limit -1` prints every row.
  This frees `0` to mean what it plainly says — print the heading and no rows —
  which is a useful way to ask for the counts alone.
- **The default stays a per-section cap of 20 rows.**
- **The heading always prints**, whatever the limit. The requester was shown
  that `--limit -1` stops truncation but not the heading, so the exact-stdout
  assertions in `tests/test_work.py` and `tests/test_taxonomy.py` need their
  expected strings updated either way; and that suppressing the heading under
  `-1` would make the output's shape depend on the flag and would hide the
  counts exactly when someone asked to see everything. They chose the uniform
  output.

The requester also confirmed the scope increase from folding the two halves
together is acceptable, and that existing callers in skills and tests should
pass the no-limit sentinel rather than have the feature bend around them.
