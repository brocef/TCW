# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Added

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
