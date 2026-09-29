## Fixed

- A blocker naming an item of this node as `<status>/<slug>` or as
  `<own-project-id>/<slug>` is recorded as `slug:` rather than external text.
  `WorkStore._entry_for` tries the new `_local_forms(ref)` (status prefix in the
  base store; own-id through `resolve_qualified_work_ref` in `FsWorkStore`), so
  such a reference now meets the self-block and cycle checks — `--blocked-by
  pa/<itself>` is refused instead of blocking the item forever — and resolves
  like any local blocker. Entries already stored as text are not rewritten.
