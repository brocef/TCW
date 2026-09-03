Raw request, from a working session on 2026-09-03.

> TCW users could also have a custom completed transition that, when a work item
> is about to be deleted, uploads it to cold storage somewhere so that they keep
> a record. We might be missing a configurable lifecycle hook for that, but it
> shouldn't be hard to add and lets the TCW consumer decide if they care about
> keeping the completed work items.

> * Create a new lifecycle transition and hook for auto-discard

Decisions taken in the same session:

- The step is named `auto-delete`, not `auto-discard`.
- The two cold-storage scenarios to design against are: uploading the item to
  AWS S3, and moving it to another folder.
- `tcw serve` still runs no hooks. That may change later; it is not changing
  here. The web UI is for exploring, reading and hand-editing work artifacts,
  not for driving the lifecycle.
