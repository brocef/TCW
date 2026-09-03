# The provisioning skip misses a project that is reachable but neither ancestor nor descendant

`tcw provision` should fetch nothing at all on a machine that already holds every
repository in the workspace. Today it still plans to clone a project that is a
sibling of an ancestor — present, and resolvable through the graph.

What should be true when this is done:

- A declaration is skipped when the project is in the graph, by whatever
  relation.
- The check asks the registry the question directly rather than reconstructing
  an answer from a chosen set of relations.
- Everything else is unchanged: an absent project is still obtained,
  transitively.

## Notes

Asked for reference material; none provided beyond the session itself. The
reproduction is in `intake.md`.

This is a defect in the fix for
[tcw provision fetches a project the checkout already has](tcw://W/2026-09-03-tcw-provision-fetches-a-project-the-checkout-already-has),
found one layout later. That item's acceptance criteria said "already reachable
here"; its implementation enumerated three relations instead of asking.
