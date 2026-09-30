## Fixed

- Blocker cycles through items in other connected projects are refused. The
  cycle walk (`WorkStore._reaches`) now follows (store, slug) pairs through a
  new `WorkStore._blocker_target(entry)` hook; `FsWorkStore` extends it for
  `external: <project-id>/<slug>` entries, resolved from the node that holds the
  entry by `_qualified_target`, which `external_blocker_state` now shares.
  Stores are compared by `_store_key()` — folder identity in the filesystem
  adapter. A failure reading an item, in this store or another, leaves it unfollowed.
- The base `_blocker_target` also follows a slug-shaped bare `external` entry,
  including one naming an item not created yet.
- `create_work` (`tcw work new --blocked-by`, the web app's `POST`) checks each
  new blocker for a cycle once the slug is known, before writing; it previously
  checked none.
