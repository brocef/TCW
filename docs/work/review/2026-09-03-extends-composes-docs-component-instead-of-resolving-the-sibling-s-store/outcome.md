# Outcome — `extends` resolves the sibling's store

## What shipped

Three planned tasks, one commit.

1. **The substitution.** `_extended_component_roots` now opens the extended
   project's store through `STORE_CLASSES[component].open(...)` and takes its
   `root`, instead of composing `docs/<component>`. The self-extension check
   moved ahead of it — identity, not storage. `StoreNotProvisioned` and
   `StoreDeclarationError` are re-raised with the project id prefixed;
   everything else becomes `project '<id>' has no <component> component`.
2. **The existing federation suites pass unmodified**, which is criterion 3.
3. **Documentation:** changelog and release notes. README and the component
   skills were checked and say nothing about where an extended tree is looked
   for, so nothing there fired. No capability declared any of it.

## Tests

```
$ python -m pytest -q tests/ -p no:randomly
5 failed, 2306 passed in 353.15s (0:05:53)
```

The four environmental failures plus the timing-sensitive grandchild test.

Three new tests in `tests/test_capabilities_federation.py`: a sibling that moved
its tree with `capabilities.path` is extended and its capability is inherited; a
sibling with no component names the project; a sibling whose tree is declared and
unprovisioned reports the url and `tcw provision`.

## Corrections

- **The fix caused infinite recursion, and the cycle guard had to move.**
  Opening a sibling's tree store resolves *its* `extends`, so a federation cycle
  recurred instead of being reported — `test_check_federation_cycle` caught it
  immediately. The existing guard was a set of store roots checked *after*
  `_extended_component_roots` returned, which is too late once that function
  opens stores. It is now a set of **project** node roots, threaded through
  `open` → `resolve_store` → `_open_at` → the constructor, and checked before any
  store is touched. That is also the more honest guard: a cycle in `extends` is a
  cycle among projects.
- **The `is_dir()` check had to stay, on the resolved root.** Rule 4 of the
  ladder validates nothing for a component's bare default, so a project with no
  tree resolves to a path that is simply absent rather than raising. Correct for
  that project's own store, wrong to federate from. The plan assumed the
  resolution would raise; it does not, and the directory check is what makes
  criterion 5 true.
- **The threading touched more signatures than planned.** `resolve_store`,
  both `_open_at` implementations, both tree-store constructors and
  `FsTreeStore.open` all gained a private `_seen_nodes`. The work store accepts
  and ignores it, which keeps one ladder rather than forking it.

## Notes

The read-path cost the plan asked about: `resolve_store` reads one config file
where the old code did one `is_dir()`, and federation roots are resolved once per
store open rather than per entry. `tcw validate` on this repository is unchanged
to the eye — it was under a second before and after. Not a measured benchmark,
and it does not need to be at this magnitude.
