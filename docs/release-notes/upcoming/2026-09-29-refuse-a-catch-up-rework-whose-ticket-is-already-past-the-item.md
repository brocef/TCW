## Fixes

- **Sending work back to in-progress works on older Jira links.** An item linked
  to its ticket by an older version (marked `catch-up`) could not be sent back from
  review with `tcw work rework`: the item moved, but the ticket stayed in review and
  a conflict was recorded that then blocked later moves. The ticket now moves back
  as it does for any other link, and a conflict left by the old behavior clears the
  next time you run `tcw work tracker sync`.
