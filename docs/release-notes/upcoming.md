# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

**This is the release v2.5.0 was meant to be.** v2.5.0 was tagged but never
reached PyPI, because a test that only failed on the build server stopped the
upload. Everything described in the [v2.5.0 notes](v2.5.0.md) (making Jira
tickets with `tcw work tracker create`, and moving `extends` into
`tcw-config.yaml`) arrives with this version, together with the changes below.
**Read those notes before upgrading if you use inheritance**, because that part
needs a migration step. The first two sections below follow on from it.

## An old inheritance file is now pointed out

Before 2.5.0, a project that inherited another project's taxonomy or
capabilities listed it in a file inside the tree:
`docs/taxonomy/config.yaml` or `docs/capabilities/.config.yaml` (or the same
file wherever you keep that tree). 2.5.0 stopped reading those files, and a
project that did not move the list lost every inherited entry without a word.

Now `tcw taxonomy check`, `tcw capabilities check` and `tcw validate` report
such a file, and tell you what to do: copy any `extends` you still need into
`tcw-config.yaml` (under `taxonomy:` or `capabilities:`), then delete the file.
If you already copied it, just delete the file.

**This can make a previously passing project fail.** A file you migrated but
kept now fails `check` and `validate` until it is deleted — and so it can stop
`tcw work complete` in any project that runs `tcw validate` before completing.
TCW never edits or deletes the file for you.

Two smaller changes come with it:

- `tcw validate` now looks at a taxonomy or capabilities tree it used to skip —
  one kept outside `docs/` — and reports it if the tree cannot be opened. That
  covers three situations: the tree is kept in another repository and has not
  been downloaded to this machine yet (it tells you to run `tcw provision`, as
  it already did for the work board); `taxonomy.path` or `capabilities.path`
  points at a folder that is not there, such as a sibling checkout a CI or
  cloud copy does not have; and the project inherits from a project this
  checkout cannot reach. In a project that runs `tcw validate` before
  completing work, any of these can stop `tcw work complete` until it is
  fixed.
- When a capability overrides one from a project you do not inherit from, the
  "unknown alias" problem now says the project is missing from
  `capabilities.extends` in `tcw-config.yaml`.

## Your comments in `tcw-config.yaml` are kept

The commands that add a setting to `tcw-config.yaml` used to rewrite the whole
file, which deleted every comment, re-wrapped long lines and changed the
indentation. That hit `tcw taxonomy extends add`, `tcw capabilities extends`
(the easy route in the v2.5.0 migration guide) and `tcw work tags add`. Now they
change only the lines of the setting they write — and so do their removal
counterparts and `tcw init` — and leave the rest of the file exactly as you
wrote it, down to the line endings.

If a file is laid out in a way the command cannot edit safely — for example a
section written on one line in braces, like `taxonomy: {path: docs/taxonomy}` —
it stops without changing anything and tells you the exact edit to make by hand.

Three hand-written shapes that used to be quietly overwritten now get that
message instead: a `work:` line holding a single value rather than settings
beneath it (when registering tags or running `tcw init --work-path`), a `tags:`
that is not a list, and the same single-value shape for `taxonomy:` or
`capabilities:` when `tcw init` sets its location.

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

## A warning when the `tcw` command and the plugin's skills differ

Your agent now tells you when the `tcw` command and the plugin's skills come
from different releases. It names both versions and how to bring them into
line — updating the plugin, or upgrading the `tcw` command — with the exact
commands to run. It is only a warning and never stops your work. Claude shows it
when a session starts; in Codex, the skills ask the agent to run the check.

## A refused `tcw work drop` now tells you how to discard

`tcw work drop` only deletes items still in the backlog. For an item you have
started, or sent to review, it used to refuse without saying what to do instead.
Now it names the command that works:
`tcw work complete <slug> --resolution wontfix --confirm`, which discards the item,
keeps a record of it, and updates a linked ticket. Reported from real use in the
proposit-app project.

If the item has child items, it says so straight away instead of after you add
`--confirm`, and names any children you must finish or discard first.
