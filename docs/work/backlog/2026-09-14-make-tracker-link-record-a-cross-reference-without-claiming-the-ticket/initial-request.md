# Make `tracker link` record a cross-reference without claiming the ticket

## What is being asked for

`tcw work tracker link` should do one thing: write down that a work item and a
tracker ticket are the same piece of work. Today it also takes the ticket —
transitioning it to the in-progress status and assigning it to the caller — and
refuses to bind at all unless that claim succeeds.

That makes recording a cross-reference impossible without announcing that the
work has started. The requester wanted Jira tickets for the ten or so backlog
items expected next, each linked to its item so the tracker would show what is
queued. Every one of those items is in `backlog`. Running `link` against tickets
in `To Do` would have moved all ten to `In Progress` and assigned them, so the
tracker would have reported nine or ten pieces of work under way when none were.

The only way through was an accident of the claim rules: a ticket in a status
that does not offer the claim transition, already assigned to the caller by a
component default, binds without any transition. That path depends on two
coincidences and is not a way to work.

So: **a link is a reference, not a commitment.** It should be possible to say
"this item is that ticket" at any point in an item's life, including before work
starts and after it is finished, without the tracker or the work item changing.

## What the requester wants to be true afterwards

- **Linking writes the binding and nothing else.** No tracker transition, no
  change to the ticket's assignee, and no change to the work item — not its
  status, owner, lifecycle stage, or any of its intake, request, spec or plan
  documents.
- **Linking works at any status except the inbox.** `backlog`, `active` and
  `review`, and the resolved `completed` and `discarded` too. Linking finished
  work to the ticket that tracked it is a normal thing to want. An inbox entry
  is not a work item and has no slug to bind, so it stays out.
- **Unlinking works at those same statuses**, for the same reason: otherwise a
  wrong binding on a finished item can never be repaired.
- **A ticket held by someone else can be linked.** Recording a reference takes
  the ticket from nobody, so there is no reason to refuse it. `import`, which
  does claim, keeps refusing it.
- **The binding file does not claim a claim happened.** `tracker.yaml` currently
  carries a `claimed-by` block naming the tracker account that took the ticket.
  Drop it — from `import`'s bindings as well as `link`'s. Who holds a ticket is
  the tracker's own assignee field and is readable with `tracker show`; the
  binding's job is to say which item is which ticket.
- **Every `tracker` subcommand explains itself in `--help`.** Right now
  `tracker link --help` prints argument names and nothing else — no description,
  no statement that it moves and assigns the ticket, which is the single most
  important thing to know before running it. `import` and `unlink` have the same
  gap. Each subcommand should give: what it does, including every change it makes
  in the tracker and in the work store; what each argument is; when `--part` is
  needed and an example of it; the main reasons it refuses; and an example
  invocation or two.

## Claiming, after this

Claiming does not disappear — it moves. `import` keeps claiming, because it
creates a new item from a ticket somebody chose to take. For an item that is
already linked, claiming belongs to `tcw work start`, and wiring that up is the
job of `2026-09-12-synchronize-the-work-lifecycle-outward-to-the-tracker`, which
is already going to touch it. **This item does not add a new claiming verb and
does not change `start`.** Between this item shipping and that one,
`tracker import` is the only path that claims — the requester accepts that gap.

## The guards that stay

These refusals are not part of the claim and should survive unchanged: an item
that is already bound to a ticket; a ticket and part already bound to some other
item; a binding file that cannot be read; and an invalid `--part`.

## Out of scope

- Adding a `tracker claim <slug>` verb, or any change to `tcw work start`.
- Anything about which Jira site a binding belongs to — that is the separate
  inbox entry `2026-09-14-a-tracker-binding-does-not-record-its-site.md`.
- Migrating existing `tracker.yaml` files. Nobody is on this version, so
  dropping `claimed-by` needs no compatibility path.

## Notes

- The requester was asked for reference material beyond what the intake already
  cites and had none to add.
- The requester's first phrasing of the `claimed-by` decision described it as a
  record of which user claimed a *work item*; it is in fact the tracker account
  that claimed the *ticket*, and `import` still claims. The decision to drop it
  everywhere was re-confirmed against that correction.
- The intake's own verification of the current behaviour was re-checked against
  the working tree while accepting it, and holds: `_tracker_link` calls `claim`
  and returns non-zero unless `outcome.claimed`; `_unresolved_item` refuses both
  resolved statuses for `link` and `unlink` alike.

## References

- `tcw/work/cli.py` — `_tracker_link` and `_unresolved_item` are what this item
  changes, and the `tracker` subparser registrations are where the missing help
  text would go.
- `tcw/tracker/intake.py` — `claim` holds the numbered decision rows the intake
  cites (`1b` assigned elsewhere, `1e` the side door the requester had to use,
  `1f` its unassigned refusal), and `binding_document` is what writes
  `claimed-by`.
- `2026-09-12-synchronize-the-work-lifecycle-outward-to-the-tracker` — where
  claiming lands once `link` stops doing it; the two need to agree about who
  claims and when.
- `2026-08-04-supplement-filesystem-tcw-work-with-an-external-tracker-bridge` —
  the owning epic, which declares the tracker capabilities this behaviour sits
  under.
