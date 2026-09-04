Found by a third adversarial review, 2026-09-04. The same class of thing this
branch has been fixing throughout: prose that was true when written and survived
the change that falsified it.

**False:**

1. `_extended_component_stores`' docstring still explains "`seen_nodes` carries
   the *projects* already on the federation path". The parameter is now `walk`,
   and the sentence describes a name that no longer exists.
2. `hook_env` asserts "**Every** transition has an item folder, and every caller
   passes it" and, six lines later, "A caller with no answer — the item is
   already gone — passes None and the variable is absent". Both cannot hold.
   `tcw work delete`'s resume path is the second case, and it is observable: the
   binding's `"$TCW_ITEM_PATH"` expands to empty (`mv: cannot stat ''`).

**Dead:**

3. `describe_location`'s `if not location:` branch is unreachable from the CLI.
   Both callers guard — `_show` on `if grave.location:`, and `_delete` reaches it
   only under `not pending_removal(...)`, which for an absent item implies a
   non-empty location. Only a test calls it.
4. `misdirected()`'s `cfg.path == Path(str(entry.locator)) / SENTINEL` can never
   be true. An entry reaches `_unreachable` only from the `not path.is_file()`
   branch of `_read_config`, while `cfg.path` is by construction a file that was
   read.

Items 3 and 4 are each a branch whose presence tells a reader that a state is
possible when it is not. Decide per branch whether to delete it or to make it
reachable — item 3's wording is the honest answer for a tombstone with no
location, and the reason nothing reaches it may be that `_show` guards too early.
