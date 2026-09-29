## Fixes

- **The line `tcw work` prints after creating or moving an item now names the
  real next step.** After `tcw work start` it used to say to run
  `tcw work complete`, which skipped building and checking the work. Now `new`
  and `inbox accept` point at the request stage, `start` at the first stage the
  item still needs, `submit` at the verify stage, and `rework` at the implement
  stage. The line after `submit` no longer tells you to delete a file that does
  not exist yet.
- **`tcw work submit` and `tcw work rework` say where the item went.** Like
  `start` and `complete`, they now print the item's new folder, so you write the
  next document in the right place.
- **`tcw work complete --confirm` says what it did with the Definition of Done.**
  It used to print the checklist with empty boxes and then complete anyway, and
  printed the same empty list above unrelated refusals. Now, with `--confirm`,
  the list appears only once the item has actually closed, with each entry
  ticked. Without `--confirm`, nothing changes.
