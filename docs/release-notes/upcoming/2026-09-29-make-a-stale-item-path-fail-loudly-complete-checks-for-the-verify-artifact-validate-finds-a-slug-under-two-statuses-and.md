## Improvements

- **Completing reviewed work now needs its acceptance record.**
  `tcw work complete --resolution done` on an item in review refuses until
  `refined-outcome.md` is in the item's folder. The refusal says where that
  folder is, and points out a copy written to the folder the item left behind
  at `submit`. `--force` still goes ahead.
- **Folder paths printed by `tcw work` commands work from where you are**,
  including from a parent project.

## Fixes

- `tcw validate` no longer crashes when two folders hold the same item; it
  names both. It also reports files left in an item's old folder.
