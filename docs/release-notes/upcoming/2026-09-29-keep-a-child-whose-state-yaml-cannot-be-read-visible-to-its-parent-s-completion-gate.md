## Fixed

- **An item or epic can no longer be closed over work whose record is
  damaged.** Previously, if an open child's `state.yaml` was damaged
  (unreadable, not valid text, or not a regular file), its parent could be
  completed, discarded or dropped as if that child did not exist, and so
  could an epic over such a slice, including one in a project below it. TCW
  now refuses, before anything is merged, and names each file to fix.
