# Read item tags normalized and keep non-tag work.tags entries visible

Fix both gaps in how tags are read before the next bugfix release is cut.

1. **Item tags are read as written.** The unreleased change
   `2026-09-15-report-malformed-keys-and-unregistered-tags-in-lifecycle-config`
   made lifecycle conditions case-insensitive: a condition written `CLI` now
   means `cli`. Item tags are still read exactly as stored in `state.yaml`, so
   an item whose tag was typed by hand as `CLI` no longer matches a condition
   written `CLI`. It matched in v2.6.2. The lifecycle rules bound to that
   condition are then skipped for that item without a word, and `check` reports
   "unregistered tag 'CLI'". The release must not ship with this.
2. **`tcw work tags add` / `rm` silently drops non-tag entries of `work.tags`.**
   `check` reports an entry such as `7` as "not a tag", but the next `add` or
   `rm` rewrites the list and the entry disappears without a word. This predates
   the release, but is cheap to settle in the same change: either keep the entry
   or say it was dropped.

## Notes

- Requested by the user on 2026-09-27, after a review of the twelve follow-ups
  from the autonomous bug run judged part 1 a regression this release would
  otherwise introduce. The user agreed to do it before cutting the version.
- `docs/changelogs/upcoming.md` currently documents part 1 as a known behavior
  change ("an item whose tags were hand-edited into a non-canonical form (`CLI`)
  no longer matches a condition written the same way"). That sentence should not
  survive the fix.
- Out of scope: cutting the version, pushing.
- Reference material: asked; none provided beyond the intake.

## References

- `intake.md` — the review finding this item was filed from.
- `tcw/store/fs.py` — the item read (`tags=list(state.get("tags") or [])`),
  `_write_tags`, `_registered_tag_entries`: where both gaps live.
