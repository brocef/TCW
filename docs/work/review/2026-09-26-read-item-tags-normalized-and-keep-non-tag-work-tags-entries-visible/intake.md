# Read item tags normalized and keep non-tag work.tags entries visible

Two gaps in how tags are read, found by the code review of
2026-09-15-report-malformed-keys-and-unregistered-tags-in-lifecycle-config and
placed by it in a separate change:

1. **Item tags are read raw.** `FsWorkStore` builds `WorkItem.tags` straight from
   `state.yaml` (`tags=list(state.get("tags") or [])`). Every writer normalizes,
   so only a hand edit produces `CLI`; such an item no longer matches the
   (now normalized) condition `CLI`, and `check` reports "unregistered tag
   'CLI'". Normalizing on read, or reporting the non-canonical spelling as its
   own problem, would make the two agree.
2. **`_write_tags` silently drops non-tag entries of `work.tags`.** `check` now
   reports an entry such as `7` as "not a tag", but the next `tcw work tags add`
   or `rm` rewrites the list from the normalized set and the entry disappears
   without a word. Say so when it happens, or keep it.

## References

- tcw/store/fs.py: item read (`tags=list(state.get("tags") ...)`), `_write_tags`,
  `_registered_tag_entries`
