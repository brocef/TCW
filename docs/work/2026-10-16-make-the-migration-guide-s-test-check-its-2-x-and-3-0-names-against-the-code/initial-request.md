# Make the migration guide's test check its 2.x and 3.0 names against the code

Raised by TCW-76's guide review (Task A9, 2026-10-16), and deferred as a
separate change. `tests/test_migration_guide.py` can pass while
`docs/migration-guide-2.8-to-3.0.0.md` is wrong:

- its list of 2.x names (`TWO_X_NAMES`) is written by hand, holds no 2.8
  command and none of 2.8's resolutions, so a missing row in the Commands
  table passes;
- one table row can satisfy a name that appears twice (`project`, `created`,
  `start`, `transitions`);
- any non-empty second column passes: no 3.0 name is checked against the 3.0
  code, so a wrong hook variable or default would pass;
- the step checks are never run, only checked for a backtick and the word
  "prints".

Wanted: generate the 2.x names from v2.8.1's own source (`git show
v2.8.1:...`: the CLI's commands, the config keys, the hook variables, the
resolutions), check each 3.0 name in the second column against the 3.0 code,
and run the filesystem-mode checks against a rehearsal fixture.
