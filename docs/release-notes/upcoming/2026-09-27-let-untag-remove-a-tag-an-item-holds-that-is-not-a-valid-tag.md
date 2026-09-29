## Fixes

- A tag typed by hand into an item that is not a valid tag — `cli,docs`, `!!!` —
  can now be removed with `tcw work edit <item> --untag 'cli,docs'`, and no
  longer stops every other edit of that item, in the CLI or the web app, until
  you fix the file by hand.
