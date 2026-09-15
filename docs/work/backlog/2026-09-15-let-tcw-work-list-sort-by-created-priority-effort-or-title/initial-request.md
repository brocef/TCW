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
