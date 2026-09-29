## Fixes

- One work item with a damaged file — a `state.yaml` or request that is not
  valid text, or a folder where a file should be — no longer stops
  `tcw work list` from showing every other item, and `tcw work show` still shows
  it. `tcw validate` is where the damage is reported, and starting, submitting
  or completing such an item is refused, naming the file, until it is fixed.
- In the web app, such an item's page now opens, and saving over a damaged
  document replaces it, so the web app can repair one.
