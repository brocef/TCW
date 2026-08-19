# 10 — Cross-node work, epics, and nesting

Work that spans more than one item or more than one repository.

## Functionality covered

- `tcw work new --parent` (nested items) and `--epic`
- `--initiative` back-pointers
- `tcw work nodes`, `delegate`, `escalate`
- `tcw work reconcile`, `--commit`, `--complete-when-ready`
- `tcw work list -i` (descendant boards)
- Subproject-qualified slugs

## What is tested

| # | Assertion |
| - | --------- |
| 1 | `tcw work new "Child" --parent $EPIC` nests the child under the parent; `tcw work path` for the child resolves inside the parent's folder. |
| 2 | `tcw work show $EPIC` lists its children; `tcw work list` renders the nesting. |
| 3 | `--epic` marks `type: epic`, visible in `show --json`. |
| 4 | An epic's `complete` is gated on its children: with a child still open, `complete --resolution done --confirm` is refused; once every child is resolved, it completes. |
| 5 | `--initiative <epic-slug>` stamps the back-pointer, and it round-trips through `show --json`. |
| 6 | **Two nodes on disk**, parent and child, registered through the CLI. `tcw work nodes` in the parent lists the child, and in the child lists the parent. |
| 7 | `tcw work delegate <child-id> "Please do X"` writes a request into the **child node's** inbox, not the parent's. Asserted by reading the child's `tcw work inbox list`. |
| 8 | The delegated entry records the **originating project id** correctly (fixed defect: `2026-07-20-fix-delegate-inbox-origin-project-id`). |
| 9 | `tcw work escalate "Please decide Y"` from the child writes into the **parent's** inbox. |
| 10 | `echo "detail" \| tcw work delegate <child> "Title"` carries the piped body into the child's inbox entry. |
| 11 | `tcw work reconcile $EPIC` scans child nodes and writes the epic rollup; running it twice is idempotent. |
| 12 | `--commit` also commits the rollup; without it, the rollup is written but uncommitted. |
| 13 | `--complete-when-ready` auto-completes the epic once every child is resolved, and does **not** when one is open. |
| 14 | A reconcile whose commit is refused reports a **CLI error, not a traceback** (fixed defect: `2026-08-13-report-a-refused-reconcile-commit-as-a-cli-error-not-a-traceback`). Assert stderr carries no `Traceback (most recent call last)`. |
| 15 | `tcw work list -i` in the parent shows the child node's board grouped by node; without `-i` it does not. |
| 16 | A subproject-qualified slug (`<child-id>/<slug>`) resolves from the parent for `show`. |
| 17 | The child node being a **separate git repository that the parent gitignores** does not break the parent's scan — no command walks into it as if it were the parent's own tree. |

## Refusals asserted

- epic with open children refuses complete (4)
- refused reconcile commit is a clean error (14)

## Explicitly not covered here

Three-level node chains, and cross-node epic slices linking upward — a known
open item (`2026-07-23-cross-node-epic-slices-cannot-link-their-parent-epic-...`).
Recorded here as a gap so nobody reads its absence as coverage.

## Notes for the implementer

Build the node graph entirely through the CLI. Assertion 17 needs the child to be
a genuine nested git repo (`git init` inside the parent's tree, with the path in
the parent's `.gitignore`) — that is the real-world layout and the one that broke
before.

Nothing here touches the network. `nodes` and `delegate` resolve through relative
paths recorded in `tcw-config.yaml`.
