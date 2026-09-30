## Fixes

- **A blocker is no longer accepted unchecked when an item it leads to is
  damaged.** If an item on the chain a new blocker leads into has a
  `state.yaml` that cannot be read (or its slug is held by two folders), TCW
  cannot tell whether the blocker would make a loop, and used to accept it
  anyway. It now refuses the edit and names the item to fix; `tcw validate`
  lists it. A loop found through the rest of the chain is still reported as a
  loop.
