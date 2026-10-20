## Fixed

- The web viewer's development tooling no longer uses versions with known
  security problems: `vite` 7.3.6 → 7.3.7 (GitHub's Dependabot alerts 81 to
  86) and `source-map-js`, which `vite` uses through `postcss`, 1.2.1 → 1.2.2
  (alert 80, an event-loop denial of service). `@babel/runtime` moved from
  7.29.7 to 7.29.10 in the same lockfile refresh. These are development
  dependencies only: the built viewer TCW ships is unchanged.
- A `tcw taxonomy rm`, `tcw capabilities rm` or `tcw capabilities reset`
  that cannot delete everything now deletes everything it can before
  reporting what is left. Before, it stopped at the first file it could not
  delete, so on Python 3.11 under Linux it could delete nothing and still
  call the removal partial. `tests/test_partial_removal.py` checks that only
  the undeletable folder's files are left, and adds a case that lists folders
  first, the order Linux used.

## Internal

- `tests/work/test_no_2x_names.py`: the check that `tcw.tracker` is gone no
  longer fails in a checkout that git moved past the package's deletion while
  its ignored `__pycache__/` stayed behind; it still fails if the folder holds
  source.
