# Keep a child whose state.yaml cannot be read visible to its parent's completion gate

A child item records its parent in `state.yaml` (`parent:`). When that file
cannot be read — malformed YAML, not UTF-8, not a regular file — the board reads
it as `{}` (`FsWorkStore._safe_yaml`), so the child loses its `parent:` and falls
back to folder nesting. `_relation_snapshot` then no longer counts it, and the
parent can be completed past an unresolved child. True for a YAML syntax error
before 2026-09-26-keep-one-unreadable-state-yaml-or-artifact-from-breaking-the-board-or-an-item-s-detail;
that item widened it to the other kinds of damage (which used to crash every
read, so failed closed).

Likely direction: have the completion gate refuse while any item's state could
not be read, naming it — `tcw validate` already reports the damaged file.

## Origin

Raised by the Opus advisor and the code review of
2026-09-26-keep-one-unreadable-state-yaml-or-artifact-from-breaking-the-board-or-an-item-s-detail
(2026-09-29), placed out of that item's scope.

## References

- tcw/store/fs.py `_safe_yaml`, `_parent_slug`, `_relation_snapshot`, `complete`
