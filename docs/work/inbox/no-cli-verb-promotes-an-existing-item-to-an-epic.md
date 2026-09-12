# No CLI verb promotes an existing work item to an epic

`tcw work new --epic` is the only way to set `type: epic`. An item that was
filed as an ordinary backlog item and later turns out to be an initiative has
no supported route: `tcw work edit` carries `--title`, estimates, tags,
blockers, `--priority` and `--initiative`, but no `--type`/`--epic`, and the
abstract `update_work` has no `type` keyword either
(`tcw/store/base.py:2364-2374`).

Hit while planning
`2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge`.
The request had already been written as a whole initiative, so the planning
session had three bad choices: recreate the item under a new slug and lose the
request's history, leave it a plain item and lose `epic_completable` (the
`ready-to-close` marker in `tcw work list`, completing straight from `backlog`,
and `reconcile --complete-when-ready`), or set the field by hand. It set the
field by hand, which is the thing the skill tells an agent never to do.

Note that most of the epic machinery does **not** need the type: `reconcile`
scans for `initiative == <slug>` and never checks it
(`tcw/work/recursion.py:194-224`), and the "a child cannot start before its
epic is active" gate reads the parent's status, not its type
(`tcw/store/base.py:2676-2685`). Only `epic_completable`
(`tcw/store/base.py:2609`) and the board's `ready-to-close` segment
(`tcw/work/cli.py:398`) actually require it.

Suggested shape: `--type epic` / `--type ""` on `tcw work edit`, plus a `type`
keyword on `update_work`, with demotion refused while any item points at it
with `initiative:` — a demoted epic would orphan its children.

Storage-abstracted: `type` is already a `WorkItem` field every adapter carries,
so setting it is an ordinary field write and needs nothing filesystem-specific.
