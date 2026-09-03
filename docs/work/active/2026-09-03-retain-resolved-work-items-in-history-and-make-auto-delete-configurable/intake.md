Raw request, from a working session on 2026-09-03.

> Also we really should change the behavior for the TCW repos in that we don't
> need to ignore the completed folder anymore. We have a graveyard file to hold
> the slugs of all discarded work items so that we know that they did exist at
> some point, so we could also do a work complete transition with two commits:
> one where the work item moves to the completed folder (plus any other commits
> for refined output), and then another commit where it's deleted. That way we
> still clean up the completed folder and remember slugs of prior items. There is
> a chance that commits are squashed which would drop the commit where the work
> item existed in the completed folder (prior to deletion), but it's not
> essential to have it in the commit history.

> * Auto-deletion of completed and/or discarded work items should be configurable
>   (via tcw-config.yaml)

Decisions taken in the same session:

- The name is `auto-delete`. "Auto-discard" was rejected: `discard` is already a
  lifecycle transition id meaning *resolve as not-done*.
- The default configuration retains everything.
- Record the pre-delete commit SHA in the graveyard entry, so a resolved slug
  points at retrievable content rather than only asserting the item existed.
