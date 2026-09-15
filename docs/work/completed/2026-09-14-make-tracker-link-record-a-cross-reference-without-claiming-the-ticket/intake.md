## Inbox manifest

- `tracker-link-claims-the-ticket-so-an-unstarted-item-cannot-be-linked-without-starting-it.md`

## Inbox body

# `tracker link` claims the ticket, so an item cannot be linked without starting it

`tcw work tracker link <slug> <ticket>` does two things at once: it records the
cross-reference between a work item and a tracker ticket, and it **claims** the
ticket by the same rules as `import`. It applies `work.tracker.transitions.claim`
(moving the ticket to its in-progress status), assigns the ticket to the caller,
and refuses to bind unless the re-read shows the claim took
(`_tracker_link`, `tcw/work/cli.py:1846-1905`, calling `claim` in
`tcw/tracker/intake.py:272`).

That makes linking inseparable from starting. There is no way to say "this backlog
item is that ticket" without Jira reporting the ticket as In Progress.

## How it came up

A workspace wanted Jira tickets for the ten or so backlog items it expected to
work next, each linked to its item, so the tracker would show what is queued.
The items are all in `backlog`. Running `link` on a ticket in `To Do` would have
moved every one of them to `In Progress` and assigned them, so the tracker would
have claimed nine pieces of work were under way when none were.

The only way through was a side door. `claim` binds without a transition when the
ticket does not offer the claim and is already assigned to the caller
(`intake.py:316-319`, row `1e`, meant for finishing an interrupted claim). New
tickets in that project start in `Triage`, where `Start` is not offered, and a
component default assignee assigns them automatically. So each ticket was created,
linked while still in `Triage`, and only then moved to `To Do` by hand:

```text
$ tcw work tracker link example-backlog-item EX-6
→ EX-6 is in 'Triage', already assigned to you; bound to example-backlog-item
```

That works only by accident. It depends on the ticket being in a status that does
not offer the claim, and on Jira having assigned it already. An unassigned ticket
in the same status is refused (row `1f`).

## What `link` should do

- **Record the cross-reference and nothing else.** Write the binding
  (`tracker.yaml`) and whatever reference TCW keeps on the ticket side, if any.
  No tracker transition, and no change to the ticket's assignee.
- **Leave the work item alone.** No status change, no owner, no lifecycle stage
  advanced, no edit to intake, request, spec or plan. The binding sidecar is the
  only file written.
- **Work at any point in the lifecycle except the inbox.** `backlog`, `active`,
  `review`, and the resolved statuses `completed` and `discarded` too. An inbox
  entry is not a work item yet and has no slug to bind, so it stays out.
  Today `_unresolved_item` (`cli.py:1830-1843`) refuses both resolved statuses
  with "a resolved item's binding is not changed", which rules out linking work
  that is already finished to the ticket that tracked it.

The existing guards still make sense and should stay: an item already bound
(`cli.py:1872-1876`), a ticket and part already bound to another item
(`cli.py:1883-1886`), a malformed binding, and an invalid `--part`.

## Decisions this leaves open

- **Where claiming goes.** With `link` no longer claiming, taking a ticket needs a
  home. `import` can keep claiming, since it creates a new backlog item from a
  ticket someone chose to take. For an item that is already linked, the natural
  moment is `tcw work start`, which the planned outbound synchronization item
  (`2026-09-12-synchronize-the-work-lifecycle-outward-to-the-tracker`) already
  touches. A separate explicit verb, such as `tracker claim <slug>`, is the other
  option.
- **A ticket assigned to someone else.** `link` refuses it today as part of the
  claim (row `1b`). Recording a reference does not take the ticket from anyone,
  so there may be no reason to refuse. It is worth deciding deliberately rather
  than inheriting the claim rule.
- **What the binding records.** `tracker.yaml` has a `claimed-by` block
  (`binding_document`, `intake.py:161-174`). A link that claims nothing should
  either leave it out or name it for what it is, for example `linked-by`, so
  the file does not say a claim happened when none did.
- **`unlink` on resolved items.** It shares `_unresolved_item`, so it refuses
  resolved items the same way. If `link` accepts them, `unlink` probably should
  too, or a wrong binding on a finished item cannot be repaired.

## The `tracker` help output needs work

`tcw work tracker link --help` prints only argument names, with no description
of what the command does, what its arguments are, or its side effects:

```text
usage: tcw work tracker link [-h] [--part PART] slug ticket

positional arguments:
  slug
  ticket

options:
  -h, --help   show this help message and exit
  --part PART  which of several items for this ticket (default: default)
```

Nothing here says the command moves the ticket in the tracker and assigns it,
which is the single most important thing to know before running it. `import`
(`ticket` undescribed) and `unlink` (`slug` undescribed) have the same gap. For
each `tracker` subcommand the help should give:

- a one-paragraph description of what the command does, including every change it
  makes in the tracker and in the work store;
- what each positional argument is: a work item slug in the current node, and a
  ticket key such as `EX-123`;
- when `--part` is needed, with an example;
- the main reasons it refuses;
- one or two example invocations.

`argparse`'s `description=` and `epilog=` with `RawDescriptionHelpFormatter`
(where the `tracker` parsers are registered, `cli.py:2233-2258`) carry this without
changing how the commands behave.

Storage-abstracted: the binding is already written through `write_sidecar`, and
the proposed change removes tracker calls rather than adding store operations, so
nothing here is filesystem-specific.
