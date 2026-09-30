## Fixes

- **A blocker loop between projects is refused.** Making an item wait on an item
  in another connected project, which already waits on it — directly or
  through other projects — is now refused as a loop, as it already was within
  one project. Before, both items ended up blocking each other forever. The
  same check now also applies when creating an item with `--blocked-by` and in
  the web app.
