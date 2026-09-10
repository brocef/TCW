# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Fixed

- **Store resolution consults the project registry before the provisioned
  checkout.** `resolve_store` gained a rung between the configured
  `<component>.path` and `provisioned_store_root`: it asks the registry which
  project is a checkout of the declared repository and descends to the store's
  path within it. A workspace laid out flat where its configuration describes it
  nested previously cloned a second copy of a repository the same command had
  located via `TCW_PROJECT_*` moments earlier. Applies to all three components,
  since the ladder is one function.
- **A store resolved that way does not publish.** The rung passes no
  `declaration` to `_open_at`, which is the only thing `FsWorkStore.publishes`
  consults. The previous behaviour reached the store through rule 2, which does
  carry the declaration, so a transition committed and pushed to the declared
  ref instead of landing on the working branch.
- **A configured path that exists but holds no store is reported.** The rung-1
  `StoreLocationUnusable` is carried into `StoreNotProvisioned` rather than
  discarded, and `tcw validate` checks the configured path independently of
  resolution so two faults count as two. Independence covers the case where the
  declaration resolves successfully and the broken path would otherwise never
  surface. A path that does not exist stays silent, tested by presence rather
  than by matching the message, because `_open_at` raises identical text for an
  absent path and a file.
- **`work.path is not a work store` now names the directory.** The other two
  branches of that check always did; this one reported the fault without saying
  which path it referred to, which matters most when the value is relative and
  resolves somewhere unexpected.

## Internal

- `checkouts.normalized_url` compares two repository URLs for identity across a
  `.git` suffix, a trailing slash, and `git@host:owner/repo` versus
  `https://host/owner/repo`. Deliberately **not** shared with `_cache_key`,
  which hashes the raw URL and so keeps those spellings apart on purpose;
  routing that digest through a shared normalizer would rename every provisioned
  cache directory at once. `test_the_cache_key_is_unchanged` pins the existing
  names literally.
- `FsProjectRegistry.checkout_of` answers which project in the graph is a
  checkout of a given repository URL, resolved location rather than declared
  locator so `TCW_PROJECT_*` is honoured. Kept off the abstract
  `ProjectRegistry`: it reads a declaration URL and returns a locator, both
  adapter-private, and its only caller is the same adapter.
- `tcw provision` needed no change. Its component loop already asks the
  resolution ladder before provisioning, so it reports a registry-resolved store
  as already available and contacts nothing.
