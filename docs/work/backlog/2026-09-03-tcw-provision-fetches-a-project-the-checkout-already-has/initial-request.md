# `tcw provision` fetches a project the checkout already has

Provisioning should never obtain a project that is already reachable here. The
rule the whole feature rests on — *a store that is already here always wins* —
has to hold for nodes too, or a walk that follows declarations transitively will
re-clone repositories the user is standing in.

Found by configuring the Proposit repositories for real, not by a test.

What should be true when this is done:

- A declaration for a project id already reachable from this checkout is skipped,
  and reported as already available rather than silently ignored.
- The check is by project id, since that is identity; a path or a URL is not.
- Everything else about the walk is unchanged: an absent project is still
  obtained, transitively, with its remote printed first.

## Notes

Asked for reference material; none provided beyond the session itself. The
reproduction is in `intake.md`.

This is a small correction to
[Connected-project entries declare where they come from](tcw://W/2026-09-03-connected-project-entries-declare-where-they-come-from-so-tcw-provision-can-obtain-a-node),
found immediately after it, by the first real configuration to exercise it.
