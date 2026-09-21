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
- Any path checked against a ledger kept somewhere other than
  `docs/capabilities` — moved with `capabilities.path`, or in another repository
  through `capabilities.repository`. Those ledgers used to be skipped entirely, so
  a capability still `Missing` there went through.
- Every declared path, on a project whose own ledger is declared but has not been
  fetched to this machine. Run `tcw provision` to fetch it, or complete with
  `--force`.

Discarding an item is never blocked by any of these; they print as warnings.

## Tickets waiting in Triage can be linked, synced and accepted

A Jira ticket sitting in a status before your backlog, such as **Triage**, used to
stop `tcw work tracker link --sync-status`, `tcw work tracker sync`, `tcw work
start` and `tcw work inbox accept` with a conflict, because Triage does not offer
the transition that starts work. You had to move each ticket out by hand first.

Now you can name that status and the transition out of it:

```yaml
work:
    tracker:
        statuses:
            backlog: To Do
        pre-backlog:
            Triage: Accept
```

With that set, TCW moves a ticket from Triage to your backlog status just before
claiming it, and tells you it did. Nothing happens without the setting: accepting
a ticket out of triage can be a deliberate team decision, so TCW leaves it alone and
the refusal tells you which setting would change that. Reported from real use in
the proposit-app project.

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
