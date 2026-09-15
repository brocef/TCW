# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Your Jira tickets keep up with your work in more of the ordinary cases

**You can say which transition a move should use.** Lots of Jira workflows have two
ways to reach `Done` — one for finished work, one for abandoned work. TCW would not
guess between them, so completing or discarding an item could never reach the
ticket. Now you can name the transition for each move, and name a different one for
each kind of discard so the ticket ends with the right resolution. Anything you do
not name keeps working exactly as before.

**A ticket you link to work already under way is brought up to date.** Linking is how
you tie an existing item to its ticket, and existing work is often already started.
Before, the ticket stayed where it was for good and every later move was reported as
a conflict that blamed you for moving it. Now TCW claims the ticket and walks it
forward to where the item is, one step at a time, through the statuses you mapped.

**Moving a ticket part of the way by hand is no longer treated as interference.** If
a move failed to reach Jira and you moved the ticket yourself to the next status
along, TCW now finishes the journey instead of reporting that somebody moved it.

**Discarding work whose ticket nobody is assigned now closes the ticket.** Teams
whose queue hands out unassigned tickets were left with every such ticket open and
unresolved. A discard can now close one — and says why on the ticket. Every other
kind of move still leaves an unassigned ticket alone, and a ticket somebody else is
assigned is never touched.

**`tcw work tracker sync <slug>` no longer reports success when it did nothing.**
Naming an item somebody else started now fails, tells you what is still owed, and
tells you how to run it as them or take the item over.
