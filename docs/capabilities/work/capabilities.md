# Work — capabilities

## Open a work item
**Status:** Supported
**Subject:** work-item

As a user, I run `tcw work new "<title>"` (with an optional piped body) to create a backlog item; the tool prints its generated slug. I can pass `--blocked-by <refs>` (comma-separated slugs or external strings) to attach blockers at creation time.

## View the board
**Status:** Supported
**Subject:** work-item

As a user, I run `tcw work list` to see work items as ` | `-delimited rows of slug, status, phase, priority (the integer, or `-` when unspecified), and title. By default the board shows the live columns (inbox, backlog, active) and hides completed items; I pass `--status <s>` to list one column (including `--status completed`), or `--all` to show everything. The board sorts by priority first (higher integer above lower; unspecified-priority items keep creation order, below the prioritized ones), then topologically — blockers appear before the items they block, since priority can't jump a hard dependency. Items with unresolved blockers are annotated with their blocker slugs.

## Prioritize a work item
**Status:** Supported
**Subject:** work-item

As a user, I assign an integer priority with `tcw work new "<title>" --priority N` or `tcw work edit <slug> --priority N` (higher integer = higher priority; the default is unspecified). Higher-priority items sort to the top of the board.

## Read a work item
**Status:** Supported
**Subject:** work-item

As a user, I run `tcw work show <slug>` to read an item's state and body (including any recorded blockers), or `tcw work path <slug>` to print its current on-disk path.

## Start a work item
**Status:** Supported
**Subject:** work-item/transition

As a user, I run `tcw work start <slug>` to move an item from inbox or backlog into active. The tool refuses if the item has unresolved blockers; I pass `--force` to override.

## Manage blocking relations
**Status:** Supported
**Subject:** work-item

As a user, I run `tcw work edit <slug> --blocked-by <refs>` to record that named items (or external dependencies) block my item, `--blocks <refs>` to record that my item blocks named items, and `--unblocked-by <refs>` to remove blockers that have been resolved. The tool guards against self-blocking and cycles. Blockers are stored in the item's data, not as a separate folder or status.

## Complete a work item
**Status:** Supported
**Subject:** work-item/definition-of-done

As a user, I run `tcw work complete <slug> --resolution <r>`; the tool checks for unresolved blockers (refused unless I pass `--force`), then prints the Definition-of-Done checklist and refuses until I re-run with `--confirm`.

## Drop a work item
**Status:** Supported
**Subject:** work-item/transition

As a user, I run `tcw work drop <slug>` to delete an inbox or backlog item that won't be done.

## Decompose a work item into children
**Status:** Missing
**Subject:** work-item
**Planning doc:** 2026-06-21-nested-work-items

As a user, I run `tcw work new "<title>" --parent <slug>` to create a child work item nested inside an existing item, so a large item can be broken into smaller ones that travel with it. `tcw work list` shows children indented under their parents. A child shares its parent's status by living inside it; starting or completing the parent carries its children along, and transitioning a child on its own promotes it to a top-level item.
