## Fixed

- The web viewer's development tooling no longer uses versions with known
  security problems: `vite` 7.3.6 → 7.3.7 (GitHub's Dependabot alerts 81 to
  86) and `source-map-js`, which `vite` uses through `postcss`, 1.2.1 → 1.2.2
  (alert 80, an event-loop denial of service). `@babel/runtime` moved from
  7.29.7 to 7.29.10 in the same lockfile refresh. These are development
  dependencies only: the built viewer TCW ships is unchanged.

## Internal

- `tests/work/test_no_2x_names.py`: the check that `tcw.tracker` is gone no
  longer fails in a checkout that git moved past the package's deletion while
  its ignored `__pycache__/` stayed behind; it still fails if the folder holds
  source.
