# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Added

- **Progress comments on tickets.** With `comments: true` in a project's tracker
  settings, starting, submitting, reworking, completing or discarding a linked item
  also leaves a one-line comment on its Jira ticket, with an optional link you
  choose. No lifecycle documents are copied, a comment is posted only while the
  ticket is yours, and one that could not be posted is sent later by
  `tcw work tracker sync` without repeating itself. Upgrade every copy of `tcw` on a
  project before turning this on: older copies treat the new settings as a broken
  tracker block.
- **Strict tracker mode.** Setting `strict: true` in a project's tracker settings
  means no work happens without a Jira ticket you have claimed. New items come only
  from `tcw work tracker import`; starting an item claims its ticket first; submitting,
  reworking and completing check the ticket is still yours and where the item left
  it; and the web app sends you to the command line for those steps. When something
  is refused, nothing changes and the message says what to fix. Discarding an item is
  always allowed. Strict mode needs Jira to be reachable.
- **Tickets follow their work items.** Starting an item linked to a Jira ticket now
  takes that ticket for you, and submitting, reworking, completing or discarding the
  item moves the ticket to the status you choose for each step in `tcw-config.yaml`.
  Your own work always moves first: if Jira is down, or the ticket is held by someone
  else or was moved in Jira, the command still finishes locally, tells you the ticket
  did not follow, and shows it on the board. `tcw work tracker sync` tries again once
  the problem is fixed. TCW never moves a ticket that somebody else has, and never
  moves one back from where a person put it.
- **Stale ticket links are caught.** If a project's Jira site changes, an item still
  linked to a ticket on the old site is no longer mistaken for a different ticket
  with the same number on the new one.

- **See which ticket an item belongs to.** An item linked to a Jira ticket now shows
  that ticket in `tcw work show`, at the end of its row in `tcw work list`, in
  `tcw work show --json`, and as a link on its page in `tcw serve`. Items with no
  ticket look exactly as before on the board and in `show`.
