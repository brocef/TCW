## Fixes

- If Jira answers a ticket creation with something unexpected, TCW now warns
  that the ticket may still have been made and tells you what to look for,
  instead of a generic error.
- `tcw work tracker show` and the other tracker commands report a Jira answer
  with a value of the wrong type as a tracker problem, instead of crashing.
- When filing an item makes its ticket but cannot record the link, the message
  no longer says the ticket was not created.
- In strict tracker mode, refusing to drop an item whose `tracker.yaml` cannot
  be read now says the file cannot be read, rather than that the item is bound
  to a ticket.
