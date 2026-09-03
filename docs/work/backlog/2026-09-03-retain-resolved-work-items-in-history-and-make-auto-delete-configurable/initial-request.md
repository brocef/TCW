# Retain resolved work items in history, and make auto-delete configurable

A project should be able to say what happens to a work item once it is resolved,
and the default should keep everything.

The request was put as a change to the mechanic:

> we don't need to ignore the completed folder anymore. We have a graveyard file
> to hold the slugs of all discarded work items so that we know that they did
> exist at some point, so we could also do a work complete transition with two
> commits: one where the work item moves to the completed folder (plus any other
> commits for refined output), and then another commit where it's deleted. That
> way we still clean up the completed folder and remember slugs of prior items.

and summarized as:

> Auto-deletion of completed and/or discarded work items should be configurable
> (via tcw-config.yaml)

What should be true when this is done:

- Retention is declared in `tcw-config.yaml`, per resolved status, so `completed`
  and `discarded` can differ.
- **The default retains everything.** Nothing is deleted unless a project says so.
- Where auto-delete is on, the item is committed into its resolved status folder
  first and deleted in a second commit, so the content is in the repository's
  history and the working tree stays clean.
- The graveyard keeps the slug, so a resolved item is still known to have
  existed and its slug can never be reissued.
- A resolved slug points at content someone can actually retrieve: record the
  commit the item was last present in, alongside the slug.

The requester accepted, unprompted, that a squashed history would drop the
commit holding the content, and does not consider that essential.

Constraints stated in session:

- The name is **`auto-delete`**. "Auto-discard" was rejected on the grounds that
  `discard` already names a lifecycle transition meaning *resolve as not-done*,
  and reusing the word would make every `discard` binding ambiguous.
- Retention is a property of the project, expressed as retention rather than as
  a `.gitignore` mechanic, so a non-filesystem store can honor it.

Out of scope: the hook that lets a consumer archive an item before it is deleted.
That is a separate item, and it depends on this one.

## Notes

Asked for reference material; none provided beyond the session itself.

One finding from the session that the requester did not state, and that the spec
should treat as part of the motivation rather than a side effect: today a
resolved item's content survives **only on the machine that resolved it**. The
`.gitignore` mechanic untracks it and leaves it on disk, so it reaches no other
clone. A provisioned work store obtained by `tcw provision` therefore has no
resolved items at all, and `tcw://W/…` references to them dangle there. Two
commits put the content in history, where every clone can reach it.
