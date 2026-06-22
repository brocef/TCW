# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Added

- `tcw work new` now prints an `→ edit: <abs>/content.md` hint to **stderr**
  after the slug, so the new item's body file can be opened immediately. stdout
  stays slug-only (scriptable). Backed by new `FsWorkStore.body_path(slug)` in
  `tcw/store/fs.py` (keeps the `content.md` filename in the FS adapter rather
  than leaking it into the CLI); called from `_new` in `tcw/work/cli.py`. Shown
  for epics too (which still omit the next-step line). Test:
  `test_body_path_points_at_content_md`. (`dc832d1`..HEAD)
