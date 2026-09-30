## Fixes

- If an item's folder ends up copied into two places, `tcw work list` still
  shows your board instead of crashing, with that item marked. Starting,
  submitting or otherwise changing it now stops with a short message naming both
  folders and pointing at `tcw validate`, instead of a Python error.
