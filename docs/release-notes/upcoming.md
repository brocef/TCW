# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## The people who file your issues now hear back when the work ships

`/tcw-triage-issues` turns a GitHub issue into a work item and tells the reporter
it is being tracked. That was a promise with nothing behind it: the item could
ship weeks later and the issue would sit there, open and silent.

Closing a work item now includes answering the issue it came from. What gets said
depends on how the item actually closed — it shipped, it was folded into
something else, it was declined, or it was replaced by different work. Most of
those close the issue. One deliberately does not: if the item was superseded and
the replacement **postponed** the request rather than taking it on, the issue
stays open, because telling someone their request was refused when it was merely
deferred is worse than saying nothing. As always, nothing is posted until you
approve the exact wording.

## Your completion checklist was configurable all along

`tcw work complete` prints a Definition of Done and won't finish until you
confirm it. That list has always been yours to set — put your own in
`docs/work/dod.yaml`, one line per item — but nothing said so anywhere, so
effectively nobody could.

Now it is written down, including the two parts that bite:

- The file **replaces** the built-in list rather than adding to it. Leave an item
  out and that check quietly disappears from every completion.
- It only appears when you finish work as *done*. Dropping an item instead — as
  declined, duplicate, or superseded — prints no checklist at all.
