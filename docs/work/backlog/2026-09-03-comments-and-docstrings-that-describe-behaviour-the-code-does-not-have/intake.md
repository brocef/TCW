Found by two adversarial reviews, 2026-09-03. Each is a comment a future reader
would rely on and be wrong.

1. **`WorkStore.transition`'s fallback.** Its comment says "Under
   `work.retain: false` the item is gone by the time the move returns". The
   store deliberately never deletes during a transition — `pending_deletion`'s
   own docstring says so — and deletion is a separate CLI call. So the only way
   `get(slug)` is None there is a *concurrent* removal, where the old
   `_require` raised accurately and the new code fabricates a success record
   carrying the pre-move `owner`/`started` that `merged` had cleared.

2. **`hook_env`'s docstring** says `TCW_ITEM_PATH`/`TCW_RESOLUTION` are omitted
   only for a transition that has neither, "so a script can test for presence".
   `_complete` has both and passes neither, so a `complete` binding testing
   `[ -n "$TCW_ITEM_PATH" ]` concludes there is no item folder.

3. **`resolve_store` rules 1 and 2 `except ValueError: pass`.** A federation
   config error in a node that also declares a repository is reported as "not
   provisioned; run `tcw provision`" — which then succeeds and leaves the store
   still unopenable. Rule 4 re-raises correctly; 1 and 2 do not. Pre-existing in
   shape, but `_extended_component_roots` now raises for many more reasons, so
   far more real errors land in this hole.

4. **`describe_location`** runs `git cat-file -e` without `capture_output`, so
   `tcw work show` prints a raw `fatal: Not a valid object name` immediately
   before the friendly sentence explaining it.

5. **The `cycle in connected-projects` guard in `_visit` can never fire.**
   `self._cache[config_path] = cfg` is set before any recursion, so the
   `config_path in self._cache` branch returns first. Cycles are caught only by
   `_validate_cycles`, which walks `children` edges; a cycle expressed purely
   through `parent` edges is caught incidentally by reciprocity. Pre-existing;
   the comments around it are load-bearing and wrong.
