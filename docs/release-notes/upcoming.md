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

## An interrupted save no longer leaves something half-written

If TCW is interrupted while saving — the disk fills up, a file cannot be written
because of a permissions problem — the work item, term, or capability it was
saving is now left exactly as it was, instead of half-saved. Before this, a save
that failed partway through could leave an item whose details had been updated
but whose request document had not, or leave a brand-new item behind as an empty
shell on the board.

One honest limit: this covers a save that fails. A machine losing power during
the final instant of a save is still not covered.
