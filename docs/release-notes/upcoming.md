# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

**This is the release v2.5.0 was meant to be.** v2.5.0 was tagged but never
reached PyPI, because a test that only failed on the build server stopped the
upload. Everything described in the
[v2.5.0 notes](v2.5.0.md) (making Jira tickets with `tcw work tracker create`,
and moving `extends` into `tcw-config.yaml`) arrives with this version, together with the changes below.
**Read those notes before upgrading if you use inheritance**, because that part
needs a migration step.

## Declaring capability changes in a child project's ledger

A work item on a board whose project keeps no capabilities ledger of its own —
a repository root that groups several packages, for example — can now say which
capabilities it changes in each package's ledger. Start the path in the item's
`capabilities.yaml` with the package's project id, such as
`proposit-shared/authoring/add-a-claim`, and `tcw work complete` checks it in that
package's ledger. You reconcile it by running `tcw capabilities set` inside the
package's folder.

The completion check also finds a ledger that has been moved with
`capabilities.path` or kept in another repository, which it used to skip.

**What may now refuse a completion that used to pass:**

- On a project with no ledger of its own, a `capabilities.yaml` path without a
  child project id at the front. Nothing could ever check it, so it is refused
  rather than waved through. Add the child's id, or complete with `--force`.
- A `removed:` path naming a capability the ledger inherits from another
  project. `tcw capabilities rm` cannot delete those, so the path could never
  honestly be satisfied.
- A path whose first part is both a child project's id and a namespace your own
  ledger already shows. It is refused as ambiguous rather than guessed at.

Discarding an item is never blocked by any of these; they print as warnings.
