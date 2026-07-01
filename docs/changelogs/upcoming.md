# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Changed

<changes starting-hash="6b86dbc" ending-hash="6b86dbc">

- `tcw work new`/`edit` `--effort` and `--complexity` now accept case-insensitive
  `L`/`M`/`H`/`VH` shorthand in addition to the canonical `low`/`medium`/`high`/
  `very-high`. Input normalization only — the stored/displayed value stays
  canonical. New `normalize_work_level(value)` + `WORK_LEVEL_ALIASES` in
  `tcw/store/base.py` are the shared source of truth (framework-free: raises
  `ValueError`, no argparse dependency in the store layer). `tcw/work/cli.py`
  wraps it in `_work_level()` (re-raising as `argparse.ArgumentTypeError` for a
  clean CLI message) and swaps the four flag definitions from
  `choices=WORK_LEVELS` to `type=_work_level`; help text advertises the shorthand.

</changes>
