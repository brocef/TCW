# Report a missing taxonomy path as a validate problem instead of crashing inside the capabilities check

With `docs/taxonomy` and `docs/capabilities` both present and `taxonomy.path`
pointing at a directory that does not exist, `tcw validate` crashes with a
traceback instead of listing a problem. The chain: validate.py `_run_check("capabilities")`
→ `FsCapabilitiesStore.check` → `_taxonomy()` (tcw/store/fs.py around line 3016)
→ `FsTaxonomyStore.open`, which raises `StoreLocationUnusable`. `_run_check`
guards only the capabilities store's own open, not the taxonomy open inside
`check()`. It should report a problem line like every other open failure.

## Origin

Found by the code review of
2026-09-21-report-a-leftover-pre-2-5-0-store-config-file-instead-of-silently-dropping-its-extends.
It predates that item. Bug.

## References

- tcw/validate.py `_run_check`
- tcw/store/fs.py `FsCapabilitiesStore._taxonomy`
