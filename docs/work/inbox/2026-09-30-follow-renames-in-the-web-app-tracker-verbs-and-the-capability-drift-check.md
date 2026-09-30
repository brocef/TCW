# Follow renames in the web app, tracker verbs and the capability drift check

Follow-up from #70 (`tcw work rename`).

The CLI's `_resolve` follows a renamed slug for reads and names the new slug
for writes, and blockers and `tcw://` links follow `renames.yaml`. Three
readers do not:

- the web app's item routes (`work.get(slug)`), so a bookmarked
  `/work/<old>` link 404s;
- the tracker verbs (`_item_or_reason`), which refuse the old slug with a
  generic "no such item" instead of naming the new one;
- the capability drift check (`tcw/capabilities/cli.py`), for a
  `Planning doc:` the rename could not rewrite (a quoted or qualified value).

Also from review: external blockers accept only `<project-id>/<slug>`, never a
`tcw://` spelling, although a user might reasonably write one.
