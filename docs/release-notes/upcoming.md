# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Strict mode needs one more setting

- **Breaking change for projects that set `strict: true`.** Strict mode now needs
  `work.tracker.exclusive-claim-transition`. Until it is set, `tcw validate`
  reports it missing, and every command strict mode checks refuses and tells you to
  run `tcw validate`. Projects that do not use strict mode are not affected.
- **Why.** Strict mode promises that only one person can take a ticket. A
  transition your workflow will not apply to a ticket someone has already taken is
  what stops a second person, so strict mode now insists you name one.
- **What to set.** The transition your workflow uses to take a ticket into work,
  one it will not apply to a ticket already taken:

  ```yaml
  work:
    tracker:
      strict: true
      exclusive-claim-transition: Start Progress
  ```
- **What it costs.** With it set, `tcw work tracker claim` applies that transition,
  so claiming a ticket moves it.

## Taking a ticket and moving it are separate

- **A strict `tcw work start` now takes its ticket through
  `exclusive-claim-transition`.** Before it moves the item, it applies that
  transition and then assigns the ticket to you. A workflow that will not apply
  the transition to a ticket somebody already took refuses the second person
  there, and their item does not move. That is what makes the setting required.
- **Claiming a ticket no longer moves it**, unless that setting names a
  transition. `tcw work start` assigns the ticket to you, then moves it to your
  `active` status as an ordinary move. A ticket already past `active` — in review,
  say — is claimed and left where it is. No lifecycle move takes a ticket back out
  of its own window: `tcw work rework` still brings a ticket from your review
  status down to your active status, because that is what a rework is, but nothing
  drags a ticket back because somebody else moved it on. `tcw work tracker sync`
  has no window and reconciles both ways, because that is what you run it for.
- **`exclusive-claim-transition` is never applied to a ticket already past your
  `active` status.** It leads onto that status, so applying it from above would
  move the ticket backwards. Without strict mode the transition is skipped, the
  ticket is taken by the assignment alone and left where it is, and the output says
  so. Under strict mode `tcw work start` is refused before the item moves, because
  an assignment on its own is not the exclusivity strict mode promises; the message
  tells you to move the ticket back in Jira or turn strict mode off.
- **If a claim's transition lands and the assignment then fails, TCW says so.**
  With `exclusive-claim-transition` set, the transition goes first, so a failed
  assignment leaves the ticket moved and held by nobody. The message now names the
  status it was moved to and tells you to assign it to yourself in Jira, because
  running the command again cannot finish the claim: the transition is no longer
  offered from where the ticket now sits, which is exactly what makes it exclusive.
- **`submit` and `rework` need the ticket to be yours**, with or without strict
  mode. For an item with a ticket, they are refused before the item moves when the
  ticket is somebody else's (the message names them) or nobody's (the message
  names `tcw work tracker claim`). If Jira cannot be reached, what happens depends
  on the mode: without strict mode they go ahead, as before, and report that the
  ticket did not follow; under strict mode they are refused and the item does not
  move, which is what strict mode has always done with a tracker that cannot
  answer.
- **`complete` and discards need no claim.** They move the ticket whoever holds
  it, and leave the assignment alone. Under strict mode, completing work is no
  longer refused because somebody else holds the ticket.
- **`tcw work start` on an active item nobody holds takes it** instead of
  refusing — that is what `tcw work tracker release` leaves. An item somebody else
  holds is still refused, and the message now names
  `tcw work tracker claim <slug> --take-over`.
- **`tcw work tracker link --sync-status` is retired.** Run
  `tcw work tracker link <slug> <KEY>`, then `tcw work tracker claim <slug>`, then
  `tcw work tracker sync <slug>`. Using the old flag refuses and names those three
  commands. Tickets linked with it by an earlier version keep working.
