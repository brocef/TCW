# Tidy the loose ends the combined v2.5.1 review found in children and config messages

Three small, non-blocking findings from the combined review of the v2.5.1 batch:

1. `_complete`'s open-children refusal (tcw/work/cli.py, before the merge-back)
   copies the message of `WorkStore.require_nothing_open_beneath` word for word,
   and the CLI never calls that method, though its docstring says it is shared
   with callers that refuse before merging. Build the CLI message from one place,
   or correct the docstring, before the two copies drift apart.
2. The leftover-store-config report names the old file by a relative path and
   `tcw-config.yaml` by an absolute one. Use the same form for both.
3. `_start` calls the filesystem store's private `_tracked_source(bare)` outside
   any `try`. When git tracks two folders with the same slug it raises
   `ValueError`, and the user sees a traceback. It only runs when recovering an
   interrupted claim. Catch it, and consider whether the CLI should reach a
   private filesystem method at all (docs/lifecycle/abstraction.md).

## Origin

Combined review of the v2.5.1 batch, 2026-09-21.
