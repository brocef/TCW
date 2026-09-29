## Fixed

- `tcw work edit --untag` matches each value against the item's tags as written
  before splitting and normalizing it, so a held tag that is not a valid tag
  (`'cli,docs'`, `'!!!'`, which `read_tags` keeps as text) can be removed. The
  option no longer normalizes at parse time; an invalid value the item does not
  hold is refused by the command (exit 1) rather than by argparse (exit 2).
- `FsWorkStore.update_work` validates only the tags an edit adds:
  `_validate_tags(tags, held=…)` keeps a tag the item already holds as it
  stands. One bad hand-written tag no longer refuses every `--tag`, every web
  save that resends the tags, and every partial `--untag`.
