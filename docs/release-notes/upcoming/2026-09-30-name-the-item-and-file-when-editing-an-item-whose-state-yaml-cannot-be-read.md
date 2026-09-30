## Fixes

- When an item's `state.yaml` file is damaged, `tcw work edit` now tells you
  which item and which file it could not read, and that `tcw validate` lists
  them, instead of a bare error from the file reader. Errors in other TCW files,
  such as `tcw-config.yaml`, now name the file too.
