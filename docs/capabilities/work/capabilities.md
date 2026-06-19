# Work — capabilities

## Open a work item
**Status:** Supported
**Subject:** work-item

As a user, I run `tcw work new "<title>"` (with an optional piped body) to create a backlog item; the tool prints its generated slug. I can pass `--blocked-by <refs>` (comma-separated slugs or external strings) to attach blockers at creation time.

## View the board
**Status:** Supported
**Subject:** work-item

As a user, I run `tcw work list` (optionally `--status`) to see every work item with its slug, status, phase, and title in topological order (blockers appear before the items they block). Items with unresolved blockers are annotated with their blocker slugs.

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
