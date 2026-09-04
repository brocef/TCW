# Outcome — Comments and docstrings that describe behaviour the code does not have

## What shipped

Five findings, each a comment a reader would have relied on. Where the comment
described the better behaviour, the **code** changed to match it; where the
comment was simply false about a mechanism, it was replaced with an accurate
account rather than deleted.

1. **`WorkStore.transition` requires the item again.** The fallback record was
   introduced when auto-delete still lived inside the store; the removal moved
   out to the CLI and the comment stayed, so it claimed a deletion the store
   deliberately never performs — `pending_deletion`'s own docstring says as
   much. With that premise gone, the only way `get()` returns None there is a
   *concurrent* removal, and the fabricated record turned that into an apparent
   success carrying the pre-move `owner` and `started` the method had just
   cleared. Restored to `self._require(slug)`, with the reasoning written down.
   `dataclasses.replace` was its last user and is no longer imported.

2. **Every transition passes `TCW_ITEM_PATH`; the resolving ones pass
   `TCW_RESOLUTION`.** The docstring said the two are omitted only when the
   transition has neither, naming `start` and `submit` — but `start`, `submit`
   and `rework` all have an item folder, and `complete` had *both* a folder and
   a resolution and passed neither, so a binding testing
   `[ -n "$TCW_ITEM_PATH" ]` concluded there was no item folder on the one
   transition most likely to want it. All six call sites now pass what they
   have. The docstring gains the fact that makes `pre` and `post` differ: the
   path is where the item is *at the moment the hook runs*.

3. **`StoreLocationUnusable`** — a new `ValueError` subclass on the abstract
   interface, meaning "the place I was told to look does not hold one of these".
   The resolution ladder's rules 1 and 2 fall through only on it. They caught
   every `ValueError`, so a store that was *present* and failed to open — a
   federation error, a legacy `extends` map — was reported as "not provisioned;
   run `tcw provision`", which then succeeded and left the store exactly as
   unopenable. Pre-existing in shape, and much wider since
   `_extended_component_stores` gained many more reasons to raise. Both
   `_open_at` implementations now raise it for their location checks, and
   nothing else changed about what they check.

4. **`describe_location` was already fixed.** The finding described
   `git cat-file -e` running without `capture_output`, printing a raw
   `fatal: Not a valid object name` before the friendly sentence. The delete-
   safety item replaced that probe with a captured `ls-tree`, and
   `test_show_says_when_a_recorded_commit_is_gone` covers it. Verified rather
   than assumed: there is no `cat-file` left in `tcw/`.

5. **The dead cycle guard in `_visit` is removed.** `self._cache[config_path]`
   is written before the config's own edges are walked, so a cycle returns on
   the cache hit above and the `_visiting` branch could never fire; the
   `_visiting` set had no other user. `_validate_cycles` gains a docstring
   saying it is the only thing that reports a cycle, that it walks `children`
   alone *because* every connection is declared from both sides — walking
   `parent` too makes every legitimate reciprocal pair a two-cycle, which is
   what the attempt to do so demonstrated — and that a cycle expressed purely
   through `parent` edges therefore surfaces through the reciprocity check
   instead. That is the honest description of the coverage, rather than a claim
   that one check sees everything.

## Tests

```
$ python -m pytest -q -p no:randomly tests/
4 failed, 2341 passed in 349.63s (0:05:49)
```

The four are environmental and unrelated: three `chmod`-based tests that cannot
fail as root, and one wheel build this container's patched setuptools refuses
under `--no-build-isolation`.

Three new tests, each confirmed to fail against the previous code:

- `tests/test_retention.py::test_every_transition_gives_a_hook_the_item_path` —
  binds a recording `pre` command to `start`, `submit`, `rework` and `complete`,
  drives the item through all four, and asserts each saw the item's own folder
  and that only `complete` saw a resolution;
- `…::test_a_transition_over_a_concurrently_removed_item_says_so` — removes the
  folder from inside `_effect_transition` and asserts the transition raises
  rather than fabricating a record;
- `tests/test_store_provisioning.py::test_a_federation_error_is_not_reported_as_unprovisioned`
  — a present capabilities store with a legacy `extends` map in a node that also
  declares a repository, asserting the real error surfaces and `tcw provision`
  is not suggested; with a companion asserting the other half still works, since
  a rule that stops falling through breaks the declaration if it stops too much.

## Autonomous decisions

Codex is not installed in this container, so the two-advisor rule could not be
met; no external consult was made on this item. Each finding named the defect
precisely enough that the choice was between two readings of the same code, and
both were settled by making the change and reading the result.

1. **Whether `_validate_cycles` should walk `parent` edges too.** Decided by
   trying it: it made every legitimate reciprocal pair report a two-cycle, which
   is the answer to why it walks one direction. The finding's observation stands
   — a pure-`parent` cycle is caught incidentally, by reciprocity — but the fix
   is to write that down, not to double-count every edge.
2. **Whether to delete the `_visit` guard or make it live.** Deleted. Making it
   live would mean checking `_visiting` before the cache, which would turn a
   diamond — a project reachable by two routes, which is normal — into a
   reported cycle. Termination is already guaranteed by the cache.
3. **Where `StoreLocationUnusable` belongs.** On `tcw/store/base.py` with its
   siblings, as a `ValueError`, because "the place I was told to look holds no
   store" is a question any adapter answers and is categorically different from
   "what I found there is misconfigured" — and because every existing
   `except ValueError` around a store `open()` has to keep working, which is the
   stated reason `StoreNotProvisioned` and `StoreDeclarationError` are
   `ValueError`s as well.

## Notes

Findings 1, 2 and 5 are the same failure mode at three ages: a comment that was
true when written and survived the change that falsified it. The auto-delete
fallback outlived the removal moving to the CLI; `hook_env`'s list of transitions
outlived the transitions gaining folders; the `_visit` guard outlived the cache
being populated earlier. None of the three was detectable by reading the comment
alone — each needed the reader to ask what the surrounding code now does.
