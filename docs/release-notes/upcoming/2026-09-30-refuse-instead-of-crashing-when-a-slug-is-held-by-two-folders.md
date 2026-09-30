## Fixes

- If an item's folder ends up copied into two places, `tcw work list` still
  shows your board instead of crashing, with that item marked. Starting,
  submitting or otherwise changing it now stops with a short message naming both
  folders and pointing at `tcw validate`, instead of a Python error.
- An item blocked by such an item now says why it is still blocked. The local
  web app keeps showing the board too, and opening the duplicated item explains
  the problem instead of showing a server error.
