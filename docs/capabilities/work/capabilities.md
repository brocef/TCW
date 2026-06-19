# Work — capabilities

## Open a work item
**Status:** Supported
**Subject:** work-item

As a user, I run `tcw work new "<title>"` (with an optional piped body) to create a backlog item; the tool prints its generated slug.

## View the board
**Status:** Supported
**Subject:** work-item

As a user, I run `tcw work list` (optionally `--status`) to see every work item with its slug, status, phase, and title.

## Read a work item
**Status:** Supported
**Subject:** work-item

As a user, I run `tcw work show <slug>` to read an item's state and body, or `tcw work path <slug>` to print its current on-disk path.

## Start a work item
**Status:** Supported
**Subject:** work-item/transition

As a user, I run `tcw work start <slug>` to move an item from inbox or backlog into active.

## Block a work item
**Status:** Supported
**Subject:** work-item/transition

As a user, I run `tcw work block <slug> --on <blocker>` to move an active item to blocked, recording either a blocker slug or a free-text external dependency.

## Unblock a work item
**Status:** Supported
**Subject:** work-item/transition

As a user, I run `tcw work unblock <slug>` to return a blocked item to active. The tool refuses while blockers are unresolved unless I pass `--force`.

## Complete a work item
**Status:** Supported
**Subject:** work-item/definition-of-done

As a user, I run `tcw work complete <slug> --resolution <r>`; the tool prints the Definition-of-Done checklist and refuses until I re-run with `--confirm`.

## Drop a work item
**Status:** Supported
**Subject:** work-item/transition

As a user, I run `tcw work drop <slug>` to delete an inbox or backlog item that won't be done.
