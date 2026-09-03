# An auto-delete step with hooks, so a consumer can archive an item before it is removed

A project that lets TCW delete its resolved work items should be able to keep its
own copy first, wherever it wants one, without TCW knowing anything about where
that is.

The request, as put:

> TCW users could also have a custom completed transition that, when a work item
> is about to be deleted, uploads it to cold storage somewhere so that they keep
> a record. We might be missing a configurable lifecycle hook for that, but it
> shouldn't be hard to add and lets the TCW consumer decide if they care about
> keeping the completed work items.

and summarized as:

> Create a new lifecycle transition and hook for auto-discard

What should be true when this is done:

- There is a named lifecycle step for the deletion, bindable in
  `tcw-config.yaml` under `work.lifecycle` exactly as the existing transitions
  are, with `pre` and `post`.
- A `pre` binding that fails means the item is **not** deleted. A consumer whose
  upload failed has not lost the item.
- A binding has enough context to act on the item without re-deriving it: where
  the item is, and how it was resolved.

Two scenarios were named as the ones to design against:

- uploading the item to AWS S3;
- moving it to another folder.

Constraints stated in session:

- The step is named **`auto-delete`**, not `auto-discard`: `discard` already
  names a lifecycle transition meaning *resolve as not-done*, and reusing the
  word would make every `discard` binding ambiguous.
- If the archive fails and the item is left sitting in its resolved folder, the
  retry verb is **`tcw work delete <slug>`** — the same code path as the
  automatic step, under a name that reads as something a person types.
- **`tcw serve` still runs no hooks.** That may change one day; it is not
  changing here. The web UI is for exploring, reading and hand-editing work
  artifacts, not for driving the lifecycle.

Out of scope: retention configuration itself, and the two-commit deletion. Those
are the blocking item.

## Notes

Asked for reference material; none provided beyond the session itself.

The requester's phrase was "a custom completed transition". The design that
follows attaches to the deletion rather than to `complete`, because the deletion
is the moment the content stops existing and because it happens for `discarded`
items too. The spec should say why it read the request that way.
