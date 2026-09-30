## Improvements

- **An item started before it was written up can still get its request.**
  `tcw work stage gate request <slug>` now runs on an active item, as `spec`
  and `plan` already did. `tcw work start` warns about a missing request as it
  does about a missing spec or plan, and points you at the `request` stage
  first.
- **A stage refused for an item's status now says what to do.** For example,
  `spec` on an item in review suggests `tcw work rework` to send it back, or
  `tcw work stage prompt spec <slug>` to read the instructions without the
  gate.
