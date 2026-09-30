## New

- **Rename a work item: `tcw work rename <slug> <new-slug>`.**
  - When an item's scope changes, its slug can now follow. The item keeps its
    date.
  - Everything on the board that names the item is updated in the same
    commit.
  - The old slug keeps working for reading and for other projects' blockers,
    and any command that would change the item under its old name tells you
    the new one.
