# Let a broken extends reach the user instead of find_node answering no node here

`find_node` (tcw/store/fs.py, around line 218) passes `StoreNotProvisioned` and
`StoreDeclarationError` through, but turns any other `ValueError` from opening a
taxonomy or capabilities store into `None`. The command then says "no tcw
taxonomy node here — run `tcw init`". A node with a bad `extends` (an unknown
project ID, a cycle, a legacy alias map) is sent to `tcw init`, which the comment
beside that code calls a hazard: it would scaffold a second, empty store beside
the real one. Every taxonomy and capabilities command is affected.

Change: let a federation error from opening the store reach the user with its own
message, as the two provisioning errors already do. First find out which
`ValueError`s the `except` exists to catch, so the ones that really mean "no
store here" keep answering `None`.

## Origin

Found while implementing
2026-09-21-report-a-leftover-pre-2-5-0-store-config-file-instead-of-silently-dropping-its-extends
(acceptance criterion 10 could be met only partly for the check commands because
of this). The behavior predates that item. Bug.

## References

- tcw/store/fs.py `find_node`: the `except ValueError: return None`
- The leftover-config item's outcome.md, "Spec gap", which has the reproduction
