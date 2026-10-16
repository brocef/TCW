# Follow renamed slugs in the web app, tracker verbs and capability drift check

## What is wanted

After `tcw work rename` (#70), an item's old slug should keep working everywhere
a user might still use it, as it already does in the CLI (`_resolve` follows a
renamed slug for reads and names the new slug for writes) and in blockers and
`tcw://` links (through `renames.yaml`).

**Decided with the maintainer at triage:** one item covering all four of these:

1. **The web app's item routes** (`work.get(slug)`): a bookmarked `/work/<old>`
   link returns 404 today.
2. **The tracker verbs** (`_item_or_reason`): they refuse the old slug with a
   generic "no such item" instead of naming the new one.
3. **The capability drift check** (`tcw/capabilities/cli.py`): a
   `Planning doc:` value the rename could not rewrite (a quoted or qualified
   value) is not followed.
4. **External blockers written as `tcw://` links**: they accept only
   `<project-id>/<slug>` today, although a user might reasonably write a
   `tcw://` spelling.

## Notes

- Items 1-3 are a follow-up from #70; item 4 came from that change's review.
- Reference material: asked; none provided beyond the entry.
