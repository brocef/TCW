# Upcoming

User-facing release notes for the next version. Plain language — no jargon or
internal module names.

## Rename a work item from the command line

You can now change a work item's title after you create it:

```
tcw work edit <item> --title "A clearer title"
```

The item's ID stays the same, so anything already pointing at it keeps working —
only the name shown on the board changes. Until now the only way to fix a title
was through the web app.

The heading inside the item's own request document is yours to edit; renaming an
item leaves it alone.
