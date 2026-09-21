# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

**This is the release v2.5.0 was meant to be.** v2.5.0 was tagged but never
reached PyPI, because a test that only failed on the build server stopped the
upload. Nothing else changed: everything described in the
[v2.5.0 notes](v2.5.0.md) (making Jira tickets with `tcw work tracker create`,
and moving `extends` into `tcw-config.yaml`) arrives with this version.
**Read those notes before upgrading if you use inheritance**, because that part
needs a migration step.

## Child items have their own status

- **A child item can now be planned on its own, even after its parent has been
  started.** `tcw work new "<title>" --parent <item>` always creates the child
  in backlog, so its request, spec and plan stages work. Before, a child created
  under an item that was already underway started out as underway too, and
  those stages refused it.
- **A child keeps its parent.** Starting, submitting or completing a child no
  longer detaches it from its parent, and starting the parent no longer drags
  its children along.
- **A parent cannot be closed while a child is still open.** `tcw work complete`
  refuses, even with `--force`, and names the open children. It checks before
  merging a worktree branch, so a refusal changes nothing. Dropping an item that
  has children is refused too, and you cannot add a child to a finished item.
- **Existing children keep working as before.** Children made by earlier
  versions live inside their parent's folder and still move with it. If one is
  moved on its own it keeps its parent and has its own status from then on.
- `tcw validate` now reports a child whose parent does not exist.
